from solution import validate_password


def test_valid_password():
    assert validate_password("Str0ng!pass") == []


def test_empty_fails_everything_except_whitespace():
    assert validate_password("") == ["length", "uppercase", "lowercase", "digit", "special"]


def test_order_is_fixed():
    assert validate_password("abc") == ["length", "uppercase", "digit", "special"]


def test_whitespace_rule():
    assert validate_password("Str0ng! pass") == ["whitespace"]


def test_whitespace_does_not_count_as_special():
    assert validate_password("Str0ng pass") == ["special", "whitespace"]


def test_tab_is_whitespace():
    assert validate_password("Str0ng!\tpass") == ["whitespace"]


def test_exactly_eight_characters_is_long_enough():
    assert validate_password("Aa1!aaaa") == []


def test_underscore_is_special():
    assert validate_password("Str0ng_pass") == []
