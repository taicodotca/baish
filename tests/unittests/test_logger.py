import unittest
from unittest.mock import patch, MagicMock
import sys
from src.baish.logger import setup_logger

class TestLogger(unittest.TestCase):
    @patch('loguru.logger.add')
    @patch('loguru.logger.remove')
    def test_setup_logger_debug_mode(self, mock_remove, mock_add):
        logger = setup_logger(debug=True)
        
        # Verify logger.remove was called
        mock_remove.assert_called_once()
        
        # Verify stderr handler was added with DEBUG level
        mock_add.assert_any_call(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
            level="DEBUG",
            colorize=True
        )

    @patch('loguru.logger.add')
    @patch('loguru.logger.remove')
    def test_setup_logger_info_mode(self, mock_remove, mock_add):
        logger = setup_logger(debug=False)
        
        # Verify logger.remove was called
        mock_remove.assert_called_once()
        
        # Verify stderr handler was added with INFO level
        mock_add.assert_any_call(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
            level="INFO",
            colorize=True
        )
        