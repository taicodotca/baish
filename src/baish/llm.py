import datetime
import json
import re
import uuid
from typing import Any, Dict, Optional

from langchain.callbacks.base import BaseCallbackHandler
from langchain.prompts import ChatPromptTemplate
from langchain.schema.runnable import Runnable
from langchain_anthropic import ChatAnthropic
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from .config import Config
from .logger import setup_logger
from .prompts.security import PROMPT as SECURITY_PROMPT
from .results_manager import ResultsManager

# Initialize logger at module level
logger = setup_logger()


class CustomJsonParser(Runnable):
    def invoke(self, input: Any, config: Optional[Dict] = None) -> Dict:
        if hasattr(input, "content"):
            text = input.content
        else:
            text = str(input)

        if not text.strip():
            raise ValueError("Empty response from LLM")

        json_match = re.search(
            r"\{[\s\S]*?\}", text
        )  # Just match the first complete JSON object
        if json_match:
            try:
                # First try direct parsing
                json_str = json_match.group().replace("\n", " ")
                return json.loads(json_str)
            except json.JSONDecodeError:
                try:
                    # If that fails, try cleaning up the JSON
                    cleaned_json = json_match.group()
                    # Replace True/False with true/false for JSON compliance
                    cleaned_json = cleaned_json.replace("True", "true")
                    cleaned_json = cleaned_json.replace("False", "false")
                    cleaned_json = cleaned_json.replace("\\_", "_")
                    cleaned_json = cleaned_json.replace("\n", " ")
                    # Replace single quotes with double quotes
                    cleaned_json = cleaned_json.replace("'", '"')
                    # Remove any trailing quotes
                    cleaned_json = cleaned_json.rstrip('"')
                    return json.loads(cleaned_json)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Failed to parse JSON: {text}\nError: {str(e)}")
        raise ValueError(
            f"No JSON found in response, this is usually due to a short context window in the LLM provider"
        )


class LLMError(Exception):
    """Base exception for LLM-related errors"""

    pass


class APIError(LLMError):
    """Exception for API-related errors"""

    def __init__(self, provider: str, message: str):
        self.provider = provider
        self.message = message
        super().__init__(f"{provider} API Error: {message}")


class LLMLoggingCallback(BaseCallbackHandler):
    def __init__(self, config: Config):
        super().__init__()
        self.results_mgr = ResultsManager(config)
        self._current_date = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self._current_id = str(uuid.uuid4())[:8]
        self.results_mgr.current_date = self._current_date
        self.results_mgr.current_id = self._current_id

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: list[str], **kwargs: Any
    ) -> None:
        logger.debug(f"LLM Start: {self._current_date}, {self._current_id}")
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "provider": serialized.get("name", "unknown"),
            "model": serialized.get("model_name", "unknown"),
            "prompt": prompts[0] if prompts else "",
            "response": "",
            "error": None,
            "script_id": self._current_id,
        }
        self.results_mgr.write_log_entry(
            self._current_date, self._current_id, log_entry
        )

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        if hasattr(response, "generations") and response.generations:
            text = response.generations[0][0].text
        else:
            text = str(response)

        logger.debug(f"LLM Response: {text[:100]}...")
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "provider": "unknown",
            "model": "unknown",
            "prompt": "",
            "response": text,
            "error": None,
            "script_id": self._current_id,
        }
        self.results_mgr.write_log_entry(
            self._current_date, self._current_id, log_entry
        )

    def on_llm_error(self, error: Exception, **kwargs: Any) -> None:
        logger.error(f"LLM Error: {str(error)}")
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "provider": "unknown",
            "model": "unknown",
            "prompt": "",
            "response": "",
            "error": str(error),
            "script_id": self._current_id,
        }
        self.results_mgr.write_log_entry(
            self._current_date, self._current_id, log_entry
        )


def get_llm(config: Config, results_mgr: ResultsManager = None):
    """Get LLM instance based on config"""
    try:
        if not hasattr(get_llm, "_callback"):
            get_llm._callback = LLMLoggingCallback(config)

        # Use the results manager's ID if provided
        if results_mgr and hasattr(results_mgr, "current_id"):
            get_llm._callback._current_id = results_mgr.current_id
            get_llm._callback._current_date = results_mgr.current_date
            get_llm._callback.results_mgr = results_mgr

        # NOTE(curtis - don't remove): We set the context window to 4096 to support the
        # long prompt. Otherwise the prompt will be truncated and the LLM will not be
        # able to see the entire prompt including the request to return json.
        if config.llm.provider == "ollama":
            return ChatOllama(
                temperature=config.llm.temperature,
                model=config.llm.model,
                base_url=config.llm.url,
                format="json",
                num_ctx=4096,
                callbacks=[get_llm._callback],
            )
        elif config.llm.provider == "groq":
            if not config.llm.api_key:
                raise APIError(
                    "Groq", "API key not found in environment or config file"
                )
            return ChatGroq(
                temperature=config.llm.temperature,
                groq_api_key=config.llm.api_key,
                model_name=config.llm.model,
                callbacks=[get_llm._callback],
            )
        elif config.llm.provider == "anthropic":
            if not config.llm.api_key:
                raise APIError(
                    "Anthropic", "API key not found in environment or config file"
                )
            return ChatAnthropic(
                temperature=config.llm.temperature,
                anthropic_api_key=config.llm.api_key,
                model_name=config.llm.model,
                callbacks=[get_llm._callback],
            )
        elif config.llm.provider == "openai":
            if not config.llm.api_key:
                raise APIError(
                    "OpenAI", "API key not found in environment or config file"
                )
            return ChatOpenAI(
                temperature=config.llm.temperature,
                api_key=config.llm.api_key,
                model_name=config.llm.model,
                callbacks=[get_llm._callback],
            )
        raise ValueError(f"Unsupported LLM provider: {config.llm.provider}")
    except Exception as e:
        if "credit balance is too low" in str(e):
            raise APIError(
                config.llm.provider,
                "Insufficient credits. Please check your account balance.",
            )
        elif "API key" in str(e):
            raise APIError(config.llm.provider, "Invalid API key")
        raise APIError(config.llm.provider, str(e))


def create_security_chain(config: Config = None, results_mgr: ResultsManager = None):
    if config is None:
        config = Config().load()

    parser = CustomJsonParser()
    llm = get_llm(config, results_mgr)

    return SECURITY_PROMPT | llm | parser
