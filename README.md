# Intelligence Module: Statistics

A statistical judgment module for AI agents — a library of statistical models callable as
command-line scripts, plus a skill that decides **whether statistics is warranted at all** and routes
to the right model.

**Status:** complete at seven models. Three independent studies say further models would be
building where there is no measured gap — see [Evidence](#evidence) below.

## Why

Research on tool-using agents finds a *confidence dichotomy by tool type*: **evidence tools** (search,
retrieval) systematically induce overconfidence, because the agent mistakes information availability
for correctness. **Verification tools** — anything that checks reasoning against a computable signal —
improve calibration. This module is a verification tool.

## Design constraints

- **Pure Python standard library.** No numpy, no scipy, no installs, no network. The Claude API
  code-execution environment has neither network access nor runtime package installation, so a
  scipy-dependent statistics tool is structurally unusable there. Pure stdlib is the only portable
  choice — and it makes the module trivially auditable.
- **Zero-token discovery.** Models are found by running `route.py`, not by reading a catalog into
  context. Scripts are executed, never read; only their output costs tokens.
- **Refuse rather than mislead.** When a model's assumptions are violated badly enough that the answer
  would deceive, the script suppresses the number entirely and says what to do instead.

## Layout

| Path | What |
|---|---|
| `SKILL.md` | The skill: gating doctrine and navigation |
| `registry.json` | Single source of truth for every model |
| `route.py` | `python3 route.py "is this slowdown real"` → ranked matches + usage |
| `INDEX.md`, `docs/families/` | Generated from the registry — never hand-edit |
| `lib/` | Pure-stdlib numerics core |
| `models/<family>/` | One script per model |
| `tests/`, `evals/` | Correctness tests and agent-behavior evaluations |
| `RESEARCH.md` | Living research log |
| `docs/superpowers/specs/` | Design documents |

## Evidence

This module is small because it was measured, not because it was rushed. Three studies, each
designed to justify expanding it, each concluding otherwise:

| Study | Method | Result |
|---|---|---|
| [Research sweep](RESEARCH.md) | 13 parallel territories | 310 models ranked, 266 cut, ~18 identity clusters found |
| [Behavioural evals](evals/RESULTS-final.md) | 9 scenarios, 18 arms, rubrics committed before running | 4 gains, 5 ties, 0 regressions. Both ordering hypotheses refuted |
| [Wrong-belief study](research/wrong-beliefs/FINDINGS.md) | 43 probes, verified by derivation | 1 defect, already covered |

**What the evidence says.** A capable agent computes most of this correctly unaided — recorded
baselines produced correct Welch t-tests, Wilson intervals, exact binomial CDFs, Hanley-McNeil
standard errors and the Sellke-Berger bound with no tools. The module earns its cost in a narrow,
identifiable minority of situations: when the agent holds a belief that is wrong in the published
literature, and when a number is **relayed rather than owned** — a claim in a PR description, a QA
note, a dashboard row — where scrutiny is optional and degrades under a competing deliverable.

The most reusable artifacts here may not be the scripts. They are the 266-entry cut list, the
recorded baselines, and the finding that the one repeatable win came from a formula whose canonical
published form is self-contradictory.

## Documents

- [Design spec](docs/superpowers/specs/2026-07-31-statistical-judgment-module-design.md)
- [Research log](RESEARCH.md) — Parts 0-3
- [Evaluation results](evals/RESULTS-final.md)
- [Wrong-belief study](research/wrong-beliefs/METHOD.md)
