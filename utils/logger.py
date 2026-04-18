"""
utils/logger.py — Centralised rotating-file logger for PRISM
=============================================================
All PRISM modules must obtain their logger via ``get_logger(__name__)``
rather than calling ``logging.getLogger`` directly.  This ensures that
every logger automatically inherits:

  • A ``StreamHandler`` to stdout (coloured via ``rich`` if available).
  • A ``RotatingFileHandler`` writing to the path set in ``config.LOG_FILE``.
  • A consistent timestamped format.

The root logger is configured once on first import; subsequent calls to
``get_logger`` return the standard named child loggers unchanged.

Usage
-----
    from utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Stream connected for %s", machine_id)
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Pulled lazily to avoid circular imports at module-load time
# ---------------------------------------------------------------------------
_LOG_LEVEL: Optional[str] = None
_LOG_FILE: Optional[str] = None
_configured: bool = False

# Log record format (human‑friendly + machine‑parseable)
_FMT = "%(asctime)s | %(levelname)-8s | %(name)-35s | %(message)s"
_DATE_FMT = "%Y-%m-%d %H:%M:%S"


def _ensure_configured() -> None:
    """Configure the root logger once; no-op on subsequent calls."""
    global _configured, _LOG_LEVEL, _LOG_FILE

    if _configured:
        return

    # Import here to avoid circular deps at collection time
    try:
        from config import LOG_FILE, LOG_LEVEL  # type: ignore[import]

        _LOG_LEVEL = LOG_LEVEL
        _LOG_FILE = LOG_FILE
    except ImportError:
        _LOG_LEVEL = "INFO"
        _LOG_FILE = "prism.log"

    level = getattr(logging, (_LOG_LEVEL or "INFO").upper(), logging.INFO)
    formatter = logging.Formatter(_FMT, datefmt=_DATE_FMT)

    root = logging.getLogger()
    # Only add handlers if none exist yet (prevents duplication when
    # the module is reimported inside tests).
    if not root.handlers:
        root.setLevel(level)

        # ── Console handler — plain UTF-8 stream (avoids CP1252 issues on Windows) ─
        import io
        # Wrap stdout in a UTF-8 writer so Unicode log chars don't crash on Windows
        utf8_stream = io.TextIOWrapper(
            sys.stdout.buffer if hasattr(sys.stdout, 'buffer') else sys.stdout,
            encoding='utf-8',
            errors='replace',
            line_buffering=True,
        ) if hasattr(sys.stdout, 'buffer') else sys.stdout
        ch = logging.StreamHandler(utf8_stream)
        ch.setFormatter(formatter)
        ch.setLevel(level)
        root.addHandler(ch)

        # ── Rotating file handler ──────────────────────────────────────
        log_path = Path(_LOG_FILE or "prism.log")
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            fh = logging.handlers.RotatingFileHandler(
                log_path,
                maxBytes=10 * 1024 * 1024,   # 10 MB per file
                backupCount=5,
                encoding="utf-8",
            )
            fh.setFormatter(formatter)
            fh.setLevel(logging.DEBUG)        # file always captures DEBUG+
            root.addHandler(fh)
        except OSError as exc:
            # Non‑fatal — carry on without file logging
            logging.warning("Could not open log file %s: %s", log_path, exc)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger, configuring the root logger on first call.

    Parameters
    ----------
    name : str
        Typically ``__name__`` of the calling module.

    Returns
    -------
    logging.Logger
        A fully configured child logger ready for use.

    Examples
    --------
    >>> from utils.logger import get_logger
    >>> log = get_logger(__name__)
    >>> log.info("hello from %s", __name__)
    """
    _ensure_configured()
    return logging.getLogger(name)
