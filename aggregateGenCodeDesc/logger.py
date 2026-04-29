import logging
import sys
from typing import Optional


DEFAULT_LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(component)s] %(message)s"

_logger: Optional[logging.Logger] = None
_quiet_filter_added: bool = False


class PhaseFilter(logging.Filter):
    def filter(self, record):
        phase = getattr(record, "phase", "")
        return phase != "PROCESS"


def add_quiet_filter() -> None:
    global _quiet_filter_added
    if _quiet_filter_added:
        return
    logger = get_logger()
    logger.addFilter(PhaseFilter())
    _quiet_filter_added = True


def set_component(name: str) -> None:
    logger = get_logger()
    for f in logger.filters:
        if isinstance(f, ComponentFilter):
            f.default_component = name


def configure_logger(level: str = "INFO") -> logging.Logger:
    global _logger, _quiet_filter_added
    _quiet_filter_added = False

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
    logger.filters.clear()

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(log_level)
    handler.setFormatter(logging.Formatter(DEFAULT_LOG_FORMAT))
    logger.addHandler(handler)

    cf = ComponentFilter()
    logger.addFilter(cf)

    _logger = logger
    return logger


class ComponentFilter(logging.Filter):
    def __init__(self, name: str = ""):
        super().__init__()
        self.default_component = name

    def filter(self, record):
        if not hasattr(record, "component") or not record.component:
            record.component = self.default_component or "core"
        return True


def get_logger() -> logging.Logger:
    global _logger
    if _logger is None:
        return configure_logger("INFO")
    return _logger
