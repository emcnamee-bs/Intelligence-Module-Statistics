# Design: Statistical Judgment Module

**Date:** 2026-07-31 (revised after the 13-territory research sweep)
**Repo:** https://github.com/emcnamee-bs/Intelligence-Module-Statistics
**Status:** Revised design, pending review
**Research basis:** `RESEARCH.md` — 310 models ranked, 266 cut, 576 candidates evaluated

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
paying, and the skill states this rationale to the agent. (`RESEARCH.md` §0.2)

### Success criteria

1. An agent facing a judgment call it would otherwise answer with "probably" reaches for the module,
   runs one script, and states a defensible number instead.
2. The module never fires on decisions where no number could change the action — and can now *prove*
   that case rather than judge it (§5).
3. Every script runs on a bare `python3` with no installs and no network.
4. No script ever emits a confident number when its assumptions are violated, when the question has
   no answer, or when it fails to beat its own declared baseline.

---

## 2. Non-goals

- Not a general data-analysis platform. No plotting, no dataframes, no ETL.
- Not an academic reporting tool. No APA output.
- Not domain-specific. No BrightSign-specific models in this scope.
- Not an MCP server. Plain scripts plus a skill.
- **Does not generate estimates on the agent's behalf.** LLM-elicited priors measure at effective
  sample size zero (`RESEARCH.md` §1.17). The module consumes stated numbers and checks, propagates,
  and stress-tests them. A script that *asks* for a prior is fine; one that invents a prior is a
  liability.

---

## 3. The ten governing principles

Extracted from the sweep (`RESEARCH.md` §2.1), several from independent directions. Every design
decision below traces to one.

| # | Principle |
|---|---|
| **P1** | Exactness comes from **enumeration under exchangeability**, not from resampling. The bootstrap is an asymptotic approximation and fails hardest at agent-scale n |
| **P2** | **Never route on an assumption test.** A passing check is not evidence unless its power against the specific failure is established |
| **P3** | **Trust thresholds scale with n**; several are arithmetic impossibilities, not conventions |
| **P4** | **Report breakdown values, not pass/fail** |
| **P5** | The dangerous failures are **composition, provenance, and incomplete reporting** — not model choice |
| **P6** | **Pseudo-replication** is the dominant violation when combining sources |
| **P7** | The module **consumes stated numbers; it never generates them** |
| **P8** | **The decision to use statistics is itself computable** |
| **P9** | Every model **declares the baseline it must beat**, and prints the baseline instead when it doesn't |
| **P10** | **Big-data ML benchmark results do not transfer** to agent scale |

---

## 4. Invocation model

| Tier | Agent has | Example |
|---|---|---|
| `INLINE` | A handful of numbers or stated beliefs, passed as flags | `--a-success 3 --a-total 40 --b-success 9 --b-total 41` |
| `DATAFILE` | A dataset already on disk | `--data runs.csv --col latency_ms` |
| `MUST-CONSTRUCT-DATA` | Nothing yet; the judgment justifies going and measuring | run the benchmark 30×, *then* model |

Escalation to Tier 3 is no longer a judgment call — it is the output of the value-of-information check
in §5.

---

## 5. The gate — now computable (P8)

**This replaces the heuristic gating doctrine of the previous revision.**

The old design asked the agent to judge whether statistics was warranted ("is this reversible?",
"would a number change the action?"). Those are heuristics an overconfident agent can talk itself
past in either direction.

Value-of-information theory makes the gate arithmetic. **The skill's first act is always the same:**

```
python3 models/decision/value_of_information_reachability.py \
    --options "ship,hold" --loss-if-wrong 40 --current-belief 0.7 --cost-to-measure 2
```

For many proposed measurements the Expected Value of Sample Information is **exactly zero at any
accuracy** — no data could move the decision — and this is provable in about three lines
(`RESEARCH.md` §1.21). The output routes directly:

| EVPI result | Action |
|---|---|
| EVPI = 0 | **Stop.** No measurement can change the decision. The agent now has a *number* justifying stopping. |
| 0 < EVPI < cost to measure | **Stop.** Information is worth less than it costs. |
| EVPI > cost, data exists | Tier 1 or 2 — route to a model. |
| EVPI > cost, data does not exist | **Tier 3.** Constructing the dataset is justified; the check says by how much. |

This single tool is simultaneously the Tier 0 gate, the Tier 3 escalation trigger, and a model in its
own right. It also answers the cost objection honestly: the module's opening move is a cheap check on
whether it should run at all.

