import re
import unicodedata


def slugify(title: str) -> str:
    text = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    text = text.lower().replace("'", "")
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")
