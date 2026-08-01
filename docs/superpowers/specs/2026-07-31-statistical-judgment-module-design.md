# Design: Statistical Judgment Module

**Date:** 2026-07-31 · **Revision 3** — after the 13-territory sweep, 7 recorded baselines, and 5 adversarial reviews
**Repo:** https://github.com/emcnamee-bs/Intelligence-Module-Statistics
**Evidence:** `RESEARCH.md` (Parts 0–3) · `evals/baselines/RESULTS.md` · `research/reviews/`

---

## 1. What the evidence changed

Revision 2 assumed agents answer judgment calls with "probably" and need a library to compute for
them. **Seven recorded baselines refuted that.** Fresh agents with no tools passed 23 of 25 required
criteria, computing Welch t-tests, Wilson score intervals, exact binomial CDFs and the rule of three
correctly — several verified to three decimal places. Three of them reframed the problem better than
the model this spec planned to ship for it.

Revision 3 is built on what the baselines *couldn't* do.

### The selection principle

> **A model earns a slot only if it does something the baselines demonstrably cannot:**
> **(a)** encodes a fact the agent has no way to know it doesn't know,
> **(b)** corrects a formula it reliably gets wrong, or
> **(c)** refuses something it would otherwise confidently do.
>
> **Computation alone does not qualify.**

This is the spec's central rule. It cuts the catalogue from 310 candidates to ~14, and it cuts two of
revision 2's own pilots.

### Success criteria

1. Every shipped entry point traces to (a), (b), or (c) above, with the baseline evidence cited.
2. Runs on a bare `python3` — no installs, no network.
3. When a number would mislead, none is printed, and the exit code makes that unmissable.
4. Total token cost of a typical use is stated honestly and measured, not asserted.

### Non-goals

Not a data-analysis platform. Not academic reporting. Not domain-specific. Not an MCP server.
**Does not generate estimates on the agent's behalf** — LLM-elicited priors measure at effective
sample size zero (`RESEARCH.md` §1.17). It consumes stated numbers and checks them.

---

## 2. The skill

*(Revision 2 deleted this section. Restored and expanded.)*

```yaml
name: statistical-judgment
description: >
  Checks whether a statistical claim is even reachable from the data at hand, corrects formulas that
  are commonly wrong, and refuses conclusions the evidence cannot support. Use when about to state a
  number, range, probability, or comparison that is not directly observed — a p-value, confidence
  interval, effect size, failure rate, estimate, forecast, or "X is better than Y" — and especially
  when the sample is small, when several things were compared or several checks run before a pattern
  was noticed, when combining results from multiple runs, agents, or sources, when deciding whether
  more data is worth collecting, or when asked how long something will take. Also use before
  concluding a search or investigation is complete.
```

Constraints met: lowercase-hyphen name ≤64 chars, no reserved word, third-person description
≤1024 chars stating both function and trigger, deliberately trigger-dense because agents under-trigger.

Note the description leads with **checks / corrects / refuses**, not "computes." That is the
selection principle expressed where discovery happens.

### SKILL.md body — target ≤120 lines

1. **Why this exists** (3 sentences). Verification tools improve agent calibration; evidence tools
   degrade it (`RESEARCH.md` §0.2). Then the honest part: *you can already compute most of this
   correctly. What you cannot do is know what you were never told, or catch yourself doing something
   that felt reasonable.*
2. **Start here** — `python3 route.py "<your predicament in plain words>"`. One command. The gate is
   inside it (§3).
3. **How to read output** — the four outcomes and the `REPORT AS:` line.
4. **Entry-point map** — one line each, linking directly to `docs/families/*.md`.
5. **Three things worth knowing before you compute anything** — the highest-value facts, inline
   because they change behaviour before any script runs: implicit multiplicity, the p<0.05 floors,
   and pseudo-replication when combining sources.

---

## 3. Discovery and the gate — one command

*(Revision 2 made the gate a separate mandatory first step. Three reviews independently rejected it:
`EVPI = min(p,1−p)·L` is nonzero except in degenerate cases so its acceptance criterion was
unsatisfiable; `EVSI(n) ≤ EVPI` makes the "go measure" direction invalid; it was cleanly populable in
0 of 6 baseline scenarios; and it demanded exactly the numbers P7 forbids the module to invent.
Nothing enforced it, and it relitigated a decision the agent made one turn earlier.)*

**The gate folds into the router, so complying is the cheapest path rather than an extra step.**

