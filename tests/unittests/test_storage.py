import unittest
from unittest.mock import patch, Mock
from datetime import datetime
from src.baish.storage import save_script, save_results_json
from src.baish.config import Config
from pathlib import Path
import tempfile
import json

class TestStorage(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.mock_config = Config(llms={})
        self.mock_config.baish_dir = Path(self.temp_dir)
        
        # Create necessary directories
        for subdir in ['scripts', 'results']:
            (Path(self.temp_dir) / subdir).mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_save_script_shell(self):
        script = "#!/bin/bash\necho 'test'"
        path_str = save_script(script, self.mock_config)
        path = Path(path_str)
        
        assert path.exists()
        assert path.suffix == ".sh"
        assert path.read_text() == script

    def test_file_naming_consistency(self):
        with patch('src.baish.storage.datetime') as mock_dt:
            mock_dt.now.side_effect = [
                datetime(2024, 1, 1, 12, 0, 0, 123456),
                datetime(2024, 1, 1, 12, 0, 0, 234567)
            ]
            mock_dt.strftime = datetime.strftime
            
            name1 = Path(save_script("test1", config=self.mock_config))
            name2 = Path(save_script("test2", config=self.mock_config))
            
            self.assertNotEqual(name1.name, name2.name)

    def test_save_results_json(self):
        results = {
            "harm_score": 1,
            "complexity_score": 2,
            "explanation": "Test results"
        }
        date_str = "2024-03-14_12-00-00"
        unique_id = "test123"
        script_path = Path(self.temp_dir) / "scripts" / f"{date_str}_{unique_id}_script.sh"
        
        results_path = save_results_json(results, script_path, date_str, unique_id, self.mock_config)
        
        self.assertTrue(results_path.exists())
        self.assertEqual(results_path.name, f"{date_str}_{unique_id}_results.json")
        
        with open(results_path) as f:
            saved_results = json.load(f)
        self.assertEqual(saved_results, results)

    def test_save_script_matches_results_id(self):
        date_str = "2024-03-14_12-00-00"
        unique_id = "test123"
        
        python_script = "#!/usr/bin/env python3\nprint('test')"
        script_path = save_script(python_script, self.mock_config, date_str, unique_id)
        results_path = save_results_json({}, Path(script_path), date_str, unique_id, self.mock_config)
        
        self.assertEqual(Path(script_path).name, f"{date_str}_{unique_id}_script.py")
        self.assertEqual(results_path.name, f"{date_str}_{unique_id}_results.json") 