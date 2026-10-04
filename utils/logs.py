"""
The single logging setup of DeepGRB, in the style of the original pipeline of Crupi et al.:

    2026-10-04 12:00:00 INFO     message

Entry points call setup_logging() once (stdout, and optionally a file in logs/); library
modules only use logging.getLogger(__name__). Helpers print the pipeline layout: a header
with the period, numbered step titles, "  -> " detail lines and step durations.
"""

import logging
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional, Sequence

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
RULE = "=" * 72
THIN_RULE = "-" * 72

log = logging.getLogger("deepgrb")


class _StdoutHandler(logging.StreamHandler):
    """Writes to the current sys.stdout (so redirections made after setup are honoured)."""

    _deepgrb_stdout = True

    def __init__(self) -> None:
        super().__init__(sys.stdout)

    @property
    def stream(self):
        return sys.stdout

    @stream.setter
    def stream(self, _value):
        pass


def setup_logging(log_file: Optional[Path] = None, level: int = logging.INFO) -> None:
    """Configures the root logger once: stdout (flushed at every line) and an optional file."""
    root = logging.getLogger()
    fmt = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    if not any(getattr(h, "_deepgrb_stdout", False) for h in root.handlers):
        out = _StdoutHandler()
        out.setFormatter(fmt)
        root.addHandler(out)
    if log_file is not None:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        if not any(isinstance(h, logging.FileHandler) and Path(h.baseFilename) == log_file.resolve() for h in root.handlers):
            fh = logging.FileHandler(log_file, encoding="utf-8")
            fh.setFormatter(fmt)
            root.addHandler(fh)
    root.setLevel(level)
    # third-party chatter
    for name in ("matplotlib", "h5py", "absl", "PIL", "numexpr", "pyswarms"):
        logging.getLogger(name).setLevel(logging.WARNING)


def ensure_logging() -> None:
    """Sets up stdout logging only if nothing is configured yet (for library code run on its own)."""
    if not logging.getLogger().handlers:
        setup_logging()


def header(lines: Sequence[str]) -> None:
    log.info(RULE)
    for line in lines:
        log.info(f"  {line}")
    log.info(RULE)


def detail(msg: str) -> None:
    log.info(f"  -> {msg}")


def summary(title: str, rows: Sequence[str]) -> None:
    log.info("")
    log.info(title)
    log.info("  " + THIN_RULE[:55])
    for r in rows:
        log.info(f"  {r}")
    log.info("  " + THIN_RULE[:55])


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f} s"
    m, s = divmod(int(round(seconds)), 60)
    h, m = divmod(m, 60)
    return f"{h}h {m:02d}m {s:02d}s" if h else f"{m}m {s:02d}s"


@contextmanager
def step(number: int, total: int, title: str) -> Iterator[None]:
    """Numbered step title and its duration."""
    log.info("")
    log.info(f"[STEP {number}/{total}] {title}")
    t0 = time.time()
    yield
    detail(f"step {number} finished in {format_duration(time.time() - t0)}")