**Fallback.** When the decision cannot be put in a loss table (no quantified stakes), fall back to the
qualitative gate: if the decision is cheap to reverse or the answer is already determined, stop.

---

## 6. Repository layout

```
Intelligence-Module-Statistics/
├── SKILL.md                     # <500 lines. The gate + navigation. Loaded on trigger.
├── README.md
├── RESEARCH.md                  # Research log (Parts 0-2)
├── registry.json                # SINGLE SOURCE OF TRUTH
├── route.py                     # Discovery: query -> ranked matches + usage
├── generate_docs.py             # registry.json -> INDEX.md + docs/families/*.md
├── INDEX.md                     # GENERATED
├── docs/
│   ├── families/*.md            # GENERATED, one per family, each opens with a TOC
│   └── superpowers/specs/
├── lib/
│   ├── special.py               # regularized incomplete beta; incomplete gamma + inverse. That is all.
│   ├── dist.py                  # distributions: pdf/logpdf/cdf/sf/ppf (sampling comes free from `random`)
│   ├── exact.py                 # CORE: permutation enumeration, rank-statistic nulls by DP,
│   │                            #       order statistics, math.comb combinatorics
│   ├── grid.py                  # CORE: 1-3 parameter Bayesian quadrature (no diagnostics needed)
│   ├── optim.py                 # brentq, brent minimize, Nelder-Mead
│   ├── report.py                # output contract, --json, the five output modes
│   ├── dataio.py                # CSV/JSON loading, messy-input handling        [Wave 1]
│   ├── linalg.py                # small dense: cholesky, QR least squares       [Wave 1]
│   ├── bootstrap.py             # DEMOTED. Behind measured small-n refusals.    [Wave 2]
│   └── mcmc.py                  # 4-10 param fallback, behind R-hat/ESS gating  [Wave 2]
├── models/<family>/<descriptive_name>.py
├── tests/{lib,models,routing}/
├── evals/                       # behavioral scenarios + recorded baselines
└── research/territories/*.md    # 13 reports, ~5000 lines
```

`INDEX.md` and `docs/families/` are **generated**; CI fails if regenerating produces a diff.
All reference files link **directly** from SKILL.md — nested references cause partial reads.

---

## 7. `registry.json` — single source of truth

```json
{
  "schema_version": 1,
  "families": [{"id": "signal-vs-noise", "question": "Is this difference real?"}],
  "implementations": [
    {"id": "exact-binomial-coverage-inequality",
     "path": "lib/exact.py:coverage_inequality",
     "note": "n >= ln(alpha)/ln(p). Backs 5 registry entries across 4 families."}
  ],
  "models": [
    {
      "id": "zero-events-observed-upper-bound",
      "path": "models/tail-risk/zero_events_observed_upper_bound.py",
      "implementation": "exact-binomial-coverage-inequality",
      "family": "tail-risk",
      "title": "Upper bound on a rate after observing zero events",
      "situations": [
        "it hasn't failed once in 200 runs, how safe is it really",
        "no errors so far, what rate can I rule out",
        "zero failures observed what can I claim"
      ],
      "keywords": ["zero events", "rule of three", "no failures", "clean run"],
      "tier": "INLINE",
      "usage": "--trials N [--confidence 0.95]",
      "output": "upper bound on the true rate, and the n needed for a target bound",
      "baseline_to_beat": "assuming the rate is zero",
      "naive_answer_is_wrong": false,
      "refuses_when": "trials < 1",
      "composition_hazards": [],
      "data_provenance_required": null,
      "independence_required": false
    }
  ]
}
```

**Field rationale** — each closes a failure the sweep found:

| Field | Closes |
|---|---|
| `situations` (≥3 phrasings) | Terminology mismatch, the dominant skill-retrieval failure |
| `implementation` | The identity clusters (§8) — many entries, one tested implementation |
| `baseline_to_beat` | P9 |
| `naive_answer_is_wrong` | Models where the obvious answer is *actively misleading*, not merely imprecise (staggered DiD, Kelly folklore, kurtosis heavy-tail detection). Router surfaces the warning even on a weak match |
| `composition_hazards` | P5 — names model ids that must not be chained into this one |
| `data_provenance_required` | Mixed-elicitation calibration logs, adaptively-collected studies |
| `independence_required` | P6 — pseudo-replication |

---

## 8. Identity clusters — fewer implementations than entries

