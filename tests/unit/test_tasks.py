"""Every task must be solvable: its reference solution passes its protected tests.

The reference solutions are trusted project code, so they run on the host. They are
never shown to the model.
"""

import os
import shutil
import subprocess
import sys

import pytest

from bounded_reflexion.state import ROOT, list_tasks, load_task

REFERENCE_DIR = ROOT / "tests" / "reference"


def test_task_set_is_consistent():
    tasks = list_tasks()
    assert 10 <= len(tasks) <= 15
    assert {p.stem for p in REFERENCE_DIR.glob("*.py")} == set(tasks)


@pytest.mark.parametrize("task_id", list_tasks())
def test_reference_solution_passes_protected_tests(task_id, tmp_path):
    shutil.copy(REFERENCE_DIR / f"{task_id}.py", tmp_path / "solution.py")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(load_task(task_id).eval_dir), "-q",
         "-p", "no:cacheprovider"],
        env={**os.environ, "PYTHONPATH": str(tmp_path), "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout
