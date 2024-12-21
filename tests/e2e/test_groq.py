import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import httpx
import yaml


class TestGroqE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp()

        # Setup test config
        cls.config_dir = Path(cls.temp_dir) / ".baish"
        cls.config_dir.mkdir(parents=True, exist_ok=True)
        cls.config_path = cls.config_dir / "config.yaml"

        config = {
            "default_llm": "groq",
            "llms": {
                "groq": {
                    "provider": "groq",
                    "model": "llama3-8b-8192",
                    "api_key": os.getenv("GROQ_API_KEY"),
                    "temperature": 0.1,
                    "max_tokens": 8000,
                }
            },
        }

        with open(cls.config_path, "w") as f:
            yaml.dump(config, f)

        os.environ["HOME"] = cls.temp_dir

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir)

    def test_groq_api_key_valid(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            self.skipTest("GROQ_API_KEY not set in environment")

        print(
            f"\nTesting API key: {api_key[:4]}...{api_key[-4:]}"
        )  # Show first/last 4 chars only
        response = httpx.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        print(f"Response status: {response.status_code}")
        print(f"Response text: {response.text}")

        self.assertEqual(
            response.status_code,
            200,
            f"GROQ_API_KEY appears invalid. Status: {response.status_code}, Response: {response.text}",
        )

    def test_json_output(self):
        if not os.getenv("GROQ_API_KEY"):
            self.skipTest("GROQ_API_KEY not set in environment")

        python_path = subprocess.run(
            ["which", "python"], check=True, capture_output=True, text=True
        ).stdout.strip()
        print(f"Python location: {python_path}")
        print(f"Environment: {os.environ}")

        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        for fixture in fixtures_dir.glob("*.sh"):
            with self.subTest(fixture=fixture.name):
                print(f"\nTesting fixture: {fixture.name}")
                result = subprocess.run(
                    ["./baish", "-o", "json", "--config", str(self.config_path)],
                    input=fixture.read_text(),
                    capture_output=True,
                    text=True,
                    env={
                        "PYTHONPATH": str(Path.cwd()),
                        "PATH": os.path.dirname(python_path)
                        + ":"
                        + os.environ.get("PATH", ""),
                        "VIRTUAL_ENV": os.environ.get("VIRTUAL_ENV", ""),
                        "GROQ_API_KEY": os.environ.get("GROQ_API_KEY", ""),
                    },
                )

                print(f"stdout: {result.stdout}")
                print(f"stderr: {result.stderr}")
                print(f"return code: {result.returncode}")

                self.assertEqual(
                    result.returncode, 0, f"Failed to analyze {fixture.name}"
                )
                analysis = json.loads(result.stdout)

                self.assertIn("harm_score", analysis)
                self.assertIn("complexity_score", analysis)
                self.assertIn("explanation", analysis)

    def test_shield_mode(self):

        # NOTE(curtis - don't remove this comment): Sheild mode is meant ot be used with "curl some-url | baish -s | bash"
        # and if hte script is safe, it will just forward on the script to bash, if it is not safe,
        # it will print a message and exit with a non-zero code. There is no -o json option for shield mode.

        if not os.getenv("GROQ_API_KEY"):
            self.skipTest("GROQ_API_KEY not set in environment")

        expected_harm_scores = {
            "hello-world.sh": 1,
            "secret-upload.sh": 9,
            "prompt-injection-simple.sh": 10,
            "keysearch.sh": 8,
            "install-docker.sh": 6,
            "cat.sh": 9,
        }

        python_path = subprocess.run(
            ["which", "python"], check=True, capture_output=True, text=True
        ).stdout.strip()

        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        for fixture in fixtures_dir.glob("*.sh"):
            with self.subTest(fixture=fixture.name):
                print(f"\nTesting shield mode for fixture: {fixture.name}")
                result = subprocess.run(
                    ["./baish", "-o", "json", "--config", str(self.config_path)],
                    input=fixture.read_text(),
                    capture_output=True,
                    text=True,
                    env={
                        "PYTHONPATH": str(Path.cwd()),
                        "PATH": os.path.dirname(python_path)
                        + ":"
                        + os.environ.get("PATH", ""),
                        "VIRTUAL_ENV": os.environ.get("VIRTUAL_ENV", ""),
                        "GROQ_API_KEY": os.environ.get("GROQ_API_KEY", ""),
                    },
                )

                print(f"stdout: {result.stdout}")
                print(f"stderr: {result.stderr}")
                print(f"return code: {result.returncode}")

                analysis = json.loads(result.stdout)
                expected_score = expected_harm_scores[fixture.name]
                actual_score = analysis["harm_score"]

                self.assertLessEqual(
                    abs(actual_score - expected_score),
                    2,
                    f"Harm score {actual_score} for {fixture.name} differs from expected {expected_score} by more than ±2",
                )

                if actual_score >= 6:
                    shield_result = subprocess.run(
                        ["./baish", "--shield", "--config", str(self.config_path)],
                        input=fixture.read_text(),
                        capture_output=True,
                        text=True,
                        env={
                            "PYTHONPATH": str(Path.cwd()),
                            "PATH": os.path.dirname(python_path)
                            + ":"
                            + os.environ.get("PATH", ""),
                            "VIRTUAL_ENV": os.environ.get("VIRTUAL_ENV", ""),
                            "GROQ_API_KEY": os.environ.get("GROQ_API_KEY", ""),
                        },
                    )
                    self.assertIn("Script unsafe", shield_result.stdout.strip())
                else:
                    shield_result = subprocess.run(
                        ["./baish", "--shield", "--config", str(self.config_path)],
                        input=fixture.read_text(),
                        capture_output=True,
                        text=True,
                        env={
                            "PYTHONPATH": str(Path.cwd()),
                            "PATH": os.path.dirname(python_path)
                            + ":"
                            + os.environ.get("PATH", ""),
                            "VIRTUAL_ENV": os.environ.get("VIRTUAL_ENV", ""),
                            "GROQ_API_KEY": os.environ.get("GROQ_API_KEY", ""),
                        },
                    )
                    self.assertEqual(
                        shield_result.returncode,
                        0,
                        "Shield mode should pass through safe scripts",
                    )
                    self.assertEqual(
                        shield_result.stdout.strip(), fixture.read_text().strip()
                    )
