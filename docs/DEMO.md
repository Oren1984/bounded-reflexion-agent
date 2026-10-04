# Demo guide

A walkthrough of about three minutes. It needs Docker and nothing else: no model API key,
no LangSmith account, no network access at run time.

## Setup

```bash
docker build -t bra-sandbox .
uv sync --extra demo
uv run streamlit run app.py
```

## What is mock and what is real

| Part | In the demo |
|---|---|
| Model replies | **Mock.** Stored sample responses in `demo.py`, replayed in order. |
| Tracing | **Mock.** A run tree built locally; nothing is sent to LangSmith. |
| LangGraph workflow, stop conditions, retry limit | Real |
| Policy checks and audit events | Real |
| Docker sandbox and pytest results | Real |

The UI shows a "Demo / Mock Mode" banner on every run and a separate "Mock / Demo tracing"
notice on the trace panel. Mock runs are never reported to LangSmith, even if tracing
variables are set in the environment.

## Scenarios

| # | Scenario | Path shown | What to point out |
|---|---|---|---|
| 1 | Successful first attempt | Generate → Boundary (allowed) → Test (pass) | No repair is spent when none is needed. |
| 2 | Reflexion repair | Generate → Test (fail) → Reflect → Repair → Test (pass) | The first solution uses `round()`. The failing assertions come back as feedback, the reflection names the cause (banker's rounding, binary floats), and the repair switches to `Decimal`. |
| 3 | Bounded failure | Three attempts, two reflections, then stop | "Repairs used 2 / 2". The third attempt regresses. The workflow stops because the graph has no route to a fourth attempt. |
| 4 | Security boundary | Generate → Boundary (blocked) | The task text carries an injected instruction to overwrite the tests. The scripted model complies; the write allowlist rejects the proposal before anything executes, and the decision is in the audit log. |

Screenshots of the four scenarios are in `assets/screenshots/`.

## Trace

Each run ends with a **Mock / Demo trace**: the run tree that a LangSmith trace of the same
run would contain. It is rebuilt from the run's own event log, with the same run name, tags
and metadata that the real integration attaches.

```bash
uv run python -m bounded_reflexion demo repair --trace
```

```text
MOCK / DEMO TRACE - built locally from the run's event log. Nothing was sent to the LangSmith service.
project: bounded-reflexion-agent
round_half_up:bounded  [chain]  tags=['bounded', 'mock']  metadata={'task_id': 'round_half_up', 'config': 'bounded', 'attack': None}
|- generate  [chain]  attempt 1 (initial) -> solution.py
|    +- scripted replies (mock)  [llm]  0.0s  tokens in/out: 0/0
|- boundary  [chain]  allowed
|- execute   [chain]  fail (assertion), 4 of 13 tests passed
|    +- docker sandbox: pytest  [tool]  1.3s
|- reflect   [chain]  The built-in round() uses banker's rounding (2.5 -> 2) and works on the binary float...
|    +- scripted replies (mock)  [llm]  0.0s  tokens in/out: 0/0
|- generate  [chain]  attempt 2 (repair) -> solution.py
|    +- scripted replies (mock)  [llm]  0.0s  tokens in/out: 0/0
|- boundary  [chain]  allowed
|- execute   [chain]  pass, 13 of 13 tests passed
|    +- docker sandbox: pytest  [tool]  1.2s
|- finalize  [chain]  passed, repairs 1/2
+- outputs: {'status': 'passed', 'attempts': 2, 'repairs_used': 1}  total 2.6s
```

(Timings vary by machine.) What the trace makes visible:

| In the trace | Meaning |
|---|---|
| Root run with tags and metadata | Which task, configuration and mode; whether an attack was injected |
| One child run per stage | The path the workflow took, in order |
| `generate` / `reflect` with an `llm` child | Each model call, with its latency and token usage |
| `boundary` decision and violations | Policy decisions, including blocks |
| `execute` with a `tool` child | Each sandbox run and its verdict |
| Repeated `generate` runs | Retries, numbered by attempt |
| `finalize` | Final outcome and repairs used against the limit |

Token counts are zero in mock mode because scripted replies carry no usage data.

In the UI the same trace appears under "Trace", with the JSON form and the raw audit log in
expanders. The blocked-injection scenario shows a three-stage trace with the violation on
the `boundary` run:

```bash
uv run python -m bounded_reflexion demo security --trace
```

## Real providers

The integration points for a real model and for real LangSmith tracing exist in the code
(`agent.make_model`, `tracing.langsmith_url`, and the `run` command) but were not exercised
in building this POC. They need `ANTHROPIC_API_KEY`, and optionally `LANGSMITH_TRACING=true`
with `LANGSMITH_API_KEY`, in `.env`.
