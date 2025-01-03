import sys
import tempfile
import unittest
from datetime import datetime
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch

from src.baish.cli import parse_args
from src.baish.config import Config, LLMConfig


class TestMain(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.mock_config = Config(
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
        self.mock_config.default_llm = "test-llm"
        self.mock_config.baish_dir = Path(self.temp_dir)

    def test_stdin_input(self):
        with patch("sys.stdin", StringIO("#!/bin/bash\necho test")):
            with patch("sys.argv", ["baish"]):
                args = parse_args()
                self.assertIsNone(args.input)


if __name__ == "__main__":
    unittest.main()
