from typing import Optional, Tuple

from magic import Magic


def evaluate_file_type(content: str) -> str:
    magic = Magic(mime=True)
    return magic.from_buffer(content)


def detect_file_type(content: str) -> dict:
    mime_type = evaluate_file_type(content)
    is_text = mime_type.startswith("text/") or (mime_type == "application/x-empty")
    return {"mime_type": mime_type, "is_text": is_text}
