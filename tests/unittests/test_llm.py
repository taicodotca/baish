import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, mock_open, patch
import json

from langchain_core.callbacks import BaseCallbackHandler
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama

from src.baish.config import Config, LLMConfig
from src.baish.llm import (APIError, CustomJsonParser, LLMLoggingCallback,
                           create_security_chain, get_llm)


class TestLLM(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()

        # Patch Path.home() for the entire test class
        self.home_patcher = patch("pathlib.Path.home", return_value=Path(self.temp_dir))
        self.home_patcher.start()
        self.addCleanup(self.home_patcher.stop)

        temp_path = Path(self.temp_dir)

        class TestConfig(Config):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._baish_dir = temp_path / ".baish"
                # Create necessary directories
                for subdir in ["logs", "scripts", "results"]:
                    (self._baish_dir / subdir).mkdir(parents=True, exist_ok=True)

                # Add default LLM config
                self.llms = {
                    "test-llm": LLMConfig(
                        name="test-llm",
                        provider="groq",
                        model="test-model",
                        api_key="test-key",
                        token_limit=32768,
                        temperature=0.7,
                    )
                }
                self.default_llm = "test-llm"

            @property
            def baish_dir(self):
                return self._baish_dir

            @baish_dir.setter
            def baish_dir(self, value):
                self._baish_dir = value

        self.mock_config = TestConfig(llms={})
        self.parser = CustomJsonParser()

    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir)

    def test_custom_json_parser_content_object(self):
        mock_input = Mock()
        mock_input.content = '{"key": "value"}'
        result = self.parser.invoke(mock_input)
        self.assertEqual(result, {"key": "value"})

    def test_custom_json_parser_string_input(self):
        result = self.parser.invoke('test {"key": "value"} more text')
        self.assertEqual(result, {"key": "value"})

    def test_custom_json_parser_no_json(self):
        with self.assertRaises(ValueError) as cm:
            self.parser.invoke("no json here")
        self.assertIn("No JSON found in response", str(cm.exception))

    def test_custom_json_parser_invalid_json(self):
        with self.assertRaises(ValueError) as cm:
            self.parser.invoke('{"invalid": json"}')
        self.assertIn("Failed to parse JSON", str(cm.exception))

    def test_api_error(self):
        error = APIError("TestProvider", "Test message")
        self.assertEqual(str(error), "TestProvider API Error: Test message")
        self.assertEqual(error.provider, "TestProvider")
        self.assertEqual(error.message, "Test message")

    @patch("src.baish.llm.ChatGroq", autospec=True)
    def test_get_llm_groq(self, mock_groq_class):
        result = get_llm(self.mock_config)
        mock_groq_class.assert_called_once()
        call_kwargs = mock_groq_class.call_args[1]
        self.assertEqual(call_kwargs["groq_api_key"], "test-key")
        self.assertEqual(call_kwargs["model_name"], "test-model")
        self.assertEqual(call_kwargs["temperature"], 0.7)
        self.assertIsNotNone(call_kwargs["callbacks"])

    @patch("src.baish.llm.ChatGroq", autospec=True)
    def test_get_llm_credit_balance_error(self, mock_groq_class):
        mock_groq_class.side_effect = RuntimeError("Insufficient credits")
        with self.assertRaises(APIError) as cm:
            get_llm(self.mock_config)
        self.assertIn("Insufficient credits", str(cm.exception))

    def test_create_security_chain(self):
        with patch("src.baish.llm.get_llm") as mock_get_llm:
            mock_llm = Mock()
            mock_get_llm.return_value = mock_llm
            mock_llm.create_security_chain.return_value = Mock()
            result = mock_llm.create_security_chain()
            self.assertIsNotNone(result)

    @patch("src.baish.llm.ChatOllama")
    def test_get_llm_ollama(self, mock_ollama):
        mock_ollama.return_value = "ollama_instance"
        config = Config(
            llms={
                "test": LLMConfig(
                    name="test",
                    provider="ollama",
                    model="mistral:latest",
                    temperature=0.1,
                    url="http://localhost:11434",
                )
            },
            default_llm="test",
        )

        result = get_llm(config)
        self.assertEqual(result, "ollama_instance")
        mock_ollama.assert_called_once()
        call_args = mock_ollama.call_args[1]
        self.assertEqual(call_args["model"], "mistral:latest")
        self.assertEqual(call_args["temperature"], 0.1)
        self.assertEqual(call_args["base_url"], "http://localhost:11434")
        self.assertTrue(isinstance(call_args["callbacks"], list))

    @patch("src.baish.llm.ChatOllama")
    def test_get_llm_ollama_default_url(self, mock_ollama):
        mock_ollama.return_value = "ollama_instance"
        config = Config(
            llms={
                "test": LLMConfig(
                    name="test",
                    provider="ollama",
                    model="mistral:latest",
                    temperature=0.1,
                )
            },
            default_llm="test",
        )

        result = get_llm(config)
        self.assertEqual(result, "ollama_instance")
        mock_ollama.assert_called_once()
        call_args = mock_ollama.call_args[1]
        self.assertEqual(call_args["base_url"], "http://localhost:11434")

    @patch("src.baish.llm.ChatOllama")
    def test_get_llm_ollama_custom_url(self, mock_ollama):
        config = Config(
            llms={
                "test": LLMConfig(
                    name="test",
                    provider="ollama",
                    model="mistral:latest",
                    url="http://custom:1234",
                )
            },
            default_llm="test",
        )

        get_llm(config)
        mock_ollama.assert_called_once()
        call_args = mock_ollama.call_args[1]
        self.assertEqual(call_args["base_url"], "http://custom:1234")

    @patch("src.baish.llm.ChatOllama")
    def test_get_llm_ollama_connection_error(self, mock_ollama):
        mock_ollama.side_effect = ConnectionError("Failed to connect to Ollama server")
        config = Config(
            llms={
                "test": LLMConfig(
                    name="test", provider="ollama", model="mistral:latest"
                )
            },
            default_llm="test",
        )

        with self.assertRaises(APIError) as cm:
            get_llm(config)
        self.assertIn("Failed to connect to Ollama server", str(cm.exception))

    def test_config_invalid_ollama_url(self):
        with self.assertRaises(ValueError):
            LLMConfig(
                name="test",
                provider="ollama",
                model="mistral:latest",
                url="not_a_valid_url",
            )

    @patch("os.path.exists")
    def test_load_config_ollama_from_yaml(self, mock_exists):
        mock_exists.return_value = True
        mock_config = """
llms:
  mistral:
    provider: ollama
    model: mistral:latest
    temperature: 0.1
    url: http://custom:1234
default_llm: mistral
"""
        with patch("builtins.open", mock_open(read_data=mock_config)):
            config = Config.load()
            self.assertEqual(config.llms["mistral"].url, "http://custom:1234")
            self.assertEqual(config.llms["mistral"].provider, "ollama")
            self.assertEqual(config.llms["mistral"].model, "mistral:latest")

    def test_config_ollama_url_validation(self):
        valid_urls = [
            "http://localhost:11434",
            "http://192.168.1.100:11434",
            "http://ollama.local:11434",
            "https://ollama.company.com",
        ]
        invalid_urls = ["not_a_url", "ftp://invalid.com", "http://", ":11434"]

        for url in valid_urls:
            config = LLMConfig(
                name="test", provider="ollama", model="mistral:latest", url=url
            )
            self.assertEqual(config.url, url)

        for url in invalid_urls:
            with self.assertRaises(ValueError):
                LLMConfig(
                    name="test", provider="ollama", model="mistral:latest", url=url
                )

    @patch("src.baish.llm.ChatGroq")
    def test_no_real_llm_calls(self, mock_groq):
        """Ensure no real LLM calls are made during testing"""
        mock_instance = Mock()
        mock_groq.return_value = mock_instance

        result = get_llm(self.mock_config)

        mock_groq.assert_called_once()
        self.assertEqual(result, mock_instance)

    @patch("src.baish.llm.ChatOllama")
    def test_get_llm_ollama_json_format(self, mock_ollama):
        mock_ollama.return_value = "ollama_instance"
        config = Config(
            llms={
                "test": LLMConfig(
                    name="test",
                    provider="ollama",
                    model="mistral:latest",
                    temperature=0.1,
                    url="http://localhost:11434",
                )
            },
            default_llm="test",
        )

        result = get_llm(config)
        self.assertEqual(result, "ollama_instance")
        mock_ollama.assert_called_once()
        call_args = mock_ollama.call_args[1]
        self.assertEqual(call_args["format"], "json")

    def test_parse_escaped_newlines(self):
        input_text = (
            '{\n    "harm_score": 7,\n    "complexity_score": 9,\n    "requires_root": True,\n    '
            '"explanation": "This script is designed to perform system modifications..."}'
        )

        result = self.parser.invoke(input_text)

        self.assertEqual(result["harm_score"], 7)
        self.assertEqual(result["complexity_score"], 9)
        self.assertTrue(result["requires_root"])
        self.assertIn("system modifications", result["explanation"])

    def test_parse_embedded_json(self):
        input_text = 'Some text before {\n    "harm_score": 7,\n    "complexity_score": 9\n} and after'

        result = self.parser.invoke(input_text)

        self.assertEqual(result["harm_score"], 7)
        self.assertEqual(result["complexity_score"], 9)

    def test_invalid_json(self):
        input_text = "Not JSON at all"

        with self.assertRaises(ValueError) as context:
            self.parser.invoke(input_text)

        self.assertIn("No JSON found in response", str(context.exception))

    def test_parse_single_quotes(self):
        input_text = (
            "{\n    'harm_score': 7,\n    'complexity_score': 9,\n    'requires_root': True,\n    "
            "'explanation': 'This script has single quotes'}"
        )

        result = self.parser.invoke(input_text)

        self.assertEqual(result["harm_score"], 7)
        self.assertEqual(result["complexity_score"], 9)
        self.assertTrue(result["requires_root"])
        self.assertEqual(result["explanation"], "This script has single quotes")

    def test_parse_trailing_quotes(self):
        input_text = (
            '{\n    "harm_score": 7,\n    "complexity_score": 8,\n    "requires_root": true,\n    '
            '"explanation": "Some explanation"}"'
        )  # Note the trailing quote

        result = self.parser.invoke(input_text)

        self.assertEqual(result["harm_score"], 7)
        self.assertEqual(result["complexity_score"], 8)
        self.assertTrue(result["requires_root"])
        self.assertEqual(result["explanation"], "Some explanation")

    def test_llm_logging_provider_model(self):
        """Test that provider and model are correctly logged across callbacks"""
        config = Config(llms={}, default_llm=None, baish_dir=Path(self.temp_dir))
        callback = LLMLoggingCallback(config)

        # Mock LLM start
        callback.on_llm_start(
            {"name": "TestProvider", "model_name": "test-model-v1"},
            ["test prompt"]
        )

        # Mock LLM end
        callback.on_llm_end(Mock(generations=[[Mock(text="test response")]]))

        # Mock LLM error
        callback.on_llm_error(Exception("test error"))

        # Read the log file
        log_file = list(Path(self.temp_dir).glob("logs/*_llm.jsonl"))[0]
        with open(log_file) as f:
            logs = [json.loads(line) for line in f]

        # Verify provider and model are consistent across all entries
        for log in logs:
            self.assertEqual(log["provider"], "TestProvider")
            self.assertEqual(log["model"], "test-model-v1")

        # Verify specific entries
        self.assertEqual(logs[0]["prompt"], "test prompt")
        self.assertEqual(logs[1]["response"], "test response")
        self.assertEqual(logs[2]["error"], "test error")

    def test_llm_logging_provider_model_cohere_metadata(self):
        """Test that provider and model are correctly logged with Cohere metadata"""
        config = Config(llms={}, default_llm=None, baish_dir=Path(self.temp_dir))
        callback = LLMLoggingCallback(config)

        # Mock Cohere-style LLM start with metadata
        callback.on_llm_start(
            {"name": "ChatCohere"},
            ["test prompt"],
            metadata={"ls_model_name": "command-r-plus-08-2024"}
        )

        # Mock LLM end
        callback.on_llm_end(Mock(generations=[[Mock(text="test response")]]))

        # Read the log file
        log_file = list(Path(self.temp_dir).glob("logs/*_llm.jsonl"))[0]
        with open(log_file) as f:
            logs = [json.loads(line) for line in f]

        # Verify provider and model are correctly captured
        self.assertEqual(logs[0]["provider"], "ChatCohere")
        self.assertEqual(logs[0]["model"], "command-r-plus-08-2024")
        self.assertEqual(logs[1]["provider"], "ChatCohere")
        self.assertEqual(logs[1]["model"], "command-r-plus-08-2024")


if __name__ == "__main__":
    unittest.main()
