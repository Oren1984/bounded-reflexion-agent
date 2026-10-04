Implement `parse_duration(text: str) -> int` returning a duration in seconds.

The format is one or more `<non-negative integer><unit>` parts with units `h`, `m`, `s`,
for example `"1h30m"`, `"45s"`, `"2h5s"`. Units must appear in the order h, m, s and each
unit at most once. Leading and trailing whitespace is ignored. Anything else raises
`ValueError`.
