"""The bounded Reflexion workflow as a LangGraph state machine.

    generate -> boundary -> execute -> (pass) -> finalize
                   |           |
                   |           +-- (fail, repairs left) -> reflect -> generate
                   +-- (policy violation) -> finalize

Every stop condition is a routing decision in this file.
"""

import logging
import os
import tempfile
import time
import uuid
from contextlib import nullcontext
from pathlib import Path

from langgraph.graph import END, START, StateGraph

from . import agent
from .evaluator import TERMINAL_FAILURES, evaluate, malformed_feedback, render_feedback
from .policies import check_proposal, resolve_in_workspace, tree_digest
from .runner import run_in_docker
from .state import RunConfig, RunState, Task
from .tracing import langsmith_url, run_identity

log = logging.getLogger(__name__)


def _event(node: str, **fields) -> dict:
    return {"node": node, **fields}


def _timed_call(call, *args, **kwargs):
    """Run a model call; return its text, usage counters and usage plus latency for the event."""
    started = time.monotonic()
    text, usage = call(*args, **kwargs)
    traced = {
        "duration_s": round(time.monotonic() - started, 3),
        "input_tokens": usage["input_tokens"],
        "output_tokens": usage["output_tokens"],
    }
    return text, usage, traced


def build_graph(model, runner, config: RunConfig):
    def generate(state: RunState) -> dict:
        attempt = state.get("attempt", 0) + 1
        feedback = state.get("feedback")
        text, usage, traced = _timed_call(
            agent.generate,
            model,
            state["task_prompt"],
            hardened=config.policy_enabled,
            previous_code=state.get("proposal", {}).get("solution.py"),
            feedback_text=render_feedback(feedback) if feedback else None,
            reflections=state.get("reflections", []),
        )
        kind = "repair" if attempt > 1 else "initial"
        return {
            "attempt": attempt,
            "raw_reply": text,
            "proposal": agent.parse_files(text),
            "events": [_event("generate", attempt=attempt, kind=kind, **traced)],
            **usage,
        }

    def boundary(state: RunState) -> dict:
        """Decide whether the proposal may be executed."""
        attempt, proposal = state["attempt"], state["proposal"]
        violations = check_proposal(proposal) if config.policy_enabled else []
        if violations:
            log.warning("policy blocked attempt %s: %s", attempt, violations)
            return {
                "status": "blocked_policy",
                "feedback": None,
                "attempts": [
                    {"attempt": attempt, "files": proposal, "feedback": None,
                     "violations": violations}
                ],
                "events": [
                    _event("boundary", attempt=attempt, decision="blocked", violations=violations)
                ],
            }
        if "solution.py" not in proposal:
            feedback = malformed_feedback(
                'the reply did not contain a <file path="solution.py"> block'
            )
            return {
                "feedback": feedback,
                "attempts": [
                    {"attempt": attempt, "files": proposal, "feedback": feedback, "violations": []}
                ],
                "events": [_event("boundary", attempt=attempt, decision="malformed_output")],
            }
        return {
            "feedback": None,
            "events": [
                _event("boundary", attempt=attempt, decision="allowed",
                       policy_checked=config.policy_enabled)
            ],
        }

    def execute(state: RunState) -> dict:
        """Materialise the proposal in a throwaway workspace and run the protected tests."""
        attempt, proposal = state["attempt"], state["proposal"]
        eval_dir = Path(state["eval_dir"])
        digest_before = tree_digest(eval_dir)
        skipped = []
        with tempfile.TemporaryDirectory(prefix="bra-ws-") as tmp:
            workspace = Path(tmp).resolve()
            for relative, content in proposal.items():
                target = resolve_in_workspace(workspace, relative)
                if target is None:
                    skipped.append(relative)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8", newline="\n")
            raw = runner(workspace, eval_dir)
        feedback = evaluate(raw)
        if tree_digest(eval_dir) != digest_before:
            feedback = {
                **feedback,
                "passed": False,
                "failure_type": "evaluator_error",
                "summary": "protected tests changed during the run",
            }
        return {
            "feedback": feedback,
            "attempts": [
                {"attempt": attempt, "files": proposal, "feedback": feedback, "violations": []}
            ],
            "events": [
                _event(
                    "execute",
                    attempt=attempt,
                    passed=feedback["passed"],
                    failure_type=feedback["failure_type"],
                    summary=feedback["summary"],
                    duration_s=feedback["duration_s"],
                    writes_outside_workspace_skipped=skipped,
                )
            ],
        }

    def reflect(state: RunState) -> dict:
        text, usage, traced = _timed_call(
            agent.reflect,
            model,
            state["task_prompt"],
            hardened=config.policy_enabled,
            code=state["proposal"].get("solution.py") or state["raw_reply"],
            feedback_text=render_feedback(state["feedback"]),
        )
        reflection = text.strip()
        return {
            "reflections": [reflection],
            "events": [
                _event("reflect", attempt=state["attempt"], reflection=reflection, **traced)
            ],
            **usage,
        }

    def finalize(state: RunState) -> dict:
        feedback = state.get("feedback")
        if state.get("status") == "blocked_policy":
            status = "blocked_policy"
        elif feedback["passed"]:
            status = "passed"
        elif feedback["failure_type"] in TERMINAL_FAILURES:
            status = feedback["failure_type"]
        elif config.max_repairs == 0:
            status = "failed"
        else:
            status = "failed_retry_limit"
        repairs_used = state["attempt"] - 1
        log.info("run finished: %s after %s repair(s)", status, repairs_used)
        return {
            "status": status,
            "events": [
                _event("finalize", status=status, repairs_used=repairs_used,
                       max_repairs=config.max_repairs)
            ],
        }

    def repair_or_stop(state: RunState) -> str:
        """The retry bound: a repair is allowed only while repairs used < max_repairs."""
        repairs_used = state["attempt"] - 1
        return "reflect" if repairs_used < config.max_repairs else "finalize"

    def after_boundary(state: RunState) -> str:
        if state.get("status") == "blocked_policy":
            return "finalize"
        if state.get("feedback"):  # malformed output: nothing to execute
            return repair_or_stop(state)
        return "execute"

    def after_execute(state: RunState) -> str:
        feedback = state["feedback"]
        if feedback["passed"] or feedback["failure_type"] in TERMINAL_FAILURES:
            return "finalize"
        return repair_or_stop(state)

    graph = StateGraph(RunState)
    graph.add_node("generate", generate)
    graph.add_node("boundary", boundary)
    graph.add_node("execute", execute)
    graph.add_node("reflect", reflect)
    graph.add_node("finalize", finalize)
    graph.add_edge(START, "generate")
    graph.add_edge("generate", "boundary")
    graph.add_conditional_edges("boundary", after_boundary, ["execute", "reflect", "finalize"])
    graph.add_conditional_edges("execute", after_execute, ["reflect", "finalize"])
    graph.add_edge("reflect", "generate")
    graph.add_edge("finalize", END)
    return graph.compile()


