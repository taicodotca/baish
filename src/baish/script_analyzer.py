from typing import Tuple

import magic
from rich.console import Console

from .config import Config
from .content_processor import chunk_content
from .file_analyzer import detect_file_type
from .llm import CustomJsonParser, create_security_chain, get_llm
from .logger import setup_logger
from .prompts.security_map_reduce import MAP_PROMPT, REDUCE_PROMPT
from .results_manager import ResultsManager
from .token_counter import count_tokens
from .yara_checker import YaraChecker

logger = setup_logger()


def calculate_chunk_size(config: Config, debug: bool = False) -> int:
    llm_config = config.llms.get(config.default_llm)
    total_limit = llm_config.token_limit if llm_config else 4000

    empty_prompt = MAP_PROMPT.format_prompt(content="")
    prompt_tokens = count_tokens(str(empty_prompt))
    response_reserve = 1000
    chunk_size = total_limit - prompt_tokens - response_reserve

    logger.debug(
        f"Token limits - Total: {total_limit}, Prompt: {prompt_tokens}, Response: {response_reserve}, Available for chunk: {chunk_size}"
    )

    return chunk_size


def analyze_script(
    script: str,
    results_mgr: ResultsManager = None,
    debug: bool = False,
    config: Config = None,
    cli_provider: str = None,
) -> Tuple[int, int, str, bool, str]:
    if config is None:
        config = Config.load()

    if cli_provider:
        config.default_llm = cli_provider

    if results_mgr and hasattr(results_mgr, "current_id"):
        config.current_id = results_mgr.current_id
        config.current_date = results_mgr.current_date

    script_content = script.read() if hasattr(script, "read") else script
    file_info = detect_file_type(script_content)

    logger.debug(f"File type detected: {file_info}")

    # Early returns for non-scripts
    if not file_info["is_text"] or file_info["mime_type"] in [
        "text/markdown",
        "text/plain",
    ]:
        return (
            1,
            1,
            f"Non-script file detected: {file_info['mime_type']}",
            False,
            file_info["mime_type"],
        )

    # YARA check first
    yara_checker = YaraChecker()
    matched, yara_details = yara_checker.check_content(script_content)
    if matched:
        logger.debug(f"YARA match found: {yara_details}")
        return (
            10,
            10,
            " ".join(yara_details["explanations"])
            or f"Script matched security rules: {', '.join(yara_details['rules'])}",
            True,
            file_info["mime_type"],
        )

    # Check if script needs chunking
    chunk_size = calculate_chunk_size(config, debug)
    script_tokens = count_tokens(script_content)

    # For large scripts, use map-reduce
    if script_tokens > chunk_size:
        chunks = chunk_content(script_content, chunk_size=chunk_size)
        logger.debug(
            f"Script too large ({script_tokens} tokens), using map-reduce analysis"
        )
        logger.debug(f"Split into {len(chunks)} chunks")
        return analyze_chunks(
            chunks, file_info["mime_type"], config, results_mgr, debug
        )

    # For small scripts, use direct analysis
    if script_tokens < chunk_size:
        logger.debug(f"Using direct analysis (script is {script_tokens} tokens)")
        logger.debug("Sending to LLM...")
        chain = create_security_chain(config, results_mgr)
        try:
            raw_result = chain.invoke(
                {
                    "content": script_content,
                    "mime_type": file_info["mime_type"],
                    "file_type": file_info.get("file_type", "unknown"),
                    "file_type_explanation": file_info.get("explanation", ""),
                }
            )

            if not isinstance(raw_result, dict):
                raise ValueError(f"Expected dict, got {type(raw_result)}: {raw_result}")

            if "harm_score" not in raw_result:
                raise ValueError(f"Missing harm_score in response: {raw_result}")

            return (
                raw_result["harm_score"],
                raw_result["complexity_score"],
                raw_result["explanation"],
                raw_result["requires_root"],
                file_info["mime_type"],
            )
        except Exception as e:
            logger.debug(f"Error in security analysis: {str(e)}")
            logger.debug(f"Full error: {repr(e)}")
            return 0, 0, str(e), False, file_info["mime_type"]


def analyze_chunks(
    chunks: list[str],
    mime_type: str,
    config: Config,
    results_mgr: ResultsManager,
    debug: bool,
) -> Tuple[int, int, str, bool, str]:
    # Map phase - analyze each chunk
    summaries = []
    map_chain = MAP_PROMPT | get_llm(config, results_mgr) | CustomJsonParser()

    for i, chunk in enumerate(chunks):
        logger.debug(f"Analyzing chunk {i+1}/{len(chunks)}")
        logger.debug(f"Chunk size: {len(chunk)} characters")
        logger.debug("Sending chunk to LLM...")
        try:
            raw_result = map_chain.invoke(
                {
                    "content": chunk,
                    "mime_type": mime_type,
                    "file_type": "unknown",
                    "file_type_explanation": "",
                }
            )

            logger.debug(f"Raw map result: {raw_result}")

            if not isinstance(raw_result, dict):
                raise ValueError(f"Expected dict, got {type(raw_result)}: {raw_result}")

            if "harm_score" not in raw_result:
                raise ValueError(f"Missing harm_score in map result: {raw_result}")

            summaries.append(raw_result)
        except Exception as e:
            logger.debug(f"Error analyzing chunk {i+1}: {str(e)}")
            logger.debug(f"Full error: {repr(e)}")
            continue

    if not summaries:
        return 0, 0, "Failed to analyze script chunks", False, mime_type

    # Reduce phase - combine summaries
    try:
        logger.debug("Starting reduce phase...")
        logger.debug(f"Summaries to combine: {summaries}")

        reduce_chain = REDUCE_PROMPT | get_llm(config, results_mgr) | CustomJsonParser()
        raw_result = reduce_chain.invoke(
            {"summaries": "\n".join(str(s) for s in summaries)}
        )

        logger.debug(f"Raw reduce result: {raw_result}")

        if not isinstance(raw_result, dict):
            raise ValueError(f"Expected dict, got {type(raw_result)}: {raw_result}")

        if "harm_score" not in raw_result:
            raise ValueError(f"Missing harm_score in reduce result: {raw_result}")

        return (
            raw_result["harm_score"],
            raw_result["complexity_score"],
            raw_result["explanation"],
            raw_result["requires_root"],
            mime_type,
        )
    except Exception as e:
        logger.debug(f"Error combining summaries: {str(e)}")
        logger.debug(f"Full error: {repr(e)}")
        return 0, 0, str(e), False, mime_type
