VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def roman_to_int(s: str) -> int:
    if not s or any(ch not in VALUES for ch in s):
        raise ValueError("invalid Roman numeral")
    total = 0
    for ch, nxt in zip(s, s[1:] + " ", strict=True):
        value = VALUES[ch]
        total += -value if nxt in VALUES and VALUES[nxt] > value else value
    return total
