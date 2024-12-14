# tests/e2e/test_openai.py
import unittest
import os
import tempfile
import shutil
from pathlib import Path
import yaml
import httpx
import subprocess
import json

class TestOpenAIE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp()
        
        cls.config_dir = Path(cls.temp_dir) / '.baish'
        cls.config_dir.mkdir(parents=True, exist_ok=True)
        cls.config_path = cls.config_dir / 'config.yaml'
        
        config = {
            "default_llm": "openai",
            "llms": {
                "openai": {
                    "provider": "openai",
                    "model": "gpt-4",
                    "api_key": os.getenv("OPENAI_API_KEY"),
                    "temperature": 0.1,
                    "max_tokens": 128000
                }
            }
        }
        
        with open(cls.config_path, 'w') as f:
            yaml.dump(config, f)

        os.environ['HOME'] = cls.temp_dir

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir)

    def test_openai_api_key_valid(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            self.skipTest("OPENAI_API_KEY not set in environment")
        
        print(f"\nTesting API key: {api_key[:4]}...{api_key[-4:]}")
        response = httpx.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        print(f"Response status: {response.status_code}")
        
        self.assertEqual(response.status_code, 200,
            f"OPENAI_API_KEY appears invalid. Status: {response.status_code}")

    def test_json_output(self):
        if not os.getenv("OPENAI_API_KEY"):
            self.skipTest("OPENAI_API_KEY not set in environment")
        
        python_path = subprocess.run(['which', 'python'], check=True, capture_output=True, text=True).stdout.strip()
        
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        for fixture in fixtures_dir.glob("*.sh"):
            with self.subTest(fixture=fixture.name):
                result = subprocess.run(
                    ["./baish", "-o", "json", "--config", str(self.config_path)],
                    input=fixture.read_text(),
                    capture_output=True,
                    text=True,
                    env={
                        "PYTHONPATH": str(Path.cwd()),
                        "PATH": os.path.dirname(python_path) + ":" + os.environ.get("PATH", ""),
                        "VIRTUAL_ENV": os.environ.get("VIRTUAL_ENV", ""),
                        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", "")
                    }
                )
                
                self.assertEqual(result.returncode, 0, f"Failed to analyze {fixture.name}")
                analysis = json.loads(result.stdout)
                
                self.assertIn("harm_score", analysis)
                self.assertIn("complexity_score", analysis)
                self.assertIn("explanation", analysis)

    def test_shield_mode(self):

        # NOTE(curtis - don't remove this comment): Shield mode is meant to be used with 
        # "curl some-url | baish -s | bash" and if the script is safe, it will just forward 
        # on the script to bash, if it is not safe, it will print a message and exit with a 
        # non-zero code. There is no -o json option for shield mode.

        if not os.getenv("OPENAI_API_KEY"):
            self.skipTest("OPENAI_API_KEY not set in environment")
        
        expected_harm_scores = {
            "hello-world.sh": 1,
            "secret-upload.sh": 9,
            "keysearch.sh": 8,
            "install-docker.sh": 4,
            "cat.sh": 9
        }
        
        python_path = subprocess.run(['which', 'python'], check=True, capture_output=True, text=True).stdout.strip()
        
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        for fixture in fixtures_dir.glob("*.sh"):
            if "prompt-injection" in fixture.name:
                continue
                
            with self.subTest(fixture=fixture.name):
                print(f"\nTesting fixture: {fixture.name}")
                
                # First run to get harm score
                result = subprocess.run(
                    ["./baish", "-o", "json", "--config", str(self.config_path)],
                    input=fixture.read_text(),
                    capture_output=True,
                    text=True,
                    env={
                        "PYTHONPATH": str(Path.cwd()),
                        "PATH": os.path.dirname(python_path) + ":" + os.environ.get("PATH", ""),
                        "VIRTUAL_ENV": os.environ.get("VIRTUAL_ENV", ""),
                        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", "")
                    }
                )
                
                print(f"JSON output: {result.stdout}")
                print(f"Error output: {result.stderr}")
                
                analysis = json.loads(result.stdout)
                expected_score = expected_harm_scores[fixture.name]
                actual_score = analysis["harm_score"]
                
                print(f"Expected score: {expected_score}, Actual score: {actual_score}")
                
                if actual_score >= 6:
                    print(f"Testing shield mode for harmful script")
                    shield_result = subprocess.run(
                        ["./baish", "--shield", "--config", str(self.config_path)],
                        input=fixture.read_text(),
                        capture_output=True,
                        text=True,
                        env={
                            "PYTHONPATH": str(Path.cwd()),
                            "PATH": os.path.dirname(python_path) + ":" + os.environ.get("PATH", ""),
                            "VIRTUAL_ENV": os.environ.get("VIRTUAL_ENV", ""),
                            "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", "")
                        }
                    )
                    print(f"Shield mode output: {shield_result.stdout}")
                    print(f"Shield mode error: {shield_result.stderr}")
                    print(f"Shield mode return code: {shield_result.returncode}")
                    
                    self.assertIn("Script unsafe", shield_result.stdout.strip())
                else:
                    shield_result = subprocess.run(
                        ["./baish", "--shield", "--config", str(self.config_path)],
                        input=fixture.read_text(),
                        capture_output=True,
                        text=True,
                        env={
                            "PYTHONPATH": str(Path.cwd()),
                            "PATH": os.path.dirname(python_path) + ":" + os.environ.get("PATH", ""),
                            "VIRTUAL_ENV": os.environ.get("VIRTUAL_ENV", ""),
                            "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", "")
                        }
                    )
                    self.assertEqual(shield_result.stdout.strip(), fixture.read_text().strip())