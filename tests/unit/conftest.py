"""Shared fakes: a scripted model and an in-memory runner. No network, no Docker."""

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from bounded_reflexion.runner import RawResult
from bounded_reflexion.state import Task

GOOD = '<file path="solution.py">\nRESULT = "CORRECT"\n</file>'
BAD = '<file path="solution.py">\nRESULT = "WRONG"\n</file>'
REFLECTION = "The result was wrong; return the correct value next time."

REPORT_PASS = (
    '<testsuites><testsuite tests="2"><testcase name="test_a"/><testcase name="test_b"/>'
    "</testsuite></testsuites>"
)
REPORT_FAIL = (
    '<testsuites><testsuite tests="2"><testcase name="test_a"/><testcase name="test_b">'
    '<failure message="assert 1 == 2">details</failure></testcase></testsuite></testsuites>'
)


def scripted(*replies: str) -> FakeListChatModel:
    return FakeListChatModel(responses=list(replies))


class FakeRunner:
    """Passes when the solution contains CORRECT. Records what it was asked to run."""

    def __init__(self, result: RawResult | None = None):
        self.result = result
        self.calls = 0
        self.workspace_files: list[list[str]] = []

    def __call__(self, workspace, eval_dir) -> RawResult:
        self.calls += 1
        self.workspace_files.append(
            sorted(p.relative_to(workspace).as_posix() for p in workspace.rglob("*") if p.is_file())
        )
        if self.result is not None:
            return self.result
        ok = "CORRECT" in (workspace / "solution.py").read_text()
        return RawResult(0 if ok else 1, "", REPORT_PASS if ok else REPORT_FAIL, False, 0.01)


@pytest.fixture
def task(tmp_path) -> Task:
    eval_dir = tmp_path / "evaluation" / "demo_task"
    eval_dir.mkdir(parents=True)
    (eval_dir / "test_solution.py").write_text("def test_a():\n    assert True\n")
    return Task("demo_task", "Set RESULT to the right value.", eval_dir)
