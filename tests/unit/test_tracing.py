"""The Mock / Demo trace mirrors the workflow and never claims to be a real trace."""

from conftest import BAD, GOOD, REFLECTION, FakeRunner, scripted

from bounded_reflexion.attacks import ATTACKS
from bounded_reflexion.graph import run_task
from bounded_reflexion.state import CONFIGS
from bounded_reflexion.tracing import MOCK_NOTICE, build_mock_trace, render_mock_trace


def stages(trace):
    return [run["name"] for run in trace["run"]["child_runs"]]


def test_mock_trace_follows_the_workflow_stages(task):
    record = run_task(
        task, CONFIGS["bounded"], scripted(BAD, REFLECTION, GOOD), FakeRunner(), mode="mock"
    )
    trace = build_mock_trace(record)
    assert stages(trace) == [event["node"] for event in record["events"]]
    assert stages(trace) == [
        "generate", "boundary", "execute", "reflect", "generate", "boundary", "execute", "finalize",
    ]
    root = trace["run"]
    assert root["name"] == "demo_task:bounded" and root["tags"] == ["bounded", "mock"]
    assert root["metadata"] == {"task_id": "demo_task", "config": "bounded", "attack": None}
    assert root["outputs"] == {"status": "passed", "attempts": 2, "repairs_used": 1}
    by_name = {run["name"]: run for run in root["child_runs"]}
    assert by_name["generate"]["child_runs"][0]["run_type"] == "llm"
    assert by_name["reflect"]["outputs"]["reflection"] == REFLECTION
    assert by_name["execute"]["child_runs"][0]["run_type"] == "tool"
    assert by_name["finalize"]["outputs"]["max_repairs"] == 2


def test_mock_trace_records_policy_block(task):
    reply = GOOD + '\n<file path="tests/evaluation/demo_task/test_solution.py">\npass\n</file>'
    record = run_task(
        task, CONFIGS["bounded"], scripted(reply), FakeRunner(),
        attack=ATTACKS["modify_tests"], mode="mock",
    )
    trace = build_mock_trace(record)
    assert stages(trace) == ["generate", "boundary", "finalize"]
    boundary = trace["run"]["child_runs"][1]["outputs"]
    assert boundary["decision"] == "blocked"
    assert boundary["violations"][0]["rule"] == "write_outside_allowlist"
    assert "attack" in trace["run"]["tags"]
    assert trace["run"]["metadata"]["attack"] == "modify_tests"


def test_mock_trace_is_labelled_and_never_a_real_trace(task, monkeypatch):
    # Even with tracing switched on in the environment, a mock run reports nothing externally.
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGSMITH_ENDPOINT", "http://127.0.0.1:9")
    record = run_task(task, CONFIGS["bounded"], scripted(GOOD), FakeRunner(), mode="mock")
    assert record["trace_url"] is None and record["model"] == "scripted replies (mock)"
    trace = build_mock_trace(record)
    assert trace["backend"] == "mock" and trace["notice"] == MOCK_NOTICE
    text = render_mock_trace(trace)
    assert text.startswith("MOCK / DEMO TRACE") and "Nothing was sent" in text
    assert text.isascii()
