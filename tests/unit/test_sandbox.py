"""Real Docker sandbox behaviour and the mock scenarios end to end.

Skipped automatically when no Docker daemon is available.
"""

import pytest

from bounded_reflexion.demo import run_scenario
from bounded_reflexion.evaluator import evaluate
from bounded_reflexion.policies import tree_digest
from bounded_reflexion.runner import docker_available, run_in_docker
from bounded_reflexion.state import MAX_REPAIRS, load_task

pytestmark = [
    pytest.mark.docker,
    pytest.mark.skipif(not docker_available(), reason="Docker daemon not available"),
]

LEAP = "def is_leap_year(year):\n    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)\n"


def run_solution(tmp_path, code, timeout_s=30):
    (tmp_path / "solution.py").write_text(code, newline="\n")
    return run_in_docker(tmp_path, load_task("leap_year").eval_dir, timeout_s=timeout_s)


def test_correct_solution_passes(tmp_path):
    feedback = evaluate(run_solution(tmp_path, LEAP))
    assert feedback["passed"] and feedback["tests_total"] == 6


def test_wrong_solution_fails_with_structured_feedback(tmp_path):
    feedback = evaluate(run_solution(tmp_path, "def is_leap_year(year):\n    return year % 4 == 0\n"))
    assert not feedback["passed"] and feedback["failure_type"] == "assertion"
    assert 0 < feedback["tests_passed"] < feedback["tests_total"]


def test_infinite_loop_times_out(tmp_path):
    raw = run_solution(tmp_path, "while True:\n    pass\n", timeout_s=6)
    assert raw.timed_out and evaluate(raw)["failure_type"] == "timeout"


def test_protected_tests_and_workspace_are_read_only(tmp_path):
    eval_dir = load_task("leap_year").eval_dir
    before = tree_digest(eval_dir)
    code = (
        "errors = []\n"
        "for target in ('/eval/test_solution.py', '/workspace/solution.py', '/home/x.txt'):\n"
        "    try:\n"
        "        open(target, 'w').write('tampered')\n"
        "    except OSError as exc:\n"
        "        errors.append(type(exc).__name__)\n"
        "assert len(errors) == 3, errors\n" + LEAP
    )
    assert evaluate(run_solution(tmp_path, code))["passed"]  # all three writes were refused
    assert tree_digest(eval_dir) == before


def test_network_is_unavailable(tmp_path):
    code = (
        "import socket\n"
        "try:\n"
        "    socket.create_connection(('1.1.1.1', 53), timeout=3)\n"
        "    reachable = True\n"
        "except OSError:\n"
        "    reachable = False\n"
        "assert not reachable\n" + LEAP
    )
    assert evaluate(run_solution(tmp_path, code))["passed"]


def test_process_exit_cannot_fake_a_pass(tmp_path):
    feedback = evaluate(run_solution(tmp_path, "import os\nos._exit(0)\n"))
    assert not feedback["passed"] and feedback["failure_type"] == "evaluator_error"


@pytest.mark.parametrize(
    "scenario, status, attempts",
    [
        ("first_pass", "passed", 1),
        ("repair", "passed", 2),
        ("bounded_failure", "failed_retry_limit", 1 + MAX_REPAIRS),
        ("security", "blocked_policy", 1),
    ],
)
def test_mock_scenarios(scenario, status, attempts):
    record = run_scenario(scenario)
    assert (record["status"], record["attempts"], record["mode"]) == (status, attempts, "mock")
