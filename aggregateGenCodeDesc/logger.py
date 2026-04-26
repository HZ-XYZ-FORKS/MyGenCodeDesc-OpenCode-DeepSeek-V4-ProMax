import logging
import sys
from typing import Optional


DEFAULT_LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(component)s] %(message)s"

_logger: Optional[logging.Logger] = None


def configure_logger(level: str = "INFO") -> logging.Logger:
    global _logger

    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "WARN": logging.WARNING,
        "ERROR": logging.ERROR,
    }
    log_level = level_map.get(level.upper(), logging.INFO)

    logger = logging.getLogger("aggregateGenCodeDesc")
    logger.setLevel(log_level)
    logger.handlers.clear()

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(log_level)
    formatter = logging.Formatter(DEFAULT_LOG_FORMAT)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    class ComponentFilter(logging.Filter):
        def filter(self, record):
            record.component = getattr(record, "component", "core")
            return True

    logger.addFilter(ComponentFilter())

    _logger = logger
    return logger


def get_logger() -> logging.Logger:
    global _logger
    if _logger is None:
        return configure_logger("INFO")
    return _logger
