from datetime import datetime

from rich.console import Console

from .content_processor import chunk_content
from .file_analyzer import detect_file_type, evaluate_file_type
from .llm import create_security_chain
from .script_analyzer import analyze_script
from .storage import save_results_json, save_script

console = Console()

__all__ = [
    "analyze_script",
    "save_script",
    "save_results_json",
    "console",
    "evaluate_file_type",
    "chunk_content",
    "detect_file_type",
    "create_security_chain",
    "datetime",
]
