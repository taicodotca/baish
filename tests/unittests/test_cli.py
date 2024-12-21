import os
import shutil
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

from src.baish.__version__ import __version__
from src.baish.cli import BaishCLI, parse_args
from src.baish.config import Config, LLMConfig


class TestCLI(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()

        # Patch Path.home() for the entire test class
        self.home_patcher = patch("pathlib.Path.home", return_value=Path(self.temp_dir))
        self.home_patcher.start()
        self.addCleanup(self.home_patcher.stop)

        # Create mock config using temp directory
        class TestConfig(Config):
            def __init__(self, temp_dir):
                self._baish_dir = Path(temp_dir) / ".baish"
                # Create required directories
                for subdir in ["logs", "scripts", "results"]:
                    (self._baish_dir / subdir).mkdir(parents=True, exist_ok=True)

                # Initialize with default LLM config
                super().__init__(
                    llms={
                        "test-llm": LLMConfig(
                            name="test-llm",
                            provider="groq",
                            model="test-model",
                            api_key="test-key",
                            token_limit=32768,
                        )
                    }
                )
                self.default_llm = "test-llm"

            @property
            def baish_dir(self):
                return self._baish_dir

            @baish_dir.setter
            def baish_dir(self, value):
                self._baish_dir = value

        # Initialize test objects
        self.mock_args = Mock()
        self.mock_args.debug = False
        self.mock_args.shield = False
        self.mock_args.output = "text"
        self.mock_args.input = None
        self.mock_args.llm = None
        self.mock_args.config = None

        # Create config with temp dir
        self.mock_config = TestConfig(self.temp_dir)

        # Initialize CLI with mocks
        self.cli = BaishCLI(self.mock_args)
        self.cli.config = self.mock_config

    def tearDown(self):
        """Clean up test fixtures"""
        try:
            if hasattr(self, "temp_dir") and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass

    def test_is_binary(self):
        # Restore detailed binary tests
        self.assertTrue(self.cli._is_binary(b"\x89PNG"), "PNG detection failed")
        self.assertTrue(self.cli._is_binary(b"GIF8"), "GIF detection failed")
        self.assertTrue(self.cli._is_binary(b"\xFF\xD8\xFF"), "JPEG detection failed")
        self.assertTrue(self.cli._is_binary(b"\x00test"), "Null byte detection failed")
        self.assertFalse(
            self.cli._is_binary(b"#!/bin/bash"), "Shell script misidentified as binary"
        )

    def test_get_harm_color(self):
        """Test harm color selection for different scores"""
        cli = BaishCLI(self.mock_args)

        self.assertEqual(cli._get_harm_color(0), "green")
        self.assertEqual(cli._get_harm_color(3), "green")
        self.assertEqual(cli._get_harm_color(4), "yellow")
        self.assertEqual(cli._get_harm_color(6), "yellow")
        self.assertEqual(cli._get_harm_color(7), "red")
        self.assertEqual(cli._get_harm_color(10), "red")
        self.assertEqual(cli._get_harm_color("unknown"), "yellow")

    def test_get_bar_graph(self):
        """Test bar graph generation for different scores"""
        cli = BaishCLI(self.mock_args)

        # Test various scores
        self.assertEqual(cli._get_bar_graph(0).count("█"), 0)
        self.assertEqual(cli._get_bar_graph(5).count("█"), 10)
        self.assertEqual(cli._get_bar_graph(10).count("█"), 20)
        self.assertIn("[yellow]?[/yellow]", cli._get_bar_graph("unknown"))

    @patch("os.geteuid")
    def test_root_user(self, mock_geteuid):
        mock_geteuid.return_value = 0
        result = self.cli.run()
        self.assertEqual(result, 1, "Root user check failed")

    def test_file_input(self):
        self.mock_args.input = "test.sh"
        test_script = "echo 'test'"
        cli = BaishCLI(self.mock_args)

        with patch("builtins.open", mock_open(read_data=test_script.encode())):
            with patch("src.baish.cli.analyze_script") as mock_analyze:
                with patch("src.baish.cli.save_script") as mock_save:
                    with patch("src.baish.llm.get_llm") as mock_get_llm:
                        mock_llm = Mock()
                        mock_get_llm.return_value = mock_llm
                        mock_analyze.return_value = (
                            3,
                            2,
                            "Safe script",
                            False,
                            "text/plain",
                        )
                        mock_save.return_value = "/tmp/script.sh"
                        result = cli.run()
                        self.assertEqual(result, 0)
                        self.assertFalse(mock_llm.create.called)

    def test_json_output(self):
        self.mock_args.output = "json"
        cli = BaishCLI(self.mock_args)

        with patch("sys.stdin.isatty", return_value=False):
            with patch("sys.stdin.buffer.read", return_value=b'echo "test"'):
                with patch("src.baish.cli.analyze_script") as mock_analyze:
                    with patch("src.baish.cli.save_script") as mock_save:
                        with patch("src.baish.llm.get_llm") as mock_get_llm:
                            with patch("builtins.print") as mock_print:
                                mock_llm = Mock()
                                mock_get_llm.return_value = mock_llm
                                mock_analyze.return_value = (
                                    3,
                                    2,
                                    "Safe script",
                                    False,
                                    "text/plain",
                                )
                                mock_save.return_value = "/tmp/script.sh"
                                cli.run()

                                self.assertFalse(mock_llm.create.called)
                                call_args = mock_print.call_args[0][0]
                                self.assertIn('"harm_score": 3', call_args)
                                self.assertIn('"complexity_score": 2', call_args)
                                self.assertIn('"explanation": "Safe script"', call_args)

    def test_shield_mode(self):
        self.mock_args.shield = True
        cli = BaishCLI(self.mock_args)

        with patch("sys.stdin.isatty", return_value=False):
            with patch("sys.stdin.buffer.read", return_value=b'echo "test"'):
                with patch("src.baish.cli.analyze_script") as mock_analyze:
                    with patch("src.baish.cli.save_script") as mock_save:
                        # Test unsafe script
                        mock_analyze.return_value = (
                            8,
                            2,
                            "Unsafe script",
                            False,
                            "text/plain",
                        )
                        mock_save.return_value = "/tmp/script.sh"
                        result = cli.run()
                        self.assertEqual(result, 1)

                        # Test safe script
                        mock_analyze.return_value = (
                            3,
                            2,
                            "Safe script",
                            False,
                            "text/plain",
                        )
                        result = cli.run()
                        self.assertEqual(result, 0)

    def test_analyze_script_safe(self):
        """Test script analysis with safe content"""
        with patch("sys.stdin.isatty", return_value=False):
            with patch("sys.stdin.buffer.read", return_value=b'echo "hello"'):
                with patch("src.baish.cli.analyze_script") as mock_analyze:
                    with patch("src.baish.cli.save_script") as mock_save:
                        mock_analyze.return_value = (
                            2,
                            1,
                            "Safe script",
                            False,
                            "text/plain",
                        )
                        mock_save.return_value = "/tmp/test.sh"
                        cli = BaishCLI(self.mock_args)
                        result = cli.run()
                        self.assertEqual(result, 0)

    def test_analyze_script_invalid_response(self):
        """Test handling of invalid LLM responses"""
        with patch("src.baish.cli.analyze_script") as mock_analyze:
            mock_analyze.return_value = (
                None,
                None,
                "Error: Invalid response",
                False,
                None,
            )
            cli = BaishCLI(self.mock_args)

            with patch("sys.stdin.buffer.read", return_value=b'echo "test"'):
                result = cli.run()
                self.assertEqual(result, 1)

    def test_file_not_found(self):
        """Test handling of missing input files"""
        self.mock_args.input = "nonexistent.sh"
        cli = BaishCLI(self.mock_args)
        result = cli.run()
        self.assertEqual(result, 1)

    def test_file_naming_consistency(self):
        """Test consistent file naming across operations"""
        cli = BaishCLI(self.mock_args)
        with patch("sys.stdin.isatty", return_value=False):
            with patch("sys.stdin.buffer.read", return_value=b'echo "test"'):
                with patch("src.baish.cli.save_script") as mock_save:
                    with patch("src.baish.cli.analyze_script") as mock_analyze:
                        expected_path = f"/tmp/{cli.date_str}_{cli.unique_id}_script.sh"
                        mock_save.return_value = expected_path
                        mock_analyze.return_value = (
                            3,
                            2,
                            "Safe script",
                            False,
                            "text/plain",
                        )
                        cli.run()
                        mock_save.assert_called_once()
                        actual_script = mock_save.call_args[0][0]
                        self.assertEqual(actual_script, 'echo "test"')

    def test_panel_display(self):
        """Test panel display formatting"""
        cli = BaishCLI(self.mock_args)
        with patch("rich.console.Console.print") as mock_print:
            results = {
                "harm_score": 5,
                "complexity_score": 3,
                "explanation": "Test explanation",
                "requires_root": True,
                "mime_type": "text/x-shellscript",
                "script_path": "/tmp/test.sh",
                "script_content": "#!/bin/bash\necho test",
                "uses_root": True,
                "file_type": "shell script",
            }
            cli._output_results(results)

            panel = mock_print.call_args[0][0]
            panel_str = str(panel.renderable)
            self.assertIn("Test explanation", panel_str)
            self.assertIn("Uses Root:    True", panel_str)
            self.assertIn("[bold]File type:[/bold] shell script", panel_str)

    def test_stdin_input(self):
        """Test reading from stdin"""
        with patch("sys.stdin.isatty", return_value=False):
            with patch("sys.stdin.buffer.read", return_value=b'echo "test"'):
                with patch("src.baish.cli.analyze_script") as mock_analyze:
                    with patch("src.baish.cli.save_script") as mock_save:
                        mock_analyze.return_value = (
                            2,
                            1,
                            "Safe script",
                            False,
                            "text/plain",
                        )
                        mock_save.return_value = "/tmp/test.sh"
                        cli = BaishCLI(self.mock_args)
                        result = cli.run()
                        self.assertEqual(result, 0)

    def test_no_input(self):
        """Test handling when no input is provided"""
        with patch("sys.stdin.isatty", return_value=True):
            cli = BaishCLI(self.mock_args)
            result = cli.run()
            self.assertEqual(result, 1)

    def test_analyze_script_error(self):
        """Test handling of script analysis errors"""
        with patch("sys.stdin.isatty", return_value=False):
            with patch("sys.stdin.buffer.read", return_value=b'echo "test"'):
                with patch("src.baish.cli.analyze_script") as mock_analyze:
                    mock_analyze.side_effect = Exception("Test error")
                    cli = BaishCLI(self.mock_args)
                    result = cli.run()
                    self.assertEqual(result, 1)

    def test_json_output_matches_logs(self):
        """Test JSON output matches log content"""
        cli = BaishCLI(self.mock_args)
        cli.args.output = "json"

        # Use temporary directory instead of home dir
        with tempfile.TemporaryDirectory() as temp_dir:
            cli.config.baish_dir = Path(temp_dir)
            log_dir = cli.config.baish_dir / "logs"
            log_dir.mkdir(parents=True)

            test_script = b"#!/bin/bash\necho test"

            with patch("sys.stdin.buffer.read", return_value=test_script):
                with patch("sys.stdin.isatty", return_value=False):
                    with patch("src.baish.main.analyze_script") as mock_analyze:
                        mock_analyze.return_value = (
                            3,
                            2,
                            "Test analysis",
                            False,
                            "text/x-shellscript",
                        )
                        with patch("src.baish.main.save_script") as mock_save:
                            mock_save.return_value = str(Path(temp_dir) / "test.sh")
                            cli.run()

    def test_shield_mode_error_output(self):
        """Test shield mode error output format"""
        self.mock_args.shield = True
        cli = BaishCLI(self.mock_args)

        with patch("sys.stdin.isatty", return_value=False):
            with patch("sys.stdin.buffer.read", return_value=b'echo "test"'):
                with patch("src.baish.cli.save_script") as mock_save:
                    with patch("src.baish.cli.analyze_script") as mock_analyze:
                        with patch("builtins.print") as mock_print:
                            mock_save.return_value = "/tmp/test.sh"
                            mock_analyze.side_effect = Exception("Test error")
                            cli.run()
                            mock_print.assert_called_once_with(
                                'echo "Error: Error analyzing script: Test error"'
                            )

    def test_parse_args_config(self):
        """Test config file argument parsing"""
        with patch("sys.argv", ["baish", "--config", "custom_config.yaml"]):
            with patch("src.baish.cli.Config.load") as mock_load:
                mock_load.return_value = self.mock_config
                args = parse_args()
                self.assertEqual(args.config, "custom_config.yaml")

    @patch("src.baish.cli.Config.load")
    def test_parse_args_no_args(self, mock_load):
        """Test parsing with no arguments"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            class TestConfig(Config):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self._baish_dir = temp_path / ".baish"
                    for subdir in ["logs", "scripts", "results"]:
                        (self._baish_dir / subdir).mkdir(parents=True, exist_ok=True)

                    self.llms = {
                        "test-llm": LLMConfig(
                            name="test-llm",
                            provider="groq",
                            model="mixtral-8x7b-32768",
                            api_key="test-key",
                            token_limit=32768,
                        )
                    }
                    self.default_llm = "test-llm"

                @property
                def baish_dir(self):
                    return self._baish_dir

                @baish_dir.setter
                def baish_dir(self, value):
                    self._baish_dir = value

            mock_config = TestConfig(llms={})
            mock_load.return_value = mock_config

            with patch("sys.argv", ["baish"]):
                args = parse_args()
                self.assertIsNone(args.config)
                self.assertIsNone(args.llm)
                self.assertFalse(args.debug)

    def test_is_binary_detailed(self):
        """Test binary file detection for specific formats"""
        cli = BaishCLI(self.mock_args)
        test_cases = [
            (b"\x89PNG", True, "PNG"),
            (b"GIF8", True, "GIF"),
            (b"\xFF\xD8\xFF", True, "JPEG"),
            (b"SQLite", True, "SQLite"),
            (b"PK\x03\x04", True, "ZIP"),
            (b"#!/bin/bash", False, "Shell script"),
            (b'echo "hello"', False, "Text content"),
        ]
        for data, expected, file_type in test_cases:
            self.assertEqual(
                cli._is_binary(data), expected, f"{file_type} detection failed"
            )

    def test_get_bar_graph_edge_cases(self):
        """Test bar graph generation edge cases"""
        cli = BaishCLI(self.mock_args)

        # Test zero score
        result = cli._get_bar_graph(0)
        self.assertIn("[green]", result)
        self.assertEqual(result.count("█"), 0)

        # Test max score
        result = cli._get_bar_graph(10)
        self.assertIn("[red]", result)
        self.assertEqual(result.count("█"), 20)

        # Test unknown score
        result = cli._get_bar_graph("unknown")
        self.assertIn("[yellow]?[/yellow]", result)

    def test_parse_args_help(self):
        """Test help argument displays help text"""
        with patch("sys.argv", ["baish", "--help"]):
            with patch("argparse.ArgumentParser.print_help") as mock_help:
                with self.assertRaises(SystemExit):
                    parse_args()
                mock_help.assert_called_once()

    def test_parse_args_version(self):
        """Test version argument displays version"""
        with patch("sys.argv", ["baish", "--version"]):
            with self.assertRaises(SystemExit) as cm:
                with patch("sys.stdout", new=StringIO()) as fake_out:
                    parse_args()
            self.assertEqual(cm.exception.code, 0)
            self.assertIn(__version__, fake_out.getvalue())

    def test_parse_args_debug(self):
        """Test debug flag is properly set"""
        with patch("sys.argv", ["baish", "--debug"]):
            args = parse_args()
            self.assertTrue(args.debug)

    def test_parse_args_llm(self):
        """Test LLM selection argument"""
        with patch("sys.argv", ["baish", "--llm", "groq"]):
            with patch("src.baish.cli.Config.load") as mock_load:
                mock_config = Mock()
                mock_config.llms = {"groq": Mock()}
                mock_load.return_value = mock_config
                args = parse_args()
                self.assertEqual(args.llm, "groq")

    def test_shield_mode_no_spinner(self):
        """Test that shield mode doesn't show spinner"""
        self.mock_args.shield = True
        cli = BaishCLI(self.mock_args)

        with patch("sys.stdin.isatty", return_value=False):
            with patch("sys.stdin.buffer.read", return_value=b'echo "test"'):
                with patch("src.baish.cli.analyze_script") as mock_analyze:
                    with patch("rich.live.Live") as mock_live:
                        mock_analyze.return_value = (
                            8,
                            2,
                            "Unsafe script",
                            False,
                            "text/plain",
                        )
                        cli.run()
                        mock_live.assert_not_called()


if __name__ == "__main__":
    unittest.main()
