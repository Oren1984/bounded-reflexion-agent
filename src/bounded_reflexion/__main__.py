"""Command line entry point.

    python -m bounded_reflexion list
    python -m bounded_reflexion demo repair            # mock model, real sandbox
    python -m bounded_reflexion demo repair --trace    # plus the Mock / Demo trace
    python -m bounded_reflexion run slugify --config bounded [--attack modify_tests]
"""

import argparse
import json
import sys

from dotenv import load_dotenv

from .attacks import ATTACKS, classify
from .demo import SCENARIOS, run_scenario
from .graph import run_task
from .runner import docker_available
from .state import CONFIGS, list_tasks, load_task
from .tracing import build_mock_trace, render_mock_trace


def render(record: dict) -> str:
    """Human-readable trace of one run, built from the workflow's event log."""
    label = "DEMO / MOCK MODE (scripted model replies)" if record["mode"] == "mock" else "LIVE"
    lines = [
        f"[{label}]",
        f"Task: {record['task_id']}   config: {record['config']}   "
        f"max repairs: {record['max_repairs']}"
        + (f"   injected attack: {record['attack']}" if record["attack"] else ""),
        "",
    ]
    history = {entry["attempt"]: entry for entry in record["history"]}
    for step, event in enumerate(record["events"], 1):
        node, attempt = event["node"], event.get("attempt")
        if node == "generate":
            detail = f"attempt {attempt} ({event['kind']})"
        elif node == "boundary":
            detail = event["decision"].upper()
            for violation in event.get("violations", []):
                detail += f"\n       - {violation['rule']}: {violation['detail']}"
        elif node == "execute":
            verdict = "PASS" if event["passed"] else f"FAIL ({event['failure_type']})"
            detail = f"{verdict}  {event['summary']}  [{event['duration_s']}s in sandbox]"
            for failure in history[attempt]["feedback"]["failures"][:3]:
                first_line = failure["message"].strip().splitlines()[0]
                detail += f"\n       - {failure['test']}: {first_line}"
        elif node == "reflect":
            detail = event["reflection"]
        else:
            detail = (
                f"{event['status'].upper()}  repairs used: "
                f"{event['repairs_used']}/{event['max_repairs']}"
            )
        lines.append(f"[{step:>2}] {node:<9} {detail}")
    lines += [
        "",
        f"Final status: {record['status']}   attempts: {record['attempts']}   "
        f"time: {record['duration_s']}s   model calls: {record['model_calls']}",
    ]
    if record["attack"]:
        lines.append(f"Security outcome: {classify(record)}")
    if record["trace_url"]:
        lines.append(f"LangSmith trace: {record['trace_url']}")
    return "\n".join(lines)


def main(argv=None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="bounded_reflexion")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="list tasks, attacks and demo scenarios")
    demo = commands.add_parser("demo", help="run a mock scenario (no API key needed)")
    demo.add_argument("scenario", choices=sorted(SCENARIOS))
    run = commands.add_parser("run", help="run one task with the live model")
    run.add_argument("task")
    run.add_argument("--config", choices=sorted(CONFIGS), default="bounded")
    run.add_argument("--attack", choices=sorted(ATTACKS))
    for sub in (demo, run):
        sub.add_argument("--json", action="store_true", help="print the full record as JSON")
        sub.add_argument("--trace", action="store_true",
                         help="also print the Mock / Demo trace (what LangSmith would receive)")
    args = parser.parse_args(argv)

    if args.command == "list":
        print("tasks:    ", ", ".join(list_tasks()))
        print("attacks:  ", ", ".join(ATTACKS))
        print("scenarios:", ", ".join(SCENARIOS))
        return 0
    if not docker_available():
        print("Docker is not running. Generated code is only ever executed in the sandbox.",
              file=sys.stderr)
        return 2
    if args.command == "demo":
        record = run_scenario(args.scenario)
    else:
        from .agent import make_model

        attack = ATTACKS[args.attack] if args.attack else None
        record = run_task(load_task(args.task), CONFIGS[args.config], make_model(), attack=attack)
    print(json.dumps(record, indent=2) if args.json else render(record))
    if args.trace:
        print()
        print(render_mock_trace(build_mock_trace(record)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
