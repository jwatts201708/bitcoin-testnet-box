"""Utilities for Ghost audit logging.

This module provides a minimal subset of the functionality from the upstream
`ghost` project that is required by the tests in this kata.  The original
implementation created a new :class:`logging.FileHandler` every time
``get_logger`` was invoked which resulted in duplicate log entries.  The
implementation here mirrors the expected behaviour while ensuring a single
handler is attached to the logger.
"""

from __future__ import annotations

import logging
import os
from typing import Final

GHOST_HOME: Final[str] = os.path.join(os.path.expanduser("~"), ".ghost")

AUDIT_LOG_FILE_PATH: Final[str] = os.environ.get(
    "GHOST_AUDIT_LOG", os.path.join(GHOST_HOME, "audit.log")
)

_AUDIT_LOGGER_NAME: Final[str] = "ghost.audit"


def _ensure_parent_directory(path: str) -> None:
    """Ensure the directory for *path* exists.

    The upstream project guarantees the directory exists via a combination of
    side effects spread throughout the code base.  The tests executed for this
    kata, however, import and use the audit helpers directly which means the
    directory may not yet exist.  Creating it lazily keeps the helpers
    self-contained and avoids surprising ``FileNotFoundError`` exceptions.
    """

    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)


def get_logger() -> logging.Logger:
    """Return a configured logger for audit messages.

    The original implementation added a new ``FileHandler`` on every call which
    caused each audit message to be duplicated (and the number of duplicates grew
    with every call).  We guard the handler creation so that the logger remains
    singleton-like and only ever writes each message once.
    """

    logger = logging.getLogger(_AUDIT_LOGGER_NAME)

    if not logger.handlers:
        _ensure_parent_directory(AUDIT_LOG_FILE_PATH)
        handler = logging.FileHandler(AUDIT_LOG_FILE_PATH)
        formatter = logging.Formatter("%(asctime)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False

    return logger


def audit(storage: str, action: str, message: str) -> None:
    """Record an audit message using the shared logger."""

    logger = get_logger()
    logger.info("[%s] [%s] - %s", storage, action, message)


__all__ = ["audit", "get_logger", "AUDIT_LOG_FILE_PATH", "GHOST_HOME"]

