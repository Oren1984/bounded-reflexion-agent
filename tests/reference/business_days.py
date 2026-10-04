from datetime import date, timedelta


def business_days_between(start: str, end: str) -> int:
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if last < first:
        return -business_days_between(end, start)
    days = (last - first).days
    return sum((first + timedelta(d)).weekday() < 5 for d in range(days))
