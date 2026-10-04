"""Workflow state, run configurations and task loading."""

import operator
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, TypedDict

# Hard ceiling on repair iterations after the initial attempt. A RunConfig cannot exceed it.
MAX_REPAIRS = 2

ROOT = Path(__file__).resolve().parents[2]
TASKS_DIR = ROOT / "tasks"
# Protected evaluator tests. Never shown to the model, never writable from the sandbox.
EVAL_DIR = ROOT / "tests" / "evaluation"


@dataclass(frozen=True)
class RunConfig:
    name: str
    max_repairs: int
    policy_enabled: bool

    def __post_init__(self):
        if not 0 <= self.max_repairs <= MAX_REPAIRS:
            raise ValueError(f"max_repairs must be between 0 and {MAX_REPAIRS}")


# The three experiment configurations. Code always runs in the sandbox; "bounded" adds
# the policy layer (write allowlist, static code policy, untrusted-task delimiting).
CONFIGS = {
    "single": RunConfig("single", max_repairs=0, policy_enabled=False),
    "reflexion": RunConfig("reflexion", max_repairs=MAX_REPAIRS, policy_enabled=False),
    "bounded": RunConfig("bounded", max_repairs=MAX_REPAIRS, policy_enabled=True),
}


class RunState(TypedDict, total=False):
    task_prompt: str
    eval_dir: str
    attempt: int  # generation attempts made so far (1 = initial attempt)
    raw_reply: str
    proposal: dict[str, str]  # file path -> content proposed by the model
    feedback: dict | None  # structured evaluator feedback for the latest attempt
    reflections: Annotated[list[str], operator.add]  # Reflexion's long-term memory
    attempts: Annotated[list[dict], operator.add]  # history, one entry per attempt
    events: Annotated[list[dict], operator.add]  # audit / trace log
    model_calls: Annotated[int, operator.add]
    input_tokens: Annotated[int, operator.add]
    output_tokens: Annotated[int, operator.add]
    status: str


@dataclass(frozen=True)
class Task:
    id: str
    prompt: str
    eval_dir: Path


def list_tasks() -> list[str]:
    return sorted(p.stem for p in TASKS_DIR.glob("*.md"))


def load_task(task_id: str) -> Task:
    prompt_file = TASKS_DIR / f"{task_id}.md"
    eval_dir = EVAL_DIR / task_id
    if not prompt_file.is_file() or not eval_dir.is_dir():
        raise KeyError(f"unknown task: {task_id}")
    return Task(task_id, prompt_file.read_text(encoding="utf-8").strip(), eval_dir)
