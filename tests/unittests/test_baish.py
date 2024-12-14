import unittest
from unittest.mock import patch, Mock, mock_open
from src.baish.cli import parse_args, BaishCLI
from src.baish.config import Config, BaishConfigError

class TestBaish(unittest.TestCase):
    def setUp(self):
        self.mock_config = Mock()
        self.mock_config.llms = {'test-llm': Mock()}

    @patch('pathlib.Path.exists')
    def test_config_load_no_config(self, mock_exists):
        mock_exists.return_value = False
        config = Config.load()
        self.assertIsNotNone(config)

    def test_invalid_llm_config(self):
        test_config = """
llms:
  test_llm:
    provider: invalid
    model: test
"""
        with patch('sys.argv', ['baish', '--config', 'test_config.yaml']):
            with patch('builtins.open', mock_open(read_data=test_config)):
                with patch('src.baish.config.Config.load') as mock_load:
                    mock_load.return_value = Mock(llms={})
                    args = parse_args()
                    self.assertIsNone(args.llm)

    def test_valid_llm_config(self):
        test_config = """
llms:
  test_llm:
    provider: groq
    model: test
default_llm: test_llm
"""
        with patch('sys.argv', ['baish', '--config', 'test_config.yaml', '--llm', 'test_llm']), \
             patch('builtins.open', mock_open(read_data=test_config)), \
             patch('os.path.exists', return_value=True), \
             patch('pathlib.Path.exists', return_value=True), \
             patch('gettext.translation'), \
             patch('gettext.gettext', side_effect=lambda x: x):
            args = parse_args()
            self.assertEqual(args.llm, 'test_llm')

    @patch('sys.argv', ['baish', '--help'])
    @patch('src.baish.cli.Config.load', return_value=Mock(llms={}))
    def test_parse_args_help(self, mock_config):
        with self.assertRaises(SystemExit):
            parse_args()

    @patch('sys.argv', ['baish', '--version'])
    @patch('src.baish.cli.Config.load', return_value=Mock(llms={}))
    def test_parse_args_version(self, mock_config):
        with self.assertRaises(SystemExit):
            parse_args()

    @patch('sys.argv', ['baish', '--debug'])
    @patch('src.baish.cli.Config.load', return_value=Mock(llms={}))
    def test_parse_args_debug(self, mock_config):
        args = parse_args()
        self.assertTrue(args.debug)

    @patch('sys.argv', ['baish', '--llm', 'test-llm'])
    @patch('src.baish.cli.Config.load')
    def test_parse_args_llm(self, mock_config):
        mock_config.return_value = self.mock_config
        args = parse_args()
        self.assertEqual(args.llm, 'test-llm')

    def test_config_load_empty_config(self):
        """Test loading with empty config file"""
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data="")), \
             self.assertRaises(BaishConfigError) as cm:
            Config.load()
        self.assertIn("No LLMs configured", str(cm.exception))

    def test_unsupported_llm_provider(self):
        """Test handling of unsupported LLM providers"""
        test_config = """
llms:
  test_llm:
    provider: unsupported
    model: test
"""
        with patch('builtins.open', mock_open(read_data=test_config)):
            with self.assertRaises(BaishConfigError) as cm:
                Config.load()
            self.assertIn("Unsupported provider", str(cm.exception))

    def test_config_load_no_config(self):
        """Test loading with no config file"""
        with patch('pathlib.Path.exists', return_value=False), \
             patch('os.path.exists', return_value=False), \
             self.assertRaises(BaishConfigError) as cm:
            Config.load()
        self.assertIn("No config file found", str(cm.exception))
 