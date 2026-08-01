# Design: Statistical Judgment Module

**Date:** 2026-07-31
**Repo:** https://github.com/emcnamee-bs/Intelligence-Module-Statistics
**Status:** Approved design, pending spec review

---

## 1. Purpose

Give an AI agent the ability to back a judgment call with mathematics instead of intuition, by
shipping (a) a library of statistical models callable as command-line scripts, and (b) a skill that
decides **whether statistics is warranted at all** and routes to the right model.

### Thesis

Research on tool-using agents identifies a *confidence dichotomy by tool type*: **evidence tools**
(search, retrieval) systematically induce overconfidence because the agent mistakes information
availability for correctness, while **verification tools** improve calibration by grounding reasoning
against a checkable signal. This module is a verification tool. That is why the token cost is worth
paying, and the skill states this rationale to the agent.

See `RESEARCH.md` §0.2 for sources.

### Success criteria

1. An agent facing a judgment call it would otherwise answer with "probably" reaches for the module,
   runs one script, and states a defensible number instead.
2. The module never fires on decisions where statistics adds nothing (false-positive control).
3. Every script runs on a bare `python3` with no installs and no network.
4. No script ever emits a confident number when its assumptions are violated.

---

## 2. Non-goals

- Not a general data-analysis or data-science platform. No plotting, no dataframes, no ETL.
- Not an academic reporting tool. No APA output, no publication tables.
- Not a replacement for scipy when an agent genuinely has scipy and a large dataset.
- Not domain-specific. No BrightSign-specific models in this scope.
- Not an MCP server. Plain scripts plus a skill.

---

## 3. Invocation model

Three tiers of input, plus an explicit escalation:

| Tier | Agent has | Example |
|---|---|---|
| `INLINE` | A handful of numbers or elicited beliefs, passed as flags | `--a-success 3 --a-total 40 --b-success 9 --b-total 41` |
| `DATAFILE` | A dataset already on disk | `--data runs.csv --col latency_ms` |
| `MUST-CONSTRUCT-DATA` | Nothing yet; the judgment is high-stakes enough to justify going and measuring | run the benchmark 30×, *then* model |

`MUST-CONSTRUCT-DATA` is the escalation the skill exists to teach. It is deliberately gated: the
agent should stop and build a measurement only when the decision is expensive to reverse and the
evidence genuinely isn't there.

---

## 4. Repository layout

```
Intelligence-Module-Statistics/
├── SKILL.md                     # <500 lines. Gating doctrine + navigation. Loaded on trigger.
├── README.md                    # Human-facing: what this is, how to install, how to contribute
├── RESEARCH.md                  # Living research log
├── registry.json                # SINGLE SOURCE OF TRUTH for every model
├── route.py                     # Discovery: query string -> ranked matches + usage lines
├── generate_docs.py             # registry.json -> INDEX.md + docs/families/*.md
├── INDEX.md                     # GENERATED. Family-level table of contents
├── docs/
│   ├── families/*.md            # GENERATED. One per family, each opens with a TOC
│   └── superpowers/specs/       # Design docs (this file)
├── lib/                         # Pure-stdlib numerics core. Imported by every model.
│   ├── special.py               # incomplete beta/gamma, erfinv, digamma, log-beta
│   ├── dist.py                  # distributions: pdf/logpdf/cdf/sf/ppf/rvs
│   ├── linalg.py                # small dense: cholesky, QR least squares, solve, det
│   ├── optim.py                 # brentq, brent minimize, Nelder-Mead, numeric gradient
│   ├── resample.py              # seeded RNG, bootstrap (percentile/BCa), permutation
│   ├── mcmc.py                  # Metropolis, slice sampling, R-hat and ESS diagnostics
│   ├── dataio.py                # CSV/JSON loading, column selection, messy-input handling
│   └── report.py                # Output contract, --json, refusal helper, number formatting
├── models/<family>/<descriptive_name>.py
├── tests/
│   ├── lib/                     # golden + property tests for the numerics core
│   ├── models/                  # golden + property + refusal tests per model
│   └── routing/                 # routing eval set
├── evals/                       # Behavioral scenarios + recorded baselines
└── research/territories/*.md    # Raw research reports (input to the registry)
```

**Reference-depth rule:** every file the agent may need to read links *directly* from SKILL.md.
Nested references cause partial reads (`head -100`) and incomplete information. `docs/families/*.md`
each open with a table of contents so partial reads still reveal full scope.

---

## 5. The skill

### Frontmatter

