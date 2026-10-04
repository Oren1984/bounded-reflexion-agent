"""Tracing: the real LangSmith boundary and a local Mock / Demo trace.

Real path (designed, not validated against a live account): when LANGSMITH_TRACING=true,
LangGraph reports the run to LangSmith by itself. This module only supplies the run
identity and looks up the trace URL.

Mock path (used by the demo): `build_mock_trace` rebuilds, from a run record, the run
tree that LangSmith would receive - same run name, tags, metadata and stages. It is
built locally and nothing is sent anywhere.
"""

import logging
import os
import uuid

log = logging.getLogger(__name__)

MOCK_NOTICE = (
    "MOCK / DEMO TRACE - built locally from the run's event log. "
    "Nothing was sent to the LangSmith service."
)


def run_identity(task_id: str, config_name: str, attack_id: str | None, mode: str) -> dict:
    """Name, tags and metadata attached to a run. Shared by the real and the mock path."""
    return {
        "run_name": f"{task_id}:{config_name}",
        "tags": [config_name, mode] + (["attack"] if attack_id else []),
        "metadata": {"task_id": task_id, "config": config_name, "attack": attack_id},
    }


def langsmith_enabled() -> bool:
    return os.getenv("LANGSMITH_TRACING", "").lower() == "true"


def langsmith_url(run_id: uuid.UUID) -> str | None:
    """URL of the real LangSmith trace, when tracing is enabled. Never fails the run."""
    if not langsmith_enabled():
        return None
    try:
        from langchain_core.tracers.langchain import wait_for_all_tracers
        from langsmith import Client

        wait_for_all_tracers()
        return Client().read_run(run_id).url
    except Exception as exc:  # observability is optional
        log.warning("could not resolve LangSmith trace URL: %s", exc)
        return None


def _llm_run(record: dict, event: dict) -> dict:
    return {
        "name": record["model"],
        "run_type": "llm",
        "duration_s": event["duration_s"],
        "usage": {"input_tokens": event["input_tokens"], "output_tokens": event["output_tokens"]},
    }


def build_mock_trace(record: dict) -> dict:
    """The run tree a LangSmith trace of this run would contain: one root run for the
    workflow, one child run per graph node, model calls and the sandbox as grandchildren."""
    history = {entry["attempt"]: entry for entry in record["history"]}
    children = []
    for event in record["events"]:
        node, attempt = event["node"], event.get("attempt")
        run = {"name": node, "run_type": "chain", "attempt": attempt, "child_runs": []}
        if node == "generate":
            run["inputs"] = {"kind": event["kind"]}
            run["outputs"] = {"proposed_files": sorted(history[attempt]["files"])}
            run["child_runs"] = [_llm_run(record, event)]
        elif node == "boundary":
            run["outputs"] = {
                "decision": event["decision"],
                "violations": event.get("violations", []),
            }
        elif node == "execute":
            run["outputs"] = {
                "passed": event["passed"],
                "failure_type": event["failure_type"],
                "summary": event["summary"],
            }
            run["child_runs"] = [
                {"name": "docker sandbox: pytest", "run_type": "tool",
                 "duration_s": event["duration_s"]}
            ]
        elif node == "reflect":
            run["outputs"] = {"reflection": event["reflection"]}
            run["child_runs"] = [_llm_run(record, event)]
        else:
            run["outputs"] = {
                "status": event["status"],
                "repairs_used": event["repairs_used"],
                "max_repairs": event["max_repairs"],
            }
        children.append(run)
    identity = run_identity(record["task_id"], record["config"], record["attack"], record["mode"])
    return {
        "backend": "mock",
        "notice": MOCK_NOTICE,
        "project": os.getenv("LANGSMITH_PROJECT", "bounded-reflexion-agent"),
        "run": {
            "name": identity["run_name"],
            "run_type": "chain",
            "tags": identity["tags"],
            "metadata": identity["metadata"],
            "outputs": {
                "status": record["status"],
                "attempts": record["attempts"],
                "repairs_used": record["repairs_used"],
            },
            "duration_s": record["duration_s"],
            "child_runs": children,
        },
    }


def render_mock_trace(trace: dict) -> str:
    """Text view of a mock trace, shaped like the LangSmith run tree."""
    root = trace["run"]
    lines = [
        trace["notice"],
        f"project: {trace['project']}",
        f"{root['name']}  [chain]  tags={root['tags']}  metadata={root['metadata']}",
    ]
    for run in root["child_runs"]:
        outputs = run.get("outputs", {})
        if run["name"] == "generate":
            detail = f"attempt {run['attempt']} ({run['inputs']['kind']}) -> " + ", ".join(
                outputs["proposed_files"]
            )
        elif run["name"] == "boundary":
            detail = outputs["decision"] + "".join(
                f"; {v['rule']}" for v in outputs["violations"]
            )
        elif run["name"] == "execute":
            detail = ("pass" if outputs["passed"] else f"fail ({outputs['failure_type']})")
            detail += f", {outputs['summary']}"
        elif run["name"] == "reflect":
            detail = outputs["reflection"][:90] + "..."
        else:
            detail = (
                f"{outputs['status']}, repairs {outputs['repairs_used']}/{outputs['max_repairs']}"
            )
        lines.append(f"|- {run['name']:<9} [chain]  {detail}")
        for child in run["child_runs"]:
            usage = child.get("usage")
            extra = (
                f"  tokens in/out: {usage['input_tokens']}/{usage['output_tokens']}"
                if usage else ""
            )
            lines.append(
                f"|    +- {child['name']}  [{child['run_type']}]  {child['duration_s']}s{extra}"
            )
    lines.append(f"+- outputs: {root['outputs']}  total {root['duration_s']}s")
    return "\n".join(lines)
