import argparse
import datetime
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, Tuple

from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner

from .__version__ import __version__
from .config import BaishConfigError, Config
from .llm import APIError
from .logger import setup_logger
from .main import analyze_script, console, save_results_json, save_script
from .results_manager import ResultsManager


class BaishCLI:
    def __init__(self, args: argparse.Namespace):
        try:
            self.args = args
            self.logger = setup_logger(debug=args.debug)
            self.config = (
                Config.load(config_file=args.config) if args.config else Config.load()
            )
            self.date_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            self.unique_id = str(uuid.uuid4())[:8]
            self.results_mgr = ResultsManager(self.config)
            self.results_mgr.current_id = self.unique_id
            self.results_mgr.current_date = self.date_str
            self.logger.debug(f"Starting analysis session {self.unique_id}")
        except ValueError as e:
            if "Config file not found" in str(e):
                self.logger.error(f"Config file not found: {str(e)}")
                sys.exit(1)
            raise

    def run(self) -> int:
        try:
            if os.geteuid() == 0:
                self.logger.error("Running as root is not allowed for security reasons")
                return 1

            self.logger.debug("Reading input script")
            script = self._read_input()
            if not script:
                return 1

            self.logger.debug("Analyzing script")
            results = self._analyze_script(script)
            if not results:
                return 1

            if self.args.shield:
                self.logger.debug("Running in shield mode")
                return self._handle_shield_mode(script, results)

            return self._output_results(results)

        except Exception as e:
            return self._handle_error(e)

    def _read_input(self) -> str | None:
        try:
            if self.args.input:
                with open(self.args.input, "rb") as f:
                    raw_data = f.read()
            else:
                if sys.stdin.isatty():
                    self._error("No input provided", show_usage=True)
                    return None
                raw_data = sys.stdin.buffer.read()

            if self._is_binary(raw_data):
                self._error("Input appears to be binary data")
                return None

            return raw_data.decode("utf-8")
        except (FileNotFoundError, UnicodeDecodeError) as e:
            self._error(f"Error reading input: {e}")
            return None

    def _analyze_script(self, script: str) -> Dict[str, Any] | None:
        try:
            script_path = save_script(
                script,
                config=self.config,
                date_str=self.date_str,
                unique_id=self.unique_id,
            )

            if self.args.output == "json":
                results = analyze_script(
                    script,
                    self.results_mgr,
                    False,
                    config=self.config,
                    cli_provider=self.args.llm,
                )
            else:
                if not self.args.shield:
                    with Live(
                        Spinner("dots", text="Analyzing file..."), refresh_per_second=10
                    ):
                        results = analyze_script(
                            script,
                            self.results_mgr,
                            self.args.debug,
                            config=self.config,
                            cli_provider=self.args.llm,
                        )
                else:
                    results = analyze_script(
                        script,
                        self.results_mgr,
                        self.args.debug,
                        config=self.config,
                        cli_provider=self.args.llm,
                    )

            if results[0] == 0 and results[1] == 0:  # If harm and complexity are 0
                self._error(results[2])
                return None

            harm_score, complexity_score, explanation, requires_root, file_type = (
                results
            )
            return {
                "timestamp": datetime.datetime.now().isoformat(),
                "script_path": str(script_path),
                "harm_score": harm_score,
                "complexity_score": complexity_score,
                "uses_root": requires_root,
                "file_type": file_type,
                "explanation": explanation,
                "saved_script_path": str(script_path),
            }
        except Exception as e:
            self._error(f"Error analyzing script: {e}")
            return None

    def _handle_shield_mode(self, script: str, results: Dict[str, Any]) -> int:
        if results["harm_score"] >= 6 or not isinstance(
            results["harm_score"], (int, float)
        ):
            print('echo "Script unsafe: High risk score detected"')
            return 1
        print(script)
        return 0

    def _output_results(self, results: Dict[str, Any]) -> int:
        if (
            results["harm_score"] == 1
            and results["complexity_score"] == 1
            and results["explanation"].startswith("Error")
        ):
            self._error(results["explanation"])
            return 1

        # Save results to JSON file
        save_results_json(
            results,
            Path(results["script_path"]),
            self.date_str,
            self.unique_id,
            self.config,
        )

        if self.args.output == "json":
            print(json.dumps(results, indent=2))
        else:
            self._display_rich_panel(results)
        return 0

    def _display_rich_panel(self, results: Dict[str, Any]) -> None:
        harm_color = self._get_harm_color(results["harm_score"])
        console.print(
            Panel.fit(
                f"[bold]Analysis Results - {os.path.basename(results['script_path'])}[/bold]\n\n"
                f"Harm Score:       [{harm_color}]{results['harm_score']}/10[/{harm_color}] {self._get_bar_graph(results['harm_score'])}\n"
                f"Complexity Score: [blue]{results['complexity_score']}/10[/blue] {self._get_bar_graph(results['complexity_score'])}\n"
                f"Uses Root:    {results['uses_root']}\n\n"
                f"[bold]File type:[/bold] {results['file_type']}\n\n"
                f"[bold]Explanation:[/bold]\n{results['explanation']}\n\n"
                f"[bold]Script saved to:[/bold] {results['script_path']}\n"
                f"[bold]To execute, run:[/bold] bash {results['script_path']}\n\n"
                "[yellow]⚠️  AI-based analysis is not perfect and should not be considered a complete security audit. "
                "For complete trust in a script, you should analyze it in detail yourself. Baish has downloaded "
                "the script so you can review and execute it in your own environment.[/yellow]",
                title="Baish - Bash AI Shield",
            )
        )

    @staticmethod
    def _is_binary(data: bytes) -> bool:
        binary_sigs = [
            b"\x89PNG",  # PNG
            b"GIF8",  # GIF
            b"\xFF\xD8\xFF",  # JPEG
            b"SQLite",  # SQLite DB
            b"PK\x03\x04",  # ZIP
            bytes([0]),  # Null bytes
        ]
        return (
            any(data.startswith(sig) for sig in binary_sigs) or b"\x00" in data[:1024]
        )

    @staticmethod
    def _get_harm_color(harm_score: int | str) -> str:
        if harm_score == "unknown":
            return "yellow"
        return "green" if harm_score <= 3 else "yellow" if harm_score <= 6 else "red"

    @staticmethod
    def _get_bar_graph(score: int | str, width: int = 20) -> str:
        if score == "unknown":
            return "[yellow]?[/yellow]" + "─" * (width - 1)
        filled = int((score / 10) * width)
        empty = width - filled
        return f"[{'red' if score > 6 else 'yellow' if score > 3 else 'green'}]{'█' * filled}{'─' * empty}[/]"

    def _error(self, message: str, show_usage: bool = False) -> None:
        if self.args.shield:
            print(f'echo "Error: {message}"')
        elif self.args.output == "json":
            print(json.dumps({"error": str(message)}))
        else:
            console.print(f"[red]Error: {message}[/red]")
            if show_usage:
                console.print("Usage: cat script.sh | baish")

    def _handle_error(self, error: Exception) -> int:
        if isinstance(error, APIError):
            self.results_mgr.error(f"API Error: {error}")
            self._error(str(error))
        else:
            self.results_mgr.exception("Unexpected error during script analysis")
            self._error(f"Error analyzing script: {error}")
        return 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Baish - Bash AI Shield: Analyze shell scripts for security risks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  curl https://example.com/script.sh | baish
  cat script.sh | baish
  baish < script.sh
  curl https://example.com/script.sh | baish -s | bash  # shield mode
        """,
    )

    parser.add_argument("--version", action="version", version=f"Baish {__version__}")
    parser.add_argument(
        "--config", help="Path to config file (default: ~/.baish/config.yaml)"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument(
        "-s",
        "--shield",
        action="store_true",
        help="Shield mode - output safe script or error",
    )
    parser.add_argument("--input", type=str, help="Input file path")
    parser.add_argument(
        "-o",
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format (text or json)",
    )

    # First parse to get config
    args, _ = parser.parse_known_args()

    # Only load config if we're not showing version or help
    if (
        "--version" not in sys.argv
        and "-h" not in sys.argv
        and "--help" not in sys.argv
    ):
        config = Config.load(args.config) if args.config else Config.load()
        parser.add_argument(
            "--llm", choices=list(config.llms.keys()), help="Choose LLM configuration"
        )

    return parser.parse_args()


def main():
    try:
        args = parse_args()
        cli = BaishCLI(args)
        cli.run()
    except BaishConfigError:
        sys.exit(1)  # Error already logged by BaishConfigError
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