```yaml
name: statistical-judgment
description: >
  Quantifies uncertainty and tests whether a difference, trend, risk, or estimate is real, using a
  library of command-line statistical models that run on pure Python with no dependencies. Use when
  about to state a number, range, probability, or comparison that is not directly observed — when
  reaching for "probably", "roughly", "seems like", "should be fine", or "that's within noise" on a
  decision that is expensive to reverse. Covers: is this difference real, how sure am I, what happens
  next, did X cause Y, how many samples are enough, how do I combine conflicting sources, is this an
  anomaly, how bad can it get, which option should I pick, am I overconfident, when will it fail,
  which explanation is better supported.
```

Constraints honored: `name` is lowercase-hyphen, ≤64 chars, contains no reserved word.
`description` is third person, ≤1024 chars, states both what it does and when to use it, and is
deliberately trigger-dense because agents under-trigger skills.

### Body structure (target ~200 lines)

1. **Why bother** — the verification-tool rationale, two sentences.
2. **The gate** — Tier 0 through Tier 3 (below). This is the most important section and comes first.
3. **How to find a model** — `python3 route.py "<plain description of your predicament>"`, plus the
   grep fallback over `docs/families/`.
4. **How to read the output** — the result contract and what `REFUSED` means.
5. **Family map** — 12 one-line entries linking directly to `docs/families/*.md`.
6. **Red flags** — self-check list for both failure directions (skipping stats when needed; performing
   statistics as theater).

### The gating doctrine

| Tier | Condition | Action |
|---|---|---|
| **0 — Don't** | The answer is already determined, the decision is cheap to reverse, or no number would change the action | Say so. Do not run anything. |
| **1 — Inline** | A few numbers or elicited beliefs exist | Run a model with flags. Seconds. |
| **2 — Data file** | A relevant dataset already exists | Point a model at it. |
| **3 — Construct data** | High-stakes, hard to reverse, and the evidence does not yet exist | Stop; build the measurement; then model. |

Tier 0 is load-bearing. The one measured comparison available (`bayesian-workflow`: 90.5% → 100%
task success at **+29% time and +87% tokens**) shows a deep skill is expensive. A module that fires
on trivia is net-negative, and manufactures false authority besides.

**Guidance form.** Tier 0 is expressed as a *conditional keyed on observable predicates* (is the
decision reversible? would any number change the action?), not as a prohibition with exemptions —
prohibition-shaped guidance invites negotiation under competing incentives.

---

## 6. `registry.json` — single source of truth

Every model has exactly one registry entry. `INDEX.md` and `docs/families/*.md` are generated from
it and are never hand-edited; CI fails if regenerating produces a diff.

```json
{
  "schema_version": 1,
  "families": [
    {"id": "signal-vs-noise", "question": "Is this difference real?"}
  ],
  "models": [
    {
      "id": "two-proportion-difference-bayesian",
      "path": "models/signal-vs-noise/two_proportion_difference_bayesian.py",
      "family": "signal-vs-noise",
      "title": "Bayesian comparison of two rates or proportions",
      "situations": [
        "is the new version's failure rate actually lower",
        "did the pass rate improve or is it noise",
        "compare two success rates with small samples"
      ],
      "keywords": ["proportion", "rate", "conversion", "pass rate", "failure rate", "binary"],
      "tier": "INLINE",
      "usage": "--a-success N --a-total N --b-success N --b-total N [--prior jeffreys|uniform]",
      "output": "P(B better than A), credible interval on the difference",
      "cost": "instant",
      "refuses_when": "any total < 1, or successes > total"
    }
  ]
}
```

**`situations` is the retrieval index.** Skill-retrieval research finds terminology mismatch to be
the dominant failure mode of naive skill selection, so entries are phrased the way an agent describes
its predicament, with synonym coverage — not as formal model names. Minimum three phrasings per model.

---

## 7. `route.py` — discovery

```
python3 route.py "is this 8% slowdown real or did I get unlucky"
```

Prints at most 3 matches, each as: title, one-line output meaning, tier, and the exact usage line.
Scoring is BM25-style term weighting over `situations` + `keywords` + `title`, computed in pure
stdlib against the registry.

**Two behaviors that matter as much as ranking:**

- If the top score falls below a **no-match floor**, print `NO CONFIDENT MATCH` plus the family list,
  rather than confidently returning an irrelevant model. The floor is not guessed: it is calibrated
  against the L5 eval set to the value maximizing recall subject to zero false positives on the
  should-match-nothing queries, and the calibration is recorded next to the constant.
