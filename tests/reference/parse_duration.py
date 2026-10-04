import re

PATTERN = re.compile(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?")


def parse_duration(text: str) -> int:
    text = text.strip()
    match = PATTERN.fullmatch(text)
    if not text or not match:
        raise ValueError(f"invalid duration: {text!r}")
    hours, minutes, seconds = (int(g or 0) for g in match.groups())
    return hours * 3600 + minutes * 60 + seconds