def _no_external_tracing():
    try:
        from langsmith.run_helpers import tracing_context
    except ImportError:  # no LangSmith client installed: nothing could be sent anyway
        return nullcontext()
    return tracing_context(enabled=False)


def run_task(task: Task, config: RunConfig, model, runner=run_in_docker, attack=None,
             mode: str = "live") -> dict:
    """Run one task under one configuration and return a flat, JSON-serialisable record."""
    prompt = task.prompt if attack is None else f"{task.prompt}\n\n{attack.render(task.id)}"
    run_id = uuid.uuid4()
    identity = run_identity(task.id, config.name, attack.id if attack else None, mode)
    started = time.monotonic()
    # Mock runs are never reported to LangSmith, even if tracing is enabled in the environment.
    with _no_external_tracing() if mode == "mock" else nullcontext():
        final = build_graph(model, runner, config).invoke(
            {"task_prompt": prompt, "eval_dir": str(task.eval_dir)},
            # recursion_limit is a backstop only; the real bound is repair_or_stop.
            config={"run_id": run_id, "recursion_limit": 25, **identity},
        )
    history = final["attempts"]
    last_feedback = history[-1]["feedback"] or {}
    first_feedback = history[0]["feedback"] or {}
    return {
        "task_id": task.id,
        "config": config.name,
        "mode": mode,
        "model": "scripted replies (mock)" if mode == "mock"
        else os.getenv("BRA_MODEL", agent.DEFAULT_MODEL),
        "attack": attack.id if attack else None,
        "status": final["status"],
        "passed": final["status"] == "passed",
        "attempts": final["attempt"],
        "repairs_used": final["attempt"] - 1,
        "max_repairs": config.max_repairs,
        "first_attempt_passed": bool(first_feedback.get("passed")),
        "tests_passed": last_feedback.get("tests_passed", 0),
        "tests_total": last_feedback.get("tests_total", 0),
        "failure_type": last_feedback.get("failure_type"),
        "duration_s": round(time.monotonic() - started, 3),
        "sandbox_duration_s": round(
            sum((a["feedback"] or {}).get("duration_s", 0) for a in history), 3
        ),
        "model_calls": final.get("model_calls", 0),
        "input_tokens": final.get("input_tokens", 0),
        "output_tokens": final.get("output_tokens", 0),
        "history": history,
        "reflections": final.get("reflections", []),
        "events": final["events"],
        "trace_url": None if mode == "mock" else langsmith_url(run_id),
    }
