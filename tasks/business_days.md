Implement `business_days_between(start: str, end: str) -> int`.

Both arguments are ISO dates (`YYYY-MM-DD`). Count the weekdays (Monday to Friday) from
`start` up to but not including `end`. If `end` is before `start`, return the negative of
the count for the swapped dates. Raise `ValueError` for an invalid date. Public holidays
are not considered.
