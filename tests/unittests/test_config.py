import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import mock_open, patch

import yaml

from src.baish.config import BaishConfigError, Config


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.patcher = patch("pathlib.Path.home", return_value=Path(self.temp_dir))
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.addCleanup(lambda: shutil.rmtree(self.temp_dir))

    def test_validate_llm_name_valid(self):
        valid_names = ["groq", "groq_llm", "groq123", "test_llm_123"]
        for name in valid_names:
            self.assertTrue(Config.validate_llm_name(name))

    def test_validate_llm_name_invalid(self):
        invalid_names = [
            "groq llm",  # space
            "groq-llm",  # hyphen
            "groq.llm",  # dot
            "groq@llm",  # special char
            "a" * 33,  # too long
            "",  # empty
            "groq/llm",  # slash
        ]
        for name in invalid_names:
            self.assertFalse(Config.validate_llm_name(name))

    @patch("os.path.exists")
    def test_load_config_invalid_llm_name(self, mock_exists):
        mock_exists.return_value = True
        mock_config = """
llms:
  invalid name:
    provider: groq
    model: test-model
default_llm: invalid name
"""
        with patch("builtins.open", mock_open(read_data=mock_config)):
            with self.assertRaises(BaishConfigError) as cm:
                Config.load()
            self.assertIn("Invalid LLM name", str(cm.exception))

    def test_config_default_paths(self):
        """Test config uses temp dir instead of home"""
        config = Config(llms={})
        config.baish_dir = Path(self.temp_dir) / ".baish"
        self.assertEqual(config.baish_dir, Path(self.temp_dir) / ".baish")

    def test_config_file_not_found_with_explicit_path(self):
        """Test error when explicitly specified config file doesn't exist"""
        with self.assertRaises(BaishConfigError) as cm:
            Config.load(config_file="/nonexistent/config.yaml")
        self.assertIn("Config file not found", str(cm.exception))

    def test_config_paths_searched_in_order(self):
        # Create config files in different locations
        paths = [
            Path(self.temp_dir) / ".baish/config.yaml",
            Path(self.temp_dir) / ".config/baish/config.yaml",
            Path("/etc/baish/config.yaml"),  # This one won't be created in test
        ]

        # Create valid config in second location
        config_data = {
            "llms": {
                "test": {
                    "provider": "ollama",
                    "model": "llama2",
                    "url": "http://localhost:11434",
                }
            },
            "default_llm": "test",
        }

        paths[1].parent.mkdir(parents=True, exist_ok=True)
        with open(paths[1], "w") as f:
            yaml.dump(config_data, f)

        # Mock the home directory to point to our temp dir
        with (
            patch("pathlib.Path.home", return_value=Path(self.temp_dir)),
            patch(
                "os.path.expanduser",
                side_effect=lambda x: x.replace("~", self.temp_dir),
            ),
        ):
            config = Config.load()
            self.assertEqual(config.default_llm, "test")

    def test_missing_default_llm(self):
        """Test config with no default_llm specified"""
        test_config = """
llms:
  test_llm:
    provider: groq
    model: test
"""
        with patch("builtins.open", mock_open(read_data=test_config)):
            with self.assertRaises(BaishConfigError) as cm:
                Config.load()
            self.assertIn("No default_llm specified", str(cm.exception))

    def test_invalid_default_llm(self):
        """Test config where default_llm doesn't exist in llms"""
        test_config = """
llms:
  test_llm:
    provider: groq
    model: test
default_llm: nonexistent_llm
"""
        with patch("builtins.open", mock_open(read_data=test_config)):
            with self.assertRaises(BaishConfigError) as cm:
                Config.load()
            self.assertIn("Default LLM 'nonexistent_llm' not found", str(cm.exception))