```
$ python3 route.py "is this 8% slowdown real or did I get unlucky"

BEFORE YOU COMPUTE
  What size difference would change what you do? If any plausible answer leads to the
  same action, stop — you do not need this.

MATCHES
  1. minimum_attainable_p_for_design   [INLINE]  can your design even detect it
     python3 models/design/minimum_attainable_p_for_design.py --n1 5 --n2 5
  2. benchmark_runs_needed             [INLINE]  how many runs to detect a given effect
     python3 models/design/benchmark_runs_needed.py --effect 0.08 --sd 0.05
```

The precheck is a **minimum-interesting-effect question**, not a loss table — reviews 03 and
`RESEARCH.md` §1.33 both concluded that is the form agents can actually answer. It costs one line and
requires no fabricated inputs.

**Router contract.** BM25-style term weighting over `situations` + `keywords` + `title`, pure stdlib.
At most 3 matches. Below a **no-match floor** it prints `NO CONFIDENT MATCH` plus the family list
rather than returning something irrelevant; the floor is calibrated against the L4 routing eval set to
maximise recall subject to zero false positives on should-match-nothing queries, and the calibration
is recorded beside the constant. `--family <id>` lists a family; `--id <model-id>` prints one usage
block. When a match declares `composition_hazards`, the router prints them with the match.

A separate `decision_threshold_check` model exists for the minority of cases where a real loss table
*is* available. It is a model, not a gate.

---

## 4. Governing principles

From `RESEARCH.md` §2.1, with corrections from review 02 applied.

| # | Principle | Status |
|---|---|---|
| **P1** | Exactness comes from enumeration under exchangeability, not resampling | verified (bootstrap coverage 0.750/0.770/0.885 at n=6) |
| **P2** | Never route on an assumption test; a passing check is not evidence unless its power is established | verified 3× independently |
| **P3** | Trust thresholds scale with n; several are arithmetic impossibilities | **all six floors verified by enumeration** |
| **P4** | Report breakdown values, not pass/fail | design principle |
| **P5** | The dangerous failures are composition, provenance, incomplete reporting | **evidence weakened** — flagship ARL example was 9% not 76% (§3.14); principle stands, magnitude does not |
| **P6** | Pseudo-replication dominates when combining sources | design principle; Vovk–Wang fix **proved valid and tight** |
| **P7** | The module consumes stated numbers; it never generates them | binding |
| **P8** | ~~The decision to use statistics is computable~~ | **RETIRED.** See §3 |
| **P9** | Every model declares what it must beat | **narrowed** — `baseline_to_beat` is nullable; only models with a defined comparison operator declare one |
| **P10** | Big-data ML benchmark results do not transfer to agent scale | verified |

---

## 5. Engines — the real structure

Three independent passes found **~18 identity clusters** inside 310 ranked models. The library is not
a catalogue over a numerics core; it is a small set of engines with thin, situation-specific entry
points.

**Cluster unification must be verified per member.** C1 was asserted at 5/5 and verified at **4/6** —
the two-sided Wilks interval is transcendental and does not reduce to `n ≥ ln α / ln p`. Every engine
below carries a membership test in its golden suite.

| Engine | Identity | Verified members | Backs |
|---|---|---|---|
| `lib/exact_tail.py` | exact discrete-tail inversion | pending per-member test | ~11 territories; C1 is its k=0 case |
| `lib/independence.py` | `1 − (1−p)^k` | fan-out ≡ return period ≡ Šidák ≡ reruns-to-confidence | multiplicity, monitoring, reliability |
| `lib/effective_n.py` | design effect / n_eff | 6 territories | pseudo-replication, pooling, autocorrelated series |
| `lib/invert.py` | test inversion by bisection | 8 territories | every interval built from a test |
| `lib/rank_null.py` | exact rank-statistic nulls by DP | permutation, Mann–Whitney, signed-rank | signal-vs-noise |

Supporting, not engines: `lib/special.py` (regularized incomplete beta **and its inverse** — review 05
found the inverse missing and 5 models need it; incomplete gamma + inverse), `lib/dist.py`,
`lib/series.py` (**exchangeability / autocorrelation gate — absent from revision 2, needed by 8
models, underwrites P1**; emits a breakdown value per P4, never a pass/fail test), `lib/report.py`,
`lib/optim.py`.

`lib/seq.py` (supermartingale primitives) is deferred with the anytime-valid family — revision 2
mandated leading with that family while never specifying what it stands on.

---

## 6. Output contract