- `--family <id>` lists a family; `--id <model-id>` prints one usage block. These let the skill route
  without re-reading markdown.

Constants (score floor, result count) are documented with their reasoning in the source — no voodoo
constants.

---

## 8. Model script contract

Every model is a standalone `python3 models/<family>/<name>.py` with an `argparse` interface, so
`--help` always yields exact usage without the agent reading the file.

### Header comment — fixed schema, ≤12 lines, ~120 token budget

```python
# WHAT        One sentence: what this models.
# WHEN        The situation that should make you reach for this.
# INPUTS      Each flag, its meaning, its units.
# OUTPUT      What the returned numbers mean.
# ASSUMPTIONS What must be true for the answer to be valid.
# EXAMPLE     One runnable command.
```

Normal operation reads **zero** script bodies: the router supplies the usage line and `--help`
supplies detail. The header exists for grep and for human readers.

### Output contract

Success (exit 0):
```
MODEL: Bayesian comparison of two rates or proportions
RESULT
  p_b_better_than_a: 0.973
  diff_median: 0.147
  diff_ci95: [0.021, 0.281]
INTERPRETATION: B is very likely better than A; the improvement is probably between 2 and 28 points.
CAVEAT: With 40 trials per arm the interval is wide; a 3-point difference remains plausible.
```

Refusal (exit 3) — **no headline number anywhere in the output**:
```
MODEL: Bayesian comparison of two rates or proportions
REFUSED: b_success (12) exceeds b_total (10).
WHY IT MATTERS: The inputs are inconsistent, so any posterior would be meaningless.
DO INSTEAD: Re-check which number is the denominator, then re-run.
```

Usage error: exit 2, argparse's own message.

**Exit codes: `0` ok, `2` usage error, `3` refused.** Refusal is deliberately *not* 2, because
`argparse` already exits 2 on bad arguments; overloading it would make "you typed the flag wrong"
indistinguishable from "your data violates the model's assumptions" — two situations demanding
opposite responses from the agent.

`--json` emits the same content as a machine-readable object, including `"status": "ok" | "refused"`.

### Refusal semantics — the key design decision

When assumptions are violated severely enough that the result would mislead, the script **suppresses
the headline number** rather than printing it beside a warning. This is driven by observed agent
behavior: in the one measured study available, agents *ignored diagnostics signalling unreliable
results and reported the number anyway*. A warning adjacent to a number does not work.

Three severity levels:
- **OK** — assumptions hold; normal output.
- **CAVEAT** — assumptions strained but the number is still informative; number printed, caveat line
  mandatory.
- **REFUSED** — number suppressed, exit 3, concrete remedy given.

Each model's registry entry records its `refuses_when` condition, and each model has at least one
test asserting the refusal fires.

### Error handling

Scripts solve rather than punt: malformed CSV, missing columns, wrong delimiters, and non-numeric
cells produce a specific actionable message naming the observed problem — never a traceback.

---

## 9. `lib/` — the numerics core

Pure stdlib (`math`, `statistics`, `random`, `itertools`, `csv`, `json`, `argparse`). This is the
highest-risk component: every model's correctness rests on it, so it gets the hardest tests.

Feasibility is real. `math` supplies `lgamma`, `gamma`, `erf`, `erfc`; `statistics` supplies
`NormalDist.inv_cdf`. The missing primitives are the regularized incomplete beta and gamma functions,
which unlock Student-t, chi-square, F, beta, and gamma.

### Accuracy policy

- Golden tests assert against **published reference values** (ASA063 incomplete beta, ASA032
  incomplete gamma, NIST StRD datasets, textbook tables) — **never** against SciPy output, which is
  not available in the target environment and uses different algorithms with different error
  characteristics.
- Every special function declares a **stated accuracy envelope**: maximum relative error over a
  stated input domain, enforced by test.
- Outside its declared domain a function raises rather than silently returning garbage.

---

## 10. Scenario taxonomy — 12 families

| # | Family id | The question an agent is asking | Research territories feeding it |
|---|---|---|---|
| 1 | `signal-vs-noise` | Is this difference real? | 04, 06, 13 |
| 2 | `estimation` | How big is it, and how sure am I? | 01, 04, 11 |
| 3 | `forecasting` | What happens next? | 03 |
| 4 | `causal` | Did X actually cause Y? | 02 |
| 5 | `evidence-sufficiency` | How much data before I can decide? | 06 |
| 6 | `synthesis` | How do I combine conflicting sources? | 08 |
| 7 | `monitoring` | Anomaly, or normal variation? | 13 |
| 8 | `tail-risk` | How bad can it plausibly get? | 05 |
| 9 | `decision` | Which option, and is more info worth buying? | 10, 01 |
| 10 | `calibration` | Am I over- or under-confident? | 07 |
| 11 | `duration-reliability` | When will it fail / how long will it take? | 09 |
| 12 | `model-choice` | Which explanation should I believe? | 12 |

