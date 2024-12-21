import tempfile
import unittest
from pathlib import Path

from src.baish.config import Config, LLMConfig
from src.baish.content_processor import chunk_content


class TestContentProcessor(unittest.TestCase):
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

    def test_chunk_content_small(self):
        content = "small content"
        chunks = chunk_content(content, chunk_size=100)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], content)

    def test_chunk_content_large(self):
        content = "\n".join(["line " + str(i) for i in range(1000)])
        chunks = chunk_content(content, chunk_size=10)
        self.assertTrue(len(chunks) > 1)
        self.assertTrue(all(len(chunk.split()) <= 10 for chunk in chunks))

    def test_chunk_content_exact_size(self):
        content = "one two three four five"
        chunks = chunk_content(content, chunk_size=5)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], content)

    def test_chunk_content_newlines(self):
        content = "line1\nline2\nline3\nline4\nline5"
        chunks = chunk_content(content, chunk_size=2)
        self.assertTrue(len(chunks) > 1)
        self.assertTrue(all("\n" not in chunk[:-1] for chunk in chunks))

    def test_chunk_content_empty(self):
        content = ""
        chunks = chunk_content(content, chunk_size=100)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], content)

    def test_chunk_content_single_long_line(self):
        content = "word " * 1000
        chunk_size = 100
        chunks = chunk_content(content, chunk_size)
        self.assertTrue(len(chunks) > 1)
        self.assertTrue(all(len(chunk.split()) <= chunk_size for chunk in chunks))
