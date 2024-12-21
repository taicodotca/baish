import json
from pathlib import Path

from .config import Config


class ResultsManager:
    def __init__(self, config: Config):
        self.log_dir = config.baish_dir / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.current_id = config.current_id
        self.current_date = config.current_date

    def write_log_entry(self, date_str: str, unique_id: str, log_entry: dict):
        if not date_str or not unique_id:
            date_str, unique_id = self.get_latest_log()
        if not date_str or not unique_id:
            return

        log_file = self.log_dir / f"{date_str}_{unique_id}_llm.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    def get_latest_log(self):
        """Get the timestamp and ID of the latest log entry"""
        if not self.current_date or not self.current_id:
            # Find the most recent log file
            log_files = list(self.log_dir.glob("*_llm.jsonl"))
            if not log_files:
                return None, None
            latest_file = max(log_files, key=lambda x: x.stat().st_mtime)
            # Parse date and ID from filename
            parts = latest_file.stem.split("_")
            if len(parts) >= 2:
                self.current_date = parts[0]
                self.current_id = parts[1]
        return self.current_date, self.current_id
