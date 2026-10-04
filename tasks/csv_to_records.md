Implement `csv_to_records(text: str) -> list[dict]`.

Parse CSV text whose first line is the header and return one dict per data row.
Quoted fields may contain commas and doubled quotes (`""`). Blank lines are skipped.

Convert each value after stripping surrounding whitespace: an empty value becomes `None`,
an integer becomes `int`, a decimal number becomes `float`, anything else stays a string.
Empty text returns an empty list.
