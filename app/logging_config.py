import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from app.config import settings

def setup_logging() -> None:
    log_path = Path(settings.LOG_DIR) / settings.LOG_FILE
    log_path.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for h in list(root.handlers):
        root.removeHandler(h)

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    root.addHandler(ch)
    fh = RotatingFileHandler(log_path,
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(fmt)
    root.addHandler(fh)

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
