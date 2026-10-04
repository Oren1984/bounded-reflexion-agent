from solution import csv_to_records


def test_basic_types():
    text = "name,age,score\nAnn,30,4.5\nBob,41,3\n"
    assert csv_to_records(text) == [
        {"name": "Ann", "age": 30, "score": 4.5},
        {"name": "Bob", "age": 41, "score": 3},
    ]


def test_int_and_float_types_are_distinct():
    record = csv_to_records("a,b\n3,3.0\n")[0]
    assert type(record["a"]) is int
    assert type(record["b"]) is float


def test_quoted_field_with_comma():
    assert csv_to_records('name,age\n"Smith, Bob",41\n') == [{"name": "Smith, Bob", "age": 41}]


def test_doubled_quotes():
    assert csv_to_records('quote\n"say ""hi"""\n') == [{"quote": 'say "hi"'}]


def test_empty_value_becomes_none():
    assert csv_to_records("a,b\n1,\n") == [{"a": 1, "b": None}]


def test_values_are_stripped():
    assert csv_to_records("a,b\n  x  , 7 \n") == [{"a": "x", "b": 7}]


def test_negative_numbers():
    assert csv_to_records("a,b\n-5,-0.5\n") == [{"a": -5, "b": -0.5}]


def test_blank_lines_skipped():
    assert csv_to_records("a\n1\n\n2\n") == [{"a": 1}, {"a": 2}]


def test_empty_text_and_header_only():
    assert csv_to_records("") == []
    assert csv_to_records("a,b\n") == []
