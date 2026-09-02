import re


def safe_filename(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", text).strip("_")[:80]


_BROKEN_MARKERS = ("[", "]", "{", "}")
_GIBBERISH_RE = re.compile(r"\b[A-Za-z0-9+/=]{25,}\b")


def looks_broken(text: str) -> bool:
    if any(marker in text for marker in _BROKEN_MARKERS):
        return True
    return bool(_GIBBERISH_RE.search(text))
