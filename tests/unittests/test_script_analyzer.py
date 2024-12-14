import unittest
from unittest import mock
from unittest.mock import patch, Mock
from src.baish.script_analyzer import (
    analyze_script, 
    analyze_chunks,
    calculate_chunk_size
)
from src.baish.config import Config, LLMConfig
from pathlib import Path
import tempfile
from io import StringIO

class TestScriptAnalyzer(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.mock_config = Config(llms={
            'test_llm': LLMConfig(
                name='test-llm',
                provider='groq',
                model='test-model',
                api_key='test-key',
                token_limit=4000
            )
        })
        self.mock_config.default_llm = 'test_llm'
        self.mock_config.baish_dir = Path(self.temp_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)

    @patch('src.baish.script_analyzer.create_security_chain')
    @patch('src.baish.script_analyzer.analyze_script_with_yara')
    @patch('src.baish.script_analyzer.detect_file_type')
    async def test_analyze_script_shell(self, mock_detect, mock_yara, mock_security):
        mock_detect.return_value = {"mime_type": "text/x-shellscript", "is_text": True}
        mock_security.return_value.arun.return_value = {
            "harm_score": 3,
            "complexity_score": 2,
            "requires_root": False,
            "explanation": "Safe script"
        }
        mock_yara.return_value = (False, None)
        
        results = await analyze_script("#!/bin/bash\necho 'hello'")
        self.assertEqual(results["file_type"], "text/x-shellscript")
        self.assertEqual(results["security_analysis"]["harm_score"], 3)
        self.assertEqual(results["security_analysis"]["complexity_score"], 2)
        self.assertFalse(results["security_analysis"]["requires_root"])
        self.assertFalse(results["yara_matches"])

    @patch('src.baish.script_analyzer.create_security_chain')
    @patch('src.baish.script_analyzer.analyze_script_with_yara')
    @patch('src.baish.script_analyzer.detect_file_type')
    async def test_analyze_script_binary(self, mock_detect, mock_yara, mock_security):
        mock_detect.return_value = {"mime_type": "application/octet-stream", "is_text": False}
        mock_security.return_value.arun.return_value = {
            "harm_score": 1,
            "complexity_score": 1,
            "requires_root": False,
            "explanation": "Binary file"
        }
        mock_yara.return_value = (False, None)
        
        results = await analyze_script(b'\x7fELF\x02\x01\x01'.decode('latin1'))
        self.assertEqual(results["file_type"], "application/octet-stream")
        self.assertEqual(results["security_analysis"]["harm_score"], 1)
        self.assertFalse(results["yara_matches"])

    @patch('src.baish.script_analyzer.create_security_chain')
    @patch('src.baish.script_analyzer.analyze_script_with_yara')
    @patch('src.baish.script_analyzer.detect_file_type')
    async def test_analyze_script_yara_match(self, mock_detect, mock_yara, mock_security):
        mock_detect.return_value = {"mime_type": "text/x-shellscript", "is_text": True}
        mock_security.return_value.arun.return_value = {
            "harm_score": 8,
            "complexity_score": 5,
            "requires_root": True,
            "explanation": "Potentially malicious"
        }
        mock_yara.return_value = (True, {
            "rules": ["MaliciousRule"],
            "tags": ["malicious"],
            "explanations": ["Matched malicious pattern"]
        })
        
        results = await analyze_script("rm -rf /")
        self.assertEqual(results["file_type"], "text/x-shellscript")
        self.assertTrue(results["yara_matches"])
        self.assertEqual(results["security_analysis"]["harm_score"], 8)
        self.assertTrue(results["security_analysis"]["requires_root"])

    @patch('src.baish.script_analyzer.create_security_chain')
    @patch('src.baish.script_analyzer.analyze_script_with_yara')
    @patch('src.baish.script_analyzer.detect_file_type')
    async def test_analyze_script_large_content(self, mock_detect, mock_yara, mock_security):
        mock_detect.return_value = {"mime_type": "text/x-shellscript", "is_text": True}
        mock_security.return_value.arun.return_value = {
            "harm_score": 4,
            "complexity_score": 6,
            "requires_root": False,
            "explanation": "Large script analysis"
        }
        mock_yara.return_value = (False, None)
        
        # Create a large script that would trigger chunking
        large_script = "echo 'hello'\n" * 1000
        results = await analyze_script(large_script)
        
        self.assertEqual(results["file_type"], "text/x-shellscript")
        self.assertEqual(results["security_analysis"]["harm_score"], 4)
        self.assertEqual(results["security_analysis"]["complexity_score"], 6)
        self.assertFalse(results["yara_matches"])

    @patch('src.baish.script_analyzer.create_security_chain')
    @patch('src.baish.script_analyzer.analyze_script_with_yara')
    @patch('src.baish.script_analyzer.detect_file_type')
    async def test_analyze_script_with_cli_provider(self, mock_detect, mock_yara, mock_security):
        mock_detect.return_value = {"mime_type": "text/x-python", "is_text": True}
        mock_security.return_value.arun.return_value = {
            "harm_score": 2,
            "complexity_score": 3,
            "requires_root": False,
            "explanation": "Python script analysis"
        }
        mock_yara.return_value = (False, None)
        
        results = await analyze_script("print('hello')", cli_provider="alternate-llm")
        
        self.assertEqual(results["file_type"], "text/x-python")
        self.assertEqual(self.mock_config.default_llm, "alternate-llm")

    @patch('src.baish.script_analyzer.create_security_chain')
    @patch('src.baish.script_analyzer.analyze_script_with_yara')
    @patch('src.baish.script_analyzer.detect_file_type')
    async def test_analyze_script_with_debug(self, mock_detect, mock_yara, mock_security):
        mock_detect.return_value = {"mime_type": "text/x-shellscript", "is_text": True}
        mock_security.return_value.arun.return_value = {
            "harm_score": 1,
            "complexity_score": 2,
            "requires_root": False,
            "explanation": "Debug mode analysis"
        }
        mock_yara.return_value = (False, None)
        
        results = await analyze_script("echo 'debug'", debug=True)
        
        self.assertEqual(results["file_type"], "text/x-shellscript")
        self.assertEqual(results["security_analysis"]["harm_score"], 1)

    @patch('src.baish.script_analyzer.create_security_chain')
    @patch('src.baish.script_analyzer.analyze_script_with_yara')
    @patch('src.baish.script_analyzer.detect_file_type')
    async def test_analyze_script_invalid_response(self, mock_detect, mock_yara, mock_security):
        mock_detect.return_value = {"mime_type": "text/x-shellscript", "is_text": True}
        mock_security.return_value.arun.return_value = "invalid response"
        mock_yara.return_value = (False, None)
        
        results = await analyze_script("echo 'test'")
        
        self.assertEqual(results["error"], "Invalid response format")

    @patch('src.baish.script_analyzer.create_security_chain')
    @patch('src.baish.script_analyzer.analyze_script_with_yara')
    @patch('src.baish.script_analyzer.detect_file_type')
    async def test_analyze_script_missing_config(self, mock_detect, mock_yara, mock_security):
        mock_detect.return_value = {"mime_type": "text/x-shellscript", "is_text": True}
        mock_security.return_value.arun.return_value = {
            "harm_score": 1,
            "complexity_score": 2,
            "requires_root": False,
            "explanation": "Test"
        }
        mock_yara.return_value = (False, None)
        
        results = await analyze_script("echo 'test'", config=None)
        self.assertEqual(results["file_type"], "text/x-shellscript")

    @patch('src.baish.script_analyzer.create_security_chain')
    @patch('src.baish.script_analyzer.analyze_script_with_yara')
    @patch('src.baish.script_analyzer.detect_file_type')
    async def test_analyze_script_with_results_manager(self, mock_detect, mock_yara, mock_security):
        mock_results_mgr = Mock()
        mock_results_mgr.current_id = "test_id"
        mock_results_mgr.current_date = "2024-01-01"
        
        mock_detect.return_value = {"mime_type": "text/x-shellscript", "is_text": True}
        mock_security.return_value.arun.return_value = {
            "harm_score": 1,
            "complexity_score": 2,
            "requires_root": False,
            "explanation": "Test"
        }
        mock_yara.return_value = (False, None)
        
        results = await analyze_script("echo 'test'", results_mgr=mock_results_mgr)
        self.assertEqual(self.mock_config.current_id, "test_id")
        self.assertEqual(self.mock_config.current_date, "2024-01-01")

    @patch('src.baish.script_analyzer.chunk_content')
    @patch('src.baish.script_analyzer.count_tokens')
    async def test_analyze_script_chunking(self, mock_count_tokens, mock_chunk_content):
        mock_count_tokens.return_value = 5000  # Force chunking
        mock_chunk_content.return_value = ["chunk1", "chunk2"]
        
        with patch('src.baish.script_analyzer.get_llm') as mock_get_llm:
            mock_llm = Mock()
            mock_llm.invoke.side_effect = [
                {"harm_score": 3, "complexity_score": 2, "requires_root": False, "explanation": "Part 1"},
                {"harm_score": 5, "complexity_score": 4, "requires_root": True, "explanation": "Part 2"}
            ]
            mock_get_llm.return_value = mock_llm
            
            results = await analyze_script("large script")
            self.assertTrue(mock_chunk_content.called)
            self.assertEqual(results["security_analysis"]["harm_score"], 5)

    def test_calculate_chunk_size(self):
        with patch('src.baish.script_analyzer.MAP_PROMPT') as mock_prompt, \
             patch('src.baish.script_analyzer.count_tokens') as mock_count:
            
            mock_prompt.format_prompt.return_value = "test prompt"
            mock_count.return_value = 500  # Mock token count for prompt
            
            result = calculate_chunk_size(self.mock_config)
            
            # Verify result matches expected calculation:
            # token_limit (4000) - prompt_tokens (500) - response_reserve (1000) = 2500
            expected = 4000 - 500 - 1000
            self.assertEqual(result, expected)
            self.assertIsInstance(result, int)
            self.assertGreater(result, 0)

    @patch('src.baish.script_analyzer.create_security_chain')
    async def test_analyze_script_chain_exception(self, mock_chain):
        mock_chain.return_value.invoke.side_effect = Exception("Chain error")
        results = await analyze_script("echo 'test'")
        self.assertEqual(results["error"], "Chain error")

    async def test_analyze_chunks_empty_chunks(self):
        results = await analyze_chunks([], "text/x-shellscript", self.mock_config, None, False)
        self.assertEqual(results[2], "Failed to analyze script chunks")

    @patch('src.baish.script_analyzer.get_llm')
    async def test_analyze_chunks_map_phase_error(self, mock_get_llm):
        mock_llm = Mock()
        mock_llm.invoke.side_effect = Exception("Map error")
        mock_get_llm.return_value = mock_llm
        
        results = await analyze_chunks(["chunk"], "text/x-shellscript", self.mock_config, None, True)
        self.assertEqual(results[2], "Failed to analyze script chunks")

    @patch('src.baish.script_analyzer.get_llm')
    async def test_analyze_chunks_reduce_phase_error(self, mock_get_llm):
        mock_llm = Mock()
        mock_llm.invoke.side_effect = [
            {"harm_score": 3, "complexity_score": 2, "requires_root": False},
            Exception("Reduce error")
        ]
        mock_get_llm.return_value = mock_llm
        
        results = await analyze_chunks(["chunk"], "text/x-shellscript", self.mock_config, None, True)
        self.assertEqual(results[2], "Reduce error")

    @patch('src.baish.script_analyzer.detect_file_type')
    async def test_analyze_script_markdown_file(self, mock_detect):
        mock_detect.return_value = {
            "mime_type": "text/markdown",
            "is_text": True
        }
        result = await analyze_script("# Markdown content")
        self.assertEqual(result[0], 1)  # harm_score
        self.assertEqual(result[1], 1)  # complexity_score
        self.assertIn("Non-script file detected", result[2])

    async def test_analyze_chunks_invalid_map_result(self):
        with patch('src.baish.script_analyzer.get_llm') as mock_get_llm:
            mock_llm = Mock()
            mock_llm.invoke.return_value = "invalid result"  # Not a dict
            mock_get_llm.return_value = mock_llm
            
            result = await analyze_chunks(
                ["chunk1"], 
                "text/x-python", 
                self.mock_config, 
                None, 
                True
            )
            self.assertEqual(result[2], "Failed to analyze script chunks")

    async def test_analyze_chunks_missing_harm_score(self):
        with patch('src.baish.script_analyzer.get_llm') as mock_get_llm:
            mock_llm = Mock()
            mock_llm.invoke.return_value = {"no_harm_score": 5}  # Missing harm_score
            mock_get_llm.return_value = mock_llm
            
            result = await analyze_chunks(
                ["chunk1"], 
                "text/x-python", 
                self.mock_config, 
                None, 
                True
            )
            self.assertEqual(result[2], "Failed to analyze script chunks")

    async def test_analyze_chunks_reduce_invalid_format(self):
        with patch('src.baish.script_analyzer.get_llm') as mock_get_llm:
            mock_llm = Mock()
            mock_llm.invoke.side_effect = [
                {"harm_score": 3, "complexity_score": 2, "requires_root": False},
                "invalid reduce result"
            ]
            mock_get_llm.return_value = mock_llm
            
            result = await analyze_chunks(
                ["chunk1"], 
                "text/x-python", 
                self.mock_config, 
                None, 
                True
            )
            self.assertEqual(result[2], str(ValueError("Expected dict, got <class 'str'>: invalid reduce result")))

if __name__ == '__main__':
    unittest.main() 