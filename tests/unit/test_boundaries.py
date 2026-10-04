"""Policy checks, workspace confinement, output parsing and evaluator verdicts."""

import pytest
from conftest import REPORT_FAIL, REPORT_PASS

from bounded_reflexion.agent import parse_files
from bounded_reflexion.evaluator import evaluate
from bounded_reflexion.policies import (
    check_code,
    check_proposal,
    resolve_in_workspace,
    tree_digest,
)
from bounded_reflexion.runner import RawResult


def rules(violations):
    return {v["rule"] for v in violations}


def test_only_solution_file_may_be_written():
    assert check_proposal({"solution.py": "x = 1\n"}) == []
    assert rules(check_proposal({"solution.py": "x = 1\n", "conftest.py": ""})) == {
        "write_outside_allowlist"
    }


@pytest.mark.parametrize(
    "code, rule",
    [
        ("import os", "forbidden_import"),
        ("from subprocess import run", "forbidden_import"),
        ("import os.path as p", "forbidden_import"),
        ("import io", "forbidden_import"),
        ("data = open('/etc/passwd').read()", "forbidden_call"),
        ("eval('1+1')", "forbidden_call"),
        ("f = __import__('os')", "forbidden_call"),
        ("x = ().__class__.__bases__", "forbidden_attribute"),
    ],
)
def test_forbidden_code_is_flagged(code, rule):
    assert rule in rules(check_code(code))


def test_ordinary_code_is_allowed():
    code = (
        "import re\nfrom decimal import Decimal\n\n"
        "class Box:\n    def __init__(self):\n        super().__init__()\n\n"
        "def f(x):\n    return re.sub('a', 'b', str(Decimal(x)))\n"
    )
    assert check_code(code) == []


def test_unparseable_code_is_left_to_the_evaluator():
    assert check_code("def broken(:") == []


@pytest.mark.parametrize(
    "path", ["../x.py", "a/../../x.py", "/etc/x.py", "C:\\x.py", "..\\x.py", "\\\\host\\x.py"]
)
def test_paths_outside_workspace_are_rejected(tmp_path, path):
    assert resolve_in_workspace(tmp_path, path) is None


def test_paths_inside_workspace_resolve(tmp_path):
    assert resolve_in_workspace(tmp_path, "pkg/solution.py") == tmp_path.resolve() / "pkg/solution.py"


def test_tree_digest_detects_changes(tmp_path):
    (tmp_path / "test_solution.py").write_text("assert True\n")
    before = tree_digest(tmp_path)
    assert tree_digest(tmp_path) == before
    (tmp_path / "test_solution.py").write_text("assert True  # changed\n")
    assert tree_digest(tmp_path) != before


def test_parse_files():
    reply = 'text\n<file path="solution.py">\n```python\nx = 1\n```\n</file>\n<file path="b.py">\ny\n</file>'
    assert parse_files(reply) == {"solution.py": "x = 1\n", "b.py": "y\n"}
    assert parse_files("no blocks here") == {}


def test_evaluator_pass_and_fail():
    passed = evaluate(RawResult(0, "", REPORT_PASS, False, 0.5))
    assert passed["passed"] and passed["tests_passed"] == passed["tests_total"] == 2
    failed = evaluate(RawResult(1, "", REPORT_FAIL, False, 0.5))
    assert not failed["passed"] and failed["failure_type"] == "assertion"
    assert failed["tests_passed"] == 1 and failed["failures"][0]["test"] == "test_b"


def test_evaluator_classifies_failure_types():
    error = '<testsuite><testcase name="t"><error message="collection failure">x</error></testcase></testsuite>'
    assert evaluate(RawResult(2, "", error, False, 0.1))["failure_type"] == "import_or_syntax_error"
    exception = '<testsuite><testcase name="t"><failure message="TypeError: bad">x</failure></testcase></testsuite>'
    assert evaluate(RawResult(1, "", exception, False, 0.1))["failure_type"] == "exception"
    assert evaluate(RawResult(None, "", None, True, 20))["failure_type"] == "timeout"
    assert evaluate(RawResult(125, "", None, False, 0.1, error="no image"))["failure_type"] == (
        "evaluator_error"
    )


@pytest.mark.parametrize(
    "raw",
    [
        RawResult(0, "", None, False, 0.1),  # no report
        RawResult(0, "", "<testsuite></testsuite>", False, 0.1),  # zero tests
        RawResult(1, "", REPORT_PASS, False, 0.1),  # report says pass, exit code disagrees
        RawResult(0, "", "<!DOCTYPE x [<!ENTITY a 'b'>]>" + REPORT_PASS, False, 0.1),
        RawResult(0, "", "not xml", False, 0.1),
    ],
)
def test_evaluator_fails_closed(raw):
    assert not evaluate(raw)["passed"]
