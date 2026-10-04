# Research foundation

This POC borrows ideas from two papers. It reproduces neither. This document says exactly
what was taken, what was simplified and what was left out.

**Status of the claims here.** The mechanisms in the mapping table are implemented and
tested locally, and demonstrated with scripted model replies. No live-model experiment was
run, so this project neither confirms nor contradicts the papers' empirical results.

## Sources

| | Reflexion | AgentDojo |
|---|---|---|
| Title | *Reflexion: Language Agents with Verbal Reinforcement Learning* | *AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents* |
| Authors | Shinn, Cassano, Berman, Gopinath, Narasimhan, Yao | Debenedetti, Zhang, Balunović, Beurer-Kellner, Fischer, Tramèr (ETH Zurich, Invariant Labs) |
| Venue | NeurIPS 2023 | NeurIPS 2024, Datasets and Benchmarks Track |
| Paper | <https://arxiv.org/abs/2303.11366> | <https://arxiv.org/abs/2406.13352> |
| Code | <https://github.com/noahshinn/reflexion> | <https://github.com/ethz-spylab/agentdojo> |
| Project site | - | <https://agentdojo.spylab.ai/> |

## Reflexion in brief

Reflexion improves an agent across trials without changing model weights. Three roles
cooperate: an **Actor** produces an attempt, an **Evaluator** scores it, and a
**Self-Reflection** model turns the score and the attempt into a short verbal lesson. The
lesson is stored in a bounded long-term memory and given to the Actor on the next trial.
The loop ends when the Evaluator passes the attempt or a maximum number of trials is reached.

For programming, the paper's agent writes its *own* unit tests (at most 6, filtered for
valid syntax) and uses them as the Evaluator; memory is limited to one reflection. It
reports 91% pass@1 on HumanEval (Python) against an 80% GPT-4 baseline. Two findings from
the paper shaped this POC:

- **The loop is only as good as its tests.** On MBPP the self-written tests passed 16% of
  incorrect solutions, and Reflexion scored *below* the baseline (77.1% vs 80.1%).
- **Retrying without reflection did not help.** In the ablation on hard Rust problems,
  removing the verbal reflection step left accuracy at the baseline (60%), and removing
  the tests made it worse (52%).

## AgentDojo in brief

AgentDojo evaluates tool-using agents that read untrusted data. A **user task** is what the
user wants; an **injection task** is what an attacker wants; an **attack** is the text that
carries the attacker's goal inside data the agent reads. Both task kinds have deterministic
checks over the environment state rather than an LLM judge. Three metrics are reported:
*benign utility*, *utility under attack*, and *targeted attack success rate* (ASR).

The paper compares several injection phrasings ("ignore previous instructions", a `TODO:`
note, and an "important message" addressed to the model, which was the strongest) and
several defences. Relevant findings: a prompt-injection *detector* lowered ASR but produced
many false positives and hurt utility; simple *tool filtering* (isolation) was the most
effective, because limiting what an agent can do holds even when the model is fooled.

## Mapping to this implementation

| Research concept | Source | Implementation here | Relationship | Simplification |
|---|---|---|---|---|
| Actor | Reflexion | `agent.generate` - one model call producing `solution.py` | Implemented directly | No ReAct/CoT scaffolding; a single completion |
| Evaluator | Reflexion | pytest on hidden tests in a Docker sandbox (`runner.py`, `evaluator.py`) | Simplified | External, human-written tests replace self-generated tests and LLM scoring |
| Verbal self-reflection | Reflexion | `agent.reflect` - a separate call that explains the failure, no code | Implemented directly | Same model with a different prompt |
| Long-term memory | Reflexion | `reflections` list in the graph state, fed to each repair | Simplified | Lives for one run only; holds at most 2 entries (paper: bounded window, 1 for programming) |
| Trial loop with max trials | Reflexion | LangGraph loop with `MAX_REPAIRS = 2` enforced by a routing function | Implemented directly | Far fewer trials than the paper's experiments |
| Feedback signal | Reflexion | Structured feedback: counts, failure type, assertion messages | Implemented directly | Test source is never shown, only failure messages |
| User task / injection task | AgentDojo | Coding task plus one of five attacker goals (`attacks.py`) | Inspired by | 3 user tasks x 5 injection tasks = 15 cases (paper: 629) |
| Attack | AgentDojo | Injected text in three of the paper's styles | Inspired by | Injected into the task text, since this agent has no tool outputs to poison |
| Deterministic security check | AgentDojo | A detector per attack over the files the model proposed | Simplified | Checks the proposal, not an environment state |
| Utility / utility under attack / ASR | AgentDojo | Task success rate, success rate on attacked tasks, share of cases `followed` | Implemented directly | Metric code is tested on synthetic records; no live values were measured |
| Data delimiters defence | AgentDojo (after Hines et al.) | Task text wrapped in `<task>` tags and declared untrusted | Implemented directly | - |
| Isolation over detection | AgentDojo-inspired | No tools at all; write allowlist; import allowlist; sandbox | Inspired by | A fixed allowlist replaces per-task tool filtering |
| Defence false positives | AgentDojo | `false_positive` outcome and `false_blocks` metric | Inspired by | - |

## Deliberate differences from the papers

- **Hidden, immutable tests instead of self-generated ones.** The paper's weakest point
  for code was unreliable self-written tests. Here the tests are written in advance and the
  agent cannot see or change them. The cost: failure messages reveal expected values (see
  `EXPERIMENT.md`, limitations), and nothing here is comparable to the paper's pass@1
  numbers.
- **The retry bound is the subject, not a detail.** The paper lets agents run many trials.
  This POC caps repairs at two and measures what that buys.
- **Injection point.** AgentDojo injects into tool results. This agent has no tools, so the
  nearest equivalent of untrusted data is the task content itself.
- **Scale and evidence.** The designed benchmark is 12 tasks and 15 security cases. It was
  validated in Mock E2E mode only, which shows that the mechanisms work, not how a model
  performs with them.

## Out of scope

Live-model benchmarking, self-generated tests, multiple models or agents, persistent or cross-task memory,
decision-making and reasoning benchmarks (ALFWorld, HotPotQA), HumanEval/MBPP reproduction,
AgentDojo's environments and tool suites, adaptive attacks, ML-based injection detectors.
