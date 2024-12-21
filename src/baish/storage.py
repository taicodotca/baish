import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from .config import Config
from .file_analyzer import detect_file_type


def save_script(
    script: str,
    config: Optional[Config] = None,
    date_str: Optional[str] = None,
    unique_id: Optional[str] = None,
) -> str:
    if config is None:
        config = Config().load()

    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")

    if unique_id is None:
        unique_id = str(uuid.uuid4())[:8]

    scripts_dir = Path(config.baish_dir) / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)

    file_info = detect_file_type(script)
    extension = ".sh"
    if "python" in file_info["mime_type"]:
        extension = ".py"
    elif "shellscript" not in file_info["mime_type"]:
        extension = ".txt"

    filename = f"{date_str}_{unique_id}_script{extension}"
    script_path = scripts_dir / filename
    script_path.write_text(script)
    script_path.chmod(0o755)

    return str(script_path)


def save_results_json(
    results: Dict,
    script_path: Path,
    date_str: str,
    unique_id: str,
    config: Optional[Config] = None,
) -> Path:
    if config is None:
        config = Config().load()

    results_dir = Path(config.baish_dir) / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{date_str}_{unique_id}_results.json"
    results_path = results_dir / filename

    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)

    return results_path
