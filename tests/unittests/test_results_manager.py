import datetime
import json
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import mock_open, patch

from src.baish.config import Config
from src.baish.results_manager import ResultsManager


class TestResultsManager(unittest.TestCase):
    @patch("uuid.uuid4", return_value=uuid.UUID("12345678123456781234567812345678"))
    @patch("builtins.open", new_callable=mock_open)
    @patch("datetime.datetime", wraps=datetime.datetime)
    def test_write_log_entry(self, mock_datetime, mock_file, mock_uuid):
        fixed_timestamp = datetime.datetime(2024, 12, 5, 11, 21, 7)
        mock_datetime.now.return_value = fixed_timestamp

        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config(llms={}, default_llm=None, baish_dir=Path(temp_dir))
            results_mgr = ResultsManager(config)

            log_entry = {
                "timestamp": fixed_timestamp.isoformat(),
                "provider": "test_provider",
                "model": "test_model",
                "prompt": "test prompt",
                "response": "test response",
                "error": None,
                "script_id": "12345678",
            }

            results_mgr.write_log_entry("2024-12-05_11-21-07", "12345678", log_entry)

            expected_filename = (
                Path(temp_dir) / "logs" / "2024-12-05_11-21-07_12345678_llm.jsonl"
            )
            mock_file.assert_called_once_with(expected_filename, "a")

            written_data = mock_file().write.call_args[0][0]
            written_entry = json.loads(written_data.strip())
            self.assertEqual(written_entry, log_entry)

    def test_log_dir_uses_config_baish_dir(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config(llms={}, default_llm=None, baish_dir=Path(temp_dir))
            results_mgr = ResultsManager(config)
            expected_log_dir = Path(temp_dir) / "logs"
            self.assertEqual(results_mgr.log_dir, expected_log_dir)
            self.assertTrue(expected_log_dir.exists())
