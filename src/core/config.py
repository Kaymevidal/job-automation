import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

APP_NAME = "Job Automation Pro"
APP_VERSION = "0.1.0"

DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
LOG_DIR = Path(os.getenv("LOG_DIR", BASE_DIR / "logs"))
COVER_LETTERS_DIR = DATA_DIR / "cover_letters"
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
COVER_LETTERS_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'job_automation.db'}")

OLLAMA_HOST = os.getenv("OLLAMA_BASE_URL", os.getenv("OLLAMA_HOST", "http://localhost:11434"))
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma2:9b")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
