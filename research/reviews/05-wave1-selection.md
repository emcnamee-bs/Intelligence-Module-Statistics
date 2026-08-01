# Review 05 — Wave 1 Model Selection

**Date:** 2026-07-31
**Input:** 13 territory reports (310 ranked models), `RESEARCH.md` Parts 0–2, the revised design spec.
**Output:** a ranked Wave 1 build list of **33 models** spanning all 12 families, the dependency graph,
the exclusions, and a verdict on the four Wave 0 pilots.

**Contents**

1. [The selection rule, and how I applied it](#1-the-selection-rule-and-how-i-applied-it)
2. [Frequency weighting — argued, not asserted](#2-frequency-weighting--argued-not-asserted)
3. [The Wave 1 list, ordered by build priority](#3-the-wave-1-list-ordered-by-build-priority)
4. [Family coverage check](#4-family-coverage-check)
5. [Dependency graph and build order](#5-dependency-graph-and-build-order)
6. [`lib/` primitive gaps not in the Wave 0 core](#6-lib-primitive-gaps-not-in-the-wave-0-core)
7. [What I deliberately excluded, and why](#7-what-i-deliberately-excluded-and-why)
8. [Sanity check on the four Wave 0 pilots](#8-sanity-check-on-the-four-wave-0-pilots)
9. [Open questions for the review gate](#9-open-questions-for-the-review-gate)

---

## 1. The selection rule, and how I applied it

The spec says Wave 1 is `~30 models by frequency × leverage × feasibility, spanning all 12 families,
leading with the anytime-valid family`. I treated that literally and multiplicatively — a zero in any
term is a cut, not a demotion — with four additional filters that fell out of the sweep:

**F1 — Cluster credit.** A model that reuses an already-built implementation costs a fraction of a new
one. Feasibility is therefore evaluated *given the build order*, not in isolation. This is why the
second and third members of each identity cluster rank far above their standalone merit
(`expected_value_of_sample_information` is a C2 sibling of the Wave 0 gate; it is nearly free).

**F2 — Precondition frequency, not error frequency.** `RESEARCH.md` §1.2 says models where the naive
answer is *actively wrong* "deserve priority in Wave 1 regardless of how often the situation arises."
I am overriding that for a specific subclass, and the argument matters enough to state plainly:
**an agent that never has the data never makes the error.** Staggered-adoption TWFE can return the
wrong sign — but it requires a panel with multiple adoption cohorts, which an agent does not have.
The `naive_answer_is_wrong` models I *do* ship are those whose precondition is universal: the PERT
variance (Wave 0), MAD = 0 on discrete data, unanimity at k = 3, extremizing correlated sources,
additive false-alarm rates across overlapping rules, mean-of-completed-items under censoring,
kurtosis as a heavy-tail test. See §7 for the mechanism that handles the rest at zero cost.

**F3 — One script per question, not per method.** Where two territories ranked the same predicament
under two names, I merged rather than shipped both, and pushed the second name into `registry.json`
as an extra `situations` set over one implementation. This is the dedup pass the spec mandates
(§8), applied at selection time rather than after. It removed six candidate slots.

**F4 — Refusal is a deliverable.** A model whose primary output is a refusal still earns a slot if the
refusal is one an agent will otherwise get wrong (`quantile_confidence_from_order_statistics` mostly
prints "no upper bound on your p99 exists at n = 100"). A model whose primary output is a *diagnostic
that routes elsewhere* does not — it becomes a `lib/` gate. This is why the exchangeability check and
the heavy-tail panel are primitives in §6, not entries in §3.

Applying all of this to the 310 ranked rows: 33 models survive, against a hard cap of 35. I left two
slots unfilled deliberately — the sweep's own §2.5 caveat is that convergent findings across
non-independent agents are hypotheses, and I expect at least one Wave 1 model to fail primary-source
verification and need replacing.

---

## 2. Frequency weighting — argued, not asserted

The sweep repeatedly says "agents hit this constantly." That claim is doing enormous work in the
rankings and almost none of it was defended. Here is my defence, and my disagreements.

### 2.1 What "an agent" is, for the purpose of counting

The unit of frequency is *a decision an agent makes during a working session that it would otherwise
resolve with the word "probably."* That excludes decisions it resolves by reading a file, and it
excludes decisions where it has no numbers at all and cannot get any. It is not the same as "how
often does the underlying situation occur in the world" — the Edinburgh Tram is a wonderful cautionary
tale and no agent will ever be asked about a tram.

### 2.2 Daily-to-weekly (these earn slots on frequency alone)

| Situation | Why it is genuinely daily | Wave 1 model |
|---|---|---|
| "I ran it 3 times before and 3 times after" | This is the modal engineering interaction. Territory 13 opens on it; territory 04's headline is that at n₁=n₂=3 the minimum two-sided p is 0.10, i.e. the agent is *arithmetically incapable* of the conclusion it is about to state | Wave 0 pilot + `minimum_attainable_p_for_design` |
| "It failed once out of 20" | Every CI system produces this hourly. The interval on 1/20 spans roughly 0.1%–25% | `success_rate_from_few_trials` |
| "Zero failures in N runs" | Same generator, and the naive answer (0%) is not imprecise but categorically wrong | Wave 0 pilot (C1) |
| "How long will this take?" | The single most-requested estimate in software work, and the one where the textbook formula is *verifiably* wrong (§1.37) | Wave 0 pilot |
| "Should I run more, or decide now?" | Elevated to the skill's opening move by P8. Frequency is by construction 1.0 — it runs before everything else | Wave 0 pilot (C2) |
| "Three subagents came back with three answers" | A structural consequence of the agent architecture, not a statistical situation the agent stumbles into. It happens every time fan-out is used | 4 synthesis models |
| "Which of these k options do I commit to?" | Model choice, config choice, library choice, prompt choice | `bayes_action_under_stated_loss`, `best_arm_identification_with_guarantee` |
| "I noticed this pattern after looking at the data" | Territory 12 calls it "the single biggest agent self-deception," and it is a description of how agents work — they scan, then report the interesting thing | `multiplicity_correction_for_search` |
| "Is this spike an anomaly?" | Log-reading is a core agent loop | `robust_anomaly_score_with_scale_fallback` |
| "We fixed the worst offenders and they improved" | Find-the-worst-N-and-fix-them is the dominant agent remediation workflow, and regression to the mean is its dominant confounder. Nothing else catches it | `regression_to_the_mean_decomposition` |
| "Multiply three rough numbers together" | Fermi estimation is how agents size anything they cannot measure, and they get the compounding wrong in *both* directions (§1.18) | `uncertainty_propagation_through_product` |

### 2.3 Monthly (earn slots on leverage, not frequency)

- **Calibration self-audit.** An agent does not audit its own confidence daily. But §1.8 is the
  strongest single finding in the sweep: the "you need 200 resolved events" rule is imported from
  flexible calibration curves and *does not apply* to calibration-in-the-large, where **N ≈ 11–25**
  suffices to detect the gap as it actually exists (published ECE 0.17–0.57). That converts the
  family from decorative to reachable within one long session. Two slots, and only two — the
  recalibration *map* still needs n ≥ 100 and is cut.
- **Threshold setting for a monitor.** Set once, lives for months. But it is set from a voodoo
  constant ("3 sigma") every single time, and Siegmund's ARL approximation retires that constant in
  two lines (§1.32). High leverage per invocation.
- **"When do we run out of disk / hit the limit?"** Not daily, but the naive answer (gap ÷ last
  delta) produces a *date with no interval*, and the honest answer is frequently "no date is
  computable" — the cleanest `NO ANSWER EXISTS` in the library.

### 2.4 Yearly or never — demoted regardless of mathematical merit

This is where I disagree with the territory rankings most sharply.

- **Territory 02 ranks staggered-DiD corrections (Callaway–Sant'Anna, Goodman-Bacon, Sun–Abraham) at
  #11 and #12, and §1.2 promotes them on `naive_answer_is_wrong` grounds.** I cut all of them. The
  precondition is a balanced panel, unit × period, with ≥2 adoption cohorts and a never-treated
  group. An agent has this approximately never. The finding is real and important; the *model* is
  not a Wave 1 asset. It is handled in §7 by a script-less registry warning.
- **Synthetic control, SDID, RDD, IV, AIPW, propensity weighting.** Same argument, five more times.
  Territory 02's own summary concedes it: "the agent rarely has a panel dataset, but it almost always
  has an effect size, a story, and an unstated assumption." I took that seriously and shipped only
  the two tools that consume an effect size and a story.
- **GPD / GEV / Hill / Weissman / CSN power-law suite.** Territory 05 is emphatic that the cheap exact
  tools outrank the model-based extrapolation at agent scale, then ranks eight extrapolation models
  anyway. The floors settle it: GPD needs ≥30 exceedances (≥150 samples), GEV needs ≥25 blocks, Hill
  needs n ≥ 200 and returns a *range across k* rather than a number, and §1.14's external validation
  found Δξ̂ collapsing 30× between 2,000 and 30,000 samples. At agent scale ξ is a sign. Zero slots.
- **Secretary problem / odds algorithm.** Famous, exactly optimal, ~15 lines. Requires N known in
  advance and no recall. Agents almost always have recall (they can go back to candidate 2). The
  precondition is false, so the elegance is irrelevant.
- **Kelly sizing.** §1.24 is a lovely result — half-Kelly-as-estimation-hedge is wrong as stated,
  because log-growth is affine in p. But Kelly's own refusal condition is "one-shot, non-compounding
  decision," which is the agent's actual situation nearly every time. A model that refuses on its
  modal input is a registry warning, not a script.
- **Dempster–Shafer.** Zadeh's paradox is the best story in territory 08. The inputs — mass
  assignments over a frame with an explicit ignorance mass — are things no agent can supply honestly.
- **Cooke's classical model.** Beats equal weighting in 26 of 33 studies. Needs 8–10 seed questions
  with known answers *per source*. Territory 08 argues an agent can construct these; territory 11 cut
  it for exactly the opposite reason. Territory 11 is right — the agent would have to build a
  calibration battery before answering a question it wanted answered now.
- **Metalog / QPD fits.** Closed-form quantile function, no family assumption, genuinely elegant.
  Needs 3–5 stated quantiles. Agents state two, and often only one.
- **BOCPD, PELT/CROPS, LinUCB, isotonic and beta recalibration, Cox PH, competing risks.** All gated
  behind n floors (30, 50, 5d per arm, 100, 100, and a clustering structure respectively) that the
  agent-scale regime does not reach.

### 2.5 One demotion I am least sure about

`aicc_model_ranking_with_weights` survives at #33 partly on family-coverage grounds — `model-choice`
would otherwise ship only a multiplicity corrector, which does not answer the family's stated question
("which explanation should I believe?"). Its honest frequency is low: an agent rarely holds two fitted
log-likelihoods with a shared n. If the review gate wants to trim to 32, this is the row to cut, and
the family question can be answered by routing to `rolling_origin_backtest_against_naive` (out-of-sample
comparison, which P9 and P10 both prefer anyway).

---

## 3. The Wave 1 list, ordered by build priority

Ordered by build priority, not by family. Tier: `IN` = INLINE, `DF` = DATAFILE, `MC` = MUST-CONSTRUCT-DATA.
Cluster ids are defined in §5.1; `—` means a single-use implementation. Difficulty is S/M/L in the
spec's own terms (S ≈ arithmetic and one loop; M ≈ a root-find, a DP, or a simulation with a contract;
L ≈ multi-parameter optimisation or a new numeric subsystem).

| # | Model id (file) | Family | Tier | Cluster | Baseline it must beat | Refuses when | Diff | Why this slot |
|---|---|---|---|---|---|---|---|---|
| 1 | `minimum_attainable_p_for_design` | signal-vs-noise | IN | — (backs C3) | Running the test anyway and reading the p-value | Never — this *is* the refusal oracle; other models call it as a precondition | S | P3 made executable. Every signal-vs-noise model is a precondition call away from asserting an arithmetic impossibility. Build first so nothing downstream can ship without it |
| 2 | `anytime_valid_confidence_sequence` | evidence-sufficiency | DF/MC | **C5** | Fixed-n Wald/Wilson interval, which is invalid under peeking (α → 1.0 under continuous monitoring) | Values outside declared bounds; bounds neither given nor derivable; data reordered or sorted after collection (breaks the filtration); α or c changed after seeing data | M | Spec mandates leading with anytime-valid. Builds the C5 engine three models depend on, and it is the only framework in which the agent's actual workflow (peek, continue, stop when convinced) is legal |
| 3 | `multiplicity_correction_for_search` | model-choice | IN | C13 | The nominal p from an analysis chosen because it looked good | `m` not supplied when the hypothesis was formed post-hoc — hard refuse; `m` = number reported rather than number run; p = 0 | S | Territory 12: "the single biggest agent self-deception." No lib dependency. Also absorbs Holm/BH/e-BH for the list-of-p-values case |
| 4 | `unmeasured_confounding_breakdown_value` | causal | IN | — | A verbal robustness claim ("seems plausible, could be confounded") | No CI or SE (the limit E-value is the decision-relevant one); an odds ratio passed as a risk ratio with a common outcome; selection bias or measurement error is the suspected problem, not confounding | S | Canonical `ROBUSTNESS` output — the breakdown value *is* the answer (P4). Three INLINE numbers. Strongest candidate for promotion into Wave 0 (§8) |
| 5 | `success_rate_from_few_trials` | estimation | IN | C4 + C7 | The point estimate `k/n` | Trials not exchangeable (same seed, same cache, same session) — requires an explicit independence assertion; outcome defined post hoc; k > n | M | The modal INLINE question. First real exercise of `special.py`'s incomplete beta **and its inverse**. Absorbs the flaky-test registry entries via F3 |
| 6 | `pool_probabilities_with_dependence_discount` | synthesis | IN | **C9** | Naive Bayes chaining: five 3:1 reports become 243:1 instead of ≈5:1 | ρ not supplied — hard refuse, independence is the assumption that breaks; ρ ≥ 0.9 → "effectively one source", refuse the multi-source update; extremization requested with correlated sources; any p ∈ {0,1} with no clamp policy | S | P6, the highest-leverage guard in the entire sweep. Pseudo-replication is invisible: correlated agents agreeing looks exactly like independent agents converging |
| 7 | `pool_evidence_from_adaptive_collection` | synthesis | IN | C5 + C9 | Fisher's method, which is invalid when the decision to run study k+1 depended on study k — the normal agent workflow | Mixing e-values for different nulls; taking a product under arbitrary dependence; converting p→e→p and claiming a gain | S | Closes composition hazard #2. Vovk–Wang `2 × mean(p)` is one line and valid under *arbitrary* dependence, which is precisely the agent's epistemic position |
| 8 | `quantile_confidence_from_order_statistics` | tail-risk | DF | C1 + C4 | The raw empirical percentile reported with no uncertainty | `n < ln(α)/ln(p)` → **NO ANSWER EXISTS**, print the wall not a number; sample max coincides with a known cap (timeout, quota, buffer) → every tail statistic is a lie; autocorrelated input | S | C1 sibling of the Wave 0 pilot, so nearly free. "Your p99 from 100 samples is not a statistic" is a weekly correction |
| 9 | `uncertainty_propagation_through_product` | estimation | IN | **C6** | Multiplying point estimates and reporting the product bare; and the agent's `f^k` intuition, where the truth is `f^√k` | Any input is a point mass; the expression can divide by a variable straddling 0 (no finite mean — quantiles only); inputs correlated with no ρ supplied | M | §1.18 headline #1. Four factors each ±3× give **9×**, not 81×. Agents get this wrong in both directions and cannot do it in their heads. Ships the variance-contribution ranking as the same call |
| 10 | `bayes_action_under_stated_loss` | decision | IN | C7 | Modal-state planning, and reporting the posterior mean regardless of the loss function | **No loss declared → refuse to emit a point estimate at all** (the highest-leverage single constraint in territory 01); no ε → report the flip threshold only; payoffs on incommensurable scales | M | Emits the killer diagnostic: "the decision flips at P(broken) = 0.19; you are at 0.31." Also the loss→estimator table (squared→mean, pinball→quantile, newsvendor→critical fractile) |
| 11 | `consensus_interval_from_bare_numbers` | synthesis | IN | C4 | "The average of 42, 47 and 61 is 50" | k = 1; sources not exchangeable (one is a rerun or a summary of another); must always print that it covers the median of the *source* distribution, not the truth — refuse to relabel it a CI for the truth | S | The only exact statement available at k = 3. Also kills the unanimity fallacy: 3-of-3 agreement is a two-sided p of **0.25** |
| 12 | `pool_estimates_with_dispersion_check` | synthesis | IN/DF | **C8** | "Average them" (ignores precision) and "trust the tightest one" (ignores disagreement) | Any sᵢ ≤ 0; estimates on mixed scales or mixed effect metrics; Birge ratio > 3 or Q > χ²₍ₖ₋₁,0.999₎ → data are irreconcilable, print the conflict and refuse a pooled value; never a bare I² or τ² at k ≤ 5 | M | The Birge/PDG scale factor is the only principled small-k error inflation that works at k = 2. Ships leave-one-out influence in the same call, which at k = 3 is frequently the entire finding |
| 13 | `robust_anomaly_score_with_scale_fallback` | monitoring | IN/DF | **C10** | mean ± 3·SD, which is *masked* by the very outlier being tested | **MAD = 0** (fires on ordinary discrete data like `[10,10,10,11,10,40]`) → fall back to IQR/Qn, never emit ∞; n < 7; visible skew → refuse symmetric two-sided limits; trending series → route to a rolling filter | S | `naive_answer_is_wrong: true`. Two territories independently hit the MAD = 0 degeneracy *and* the same fix — the strongest convergence in the sweep that also survives the §1.16 caveat, because both measured it |
| 14 | `exact_poisson_rate_and_count_comparison` | monitoring | IN | C4 | Percent change on small counts ("errors up 100%" = 1 → 2), and 3-sigma on counts | Exposure unknown or not comparable across periods; overdispersion detected in a baseline → route to negative binomial; counts arising from one incident's burst; x₁ = x₂ = 0 | M | Exact and closed-form. 1 event against an expected 0.2 is *not* significant (p = 0.18); 2 is (p = 0.018). Agents cannot do this arithmetic and reliably alarm on the first |
| 15 | `two_quantiles_to_distribution` | estimation | IN | C6 | A bare point estimate, or a range with no distribution behind it | Quantiles not strictly increasing; q ≤ 0 for a lognormal; p10 = p90 (zero stated uncertainty is a lie); implied σ > 3.5 (a shrug, not an estimate); p10–p90 mislabelled as a 90% interval | S | The entry point to the whole INLINE tier and to C6. Its diagnostic output — how far the stated median is from the median implied by the stated tails — is the real product |
| 16 | `scenario_mixture_total_variance` | estimation | IN | C6 | Averaging scenario point estimates, which in the worked example discards **92% of total variance** | Weights not summing to 1; a branch described qualitatively with no distribution or point value; strongly multimodal and a point summary was requested — return the modes | S | §1.18 headline #2. Law of total variance is one line; the error it prevents is enormous and completely invisible to the agent |
| 17 | `expected_value_of_sample_information` | decision | IN | **C2** | Power analysis, which answers "what n detects a difference" — the wrong question | EVSI > EVPI (bug indicator); prior effective sample size n₀ < 1; σ_d guessed rather than measured; no loss/payoff supplied | M | C2 sibling of the Wave 0 gate, so cheap. This is the Tier-3 escalation *quantifier*: the gate says whether to measure, this says how much to measure |
| 18 | `mean_and_next_observation_from_small_sample` | estimation | IN/DF | C7 | `mean ± sd/√n` with a normal quantile (≈25% too narrow at n = 5); and, far worse, quoting the interval on the **mean** when the question was about the **next run** | n < 3 under the reference prior (posterior for σ improper); visible outliers or heavy tails; **time trend or autocorrelation in the runs** — the single most common violation in benchmark data | M | Closes composition hazard #5 structurally: the script always emits *both* the parameter interval and the predictive interval, labelled distinctly, so the agent cannot silently substitute one for the other |
| 19 | `sample_size_and_minimum_detectable_effect` | evidence-sufficiency | IN | — | "30 runs is enough," and running a study that cannot answer the question | Δ not supplied — hard refuse, there is no such thing as "enough runs" without a target effect; σ from a pilot with n < 5 → print an interval on n, not a point; **post-hoc power → hard refuse** with a redirect to MDE | S | The MDE direction (what am I powered for, given the budget I have) is the one agents actually need and the one textbooks invert |
| 20 | `paired_change_exact_shift_and_interval` | signal-vs-noise | IN/DF | **C3** | The paired t-test on skewed differences, and "it got better" | n ≤ 5 → minimum two-sided p is 0.0625, α = 0.05 unreachable; differences visibly asymmetric → route to the sign test; more than ⅓ zero differences | M | Same input, two configs, is a distinct and very common design from two independent samples, with a *different* arithmetic floor. Exact signed-rank null by subset-sum DP is measured at n = 100 in 0.010 s |
| 21 | `resolved_predictions_needed_for_calibration_claim` | calibration | IN | — | An agent asserting "I have been well calibrated lately" from 8 data points | Should never refuse — it is the refusal oracle for its family. Must decline to answer "how many for a full reliability curve" with a small number (that needs ≥100 of each outcome) | S | §1.8 is the sweep's most surprising finding and this model is where it lands: N ≈ 11–25 for the real gap, 85 for 10 points, 315 for 5. Build before #22, which it gates |
| 22 | `overconfidence_gap_with_skill_and_sharpness` | calibration | DF | C4 | The base-rate forecaster — **ECE = 0 is achievable by a constant forecaster**, so a calibration number alone is meaningless | n < 10; **log assembled from mixed elicitation protocols or reconstructed from recall → refuse outright**, no statistic repairs it (`data_provenance_required`); all outcomes identical and n < 20; predictions not logged before resolution | M | Must print calibration, skill-vs-base-rate and sharpness or print none of them (§1.10). Grouping is by *exact stated value*, not bins — LLM confidence concentrates on 6–8 values, which dissolves the entire ECE-binning literature |
| 23 | `best_arm_identification_with_guarantee` | decision | MC | C5 | A fixed equal budget across all k options, then argmax — which carries no error guarantee at all | Rewards unbounded with no declared range; **trials not i.i.d.** (ordering, caching, warm-up — extremely common in benchmark runs and it silently destroys the guarantee); budget exhausted before elimination → report the surviving set, never a winner | M | The MUST-CONSTRUCT-DATA exemplar. Must print `min(UCB bound, n·Δ_max)` — §1.23 shows the famous asymptotic bound is routinely *vacuous* at agent horizons |
| 24 | `regression_to_the_mean_decomposition` | causal | IN | — | Attributing the whole improvement to the intervention | Units were **not** selected on the baseline outcome (RTM does not apply — saying so is the output); r unavailable and no range supplied → print the bracket over r ∈ [0,1], which spans "all real" to "all artifact"; deterministic measurement (r = 1) | S | The agent's dominant remediation workflow is find-the-worst-N-and-fix-them, and `E[post] = μ + r(pre − μ)` says (1−r)(pre − μ) of the improvement is arithmetic. No other tool in the library raises this |
| 25 | `robust_trend_and_threshold_crossing` | monitoring | DF | C3 | Eyeballing a chart; the OLS slope p-value (one outlier flips it); gap ÷ last delta for the crossing date | Lag-1 autocorrelation > ~0.2 → Hamed–Rao correction or refuse; seasonality without the seasonal variant; n < 8; a step change fits better → suppress the trend verdict; **slope CI contains zero → the crossing interval is unbounded or disjoint, refuse to print a date** | M | Merges two territories' rows into one script under F3. The threshold-crossing refusal is the sharpest `NO ANSWER EXISTS` in the library and answers a weekly question ("when do we run out of disk") |
| 26 | `horizon_and_fanout_risk_amplification` | tail-risk | IN | — | Reading "1-in-100" as "won't happen"; assuming a p99 component gives a p99 request | Components correlated (shared queue, host, dependency) — the independence assumption drives the entire answer and must be asserted; k is not the actual parallel fan-out; clustered per-period events | S | Two powers, enormous intuition gap. A 1-in-100 event is 26% likely over 30 periods; a 100-way fan-out of p99 components makes 63% of requests slow |
| 27 | `alert_threshold_from_false_alarm_rate` | monitoring | DF/IN | **C-MC** | Round numbers — 3σ, "95th percentile", "2× baseline" — and adding per-rule false-alarm rates, which is invalid for overlapping run rules | In-control history < 50 points → analytic normal-theory number only, flagged; history contains the anomaly being detected (contaminated null); baseline σ from < 25 points → refuse to quote an ARL; check frequency not supplied | M | §1.32 says ship as first-class. Retires a voodoo constant the library would otherwise invent. Carries composition hazard #4: Western Electric rules drop ARL₀ 370 → **91.75**, and naive addition gives 52, wrong by ~76% |
| 28 | `rolling_origin_backtest_against_naive` | forecasting | DF | **C12** | The naive / seasonal-naive / drift forecast. **MASE ≥ 1 → print the naive forecast instead** | < 5 usable origins → print MASE but refuse to declare a winner between methods; methods refit on different windows; any leakage of future data into deseasonalisation or scaling | M | P9's canonical instance and the whole family's gate. Every other forecasting entry passes through it. Its rolling errors are also the source of #29's intervals, so it must be built first |
| 29 | `short_series_forecast_with_empirical_interval` | forecasting | DF | C12 | The naive forecast, enforced via #28; and model-based Gaussian intervals, which Hyndman & Billah state in-line are too narrow | n < 5; a level shift in the last ~20% of the series; a cumulative series modelled as a flow; a bounded quantity whose interval crosses the bound (never print a 112% upper bound); < 10 rolling errors at the horizon → inflated Gaussian fallback, explicitly labelled | L | Theta / SES-with-drift / damped trend, combined by median (12 of M4's 17 most accurate methods were combinations). The deliverable is not the point forecast — it is the *empirically calibrated* interval |
| 30 | `duration_distribution_with_censoring` | duration-reliability | DF | **C11** | The mean of the completed items only — biased **downward**, understating the median by 40%+ at 50% censoring, because the long-lived items are exactly the ones still running | **Informative censoring** (units killed *because* they looked stuck) — hard refuse, and ask explicitly; median requested but Ŝ never reaches 0.5 → "median not reached, ≥ t_max"; risk set < 5 at the horizon → suppress the CI; left truncation without adjustment | M | Kaplan–Meier with the complementary log-log interval (the linear one is "very liberal" at small n). The bias correction, not the curve, is the reason this ships |
| 31 | `hazard_shape_and_residual_life` | duration-reliability | DF | C11 | Folk-Lindy applied universally ("it has been stable for months, so it is stable") — which the fitted shape frequently contradicts | r < 3 uncensored events → k unidentified, fall back to exponential with the caveat printed; **profile CI for k contains 1 and is wide → refuse the aging/Lindy verdict**, report "indistinguishable from memoryless at this n"; age > 1.5× the largest observed duration; a hard lifetime bound exists | L | The three-way verdict (k>1 wear-out / k=1 memoryless / k<1 Lindy) flips the *sign* of the agent's advice about a long-running process, and an unaided agent essentially never makes the distinction. Blocks #32 |
| 32 | `timeout_from_asymmetric_loss` | duration-reliability | IN/DF | C7 + C11 | p95-by-folklore, and the posterior mean. The answer is the critical-fractile quantile of the latency posterior | **Decreasing hazard → NO ANSWER EXISTS**: no interior optimum, "the model says do not abandon" — and say it loudly, because it contradicts intuition; no cost ratio *and* no percentile target supplied; fit based on < 8 events; retries not independent draws (the retry hits the same deterministic bug) | M | "What timeout should I set" is a newsvendor problem, not a percentile lookup (§1.36) — the concrete example the spec wants in SKILL.md. Depends on #31 for the hazard shape and must not ship before it |
| 33 | `aicc_model_ranking_with_weights` | model-choice | IN | — | Eyeballing residuals; plain AIC, which over-selects at agent n | n − k − 1 ≤ 0 → AICc undefined; models fit to different data, different n, or different response transforms; best model's weight < 0.6 → print the weight distribution and refuse to name a winner; candidate set of 1 | S | Must surface the small-n inversion: AIC and BIC penalties cross at **n = e² ≈ 7.39**, so below n ≈ 7 the universal "BIC is the conservative one" intuition is backwards. The marginal row — see §2.5 |

**Count: 33.** Two slots held in reserve against primary-source verification failures (§2.1).

---

## 4. Family coverage check

| Family | Wave 0 | Wave 1 | Total | Note |
|---|---|---|---|---|
| `signal-vs-noise` | 1 | 2 (#1, #20) | 3 | The two-sample case is the Wave 0 pilot; Wave 1 adds the design floor and the paired design |
| `estimation` | 1 | 5 (#5, #9, #15, #16, #18) | 6 | Deliberately the largest — this is the modal family and the entire INLINE tier lives here |
| `forecasting` | 0 | 2 (#28, #29) | 2 | Plus a registry entry for threshold-crossing pointing at #25 |
| `causal` | 0 | 2 (#4, #24) | 2 | Both sensitivity/decomposition, no estimators. This is territory 02's own ranking inversion, applied |
| `evidence-sufficiency` | 0 | 2 (#2, #19) | 2 | #7 and #23 also serve it via registry entries |
| `synthesis` | 0 | 4 (#6, #7, #11, #12) | 4 | Sized for the agent architecture: fan-out makes this structurally frequent |
| `monitoring` | 0 | 4 (#13, #14, #25, #27) | 4 | Flaky-test entries route into #5 and the Wave 0 C1 pilot |
| `tail-risk` | 1 | 2 (#8, #26) | 3 | Zero model-based extrapolation. Argued in §2.4 |
| `decision` | 1 | 3 (#10, #17, #23) | 4 | The family P8 makes the skill's opening move |
| `calibration` | 0 | 2 (#21, #22) | 2 | Two is the honest count at agent n; recalibration maps need n ≥ 100 |
| `duration-reliability` | 0 | 3 (#30, #31, #32) | 3 | A strict chain: #30 → #31 → #32 |
| `model-choice` | 0 | 2 (#3, #33) | 2 | #3 carries the family's highest-frequency question |

All 12 families covered. Every family has at least one INLINE entry point except `forecasting` and
`duration-reliability`, both of which are irreducibly series-shaped.

---

## 5. Dependency graph

### 5.1 Implementation clusters

The spec names three (C1–C3). The sweep implies at least nine more once Wave 1 is scoped. Declaring
them now is what keeps the build cost down; discovering them mid-build is what makes it balloon.

| Cluster | The single implementation | Wave 1 consumers |
|---|---|---|
| **C1** | `n ≥ ln(α)/ln(p)` coverage inequality | W0 `zero_events_observed_upper_bound`; #8. Registry-only: reruns-to-confidence, Wilks tolerance interval, zero-failure MTBF bound |
| **C2** | marginal EVSI = marginal cost | W0 `value_of_information_reachability`; #17. Registry-only: Weitzman reservation values, abandon-or-persist, stop-or-continue |
| **C3** | exact null by DP over rank statistics | W0 `benchmark_regression_from_repeated_runs`; #1 (its combinatorial floor), #20 (signed-rank subset-sum DP), #25 (Mann–Kendall S via the Mahonian inversion-count DP) |
| **C4** *(new)* | exact binomial tail + inversion (Clopper–Pearson, order-statistic coverage) | #5, #8, #11, #14, #22 |
| **C5** *(new)* | nonnegative supermartingale / e-process | #2, #7, #23 |
| **C6** *(new)* | log-space quantile fit and propagation | #9, #15, #16 |
| **C7** *(new)* | conjugate posterior → Bayes action | #5, #10, #17, #18, #32 |
| **C8** *(new)* | inverse-variance pool + dispersion (Q, Birge) | #12 |
| **C9** *(new)* | log-odds with a dependence discount | #6, #7 |
| **C10** *(new)* | robust location/scale ladder with MAD = 0 fallback | #13, #11, #12 |
| **C11** *(new)* | censored-survival estimation | #30, #31, #32 |
| **C12** *(new)* | rolling-origin backtest harness | #28, #29 |
| **C13** *(new)* | multiplicity accounting | #3 |
| **C-MC** *(new)* | seeded Monte Carlo with a reported MC standard error | #9, #10, #16, #23, #27 |

**Net effect:** 33 models sit on 14 implementations. The Wave 0 dedup pass must be re-run against this
list *before* Wave 1 code starts, because six of these clusters were not visible at Wave 0 scoping.

### 5.2 Hard blocking edges

These are the orderings that, if violated, produce rework:

```
minimum_attainable_p_for_design  ──►  every signal-vs-noise model
                                 ──►  benchmark_regression (W0) must call it, not reimplement it

lib/seq.py  ──►  anytime_valid_confidence_sequence  ──►  pool_evidence_from_adaptive_collection
                                                    ──►  best_arm_identification_with_guarantee

special.py inverse-incomplete-beta  ──►  success_rate_from_few_trials
                                    ──►  mean_and_next_observation (t quantile)
                                    ──►  pool_estimates_with_dispersion_check (t quantile)

lib/robust.py  ──►  robust_anomaly_score  ──►  consensus_interval_from_bare_numbers (MAD)
                                          ──►  pool_estimates_with_dispersion_check (MAD)

lib/series.py (exchangeability gate)  ──►  paired_change_exact (permutation validity)
                                      ──►  robust_trend_and_threshold_crossing (Hamed–Rao)
                                      ──►  alert_threshold_from_false_alarm_rate (AR(1) refusal)
                                      ──►  quantile_confidence_from_order_statistics
                                      ──►  mean_and_next_observation (trend refusal)

rolling_origin_backtest_against_naive  ──►  short_series_forecast_with_empirical_interval
        (supplies BOTH the baseline and the empirical interval — cannot be built second)

duration_distribution_with_censoring  ──►  hazard_shape_and_residual_life  ──►  timeout_from_asymmetric_loss
        (the timeout model's central refusal IS the hazard-shape verdict)

resolved_predictions_needed_for_calibration_claim  ──►  overconfidence_gap_with_skill_and_sharpness

value_of_information_reachability (W0, C2)  ──►  expected_value_of_sample_information
```

### 5.3 Composition edges (must be encoded in `composition_hazards`, not just built)

| From | To | Hazard |
|---|---|---|
| `robust_trend_and_threshold_crossing` (detected change) | any before/after model | A *detected* changepoint used as the intervention date invalidates the inference — the date must be a priori |
| `anytime_valid_confidence_sequence` (adaptive collection) | `pool_estimates_with_dispersion_check` | Classical pooling breaks under adaptive collection; must route to #7 |
| `pool_probabilities_with_dependence_discount` (correlated sources) | extremization, Bayesian chaining | Amplifies one piece of evidence into false certainty |
| `alert_threshold_from_false_alarm_rate` | multiple overlapping rules | False-alarm rates are not additive: ARL₀ 370 → 91.75, naive addition gives 52 |
| `mean_and_next_observation_from_small_sample` | any next-value question | Parameter posterior ≠ predictive; the difference is observation noise, usually the larger term. Mitigated structurally by emitting both |

### 5.4 Suggested build phases

- **W1.a — zero new lib.** #1, #3, #4, #24, #26, #33. Six models, all S, all INLINE. Ships a usable
  slice in the first pass and validates the output contract against six more scripts before any new
  numerics land.
- **W1.b — build `lib/seq.py`.** #2, #7, #23. The spec's mandated lead.
- **W1.c — finish `special.py` (inverse incomplete beta) + build `lib/robust.py`.** #5, #8, #11, #12,
  #13, #14, #20.
- **W1.d — build `lib/mc.py` + C6.** #9, #10, #15, #16, #17, #18, #19, #21, #22.
- **W1.e — build `lib/series.py` + `lib/dataio.py`.** #25, #27, #28, #29.
- **W1.f — build C11 survival primitives.** #30, #31, #32.

---

## 6. `lib/` primitive gaps not in the Wave 0 core

Wave 0 core is `special.py` (incomplete beta + incomplete gamma), `dist.py`, `exact.py`, `grid.py`,
`optim.py`, `report.py`; Wave 1 adds `dataio.py` and `linalg.py`. Against the 33 models above, the
following are **required and currently unhomed**. Two of them are load-bearing enough to be Wave 1
blockers.

### Blocking

**G1 — `lib/seq.py`: anytime-valid supermartingale primitives. Not in the spec at all.**
The spec says Wave 1 "lead[s] with the anytime-valid family (cheapest to implement and best matched
to how agents actually collect evidence)" — and then lists no primitive for it. Three Wave 1 models
(#2, #7, #23) plus the C5 cluster depend on: running *predictable* plug-in estimators (μ̂ₜ₋₁, σ̂²ₜ₋₁),
the betting fraction λₜ with its clamp, `ψ_E(λ) = (−log(1−λ) − λ)/4`, log-wealth accumulation, capital
inversion by bisection for the CS endpoints, the p→e calibrator `e = κp^{κ−1}`, and the Vovk–Wang
arbitrary-dependence merge. None of this is in `exact.py` (it is not enumeration), `dist.py` (no
distributions involved), or `optim.py` (bisection on a monotone log-wealth is a specialised inversion
with a validity contract attached). It is ~120 lines and it is the cheapest high-value module in the
project — but it must be *named*, because the correctness property being preserved (predictability of
every quantity, so the wealth process stays a nonnegative martingale) is destroyed by an
innocent-looking refactor that uses `σ̂ₜ` where `σ̂ₜ₋₁` was required.

**G2 — `lib/series.py`: the exchangeability and dependence gate.**
Territory 04 row 23 and territory 13 row 16 both identify this as *the* silent universal failure, and
P1's exactness guarantee is conditional on it. Eight Wave 1 models need it (#8, #13, #18, #20, #25,
#27, #28, #29) and each would otherwise reimplement a fragment. Contents: Wald–Wolfowitz runs test with
an exact `math.comb` null, lag-1 rank autocorrelation with a permutation null, Ljung–Box, effective
sample size `n(1−ρ)/(1+ρ)`, the Hamed–Rao variance correction, and — critically — a hard "order
information not supplied" branch that says loudly that exchangeability is **assumed and unverifiable**
rather than certifying it. (Mann–Kendall's exact null via the Mahonian inversion-count DP belongs in
`exact.py`, not here.)

### Required, smaller

**G3 — `special.py` must declare an inverse for the incomplete beta.** The spec lists "regularized
incomplete beta; incomplete gamma + inverse." The inverse of the *beta* is not listed but is needed by
#5 (Clopper–Pearson and Jeffreys limits), #18 and #12 (Student-t quantiles), and #22 (Wilson/Jeffreys
cells). Bisection on the forward function is a perfectly acceptable implementation — but if it is not
declared with an error envelope in `special.py`, five models will each roll their own bisection with
five different tolerances, and the L1 golden tests will not cover any of them.

**G4 — `lib/mc.py`: seeded Monte Carlo with an enforced MC-error contract.** `random` supplies the
samplers (§1.19 — the propagation layer is free), but nothing supplies the *contract*: deterministic
seeding surfaced as a flag, the MC standard error computed and printed alongside every simulated
quantity, and a refusal when the requested output precision exceeds what the draw count supports.
Five models need it (#9, #10, #16, #23, #27), and territory 10 and territory 13 both list "report a
point estimate without its MC standard error" as a refusal condition — which means it is a shared
contract, i.e. a primitive, not per-model discipline.

**G5 — `lib/robust.py`: the robust location/scale ladder.** Median, MAD, IQR, Sₙ/Qₙ with **Akinshin
(2022) finite-sample factors** (the asymptotic Rousseeuw–Croux constants are simply wrong below n = 20
and the odd/even distinction is real), medcouple for the skew-adjusted fences, and the MAD = 0 →
IQR → Qₙ fallback ladder as a single tested path. Three models depend on it. Note that Akinshin's
tables are exactly the sort of shipped lookup that §2.5 of `RESEARCH.md` forbids without primary-source
verification.

**G6 — C11 survival primitives.** Kaplan–Meier product-limit, Greenwood variance, the complementary
log-log interval, Nelson–Aalen cumulative hazard, and censored log-likelihood evaluation for the
Weibull/lognormal score equations. Three models. Either `lib/survival.py` or an owner inside `dist.py`
— but it needs an owner, because the log-log interval and the "median not reached" logic are the two
places this family gets silently wrong.

**G7 — a shared provenance/assertion flag family in `report.py`.** Several Wave 1 models must
*interrogate how the data was collected* before touching it, and the registry fields
(`data_provenance_required`, `independence_required`, `composition_hazards`) currently only inform the
router. At runtime the scripts need a common contract: `--assert-independent`, `--collection
{fixed,adaptive}`, `--elicitation-protocol`, `--selected-on-baseline`, each defaulting to *unset* and
each producing a `REFUSED` rather than a guess. Without a shared implementation this will be
inconsistent across #5, #6, #7, #12, #22, #23, #24 and #30 — and P5 says these are the dangerous
failures.

### Not needed, because of what I cut

**G8 — graph algorithms** (ancestors/descendants, moralisation, d-separation, minimal adjustment-set
enumeration). Required only by the back-door / good-vs-bad-control classifier, which I cut (§7). This
is a genuine reason for the cut and not a post-hoc one: it is a whole code shape with no other
consumer in Wave 1.

**G9 — PAVA (pool-adjacent-violators).** Required by the CORP score decomposition and isotonic
recalibration, both deferred to Wave 2. ~25 lines when it is wanted.

---

## 7. What I deliberately excluded from Wave 1, and why

### 7.1 Things that look like obvious inclusions and are not

| Excluded | Territory rank | Why it does not earn a slot |
|---|---|---|
| **Bootstrap CIs of any flavour** | 04 #10, #11 | Already demoted by the spec, but worth restating because it is the *first* thing an agent reaches for. Measured coverage of a nominal 95% at n = 6: percentile **0.731**, BCa **0.753**. The two flavours agents reach for first are the two that fail hardest, and the bootstrap of a median at odd n takes exactly n distinct values across 20,000 resamples. Wave 2, behind measured refusals |
| **Difference-in-differences (2×2 and staggered)** | 02 #3, #11, #12 | The strongest exclusion argument in this review. §1.2 promotes staggered-DiD on `naive_answer_is_wrong` grounds, but the precondition — a panel with ≥2 adoption cohorts and a never-treated group — is what is rare, not the error. Handled by §7.2 instead |
| **Back-door criterion / good-vs-bad-control classifier** | 02 #2 (ranked second in its territory) | Zero data, high leverage, and I still cut it. Two reasons: it needs an entire graph-algorithm subsystem with no other Wave 1 consumer (G8), and its value is contingent on the agent volunteering a DAG — which is a behaviour change, not a computation. Strong Wave 2 candidate and arguably the first one |
| **Full CORP / PAVA score decomposition** | 07 #2 | §1.9 argues it should replace the classical Murphy decomposition as the default, and I agree — at n ≥ 25. Wave 1's calibration models must work at n ≈ 11–25, where grouping by *exact stated value* is already exact. Shipping PAVA to serve a regime the agent has not reached is premature |
| **Recalibration maps (logistic / temperature / isotonic / beta)** | 07 #7, #8, #17, #18 | Floors of 40, 20, 100 and 100 resolved predictions. Also: recalibration gains must never be reported in-sample, which means each needs a split-and-validate harness. High value once a log exists; Wave 2 |
| **Kelly / log-growth sizing** | 10 #21 | §1.24 is a genuinely valuable correction (log-growth is affine in p, so half-Kelly is not an estimation hedge — it is a CRRA statement). But Kelly's own dominant refusal is "one-shot, non-compounding decision," which is the agent's modal input. A model that refuses on its most common input is a warning, not a script |
| **HulC** | 04 #22, flagged as "the strongest new entrant in the sweep" | Six subsample estimates, no variance estimate, valid where the bootstrap provably is not — genuinely elegant. But its use case is "the bootstrap gave a nonsense interval," and Wave 1 ships no bootstrap. It also needs n ≳ 30 and median-unbiasedness. It becomes correct exactly when `bootstrap.py` lands, so it belongs in the same wave |
| **Post-hoc power** | 06, explicitly | Not merely excluded — it must ship as a named `REFUSED` with a redirect, because computing achieved power from an observed effect is a deterministic function of the p-value and reliably misleads. This is a registry entry, not a model |
| **Fisher's method for pooling** | 08 #9 | Same treatment: a script-less warning entry pointing at #7. Shipping it invites the agent to pick whichever pooling method is more favourable |
| **Naive-peeking α-inflation simulator** | 06 #10 | Cut as a script. The Armitage–McPherson–Rowe values (0.083 at K=2, 0.142 at K=5, 0.320 at K=50) are published constants; #2 should print them from a verified table rather than re-simulating them at runtime. This is the §2.5 "no unverified constants" rule cutting in our favour for once |
| **Exponential MTBF with exact χ² interval** | 09 #1 (ranked first in its territory) | A clean F3 dedup: it is the k = 1 special case of #31 and the r = 0 case of C1. It becomes two registry entries over existing implementations |
| **Flaky-or-unlucky as its own script** | 13 #5 | Same: its interval is #5, its rule-of-three and reruns-to-confidence are the Wave 0 C1 pilot. Three registry entries, zero new code. Territory 13 found the C1 identity independently for the third time (§1.33), which is exactly the signal that it should not be a new script |
| **Heavy-tail diagnostic panel** | 04 #20, 05 #6 | Painful cut, because the kurtosis finding is a genuine `naive_answer_is_wrong` (sample kurtosis is bounded by ≈ n−1, so at n = 10 a Cauchy sample *cannot* look heavier-tailed than a normal one). But its output routes rather than decides, and it needs n ≥ 30. It becomes a `lib/` gate that #8 and #12 call, with the `max\|x\|/Σ\|x\|` statistic replacing kurtosis, and the kurtosis warning becomes a registry entry |
| **Split likelihood-ratio test / universal inference** | 12 #4 | Genuinely the only *honest* answer to the forking-paths problem (#3 discounts; this restores validity), finite-sample valid with no regularity conditions, and it produces an e-value that composes with #7. Cut only on frequency: it needs n ≥ 20 with a clean fit/predict seam. First model-choice addition in Wave 2 |
| **Chebyshev / Cantelli / Vysochanskij–Petunin bounds** | 05 #8 | Cheap and assumption-free, but an agent that has a mean and an sd usually has the data those came from, in which case #8 is tighter and more honest |

### 7.2 The mechanism that makes most of these cheap to exclude

Several excluded items are valuable precisely *because the naive answer is wrong*, and cutting the
script throws that away. The fix costs nothing: **ship `naive_answer_is_wrong` registry entries with
no script.** The router surfaces the warning on a weak match and states the correct alternative,
without the library carrying an implementation for a situation the agent is not in.

Recommended script-less warning entries for Wave 1:

- staggered adoption + two-way fixed effects → estimate can be outside the convex hull of every true
  effect, including the wrong sign
- post-hoc / observed power → deterministic function of the p-value, carries no information
- Fisher's method on adaptively-run studies → route to #7
- sample kurtosis as a heavy-tail test → bounded by ≈ n−1; use `max|x|/Σ|x|`
- `[min, max]` as a 95% prediction interval → 71% coverage at n = 6; needs n = 39
- 3-sigma limits on a positive, right-skewed metric → exponential upper-tail rate is 1.83%, 13.6×
  nominal, and the lower limit is negative so the chart can never signal a decrease
- half-Kelly as protection against estimation error → it is a risk-aversion statement, not a hedge
- averaging the midpoints of scenario estimates → route to #16
- `InverseGamma(ε, ε)` as a variance prior → structurally cannot shrink to the base model

Each is a few lines of JSON, and collectively they capture most of the `naive_answer_is_wrong` value
of the cut models at roughly 1% of their build cost.

---

## 8. Sanity check on the four Wave 0 pilots

The stated purpose is that the four pilots "exercise every tier and every output mode," so that
"contract problems get found on four scripts, not thirty." I checked that claim against the spec's own
tier and mode tables. **Three of the four are the right choices. The set as specified does not meet
its own stated purpose, for three reasons, two of which are internal contradictions in the spec.**

### 8.1 Tier coverage

| Tier | Covered by | Verdict |
|---|---|---|
| `INLINE` | `value_of_information_reachability`, `zero_events_observed_upper_bound`, `three_point_estimate_to_range` | Over-covered — three of four |
| `DATAFILE` | `benchmark_regression_from_repeated_runs` | Covered, once |
| `MUST-CONSTRUCT-DATA` | `benchmark_regression_from_repeated_runs` (same script) | **Weak.** The tier is exercised only as a side channel of a DATAFILE model |

The MUST-CONSTRUCT contract is genuinely different from DATAFILE and nothing proves it: the script has
to be **runnable before the data exists**, telling the agent what to collect and how much, and then
runnable again on the collected data — and the two runs must agree. That round trip is the contract,
and no pilot demonstrates it.

**Fix, at near-zero cost:** require `benchmark_regression_from_repeated_runs` to ship a data-less
`--plan` mode that emits the required n (the MDE inversion) and the resolution floor, and an L2 golden
case that runs `--plan`, then runs with data, and asserts the two are consistent. This proves the tier
on an existing pilot rather than adding a fifth script.

### 8.2 Output-mode coverage

| Mode | Pilot | Verdict |
|---|---|---|
| `OK` | all four | Covered |
| `CAVEAT` | incidental (`three_point` near a bound) | Covered, but not designed for — should be an explicit golden case |
| `ROBUSTNESS` | **none** | **Not covered.** This is the problem |
| `BASELINE_WINS` | `benchmark_regression` | Covered, and well chosen |
| `NO ANSWER EXISTS` | claimed for `zero_events` at n = 0 | **Contradicted by the spec itself** — see below |
| `REFUSED` | implied but unassigned | Ambiguous |

**ROBUSTNESS is uncovered, and it is the mode most in need of proving.** It did not exist before the
sweep (§1.1, P4), it is the only mode whose payload is a computed *breakdown value* rather than a
status, and none of the four pilots has an assumption that is a matter of degree. VOI has no
assumption test; the C1 bound is exact; PERT is arithmetic; and `benchmark_regression`'s assumption
(exchangeability of runs) is structural, so it produces `REFUSED`, not `ROBUSTNESS`. Shipping a
six-mode contract having exercised five is exactly the failure the Wave 0 gate exists to prevent.

**`NO ANSWER EXISTS` versus `REFUSED` is internally inconsistent in the spec.** §7's registry example
gives `zero_events_observed_upper_bound` the field `"refuses_when": "trials < 1"` — i.e. exit 3. §12's
pilot description says the same model "exercises `NO ANSWER EXISTS` at n = 0" — i.e. exit 4. Both
cannot be right, and the semantics matter: §9 defines `NO ANSWER EXISTS` as "the inputs are fine and
the model is right, but the question as posed is unanswerable," which n = 0 is not — n = 0 is a
malformed *input*, which is textbook `REFUSED`. As written, the pilot set may exercise neither mode
cleanly.

Relatedly, the n = 3 floor inside `benchmark_regression` is arguably `NO ANSWER EXISTS` rather than
`REFUSED`: the inputs are fine and the model is correct, but the *design* cannot express the question
("is this significant at 0.05" has no answer when the minimum attainable p is 0.10). Deciding this
one way or the other on a pilot is worth more than deciding it thirty times later.

### 8.3 Registry-field coverage

None of the four pilots carries a non-empty `composition_hazards` or a `data_provenance_required`
value. P5 states that composition, provenance and incomplete reporting are the *dangerous* failures —
and the Wave 0 gate, as specified, validates none of those three fields end to end.

There is also a substantive error in the spec's own registry example: `zero_events_observed_upper_bound`
is given `"independence_required": false`. Territory 09 is explicit that the dominant real violation for
this exact model is that "200 reruns of one cached test are n = 1," and territory 05's refusal list
leads with non-exchangeable trials. It should be `true`, and the model should require an explicit
assertion. Since this is the field's showcase example, getting it wrong here propagates.

### 8.4 Verdict and proposed changes

**Keep all four.** Each earns its place: the VOI gate is P8 and the C2 seed; `zero_events` is C1, the
largest cluster, and dedup must be proven early; `benchmark_regression` is the only DATAFILE pilot and
the natural `BASELINE_WINS` case; and `three_point_estimate_to_range` must ship in Wave 0 because
§1.37 is the one finding in the sweep verified by independent derivation *and* simulation, and its
R(δ) golden tests are the template for every L2 case that follows.

**Add one, and make three corrections:**

1. **Add `unmeasured_confounding_breakdown_value` (the E-value) as a fifth pilot.** It is S difficulty,
   three INLINE numbers, no `lib/` dependency beyond `sqrt` and `exp` — and it is the *only* clean
   `ROBUSTNESS` producer in the whole catalogue, because the breakdown value is not a caveat attached
   to the answer, it *is* the answer. Five pilots does not defeat the "four scripts, not thirty"
   principle; shipping an unexercised output mode does.
2. **Give `benchmark_regression_from_repeated_runs` a data-less `--plan` mode** to prove the
   MUST-CONSTRUCT round trip (§8.1), and a non-empty `composition_hazards` — it must refuse when the
   before and after runs came from one process or were not interleaved (warm-up, JIT, thermal
   throttling, page cache), and must not accept a *detected* changepoint as the split point.
3. **Resolve the two mode assignments explicitly in the spec before Wave 0 starts:** n = 0 is
   `REFUSED`; the p < 0.05-unreachable floor at n = 3 is `NO ANSWER EXISTS`. And correct
   `independence_required` to `true` for `zero_events_observed_upper_bound`.

**If the pilot count must stay at four**, the swap is to drop `three_point_estimate_to_range` and add
the E-value — because the unique content of the PERT row is a *constant and an identity*, which the L1
golden suite can verify without a pilot script, whereas the `ROBUSTNESS` mode can only be validated by
a script that emits it. I do not recommend this; five is better than a swap.

---

## 9. Open questions for the review gate

1. **Five pilots or four?** §8.4 recommends five. This is the only recommendation here that changes
   the Wave 0 scope.
2. **Is `lib/seq.py` in Wave 0 or Wave 1?** The spec makes the anytime-valid family the Wave 1 lead
   but puts no primitive in the Wave 0 core. If a fifth pilot is accepted, there is a case for making
   it `anytime_valid_confidence_sequence` instead of the E-value — it exercises MUST-CONSTRUCT
   properly, carries `independence_required`, and de-risks the family the whole wave leads with.
   I still prefer the E-value, because `ROBUSTNESS` is the mode with no other candidate.
3. **Re-run the dedup pass.** Six clusters (C4–C13) were not visible at Wave 0 scoping. The spec says
   dedup runs "before any model code is written"; it should run again against this list before Wave 1
   code is written, or the cluster credit assumed in the difficulty column will not materialise.
4. **`aicc_model_ranking_with_weights` (#33) is the trim candidate** if 33 is judged too many (§2.5).
5. **Akinshin's finite-sample Rousseeuw–Croux factors (G5) are a shipped lookup table** and therefore
   fall under the §2.5 rule that no unverified constant may enter one. Either verify them against the
   primary source in Wave 1's definition of done, or restrict `lib/robust.py` to median/MAD/IQR and
   defer Sₙ/Qₙ.
