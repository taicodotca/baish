import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse

import yaml

from .logger import setup_logger

# Initialize logger at module level
logger = setup_logger()


class BaishConfigError(Exception):
    """Base exception for Baish configuration errors"""

    def __init__(self, message: str):
        logger.error(message)
        super().__init__(message)


@dataclass
class LLMConfig:
    name: str
    provider: str
    model: str
    api_key: Optional[str] = None
    temperature: float = 0.1
    token_limit: int = 8000
    url: Optional[str] = None

    def __post_init__(self):
        if self.provider == "ollama":
            if not self.url:
                self.url = "http://localhost:11434"
            else:
                self._validate_url(self.url)

    def _validate_url(self, url: str) -> None:
        try:
            result = urlparse(url)
            if not all([result.scheme in ["http", "https"], result.netloc]):
                raise ValueError
        except ValueError:
            raise ValueError(f"Invalid URL for Ollama provider: {url}")


@dataclass
class Config:
    llms: Dict[str, LLMConfig]
    default_llm: Optional[str] = None
    baish_dir: Path = Path.home() / ".baish"
    current_id: Optional[str] = None
    current_date: Optional[str] = None

    SUPPORTED_PROVIDERS = ["groq", "anthropic", "ollama", "openai"]

    @staticmethod
    def validate_llm_name(name: str) -> bool:
        import re

        return bool(re.match(r"^[a-zA-Z0-9_]{1,32}$", name))

    @classmethod
    def load(cls, config_file: Optional[str] = None) -> "Config":
        """Load config from file"""
        try:
            if config_file and not os.path.exists(config_file):
                raise BaishConfigError(f"Config file not found: {config_file}")

            config_path = config_file
            if not config_file:
                config_locations = [
                    os.path.expanduser("~/.baish/config.yaml"),
                    os.path.expanduser("~/.config/baish/config.yaml"),
                    "/etc/baish/config.yaml",
                ]
                config_path = next(
                    (f for f in config_locations if os.path.exists(f)), None
                )
                if not config_path:
                    raise BaishConfigError(
                        "No config file found. Create one at ~/.baish/config.yaml"
                    )

            with open(config_path) as f:
                config_data = yaml.safe_load(f) or {}

            if not config_data.get("llms"):
                raise BaishConfigError("No LLMs configured in config file")

            if not config_data.get("default_llm"):
                raise BaishConfigError("No default_llm specified in config")

            if config_data["default_llm"] not in config_data.get("llms", {}):
                raise BaishConfigError(
                    f"Default LLM '{config_data['default_llm']}' not found in config"
                )

            baish_dir = Path(config_data.get("baish_dir", Path.home() / ".baish"))
            llms_data = config_data.get("llms", {})
            configured_llms = {}

            for name, llm_data in llms_data.items():
                if not cls.validate_llm_name(name):
                    raise BaishConfigError(f"Invalid LLM name: {name}")

                provider = llm_data["provider"]
                if provider not in cls.SUPPORTED_PROVIDERS:
                    raise BaishConfigError(f"Unsupported provider: {provider}")

                api_key = llm_data.get("api_key") or os.getenv(
                    f"{provider.upper()}_API_KEY"
                )
                if not api_key and provider != "ollama":
                    raise BaishConfigError(f"No API key found for {provider}")

                configured_llms[name] = LLMConfig(
                    name=name,
                    provider=provider,
                    model=llm_data["model"],
                    api_key=api_key,
                    temperature=llm_data.get("temperature", 0.1),
                    token_limit=llm_data.get("token_limit", 4000),
                    url=llm_data.get("url"),
                )

            default_llm = config_data.get("default_llm")
            if not default_llm:
                raise BaishConfigError("No default LLM specified")

            return cls(
                llms=configured_llms, default_llm=default_llm, baish_dir=baish_dir
            )

        except BaishConfigError:
            raise  # Let the exception propagate
        except Exception as e:
            logger.error(f"Unexpected error loading config: {str(e)}")
            raise BaishConfigError(str(e))

    @property
    def llm(self) -> LLMConfig:
        """Get the current LLM configuration"""
        return self.llms[self.default_llm]