Three clusters where differently-named models are the same mathematics (`RESEARCH.md` §2.2):

| Cluster | Identity | Surfaces as |
|---|---|---|
| **C1** | `n ≥ ln(α)/ln(p)` | rule of three; Wilks tolerance interval; upper CI on a high quantile; zero-failure MTBF; reruns-to-confidence for flaky tests |
| **C2** | marginal EVSI = marginal cost | closed-form EVSI/ENBS; Beta-Binomial EVSI; Weitzman reservation values; optimal sample size; stop-or-continue |
| **C3** | exact null by DP over rank statistics | permutation test; Mann–Whitney; signed-rank; exact CI by test inversion |

C1 alone spans four families and was found by three territories independently. **A dedup pass runs
before any model code is written.** One tested implementation, many registry entries routing into it.

---

## 9. Model script contract

Standalone `python3 models/<family>/<name>.py` with `argparse`, so `--help` always yields exact usage
without reading the file.

### Header — fixed schema, ≤12 lines, ~120 token budget

```python
# WHAT        One sentence: what this models.
# WHEN        The situation that should make you reach for this.
# INPUTS      Each flag, its meaning, its units.
# OUTPUT      What the returned numbers mean.
# BASELINE    What this must beat, and what happens if it doesn't.
# ASSUMPTIONS What must be true for the answer to be valid.
# EXAMPLE     One runnable command.
```

### Six output modes

Three of these (`ROBUSTNESS`, `BASELINE_WINS`, `NO ANSWER EXISTS`) did not exist before the research
sweep. Each closes a failure mode the previous revision would have shipped.

| Mode | Exit | When | Prints a number? |
|---|---|---|---|
| `OK` | 0 | Assumptions hold, baseline beaten | Yes |
| `CAVEAT` | 0 | Strained but informative | Yes + mandatory caveat line |
| `ROBUSTNESS` | 0 | Assumption is a matter of degree (P4) | Yes + **breakdown value**: how strong the violation must be to overturn the conclusion |
| `BASELINE_WINS` | 0 | Model fails to beat its declared baseline (P9) | **The baseline's answer**, not the model's |
| `NO ANSWER EXISTS` | 4 | The question is malformed regardless of data | **No** — explains why, and what decidable question to ask instead |
| `REFUSED` | 3 | Structural violation; a number would mislead | **No** — states the violation and a concrete remedy |

Usage error is exit `2` (argparse's own). **Refusal is deliberately not 2**, because overloading it
would make "you typed the flag wrong" indistinguishable from "your data violates the model" — two
situations demanding opposite responses.

`--json` emits the same content with `"status"` set to the mode.

### Why refusal suppresses the number

Agents have been observed **ignoring diagnostics signalling unreliable results and reporting the
number anyway** (`RESEARCH.md` §0.3). A warning adjacent to a number does not work.

`NO ANSWER EXISTS` is a distinct and arguably higher-value mode: the inputs are fine and the model is
right, but the question as posed is unanswerable. Examples from the sweep — "when should I give up on
this long-running process?" has no threshold answer under decreasing hazard (the optimal policy is
never abandon); reliability-growth extrapolation is formally unsupported; multi-parameter EVPPI is out
of stdlib reach and the tool should say so rather than approximate.

### Hard arithmetic floors (P3)

Not conventions. Facts about what a design can express. All ship as refusals:

| Situation | Floor |
|---|---|
| Two-sided p<0.05, two-sample | Unreachable at n₁=n₂=3 (min p = 0.10) |
| Two-sided p<0.05, paired | Unreachable at n≤5 (min p = 0.0625) |
| 95% distribution-free median CI | First exists at n=6 |
| Split conformal, 95% | n ≥ 19 |
| `[min,max]` as prediction interval | 71% coverage at n=6; needs n=39 for 95% |
| Two-sided 95/95 Wilks tolerance | n = 93 |
| Robust z via MAD | MAD = 0 on data like `[10,10,10,11,10,40]` → IQR fallback required |
| Heavy tails via kurtosis | Bounded by ≈n−1; at n=10 Cauchy cannot look heavier-tailed than normal. Use `max|x|/Σ|x|` |

---

## 10. Scenario taxonomy — 12 families

| # | Family id | The question | Territories |
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

---

## 11. Verification