Thirteen research territories map onto twelve routing families; several territories feed more than
one family. Families may be revised once research lands, and the registry is the mechanism for doing
so cheaply.

---

## 11. Verification

Six levels. Levels 1–4 are code correctness; 5–6 are agent behavior.

| Level | Scope | Gate |
|---|---|---|
| **L1** | `lib/` golden tests vs published reference values | Every special function within its declared error envelope |
| **L2** | Per-model golden cases | ≥2 cases per model with literature-published or hand-verifiable answers |
| **L3** | Property tests | Monotonicity, limiting behavior, symmetry, invariance where applicable |
| **L4** | Refusal tests | ≥1 input per model that must exit 3 with no number emitted |
| **L5** | Routing evals | Recall@3 on a labelled query set, **and** false-positive control: queries that must return `NO CONFIDENT MATCH` |
| **L6** | Behavioral evals | Full scenarios run with and without the skill, against a **pre-recorded baseline** |

**L6 is recorded before any model code is written.** Both the official skill-authoring guidance and
the project's own `tdd.md` require establishing baseline failure before writing the fix; the one
measured precedent in this space obtained its numbers exactly this way. Baselines are stored in
`evals/baselines/` with the verbatim reasoning the agent produced unaided.

L5 covers both directions deliberately: a router that never misses but fires constantly is worse
than useless, because it converts the Tier 0 gate into noise.

CI (GitHub Actions): run all tests on a clean `python3` with no third-party packages installed;
regenerate `INDEX.md` and `docs/families/` and fail on any diff; assert no model imports anything
outside the standard library and `lib/`.

---

## 12. Delivery waves

### Wave 0 — prove the contract (gate)

1. Record L6 baselines: representative judgment tasks run **without** the module, failures captured
   verbatim.
2. `lib/special.py`, `lib/dist.py`, `lib/optim.py`, `lib/resample.py`, `lib/report.py` with L1 golden
   tests green. (These five are exactly what the three pilot models need: beta/t distributions,
   root-finding to fit elicited quantiles, and resampling for the benchmark comparison.
   `linalg.py`, `mcmc.py`, and `dataio.py` are deferred to Wave 1.)
3. `registry.json` schema, `route.py`, `generate_docs.py`, CI drift check.
4. **Three pilot models**, one per input tier, chosen to exercise the refusal path:
   - `two_proportion_difference_bayesian` — INLINE, counts only
   - `benchmark_regression_from_repeated_runs` — DATAFILE / MUST-CONSTRUCT-DATA
   - `elicited_quantiles_to_distribution` — INLINE, no data at all
5. Full L1–L5 ladder green on those three.

**→ User review gate.** Contract problems get found on 3 scripts, not 30.

### Wave 1 — the high-leverage core

~30 models, selected from the research sweep by *frequency × leverage × feasibility*, spanning all
12 families. Full test ladder per model. L6 evals re-run against baseline.

**→ User review gate.**

### Wave 2+ — the long tail

Remaining ranked models, in priority order, same standards.

---

## 13. Risks

| Risk | Mitigation |
|---|---|
| `lib/` numerics subtly wrong; every model inherits the error | Published-reference golden tests, declared accuracy envelopes, raise-outside-domain |
| Router misses the right model due to terminology mismatch | `situations` phrased as agent predicaments with synonym coverage; L5 recall evals |
| Skill over-triggers and produces statistical theater | Tier 0 gate stated first and as an observable-predicate conditional; L5 false-positive evals |
| Agent reports a number the tool flagged as unreliable | Refusal suppresses the number entirely; L4 tests |
| Token cost outweighs benefit | Zero-cost discovery via `route.py`; scripts executed not read; SKILL.md kept small |
| Research produces models that are infeasible in stdlib | Feasibility rating required in every research report; infeasible entries go to the cut list, not the registry |

---

## 14. Conventions

- Python 3.9+ (widest availability), standard library only, no third-party imports anywhere.
- Forward slashes in all paths.
- Model filenames are descriptive of what is modeled: `two_proportion_difference_bayesian.py`, not
  `prop_test.py`.
- Every threshold and constant is documented with its reasoning at the point of definition.
- No time-sensitive statements in SKILL.md or model headers.
