Implement `format_table(rows: list[list[str]]) -> str`.

Render rows as a plain-text table. The first row is the header. Columns are separated by
`" | "` and each column is as wide as its widest cell. Under the header there is a separator
line made of dashes, with `"-+-"` between columns. Raise `ValueError` if rows have different
lengths.

Example for `[["name", "qty"], ["apple", "3"]]`:

    name  | qty
    ------+----
    apple | 3