*(Revision 2 had six modes, two of which shared exit 0 with the success case. Review 01: `if rc == 0:
use the number` would hand the agent a naive baseline carrying the module's authority.)*

**Four outcomes. Anything that is not the model's own answer gets its own exit code.**

| Exit | Outcome | Number printed? | Meaning |
|---|---|---|---|
| `0` | `ANSWER` | yes — the model's | Assumptions hold |
| `2` | usage error | no | argparse's own |
| `3` | `REFUSED` | **no** | Inputs structurally violate the model |
| `4` | `UNANSWERABLE` | **no** | The question has no answer regardless of data |
| `5` | `USE_SIMPLER` | yes — **the simpler answer, labelled as not the model's** | The model does not beat a simpler approach |

`CAVEAT:` and `ROBUSTNESS:` are **annotations on `ANSWER`**, not separate outcomes — which also
removes revision 2's undefined precedence when modes co-occur.

**Precedence when several apply:** usage → `REFUSED` → `UNANSWERABLE` → `USE_SIMPLER` → `ANSWER`.

**Every outcome ends with a `REPORT AS:` line** giving the sentence the agent should say. This
converts interpretation into transcription and is the strongest available counter to the observed
failure of agents reporting numbers their tools flagged (`RESEARCH.md` §0.3).

```
MODEL: Minimum attainable p-value for this design
RESULT
  min_two_sided_p: 0.100
  can_reach_0.05: false
ROBUSTNESS: Reaching p<0.05 requires n1=n2>=4 (min p then 0.029).
REPORT AS: With 3 runs per arm no result can reach p<0.05 — the design cannot
           produce that conclusion, whatever the data shows.
```

`--json` emits the same content with `"outcome"` and `"report_as"`. A JSON schema per outcome is part
of `lib/report.py`'s acceptance criteria, not left to implementation.

---

## 7. Entry points — ~14, each justified

Every row states which limb of the selection principle it satisfies. **Models the baselines already
handled correctly are excluded**, including two of revision 2's own pilots.

| # | Entry point | Limb | Why it earns a slot |
|---|---|---|---|
| 1 | `minimum_attainable_p_for_design` | (a) | p<0.05 unreachable at n₁=n₂=3. No baseline mentioned this. **All six floors verified** |
| 2 | `multiplicity_correction_for_search` | (a) | "the biggest agent self-deception" — patterns noticed *after* looking. Zero lib deps |
| 3 | `three_point_estimate_to_range` | (b) | S5 baseline used `(b−a)/6`. Ships `(μ−a)(b−μ)/7`; PERT identity **verified symbolically** |
| 4 | `pool_probabilities_with_dependence_discount` | (c) | P6. Refuses / discounts when sources share a generator. Vovk–Wang **proved tight** |
| 5 | `pool_evidence_from_adaptive_collection` | (c) | "run study k+1 based on study k" is the agent's default and breaks classical pooling |
| 6 | `quantile_confidence_from_order_statistics` | (a) | At n=100 there is no upper bound above p97. A "p99 from 100 samples" is not a statistic |
| 7 | `exchangeability_breakdown_value` | (a)(c) | Underwrites P1. Emits a breakdown value, never a pass/fail (P2) |
| 8 | `discovery_saturation` | (a) | "my last 5 greps found nothing new — am I done?" Good–Turing/Chao1. **Absent from all 310** |
| 9 | `capture_recapture_remaining` | (a) | "two reviewers, 2 overlaps — how many bugs left?" **Absent from all 310** |
| 10 | `mcnemar_paired_comparison` | (a) | "A 40/50 vs B 43/50 **on the same items**" — an unpaired test here is simply wrong |
| 11 | `scaling_exponent_fit` | (a) | "is this O(n²)?" — agents eyeball it. **Absent from all 310** |
| 12 | `unmeasured_confounding_breakdown_value` | (a) | E-value. The only clean `ROBUSTNESS` producer found |
| 13 | `benchmark_runs_needed` | (a) | Planning, not testing — the baseline computed the test correctly but never asked how many runs |
| 14 | `bayes_action_under_stated_loss` | (b) | "what timeout should I set" is a newsvendor problem; agents reach for p99 |

**Deliberately excluded, against revision 2:** `zero_events_observed_upper_bound` — the S3 baseline
applied the rule of three correctly *and* found a deeper problem (99.9% of *what*?) no model would
have caught. `benchmark_regression_from_repeated_runs` as a test — S1 computed Welch correctly; only
the planning half (#13) survives. Excluding these is the selection principle working.

**Calibration ships no model.** Review 04 and review 02 independently concluded its deliverable is a
**logging protocol** — nothing is computable until predictions and outcomes have been recorded, and
the real requirement is 120–260 logged predictions, not the 11–25 revision 2 claimed. Ships as
`docs/families/calibration.md` describing what to record.

---

## 8. Registry

`registry.json` is the single source of truth; `INDEX.md` and `docs/families/*.md` are generated and
CI fails on drift. Fields: `id`, `path`, `engine`, `family`, `title`, `situations` (≥3 agent
phrasings — terminology mismatch is the dominant retrieval failure), `keywords`, `tier`, `usage`,
`output`, `selection_limb` (a/b/c, **required** — no model ships without one), `baseline_to_beat`
(**nullable**), `refuses_when`, `unanswerable_when`, `composition_hazards`, `data_provenance_required`,
`independence_required`.

Revision 2's example set `independence_required: false` on the model whose dominant real violation is
non-exchangeable reruns. Every registry entry is reviewed against its own model's failure modes.

---

## 9. Verification

| Level | Scope | Gate |
|---|---|---|
| **L1** | `lib/` golden tests vs **published reference values** (never SciPy) | within declared error envelope |
| **L2** | Engine membership tests | each claimed cluster member **derived and checked**, per the C1 failure |
| **L3** | Per-model golden + property tests | ≥2 literature- or hand-verifiable cases |
| **L4** | Outcome tests | ≥1 input per model per applicable outcome; exits 3 and 4 assert **no number in stdout** |
| **L5** | Routing evals | recall@3 **and** false-positive control |
| **L6** | Behavioral evals | vs the 7 recorded baselines |

**Requirements the evidence forced:**
- **No number from `RESEARCH.md` enters a header, skill file, or golden test until independently
  re-derived.** Four claims were refuted by derivation; every one had a correct conclusion attached to
  a wrong number.
- **Any SBC harness uses data-dependent test quantities** (joint log-likelihood minimum). A posterior
  equal to the prior passes rank-based SBC perfectly — and silently ignoring the data is this
  project's worst failure.
- **S5 re-specified** with a near-symmetric mode (4/11/18): as posed its mode sat at δ=0.176, beside
  the crossover where the wrong PERT formula is accidentally right, so it could not detect the bug it
  existed to detect.
- **S8 added** — the same question embedded inside a larger task, testing whether baselines degrade
  when the statistics are implicit rather than posed.

CI: clean `python3`, no third-party packages; regenerate docs and fail on diff; assert no import
outside stdlib and `lib/`.

---

## 10. Waves

### Wave 0 — prove the contract

1. `lib/report.py` with all four outcome JSON schemas + `REPORT AS`, and `lib/exact_tail.py` with its
   **per-member cluster verification**.
2. `registry.json` schema, `route.py` with the folded-in precheck, `generate_docs.py`, CI drift check.
   Registry contains **only shipped models** — revision 2 would have had the router pointing at ~306
   nonexistent scripts.
3. **Four pilots, chosen so each outcome and each tier is exercised by at least one:**

| Pilot | Tier | Outcomes exercised | Limb |
|---|---|---|---|
| `minimum_attainable_p_for_design` | INLINE | `ANSWER`, `ROBUSTNESS`, `REFUSED` | (a) |
| `three_point_estimate_to_range` | INLINE | `ANSWER`, `CAVEAT` | (b) |
| `unmeasured_confounding_breakdown_value` | INLINE | `ANSWER`, `ROBUSTNESS`, `UNANSWERABLE` | (a) |
| `benchmark_runs_needed` | MUST-CONSTRUCT | `ANSWER`, `USE_SIMPLER` | (a) |

4. L1–L5 green on those four. Re-run L6 against the recorded baselines.

**→ Review gate.**

### Wave 1 — the remaining ten entry points, plus the calibration logging protocol. **→ Review gate.**

### Wave 2 — only if L6 shows a real delta. Anything further is justified by measurement, not ambition.

---

## 11. Risks

| Risk | Mitigation |
|---|---|
| A model silently ignores its data | Data-dependent SBC quantities (§9) |
| Cluster unification is wrong | Per-member verification; C1 already failed at 4/6 |
| A `RESEARCH.md` number is wrong | Re-derive before shipping; 4 of ~40 checked claims were refuted |
| Agent uses a `USE_SIMPLER` number as the model's | Distinct exit code 5; `REPORT AS` names the source |
| Router misses on terminology | `situations` phrasing; L5 recall evals |
| Token cost exceeds value | Honest measurement in L6, ~4,600–8,000 realistic; Wave 2 gated on measured delta |
| The module adds nothing over the baseline | **The selection principle, applied per model, with the baseline evidence cited in the registry** |

---

## 12. Conventions

Python 3.9+, stdlib only, forward slashes, descriptive filenames, every threshold documented with its
reasoning and written as a function of n where the statistics require it, no time-sensitive statements.
