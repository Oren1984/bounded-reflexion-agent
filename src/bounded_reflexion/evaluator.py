"""Turn a raw sandbox result into structured feedback.

The verdict comes only from the sandbox exit code and the JUnit report written by
pytest. Nothing the model says about its own solution is ever considered.
"""

import xml.etree.ElementTree as ET

from .runner import RawResult

MAX_MESSAGE_CHARS = 600
MAX_REPORT_CHARS = 1_000_000
# Failure types that end the run immediately (no repair is attempted).
TERMINAL_FAILURES = frozenset({"timeout", "evaluator_error"})


def _feedback(passed, failure_type, summary, total=0, ok=0, failures=None, duration_s=0.0):
    return {
        "passed": passed,
        "failure_type": failure_type,
        "summary": summary,
        "tests_total": total,
        "tests_passed": ok,
        "failures": failures or [],
        "duration_s": round(duration_s, 3),
    }


def malformed_feedback(reason: str) -> dict:
    return _feedback(False, "malformed_output", reason)


def evaluate(raw: RawResult) -> dict:
    if raw.timed_out:
        return _feedback(
            False, "timeout", "execution exceeded the time limit", duration_s=raw.duration_s
        )
    if raw.error:
        return _feedback(
            False, "evaluator_error", f"sandbox error: {raw.error}", duration_s=raw.duration_s
        )
    if raw.report_xml is None:
        # Fail closed: e.g. the process exited before pytest could write its report.
        return _feedback(
            False,
            "evaluator_error",
            f"no test report produced (exit code {raw.exit_code})",
            duration_s=raw.duration_s,
        )
    # The report is written inside the sandbox, so it is untrusted input: refuse anything
    # oversized or carrying a DTD / entity declarations (pytest never emits one).
    if len(raw.report_xml) > MAX_REPORT_CHARS or "<!" in raw.report_xml:
        return _feedback(
            False, "evaluator_error", "rejected test report", duration_s=raw.duration_s
        )
    try:
        root = ET.fromstring(raw.report_xml)
    except ET.ParseError:
        return _feedback(
            False, "evaluator_error", "unreadable test report", duration_s=raw.duration_s
        )

    cases = list(root.iter("testcase"))
    failures, collection_errors, skipped = [], 0, 0
    for case in cases:
        problem = case.find("failure")
        if problem is None:
            problem = case.find("error")
            collection_errors += problem is not None
        if problem is not None:
            text = (problem.get("message") or "") + "\n" + (problem.text or "")
            failures.append({"test": case.get("name", "?"), "message": text[:MAX_MESSAGE_CHARS]})
        skipped += case.find("skipped") is not None

    total = len(cases)
    ok = total - len(failures) - skipped
    passed = total > 0 and ok == total and raw.exit_code == 0
    if passed:
        failure_type = None
    elif collection_errors:
        failure_type = "import_or_syntax_error"
    elif failures and all(
        f["message"].startswith(("AssertionError", "assert", "Failed: DID NOT RAISE"))
        for f in failures
    ):
        failure_type = "assertion"
    elif failures:
        failure_type = "exception"
    else:
        failure_type = "evaluator_error"
    return _feedback(
        passed, failure_type, f"{ok} of {total} tests passed", total, ok, failures, raw.duration_s
    )


def render_feedback(feedback: dict) -> str:
    """Feedback text shown to the model. Only failure messages, never the test source."""
    lines = [f"Result: {feedback['summary']} (failure type: {feedback['failure_type']})"]
    lines += [f"- {f['test']}: {f['message'].strip()}" for f in feedback["failures"]]
    return "\n".join(lines)
