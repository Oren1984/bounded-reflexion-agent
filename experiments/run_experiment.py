"""Run the live benchmark and write raw records plus a summary.

Status: implemented, not executed. This POC was validated in Mock E2E mode only
(see docs/EXPERIMENT.md); this script is the ready entry point for a live run.

    python experiments/run_experiment.py                 # all tasks x 3 configs + security cases
    python experiments/run_experiment.py --tasks slugify round_half_up --skip-security

Requires ANTHROPIC_API_KEY (paid) and a running Docker daemon. Outputs go to
experiments/results/<timestamp>/: runs.jsonl, security.jsonl, summary.json, summary.md.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from bounded_reflexion.agent import DEFAULT_MODEL, make_model
from bounded_reflexion.attacks import ATTACKS, classify
from bounded_reflexion.graph import run_task
from bounded_reflexion.metrics import summarize_runs, summarize_security
from bounded_reflexion.runner import docker_available
from bounded_reflexion.state import CONFIGS, list_tasks, load_task

# Security cases: every attack against each of these user tasks, with and without the policy layer.
SECURITY_TASKS = ["chunk_list", "slugify", "moving_average"]
SECURITY_CONFIGS = ["reflexion", "bounded"]


def _table(summary: dict, columns: list[str]) -> str:
    lines = ["| config | " + " | ".join(columns) + " |", "|---|" + "---|" * len(columns)]
    for config, row in summary.items():
        lines.append(f"| {config} | " + " | ".join(str(row[c]) for c in columns) + " |")
    return "\n".join(lines)


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", nargs="*", default=list_tasks())
    parser.add_argument("--configs", nargs="*", default=list(CONFIGS), choices=list(CONFIGS))
    parser.add_argument("--skip-security", action="store_true")
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "results")
    args = parser.parse_args()

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set; the experiment needs the live model.", file=sys.stderr)
        return 2
    if not docker_available():
        print("Docker is not running.", file=sys.stderr)
        return 2

    model_name = os.getenv("BRA_MODEL", DEFAULT_MODEL)
    model = make_model()
    out_dir = args.out / datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir.mkdir(parents=True)

    runs = []
    with open(out_dir / "runs.jsonl", "w", encoding="utf-8") as sink:
        for task_id in args.tasks:
            for config_name in args.configs:
                record = run_task(load_task(task_id), CONFIGS[config_name], model)
                runs.append(record)
                sink.write(json.dumps(record) + "\n")
                sink.flush()
                print(f"{task_id:<20} {config_name:<10} {record['status']:<20} "
                      f"attempts={record['attempts']}")

    security = []
    if not args.skip_security:
        with open(out_dir / "security.jsonl", "w", encoding="utf-8") as sink:
            for task_id in SECURITY_TASKS:
                for attack in ATTACKS.values():
                    for config_name in SECURITY_CONFIGS:
                        record = run_task(
                            load_task(task_id), CONFIGS[config_name], model, attack=attack
                        )
                        record["outcome"] = classify(record)
                        security.append(record)
                        sink.write(json.dumps(record) + "\n")
                        sink.flush()
                        print(f"{task_id:<20} {attack.id:<20} {config_name:<10} "
                              f"{record['outcome']:<15} {record['status']}")

    summary = {
        "model": model_name,
        "temperature": os.getenv("BRA_TEMPERATURE") or None,
        "tasks": args.tasks,
        "runs": summarize_runs(runs, model_name),
        "security": summarize_security(security),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    report = [
        f"# Experiment {out_dir.name}",
        f"Model: `{model_name}` - tasks: {len(args.tasks)} - observed measurements only.",
        "## Task runs",
        _table(summary["runs"], [
            "runs", "task_success_rate", "first_attempt_success_rate", "test_pass_rate",
            "mean_attempts", "total_repair_iterations", "repair_success_rate", "false_blocks",
            "mean_duration_s", "model_calls", "input_tokens", "output_tokens",
            "estimated_cost_usd",
        ]),
    ]
    if security:
        report += [
            "## Security cases",
            _table(summary["security"], [
                "cases", "attack_success_rate", "attack_blocking_rate", "ignored_rate",
                "false_positive_rate", "utility_under_attack",
            ]),
        ]
    (out_dir / "summary.md").write_text("\n\n".join(report) + "\n", encoding="utf-8")
    print(f"\nresults written to {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
