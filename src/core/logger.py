import sys

from loguru import logger

from src.core.config import APP_NAME, APP_VERSION, LOG_DIR, LOG_LEVEL

logger.remove()

logger.add(sys.stderr, level=LOG_LEVEL, colorize=True)

logger.add(
    LOG_DIR / "job_automation.log",
    level=LOG_LEVEL,
    rotation="10 MB",
    retention="30 days",
    encoding="utf-8",
)


def log_startup() -> None:
    logger.info(f"{APP_NAME} v{APP_VERSION} starting up")
