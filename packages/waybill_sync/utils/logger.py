"""Unified logger configuration"""
import logging
import os

from packages.waybill_sync.core.config import LOG_DIR


def setup_logger(name: str, log_file: str = None) -> logging.Logger:
    """Get a configured logger with file and console handlers.

    Args:
        name: Logger name (used for log file if log_file not specified)
        log_file: Optional specific log file path

    Returns:
        Configured logger instance
    """
    os.makedirs(LOG_DIR, exist_ok=True)
    if log_file is None:
        log_file = os.path.join(LOG_DIR, f"{name}.log")

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    log_format = "%(asctime)s %(levelname)s %(message)s"
    formatter = logging.Formatter(log_format)

    # File handler - DEBUG and above
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)

    # Console handler - INFO and above
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger
