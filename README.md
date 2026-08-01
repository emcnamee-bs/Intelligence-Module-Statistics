# Intelligence Module: Statistics

A statistical judgment module for AI agents — a library of statistical models callable as
command-line scripts, plus a skill that decides **whether statistics is warranted at all** and routes
to the right model.

**Status:** design approved, research in progress. No models implemented yet.

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

## Documents

- [Design spec](docs/superpowers/specs/2026-07-31-statistical-judgment-module-design.md)
- [Research log](RESEARCH.md)
