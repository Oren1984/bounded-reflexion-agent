Implement `merge_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]`.

Merge overlapping intervals and return them sorted by start. Intervals that touch
(for example `(1, 2)` and `(2, 3)`) are merged. Return a list of tuples. Do not modify the
input list. Raise `ValueError` if any interval has start greater than end.