| Level | Scope | Gate |
|---|---|---|
| **L1** | `lib/` golden tests vs **published reference values** — never against SciPy | Every function within its declared error envelope |
| **L2** | Per-model golden cases | ≥2 cases with literature-published or hand-verifiable answers |
| **L3** | Property tests | Monotonicity, limits, symmetry, invariance |
| **L4** | Refusal tests | ≥1 input per model per applicable mode (3, 4, `BASELINE_WINS`) with no number emitted |
| **L5** | Routing evals | Recall@3 on a labelled query set **and** false-positive control on should-match-nothing queries |
| **L6** | Behavioral evals | Full scenarios with and against a **pre-recorded baseline** |

**Two requirements the sweep forced:**

1. **Any SBC harness must use data-dependent test quantities** (joint log-likelihood at minimum), not
   parameter ranks alone. An implementation whose posterior equals the prior passes classic
   rank-based SBC perfectly (Modrák et al. 2023) — and a model that silently ignores its data while
   producing confident output is this project's worst failure mode. (`RESEARCH.md` §1.34)
2. **P2 applies to our own tests.** A passing check is not evidence unless its power against the
   specific failure has been established. This bit three times in the sweep — in routing, in
   assumption testing, and in correctness testing.

**Wave 1 definition of done includes primary-source verification of every constant that ships.** Five
territories exhausted their search budget; no unverified constant may enter a lookup table, because
an agent treats a shipped number as authoritative.

CI: run on a clean `python3` with no third-party packages; regenerate docs and fail on diff; assert no
model imports outside the standard library and `lib/`.

---

## 12. Delivery waves

### Wave 0 — prove the contract (gate)

1. **Record L6 baselines**: representative judgment tasks run *without* the module, failures captured
   verbatim.
2. **Dedup pass** over the 310 ranked models → implementation list + registry entries (§8).
3. `lib/special.py`, `lib/dist.py`, `lib/exact.py`, `lib/grid.py`, `lib/optim.py`, `lib/report.py`
   with L1 golden tests green.
4. `registry.json`, `route.py`, `generate_docs.py`, CI drift check.
5. **Four pilot models**, chosen to exercise every tier and every output mode:
   - `value_of_information_reachability` — the gate itself (§5); must produce EVPI = 0 on a
     constructed case
   - `zero_events_observed_upper_bound` — INLINE, C1 cluster, exercises `NO ANSWER EXISTS` at n=0
   - `benchmark_regression_from_repeated_runs` — DATAFILE/MUST-CONSTRUCT, exercises `BASELINE_WINS`
     and the p<0.05-unreachable floor at n=3
   - `three_point_estimate_to_range` — INLINE, no data; ships the corrected PERT variance
     `(μ−a)(b−μ)/7` with the R(δ) identity in its golden tests (`RESEARCH.md` §1.37)
6. Full L1–L5 ladder green on those four.

**→ Review gate.** Contract problems get found on four scripts, not thirty.

### Wave 1 — the high-leverage core

~30 models by *frequency × leverage × feasibility*, spanning all 12 families, leading with the
anytime-valid family (cheapest to implement and best matched to how agents actually collect evidence).
Primary-source verification of every constant. L6 re-run against baseline.

**→ Review gate.**

### Wave 2+ — long tail, plus `bootstrap.py` and `mcmc.py` behind their refusals.

---

## 13. Risks

| Risk | Status after the sweep | Mitigation |
|---|---|---|
| `lib/` numerics wrong | **Downgraded.** Core is two special functions; measured timings show nothing is hard | Published-reference golden tests, declared error envelopes |
| A model silently ignores its data | **New top risk.** Passes standard SBC | Data-dependent SBC test quantities (§11) |
| Router misses due to terminology | Unchanged | `situations` phrasing, L5 recall evals |
| Skill over-triggers | **Downgraded.** Now computable | EVPI reachability as the first act (§5) |
| Agent reports a flagged number | Unchanged | Refusal suppresses the number; L4 tests |
| Unverified constants ship | **New.** Five territories hit search caps | Wave 1 definition of done; no unverified lookup tables |
| Composition errors between tools | **New.** Five hazards found | `composition_hazards` registry field; router prints them |

---

## 14. Conventions

- Python 3.9+, standard library only, no third-party imports anywhere.
- Forward slashes in all paths.
- Descriptive model filenames: `zero_events_observed_upper_bound.py`, not `rule3.py`.
- Every threshold documented with its reasoning at the point of definition; thresholds that depend on
  n are written as functions of n (P3).
- No time-sensitive statements in SKILL.md or model headers.
