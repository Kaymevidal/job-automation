import re
from datetime import datetime, timezone

from src.core.constants import ExperienceLevel, WorkMode

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}
REQUEST_TIMEOUT = 15

_LEVEL_KEYWORDS = [
    ("estagio", ExperienceLevel.INTERN),
    ("trainee", ExperienceLevel.INTERN),
    ("junior", ExperienceLevel.JUNIOR),
    ("pleno", ExperienceLevel.MID),
    ("senior", ExperienceLevel.SENIOR),
    ("especialista", ExperienceLevel.LEAD),
    ("gerente", ExperienceLevel.LEAD),
    ("diretor", ExperienceLevel.LEAD),
]


def _strip_accents(text: str) -> str:
    replacements = str.maketrans("áàâãéêíóôõúçÁÀÂÃÉÊÍÓÔÕÚÇ", "aaaaeeiooouc" "AAAAEEIOOOUC")
    return text.translate(replacements)


def slugify(text: str) -> str:
    normalized = _strip_accents(text).lower().strip()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    return normalized.strip("-")


def parse_experience_level(text: str | None) -> ExperienceLevel | None:
    if not text:
        return None

    normalized = _strip_accents(text).lower()
    for keyword, level in _LEVEL_KEYWORDS:
        if keyword in normalized:
            return level
    return None


_HYBRID_KEYWORDS = ("hibrido", "hybrid")
_REMOTE_KEYWORDS = ("home office", "remoto", "remote", "trabalho remoto")


def detect_work_mode(*texts: str | None) -> WorkMode:
    normalized = _strip_accents(" ".join(t for t in texts if t)).lower()

    if any(keyword in normalized for keyword in _HYBRID_KEYWORDS):
        return WorkMode.HYBRID
    if any(keyword in normalized for keyword in _REMOTE_KEYWORDS):
        return WorkMode.REMOTE
    return WorkMode.ONSITE


def parse_br_date(text: str | None) -> datetime | None:
    if not text:
        return None

    text = text.strip().lower()
    if text in ("hoje", "ontem"):
        return datetime.now(timezone.utc)

    try:
        return datetime.strptime(text, "%d/%m/%Y").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
