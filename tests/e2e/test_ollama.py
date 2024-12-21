import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

import docker
import yaml


class TestOllamaE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create temp directory first
        cls.temp_dir = tempfile.mkdtemp()

        # Debug Python location
        subprocess.run(["which", "python"], check=True)
        subprocess.run(["which", "python3"], check=True)
        subprocess.run(["env"], check=True)

        # Wait for host's Ollama API
        start_time = time.time()
        while time.time() - start_time < 30:
            try:
                result = subprocess.run(
                    ["curl", "-s", "http://localhost:11434/api/tags"],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    break
            except Exception:
                time.sleep(1)

        # Setup test config in temp directory
        cls.config_dir = Path(cls.temp_dir) / ".baish"
        cls.config_dir.mkdir(parents=True, exist_ok=True)
        cls.config_path = cls.config_dir / "config.yaml"

        config = {
            "default_llm": "llama3",
            "llms": {
                "llama3": {
                    "provider": "ollama",
                    "model": "llama3",
                    "temperature": 0.1,
                    "token_limit": 4000,
                    "url": "http://localhost:11434",
                }
            },
        }

        with open(cls.config_path, "w") as f:
            yaml.dump(config, f)

        os.environ["HOME"] = cls.temp_dir

        # Print config content for debugging
        with open(cls.config_path) as f:
            print(f"Test config: {f.read()}")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir)

    def test_safe_script(self):
        # Add pip list debug output
        print("Installed packages:")
        subprocess.run(["pip", "list"], check=True)

        # Add model check
        print("Checking Ollama models:")
        subprocess.run(["curl", "-s", "http://localhost:11434/api/tags"], check=True)

        # Print config content for debugging
        with open(self.config_path) as f:
            print(f"Test config: {f.read()}")

        print(f"Test: {self._testMethodName}")
        print(
            f"Python location: {subprocess.run(['which', 'python'], check=True, capture_output=True, text=True).stdout.strip()}"
        )
        print(f"Environment: {os.environ}")

        # Use absolute path for config
        config_path = os.path.abspath(self.config_path)

        script_path = Path(__file__).parent.parent / "fixtures" / "hello-world.sh"
        result = subprocess.run(
            ["./baish", "--config", config_path, "--debug"],
            input=script_path.read_text(),
            capture_output=True,
            text=True,
            env={"PYTHONPATH": str(Path.cwd())},
        )
        print(f"Output: {result.stdout}")
        print(f"Error: {result.stderr}")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Harm Score:", result.stdout)
        self.assertIn("1/10", result.stdout)

    def test_unsafe_script(self):
        print(f"Test: {self._testMethodName}")
        print(
            f"Python location: {subprocess.run(['which', 'python'], check=True, capture_output=True, text=True).stdout.strip()}"
        )
        print(f"Environment: {os.environ}")

        script_path = Path(__file__).parent.parent / "fixtures" / "secret-upload.sh"
        result = subprocess.run(
            ["./baish", "--config", os.path.abspath(self.config_path), "-s"],
            input=script_path.read_text(),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Script unsafe:", result.stdout)

    def test_docker_install_script(self):
        print(f"Test: {self._testMethodName}")
        print(
            f"Python location: {subprocess.run(['which', 'python'], check=True, capture_output=True, text=True).stdout.strip()}"
        )
        print(f"Environment: {os.environ}")
        script_path = Path(__file__).parent.parent / "fixtures" / "install-docker.sh"
        result = subprocess.run(
            ["./baish", "--config", os.path.abspath(self.config_path)],
            input=script_path.read_text(),
            capture_output=True,
            text=True,
            env={"PYTHONPATH": str(Path.cwd())},
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Uses Root:    True", result.stdout)
