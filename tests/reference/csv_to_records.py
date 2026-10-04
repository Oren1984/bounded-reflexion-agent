import csv
import re


def _convert(value: str):
    value = value.strip()
    if value == "":
        return None
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)
    return value


def csv_to_records(text: str) -> list[dict]:
    rows = [row for row in csv.reader(text.splitlines()) if row]
    if not rows:
        return []
    header = [name.strip() for name in rows[0]]
    return [dict(zip(header, map(_convert, row), strict=False)) for row in rows[1:]]
