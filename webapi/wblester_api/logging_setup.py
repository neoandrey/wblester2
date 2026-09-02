"""Central logging configuration for the API.

Every request handler, blueprint and the Gunicorn process share one rotating
log file so the /logs status page (and the diagnostics endpoint behind it)
can show the health of the service and its dependencies from a single place.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FORMAT = "%(asctime)s|%(levelname)s|%(name)s|%(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_CONFIGURED = False


def log_dir() -> Path:
    """Directory holding the rotating log file (created on demand)."""
    path = Path(
        os.environ.get("LOG_DIR")
        or Path(__file__).resolve().parent.parent / "logs"
    )
    path.mkdir(parents=True, exist_ok=True)
    return path


def log_file() -> Path:
    return log_dir() / "wblester.log"


def configure_logging(level: str | None = None) -> None:
    """Idempotently attach a rotating file handler to the root logger."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    root = logging.getLogger()
    root.setLevel(getattr(logging, (level or os.environ.get(
        "LOG_LEVEL", "INFO")).upper(), logging.INFO))
    formatter = logging.Formatter(LOG_FORMAT, datefmt=_DATE_FORMAT)

    file_handler = RotatingFileHandler(
        log_file(), maxBytes=1_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    # Quiet down the noisiest third-party loggers a little.
    for name in ("werkzeug",):
        logging.getLogger(name).setLevel(logging.WARNING)

    _CONFIGURED = True


def read_recent_logs(limit: int = 300) -> list[dict]:
    """Tail the active log file (+ newest rotated backup) into structured rows.

    Rows are returned oldest -> newest with ``ts``, ``level`` and ``message``
    keys; unparsable lines are passed through with level ``INFO``.
    """
    candidates = [log_file()]
    rotated = log_file().with_suffix(log_file().suffix + ".1")
    if rotated.exists():
        candidates.insert(0, rotated)

    lines: list[str] = []
    for candidate in candidates:
        try:
            with open(candidate, "r", encoding="utf-8", errors="replace") as fh:
                lines.extend(fh.readlines())
        except OSError:  # pragma: no cover - file just may not exist yet
            continue

    rows: list[dict] = []
    for raw in lines[-limit:]:
        parts = raw.rstrip("\n").split("|", 3)
        if len(parts) == 4:
            rows.append(
                {"ts": parts[0], "level": parts[1].upper(), "logger": parts[2],
                 "message": parts[3]}
            )
        else:
            rows.append({"ts": "", "level": "INFO", "logger": "",
                         "message": raw.rstrip("\n")})
    return rows
