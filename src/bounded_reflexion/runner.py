"""Docker sandbox: the only place agent-generated code runs."""

import os
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

MAX_OUTPUT_CHARS = 8000


@dataclass
class RawResult:
    exit_code: int | None
    output: str
    report_xml: str | None
    timed_out: bool
    duration_s: float
    error: str | None = None


def docker_available() -> bool:
    try:
        probe = subprocess.run(["docker", "info"], capture_output=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return probe.returncode == 0


def _container_user() -> str:
    # On POSIX hosts, match the host user so the report directory is writable.
    return f"{os.getuid()}:{os.getgid()}" if hasattr(os, "getuid") else "1000:1000"


def run_in_docker(workspace: Path, eval_dir: Path, timeout_s: float | None = None) -> RawResult:
    """Run the protected tests in eval_dir against the solution in workspace.

    The command line is fixed; nothing the model produced is interpolated into it.
    """
    timeout_s = timeout_s or float(os.getenv("BRA_SANDBOX_TIMEOUT_S", "20"))
    image = os.getenv("BRA_SANDBOX_IMAGE", "bra-sandbox:latest")
    name = f"bra-{uuid.uuid4().hex[:12]}"
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="bra-out-") as out_dir:
        command = [
            "docker", "run", "--rm", "--name", name,
            "--network", "none",                    # no network
            "--read-only",                          # read-only root filesystem
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges",
            "--pids-limit", "64",
            "--memory", "256m", "--memory-swap", "256m",
            "--cpus", "1",
            "--user", _container_user(),
            "--tmpfs", "/tmp:rw,size=16m",
            "-e", "PYTHONPATH=/workspace",
            "-e", "PYTHONDONTWRITEBYTECODE=1",
            "-v", f"{workspace}:/workspace:ro",     # agent solution, read-only at run time
            "-v", f"{eval_dir}:/eval:ro",           # protected tests, read-only
            "-v", f"{out_dir}:/out",                # only writable mount: the test report
            "-w", "/eval",
            image,
            "python", "-m", "pytest", "/eval", "-q", "--tb=short",
            "-p", "no:cacheprovider", "--rootdir=/eval", "--confcutdir=/eval",
            "--junitxml=/out/report.xml", "-o", "junit_family=xunit2",
        ]
        try:
            proc = subprocess.run(
                command, capture_output=True, text=True, errors="replace", timeout=timeout_s
            )
        except subprocess.TimeoutExpired:
            subprocess.run(["docker", "kill", name], capture_output=True)
            return RawResult(None, "", None, True, time.monotonic() - started)
        except OSError as exc:
            return RawResult(None, "", None, False, time.monotonic() - started, error=str(exc))

        duration = time.monotonic() - started
        output = (proc.stdout + proc.stderr)[-MAX_OUTPUT_CHARS:]
        # 125-127 are Docker's own failures (daemon down, image missing, command not found).
        if proc.returncode in (125, 126, 127):
            return RawResult(proc.returncode, output, None, False, duration, error=output.strip())
        report = Path(out_dir) / "report.xml"
        report_xml = report.read_text(encoding="utf-8") if report.is_file() else None
        return RawResult(proc.returncode, output, report_xml, False, duration)
