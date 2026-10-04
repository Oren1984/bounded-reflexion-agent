def format_table(rows):
    if not rows:
        return ""
    if any(len(row) != len(rows[0]) for row in rows):
        raise ValueError("rows have different lengths")
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]
    lines = [
        " | ".join(cell.ljust(w) for cell, w in zip(row, widths, strict=True)).rstrip()
        for row in rows
    ]
    lines.insert(1, "-+-".join("-" * w for w in widths))
    return "\n".join(lines)
