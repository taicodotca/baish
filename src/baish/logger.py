import sys

from loguru import logger


def setup_logger(debug: bool = False):
    """Configure loguru logger for console and syslog"""
    # Remove default handler
    logger.remove()

    # Add stderr handler with appropriate level
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="DEBUG" if debug else "INFO",
        colorize=True,
    )

    return logger
