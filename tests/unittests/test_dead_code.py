import unittest
from vulture import Vulture
from pathlib import Path
import os

class TestDeadCode(unittest.TestCase):
    def setUp(self):
        self.vulture = Vulture(verbose=False)
        self.project_root = Path(__file__).parent.parent
        
        # Common patterns to ignore
        self.vulture.ignore_names = [
            "setUp", "tearDown", "test_*",  # Test methods
            "return_value", "side_effect", "Mock", "MagicMock",  # Test mocks
            "run", "daemon", "name",  # Common class attributes
            "frame", "signum",  # Signal handlers
            "__version__",  # Version strings
            "clean_scripts",  # CLI commands
            "on_llm_start", "on_llm_end", "on_llm_error",  # LangChain callbacks
            "serialized", "kwargs",  # Callback parameters
            "write_log_entry"  # Internal logging method
        ]

    def test_no_dead_code_in_src(self):
        src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src')
        self.vulture.scavenge([src_path])
        
        # Filter out false positives - convert Path to string
        unused = [
            item for item in self.vulture.get_unused_code()
            if not any(p in str(item.filename) for p in ['__pycache__', '.pyc'])
        ]
        
        if unused:
            dead_code = '\n'.join(
                f"{item.filename}:{item.first_lineno}: {item.name} ({item.typ})" 
                for item in unused
            )
            self.fail(f"Dead code found:\n{dead_code}")

if __name__ == '__main__':
    unittest.main()
