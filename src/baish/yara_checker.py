from pathlib import Path
from typing import Dict, Optional, Tuple

import yara


class YaraChecker:
    def __init__(self):
        self.rules_dir = Path(__file__).parent / "yara"
        self.compiled_rules = None
        self._load_rules()

    def _load_rules(self):
        """Load and compile all YARA rules from the rules directory"""
        rules = {}
        for rule_file in self.rules_dir.glob("*.yar"):
            rules[rule_file.stem] = str(rule_file)
        if rules:
            self.compiled_rules = yara.compile(filepaths=rules)

    def check_content(self, content: str) -> Tuple[bool, Optional[Dict]]:
        """
        Check content against YARA rules
        Returns: (matched, details)
        - matched: True if any rule matched
        - details: Dict with match details if matched, None otherwise
        """
        if not self.compiled_rules:
            return False, None

        matches = self.compiled_rules.match(data=content)
        if not matches:
            return False, None

        details = {
            "rules": [match.rule for match in matches],
            "tags": [tag for match in matches for tag in match.tags],
            "explanations": [match.meta.get("explanation", "") for match in matches],
        }
        return True, details
