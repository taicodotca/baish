import unittest
from unittest.mock import Mock, patch

from src.baish.file_analyzer import detect_file_type, evaluate_file_type


class TestFileAnalyzer(unittest.TestCase):
    def test_detect_file_type_shell_script(self):
        content = "#!/bin/bash\necho 'hello'"
        result = detect_file_type(content)
        self.assertEqual(result["mime_type"], "text/x-shellscript")
        self.assertTrue(result["is_text"])

    def test_detect_file_type_python(self):
        content = "#!/usr/bin/env python3\nprint('hello')"
        result = detect_file_type(content)
        self.assertEqual(result["mime_type"], "text/x-script.python")
        self.assertTrue(result["is_text"])

    def test_detect_file_type_binary(self):
        content = b"\x7fELF\x02\x01\x01".decode("latin1")  # ELF binary
        result = detect_file_type(content)
        self.assertEqual(result["mime_type"], "application/octet-stream")
        self.assertFalse(result["is_text"])

    def test_evaluate_file_type(self):
        content = "#!/bin/bash\necho 'hello'"
        mime_type = evaluate_file_type(content)
        self.assertEqual(mime_type, "text/x-shellscript")

    def test_detect_file_type_empty(self):
        content = ""
        result = detect_file_type(content)
        self.assertEqual(result["mime_type"], "application/x-empty")
        self.assertTrue(result["is_text"])


if __name__ == "__main__":
    unittest.main()
