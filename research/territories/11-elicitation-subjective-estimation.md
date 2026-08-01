# Territory 11 — Elicitation, Subjective Probability, and Structured Estimation

**Scope owner:** the pure-inline tier. Everything here works with *zero data* — only beliefs, ranges, and
stated probabilities supplied by the agent or the user.

**Status:** research pass complete, 2026-07-31. No code written.

---

## 1. Territory summary

This territory converts an agent's unstructured guessing into arithmetic that can be checked, and it is the
only territory that functions when there is no dataset at all — the inputs are judgments, and the output is
a distribution plus an audit of whether those judgments were even coherent. Its core machinery is small and
almost entirely closed-form: fit a distribution to two or three elicited quantiles (in log space when the
quantity spans orders of magnitude), propagate that uncertainty through arithmetic analytically or by Monte
Carlo, and check the result against known anchors and against the agent's other estimates of the same
quantity. Its highest-value outputs are not the point estimates — an agent can guess those — but the four
things an agent reliably gets *wrong* unaided: how wide the interval should be (documented 90% intervals
cover ~50%), how uncertainty compounds through a product (as `σ√k`, not `σ·k`, so errors partially cancel),
what a base rate does to a likelihood ratio, and which single input dominates the total variance. A second
function of the territory is defensive: coherence auditing (sum-to-one, Fréchet bounds, conjunction-fallacy
detection, Dutch-book feasibility) catches judgment sets that are internally impossible before any
downstream model consumes them, and refusal conditions here are unusually load-bearing because the inputs
are unverifiable by construction. The literature is mature on the human side (SHELF, Cooke's classical
model, three decades of overprecision measurement) and freshly relevant on the machine side — recent work
finds LLM-elicited priors are frequently *worse than uninformative*, which is precisely the argument for
running elicited judgments through a checking layer rather than trusting them.

---

## 2. Ranked model table

Ranked by (value over an unaided smart guess) × (frequency an agent hits the situation) ÷ (cost to build).

**Tier key:** `INLINE` = works from arguments on the command line, no files. `DATAFILE` = needs a small
shipped lookup table. `MUST-CONSTRUCT-DATA` = needs the agent to have accumulated a resolved-outcome log.

| # | Model / method | SITUATION (retrieval phrasings) | Min inputs + tier | Beats what | Stdlib + numerics | REFUSE to print a number when |
|---|---|---|---|---|---|---|
| 1 | **Log-space quantile fit → lognormal** (2 or 3 elicited quantiles → μ, σ) | "roughly how many X are there"; "give me a range for this"; "I think it's about N, maybe as low as A, as high as B"; "order-of-magnitude estimate"; "turn my guess into a distribution" | 2 quantiles + their probabilities (e.g. p10, p90). **INLINE** | An agent naming a single number, or naming a range with no distribution behind it and no ability to compute a mean, a p99, or P(X > t) | **EASY.** `NormalDist.inv_cdf`, `math.log/exp`. Closed-form OLS for the 3-quantile overdetermined case | Any quantile ≤ 0 (lognormal needs positive support — route to normal); quantiles not strictly increasing in the stated probabilities; p10 = p90 (zero stated uncertainty — a lie); implied σ > ~3.5 (span > 10⁴ across the middle 80%, meaning the elicitation is a shrug, not an estimate) |
| 2 | **Monte Carlo propagation through an arbitrary expression** | "I need to multiply three rough estimates"; "what's the uncertainty of this calculation"; "combine these estimates"; "propagate my error through this formula"; "how uncertain is the answer" | An expression + a distribution per input. **INLINE** | Multiplying three point estimates and reporting the product with no interval — the single most common quantitative error an agent makes | **EASY.** `random` already ships `gauss`, `lognormvariate`, `triangular`, `betavariate`, `gammavariate`, `expovariate`, `paretovariate`; `statistics.quantiles` for output. No numerics gap at all | Any input is a point mass (nothing to propagate — say so); expression can divide by a variable whose distribution straddles 0 (the output has no finite mean; report quantiles only, or refuse); requested output quantile is beyond what N draws supports (MC standard error on the quantile exceeds the reported precision) |
| 3 | **Log-space delta method for products / quotients** (closed form; *exact* for lognormal inputs) | "how do errors combine when I multiply"; "does my uncertainty blow up"; "Fermi estimate error bars"; "why don't the errors just multiply" | Per-factor log-σ (or a ratio-style interval) + exponents. **INLINE** | The agent's two default wrong answers: (a) multiply the uncertainty factors together (`3⁴ = 81×`), or (b) ignore the compounding entirely and quote one factor's spread | **EASY.** `math.sqrt`, `math.log`. Exact for products of lognormals: `μ_Y = Σeᵢμᵢ`, `σ_Y = √(Σeᵢ²σᵢ²)` | Inputs are strongly dependent and no correlation was supplied (independence is the whole assumption — demand it explicitly or route to #2 with a copula); any factor can be ≤ 0; the expression contains a sum as well as a product (delta method on the sum term is a different, weaker approximation — route to #2) |
| 4 | **Bayes from prior + likelihood ratio** (base-rate correction, log-odds form, with prior-sensitivity band) | "how likely is this given the evidence"; "the test came back positive, what now"; "am I ignoring the base rate"; "update my belief"; "does this evidence actually move the needle" | Prior probability + likelihood ratio (or sens/spec). **INLINE** | Base rate neglect — the best-documented reasoning failure in the literature. Classic case: 1% prevalence, 90% sensitivity, 9% FPR → **9.2%** posterior, against a typical intuitive answer of 70–80% | **EASY.** Arithmetic only | Prior stated as 0 or 1 (no evidence can move it — say why); LR = 1 (evidence is uninformative — say so instead of printing an unchanged number); sensitivity/specificity given but no base rate supplied and none can be defended (this is the failure being corrected; refuse rather than assume 0.5) |
| 5 | **Interval-overconfidence correction** (widen a stated interval by a documented calibration factor) | "is my range too narrow"; "my 90% interval"; "am I overconfident"; "widen my estimate"; "how much should I hedge this range" | Stated interval + its nominal probability + an assumed/measured actual coverage. **INLINE** (**MUST-CONSTRUCT-DATA** to replace the assumed coverage with a measured one) | The most robust finding in the whole territory: nominal 90% intervals empirically cover ~50%. The correction is a *multiplicative widening of the log-width*, and it is large | **EASY.** `NormalDist.inv_cdf`; factor = `z_{(1+nom)/2} / z_{(1+act)/2}` | The actual-coverage parameter is a guess and the agent has no resolved-outcome log — print the factor **as a labelled assumption with its provenance**, never as a bare corrected interval; nominal ≤ actual (nothing to correct); interval already spans > 4 orders of magnitude (widening a shrug produces a bigger shrug) |
| 6 | **Reference-class blend / outside-view correction** (percentile-of-reference-class uplift + precision-weighted inside/outside merge) | "how long will this actually take"; "planning fallacy"; "what usually happens with projects like this"; "outside view"; "my estimate vs what's typical"; "should I pad this" | Inside-view estimate + reference-class ratio distribution (actual/forecast). **DATAFILE** for shipped reference classes, **INLINE** if the user supplies the class | Inside-view-only estimation. Flyvbjerg's core result: for large projects the actual/forecast ratio distribution is **fat-tailed**, so the mean uplift is not the right summary — you pick a percentile matching risk appetite | **EASY.** Log-space precision weighting `w = (1/τ²)/(1/τ² + 1/σ²)`; percentile lookup | No defensible reference class exists (the honest answer is "the outside view is unavailable", not a fabricated uplift); reference class n < ~10; the class is fat-tailed and the caller asked for the mean (refuse the mean, offer p50/p80) |
| 7 | **Coherence audit on a probability set** (sum-to-1, Fréchet bounds, conjunction check, conditional consistency, simplex projection) | "do my probabilities add up"; "are these estimates consistent"; "check my numbers"; "sanity check these probabilities"; "did I contradict myself"; "Dutch book" | ≥2 stated probabilities with their logical relationships. **INLINE** | Nothing — there is no unaided substitute. Catches conjunction-fallacy violations (`P(A∧B) > P(A)`), non-normalised partitions, and `P(A|B)·P(B) ≠ P(A∧B)` before downstream models consume them | **EASY** for the checks (Fréchet bounds, normalisation, multiplication rule, Euclidean projection onto the simplex). **MODERATE** for full Dutch-book detection (small LP feasibility → pure-Python simplex on ≤10 outcomes) | The event structure was not stated (the tool cannot infer whether events are exclusive/exhaustive — ask); violations found → print the **violations and the nearest coherent set**, and suppress every derived number until the caller re-states |
| 8 | **Multi-family quantile fit with fit diagnostics** (SHELF `fitdist` analogue: normal / lognormal / gamma / scaled-beta / Student-t, least squares on probabilities, report SSE) | "fit a distribution to my percentiles"; "what distribution matches these numbers"; "I gave quartiles, give me a distribution"; "which shape fits my belief" | 3+ quantiles + support bounds. **INLINE** | Assuming normality by reflex. The diagnostic output — *how badly the best family misses* — is the real product; SHELF's design point is that the fitted CDF need not pass through the elicited points | **MODERATE.** Needs regularized incomplete beta (ASA063/Cephes) and incomplete gamma (ASA032) for beta/gamma/t CDFs; least squares by 1–2 parameter search + bisection | Best family's max residual in probability exceeds ~0.05 (no family represents this belief — the elicitation is internally inconsistent, not the families' fault); fewer than 3 quantiles (fit is exactly determined, SSE is meaningless as a diagnostic); bounds contradict elicited quantiles |
| 9 | **Quantile fit → normal** (symmetric, unbounded, can go negative) | "give me a range for this signed quantity"; "estimate a difference/delta"; "my estimate ± how much"; "convert my range to a standard deviation" | 2 quantiles. **INLINE** | Same as #1 for quantities that can be negative or that are genuinely symmetric | **EASY.** `NormalDist.inv_cdf` only | Quantity is strictly positive and the fitted p1 < 0 (wrong family — route to #1); the elicited quantiles are visibly asymmetric about the median beyond a stated tolerance (a symmetric family is being forced) |
| 10 | **Scenario mixture** (probability-weighted branches → mixture mean, variance via law of total variance, quantiles by root-finding) | "best case, worst case, likely case"; "what if it goes either way"; "weight these scenarios"; "combine two possible futures"; "bimodal outcome" | ≥2 branches, each with a weight and a distribution (or a point). **INLINE** | The specific, ubiquitous error of averaging scenario point estimates. Worked example (w = .6/.3/.1, μ = 10/40/200, σ = 2/8/50): true mixture sd = **58.0**, but the within-scenario average sd is **16.5** — **92% of the variance is between-scenario and gets silently dropped** | **EASY.** Law of total variance is one line; mixture-CDF inversion by bisection | Weights don't sum to 1 (route to #7); a branch is described qualitatively with no distribution and no point value; the mixture is strongly multimodal and the caller asked for "the" estimate — refuse the point summary, return the modes |
| 11 | **Variance-contribution / tornado decomposition** (which input dominates the output uncertainty) | "which of my guesses matters most"; "where should I get real data"; "what's driving the uncertainty"; "is it worth measuring X"; "sensitivity analysis on my estimate" | The same inputs as #2 or #3. **INLINE** | Nothing. Turns "I'm uncertain" into "go measure exactly this one thing." For a log-space product the fractional contribution is `eᵢ²σᵢ² / Σeⱼ²σⱼ²` — free once you've done #3 | **EASY** in the analytic (product) case; **EASY** via one-at-a-time freezing in the MC case | Only one uncertain input (nothing to rank); contributions are within MC noise of each other (report "no dominant driver", not a spurious ranking); inputs correlated and correlation unspecified |
| 12 | **PERT-beta fit from three-point (min, mode, max)**, with the Vose modified-PERT λ | "optimistic, most likely, pessimistic"; "three point estimate"; "PERT"; "how long will this task take"; "best/worst/likely duration" | 3 numbers, optionally λ. **INLINE** | Averaging the three numbers, or using the mode alone | **EASY** for moments (`E = (a+4m+b)/6`, `sd = (b−a)/6`); **MODERATE** for exact quantiles (needs incomplete beta); `random.betavariate` makes the MC path EASY | `a ≥ m` or `m ≥ b`; the caller's a/b are "realistic" rather than absolute bounds — **PERT's `(b−a)/6` sd assumes a and b are true extremes and is badly wrong for elicited p10/p90**; refuse and route to #1/#9 unless the caller confirms hard bounds |
| 13 | **Verbal probability phrase → numeric interval** (Kent / IPCC / PHIA / NIC scales + documented reader variance) | "what does 'likely' mean as a number"; "they said probably not"; "convert this hedge word to a probability"; "how should I read 'a realistic possibility'" | A phrase + optionally a scale name. **DATAFILE** (the scale tables + empirical spread) | An agent silently picking a point value for someone else's hedge word. Kent's own scale has explicit margins (`probable = 75% ±12%`), and the *between-reader* variance for common phrases routinely exceeds the decision-relevant difference | **EASY.** Table lookup + interval arithmetic | Always refuse to return a single number — return the interval and the scale it came from; refuse entirely if the phrase isn't in any shipped scale (don't interpolate hedge words); flag when the phrase's plausible range spans the caller's decision threshold, which makes the whole conversion decision-irrelevant |
| 14 | **Log-space two-estimate consistency test** (Fermi triangulation: estimate the same quantity two independent ways, test the gap against the stated uncertainty) | "I got two different answers"; "does my estimate check out"; "sanity check this number two ways"; "these don't agree, how bad is it" | 2 estimates, each with a log-σ. **INLINE** | Averaging two disagreeing estimates and hiding the disagreement. The test is literally a two-sample z in log space: `\|ln Q₁ − ln Q₂\| / √(σ₁² + σ₂²)` | **EASY.** `math.log`, `NormalDist.cdf` | z > ~3: **refuse to average** — at least one decomposition contains a wrong factor, and the correct output is the discrepancy plus a prompt to find the bad term. The two "independent" routes share a factor (not independent — the test is invalid) |
| 15 | **Beta fit for a probability / proportion** (from quantiles, or from mean + interval) | "how confident am I in this success rate"; "give me a distribution over a probability"; "uncertainty about a percentage"; "my belief about a conversion rate" | 2 quantiles in (0,1), or mean + one quantile. **INLINE** | Stating a bare probability with no second-order uncertainty, so that downstream Bayesian updates have no prior to use | **MODERATE.** Needs regularized incomplete beta + its inverse; parameter search by bisection on a 2-D reparameterisation (mean, concentration) | Quantiles at exactly 0 or 1; implied concentration `α+β` > ~10⁴ (near-degenerate — the caller is claiming certainty they don't have); implied α or β < ~0.3 without an explicit U-shaped-belief flag |
| 16 | **Metalog / quantile-parameterized distribution fit** (3–5 terms, passes exactly through elicited quantiles) | "fit my percentiles exactly"; "none of the standard distributions fit"; "flexible distribution from quantiles"; "my belief is oddly shaped" | 3–5 quantiles + optional bounds. **INLINE** | Family choice. Keelin's metalog needs no shape assumption, has a closed-form quantile function (so sampling is `M(uniform)` — trivial), and 3–5 terms is the documented sweet spot for elicitation | **MODERATE.** Tiny (3–5)×(3–5) linear solve — Gaussian elimination with partial pivoting, pure Python. Basis: `[1, ln(y/(1−y)), (y−.5)ln(y/(1−y)), (y−.5), …]` | **Infeasibility** — the fitted quantile function must be monotone increasing; for k = 3 the condition is `a₂ > 0` and `\|a₃\|/a₂ < 1.66711`, and for general k it must be checked on a dense grid of y ∈ (0,1). If infeasible, refuse and fall back to #8. Also refuse to extrapolate below the lowest or above the highest elicited quantile beyond a stated margin — metalog tails are whatever the polynomial happens to do |
| 17 | **Log-odds evidence accumulation** (stack multiple independent likelihood ratios) | "several pieces of evidence point this way"; "combine these signals"; "how much do all these clues add up to"; "naive Bayes on my hunches" | Prior + ≥2 LRs. **INLINE** | Double-counting correlated evidence, and the general inability to add up several weak signals correctly. In log-odds the update is pure addition | **EASY.** `math.log`, arithmetic | Any two LRs are plausibly measuring the same underlying thing and no correlation discount was supplied — **this is the dominant failure mode and it inflates confidence multiplicatively**; refuse unless the caller asserts conditional independence explicitly, and print that assertion in the output |
| 18 | **Distribution aggregation: linear opinion pool vs. quantile (Vincent) averaging** | "reconcile my estimate with the user's"; "two people gave different ranges"; "combine these forecasts"; "average these distributions" | ≥2 fitted distributions + weights. **INLINE** | Averaging the two medians. Linear pooling averages CDFs (widens, can be multimodal, preserves disagreement); Vincentization averages quantiles (preserves shape, narrower) — these give materially different answers and the choice must be explicit | **EASY** for Vincentization (average the quantile functions); **EASY** for linear pooling via mixture-CDF bisection (this *is* #10) | Sources are not independent (pooling two restatements of one belief manufactures false consensus); the distributions barely overlap — refuse to pool, report the disagreement (this is #14 at distribution level) |
| 19 | **Self-scoring: Brier / log score + calibration–resolution decomposition** | "how good are my predictions"; "am I well calibrated"; "score my past estimates"; "track my forecast accuracy" | A log of (stated probability, resolved outcome) pairs. **MUST-CONSTRUCT-DATA** | Nothing — and it is the only thing that turns #5's widening factor from a voodoo constant into a measured parameter. `E[S] = UNC + REL − RES` separates "my numbers are wrong" from "my numbers are uninformative" | **EASY.** Arithmetic + binning | n < ~30 resolved outcomes (the decomposition is noise); all outcomes the same class (`UNC = 0`, resolution undefined); the bins are chosen post hoc to make the curve look good — require fixed bin edges |
| 20 | **Interval coverage + Winkler interval score** | "were my ranges any good"; "did my intervals contain the answer"; "score my prediction intervals"; "am I too narrow historically" | A log of (interval, nominal level, realised value). **MUST-CONSTRUCT-DATA** | Judging intervals by whether they "felt right". Winkler: `S_α = (u−l) + (2/α)(l−y)·1{y<l} + (2/α)(y−u)·1{y>u}` — the only score that penalises both width and misses, so it can't be gamed by widening | **EASY.** Arithmetic + binomial tail (`math.comb`) for the coverage test | n < ~20 intervals; intervals on wildly different scales pooled without normalising (the width term dominates); coverage tested without a binomial CI on the coverage estimate itself |
| 21 | **Extremizing transform** (`p' = σ(a·logit(p̄))`, a > 1) | "sharpen an aggregated forecast"; "the crowd is underconfident"; "extremize"; "combine independent forecasters" | An aggregated probability from ≥3 genuinely independent sources + a. **INLINE** | Plain averaging of independent partially-informed forecasts, which provably under-uses information | **EASY.** `math.log`, `math.exp` | **Refuse for a single agent's own estimate.** Extremizing is justified only by information diversity across independent forecasters; applied to one already-overconfident model it makes calibration strictly worse. Also refuse when sources < 3, when sources share a corpus/model, or when a > ~3 |
| 22 | **Triangular fit from three-point** | "quick range with a most-likely value"; "I only have min/mode/max"; "simple three point" | 3 numbers. **INLINE** | Only a bare point estimate. **Demoted deliberately:** the triangular shape overweights the tails and underweights the shoulders relative to PERT-beta and rarely resembles any real process; it survives only as an unbounded-free fallback when hard bounds genuinely exist and no shape information does | **EASY.** `random.triangular` is in stdlib; closed-form CDF/quantiles | Same bound violations as #12; also print an explicit note that PERT-beta (#12) is preferred whenever any shape belief exists |

---

## 3. Detailed notes on the load-bearing items

### 3.1 Why log space is not optional (items 1, 3, 11, 14)

For a positive quantity spanning orders of magnitude, the natural elicitation is multiplicative ("somewhere
between 100 and 10,000") and the natural model is lognormal.

Fit from two quantiles `(p₁, q₁)`, `(p₂, q₂)`:

```
σ = (ln q₂ − ln q₁) / (z_{p₂} − z_{p₁})
μ = ln q₁ − σ·z_{p₁}
```

With three quantiles the system is overdetermined and there is a **closed-form OLS solution in log space** —
no optimiser needed:

```
σ̂ = Σ(zᵢ − z̄)(ln qᵢ − ln q̄) / Σ(zᵢ − z̄)²
μ̂ = ln q̄ − σ̂·z̄
```

and the residuals `ln qᵢ − (μ̂ + σ̂zᵢ)` are the fit diagnostic. Worked example — an agent states
p10 = 100, p50 = 400, p90 = 5000. Best lognormal has σ = 1.526, implied median **585**, and the worst
residual is a factor of **1.46**: the agent's stated median is 1.46× away from the median implied by its own
tails. That misfit number is the product; it tells the agent its three statements aren't quite compatible.

**Terminology trap the tool must enforce:** p10–p90 is an **80%** interval, not a 90% one. Agents and users
conflate these constantly, and it changes σ by 28% (`z = 1.2816` vs `1.6449`).

**The mean is not the typical value.** If p10/p90 span 100×, then σ = 1.797 and
`mean/median = e^{σ²/2} = 5.02`. An agent that elicits a range and then reports "the estimate" has to decide
which one, and unaided it will usually report something near the median while calling it the average.

### 3.2 Error cancellation in a product — the headline result (item 3)

For `Y = ∏Xᵢ^{eᵢ}` with independent lognormal factors, `ln Y` is exactly normal with
`σ_Y = √(Σeᵢ²σᵢ²)`. So for k factors of equal log-uncertainty:

> **k factors each uncertain by a factor of f ⟹ the product is uncertain by a factor of `f^√k`.**

| k factors, each ±3× (p10/p90) | Correct product spread | What an agent says unaided |
|---|---|---|
| 2 | **4.7×** | 9× |
| 3 | **6.7×** | 27× |
| 4 | **9.0×** | 81× |
| 9 | **27×** | 19,683× |

Wikipedia's Fermi-problem article states the same result from the random-walk direction: 9 steps each with
factor-2 uncertainty gives `2^√9 = 8`, i.e. a 1/8-to-8× band, against a worst case of 2⁹ = 512. This is a
number the agent cannot produce in its head and gets wrong by orders of magnitude in both directions
(catastrophising, or ignoring compounding altogether). It is the strongest single justification for this
territory existing.

Conversely, for **sums** of k comparable independent quantities the *relative* uncertainty shrinks as
`1/√k` — worth a companion note, because agents apply product intuitions to sums.

The delta-method fallbacks for non-lognormal inputs (all first-order, all in the same tool):

```
f = AB or A/B :  (σ_f/f)² ≈ (σ_A/A)² + (σ_B/B)²
f = A ± B     :  σ_f² = σ_A² + σ_B² ± 2σ_AB
f = aA^b      :  σ_f ≈ |f·b·(σ_A/A)|
f = a·ln(bA)  :  σ_f ≈ |a·(σ_A/A)|
f = a·e^{bA}  :  σ_f ≈ |f|·|b·σ_A|
```

These fail when relative uncertainties are large (say σ/μ > 0.3) or the function is strongly nonlinear over
the input range — at which point the tool must route to Monte Carlo (#2) rather than print a linearised
number. That routing rule should be automatic, not advisory.

### 3.3 The overconfidence multiplier, stated honestly (item 5)

The empirical finding is robust and large: nominal 90% intervals have hit rates "often as low as 50%".
Converting a *stated* interval into an *actually*-calibrated one is a multiplication of the interval's
half-width (in log space for #1, linear for #9) by `z_{(1+nominal)/2} / z_{(1+actual)/2}`:

| Stated level | Actual coverage | Widen half-width by |
|---|---|---|
| 90% (p5–p95) | 50% | **2.44×** |
| 90% | 60% | 1.95× |
| 90% | 70% | 1.59× |
| 90% | 80% | 1.28× |
| 80% (p10–p90) | 50% | **1.90×** |
| 98% | 60% | 2.76× |

Per the project's no-voodoo-constants rule, the *actual coverage* is a caller-supplied or
measured parameter, never a hardcoded default. The correct product design: ship the table, require the
caller to name the coverage assumption, print it in the output with its provenance, and point at #19/#20 as
the way to replace the assumption with a measurement. A tool that silently doubles someone's interval on the
strength of a 1982 psychology result is doing the same thing the result warns about.

### 3.4 Scenario mixtures — the variance term agents delete (item 10)

`Var = Σwᵢ(σᵢ² + μᵢ²) − (Σwᵢμᵢ)²`, which decomposes as within-scenario `Σwᵢσᵢ²` plus between-scenario
`Σwᵢ(μᵢ − μ̄)²`. Worked case with weights .6/.3/.1, means 10/40/200, sds 2/8/50:

- Mixture mean **38.0**, mixture sd **58.0**
- Within-scenario sd alone: **16.5**
- **92% of the total variance is between-scenario**

An agent that reasons scenario-by-scenario and then reports a weighted average of the point estimates
throws away almost all of the uncertainty. This is a one-line formula with an enormous effect size, and it
generalises: whenever the agent enumerates cases, the between-case spread usually dominates.

### 3.5 Coherence auditing (item 7)

The checkable relations, in the order they should be tested:

1. `0 ≤ p ≤ 1` for every stated probability.
2. Exhaustive-exclusive partition: `Σp = 1` within tolerance. Report the deficit and the Euclidean
   projection onto the simplex as the minimal repair.
3. `P(A) + P(¬A) = 1`.
4. Monotonicity: `A ⊆ B ⟹ P(A) ≤ P(B)`.
5. **Conjunction:** `P(A∧B) ≤ min(P(A), P(B))`. Violation is the conjunction fallacy — a hard error, not a
   rounding issue.
6. Fréchet bounds: `max(0, P(A)+P(B)−1) ≤ P(A∧B) ≤ min(P(A), P(B))`.
7. Multiplication rule: `P(A∧B) = P(A|B)·P(B)`.
8. **Dutch book:** given stated prices on bets whose payoff vectors are known, a Dutch book exists iff no
   probability vector is consistent with the prices — a small LP feasibility problem. The canonical
   illustration is the four-horse book with implied probabilities summing to 1.05, where a fixed stake
   pattern loses money on every outcome.

Design point: the audit's output is a **list of violations plus the nearest coherent set**, and it should
suppress downstream numbers rather than annotate them. Prior art in this repo (§0.3 of `RESEARCH.md`)
documents that agents read numbers past warnings.

### 3.6 What the machine-elicitation literature says about trusting the agent's own priors

This is the territory's own epistemic warning label, and it is recent and specific. Selby et al., *Had
enough of experts? Quantitative knowledge retrieval from large language models* (arXiv 2402.07770) tested
LLMs as substitutes for human experts in prior elicitation, using a histogram/roulette method and an
attempt to make models follow SHELF itself, across single-expert, expert-conference, and non-expert
role-play prompts. Findings that bear directly on tool design:

- **Effective sample size frequently zero** — the LLM-elicited prior was outperformed immediately by
  minimal real data, i.e. it was worse than uninformative.
- **Prior–data conflict** was common: prior predictive distributions conflicted with actual observations
  (weather-forecasting task).
- **Absurd overconfidence in the tails**: Mistral 7B occasionally emitted beta priors with α ≥ 1000.
- **Role-play doesn't help**: "Roleplaying as experts in different sub-fields did not have a noticeable
  effect on the priors."
- Cross-model divergence was large (LLaMA-family centred Cohen's δ at 0.2–0.25; GPT-4 at 0.5).

Implications the report recommends adopting as hard rules:

1. **Ship a prior-predictive plausibility check** as a mandatory post-step on any fitted distribution
   (item: compute the percentile of any known anchor value under the fit; refuse if it lands beyond
   p0.1/p99.9). This directly targets the prior–data conflict failure.
2. **Cap implied concentration** on beta/gamma fits (item 15's α+β > 10⁴ refusal) — that is precisely the
   α ≥ 1000 pathology.
3. **Do not offer "act as an expert" prompting as a calibration technique.** It is measured not to work.

Countervailing and also relevant: Tian et al., *Just Ask for Calibration* (EMNLP 2023, arXiv 2305.14975)
found verbalized confidence from RLHF-tuned models beats the models' own conditional probabilities,
"reducing the expected calibration error by a relative 50%". So an agent's *stated* number is the best
signal available from it — which is exactly why this territory takes stated numbers as input and spends its
effort on checking and propagating them rather than on generating them.

### 3.7 Numerics inventory (what actually has to be built)

Already in stdlib, no work:
- `statistics.NormalDist` — normal CDF and `inv_cdf`. Covers items 1, 3, 5, 9, 14, 21 outright.
- `random.gauss / lognormvariate / triangular / betavariate / gammavariate / expovariate / paretovariate /
  weibullvariate` — **the entire Monte Carlo layer is free.** This is the single biggest stdlib win in the
  territory and it means item 2, the second-most-valuable model, is EASY.
- `statistics.quantiles`, `math.lgamma`, `math.erf`, `math.comb`.

Must be built (shared with other territories, so build once in the numerics core):
- **Regularized incomplete beta** `I_x(a,b)` + inverse — unlocks beta, Student-t, PERT quantiles (items 8,
  12, 15). ASA063 / Cephes `incbet` continued fraction.
- **Regularized incomplete gamma** `P(a,x)` + inverse — unlocks gamma (item 8). ASA032.
- **Bisection/Brent root finder** — mixture-CDF inversion, parameter search. ~30 lines.
- **Gaussian elimination with partial pivoting** on ≤6×6 — metalog coefficients (item 16), correlated-input
  Cholesky. ~40 lines.
- **Simplex LP feasibility** on ≤10 outcomes — full Dutch-book detection (item 7). Optional; the Fréchet +
  normalisation checks cover most real cases without it.

Per §0.7 of `RESEARCH.md`: golden tests must assert against **published reference values** from ASA063/
ASA032, not against SciPy, and each function declares its accuracy envelope.

---

## 4. Recent advances (~last 10 years)

**Quantile-parameterized distributions become the default flexible family (2016 →).** Keelin's metalog
distribution gives a closed-form quantile function that interpolates elicited quantiles exactly, with no
shape family chosen in advance, and with sampling reduced to evaluating `M(u)` for `u ~ Uniform(0,1)`. The
documented guidance is 3–5 terms for elicitation and 8–12 for data fitting, with an explicit feasibility
condition (`a₂ > 0`, `|a₃|/a₂ < 1.66711` for k = 3). This is a genuinely better default than "pick normal or
lognormal" and it is stdlib-implementable.
[Keelin 2016, *The Metalog Distributions*](https://www.researchgate.net/publication/311091031_The_Metalog_Distributions) ·
[Metalog distribution overview](https://en.wikipedia.org/wiki/Metalog_distribution)

**Hybrid elicitation: uncertainty *about* the elicited quantiles (2024).** Perepolkin et al., *Quantile-
Parameterized Distributions for Expert Knowledge Elicitation* (*Decision Analysis*, 2024) put a Dirichlet-
type prior over the quantiles themselves, so the protocol encodes "the expert is not certain their p90 is
exactly 5000." This matches SHELF's own philosophy — the fitted CDF deliberately need not pass through the
elicited points — and it is the principled version of the residual-reporting design in §3.1.
[doi:10.1287/deca.2024.0219](https://doi.org/10.1287/deca.2024.0219)

**LLMs as elicitation subjects, measured rather than assumed (2024).** See §3.6. The headline is negative
and it is the most decision-relevant recent finding for this project: LLM-elicited priors frequently have
**effective sample size zero**, exhibit prior–data conflict, and show pathological tail concentration; expert
role-play does not improve them. [arXiv 2402.07770](https://arxiv.org/abs/2402.07770)

**Verbalized confidence beats logits for RLHF models (2023).** Relative ECE reduction ~50% across TriviaQA,
SciQ, TruthfulQA. Supports taking the agent's stated numbers as the input signal.
[arXiv 2305.14975](https://arxiv.org/abs/2305.14975)

**LM forecasting systems approaching crowd aggregates (2024).** Halawi et al., *Approaching Human-Level
Forecasting with Language Models*, build a retrieval-augmented forecasting pipeline that "nears the crowd
aggregate of competitive forecasters, and in some settings surpasses it." Relevant as evidence that the
aggregation/calibration layer (items 18, 19, 21) is where the measurable gains sit, not the raw judgment.
[arXiv 2402.18563](https://arxiv.org/abs/2402.18563)

**Reference-class forecasting institutionalised, and fat tails recognised.** The UK Department for Transport
adopted the Flyvbjerg/COWI method as formal guidance in June 2004, and the approach has since spread through
public-investment appraisal. The methodological update over the last decade is the recognition that
cost-overrun distributions are **fat-tailed**, which invalidates mean-based uplifts and forces
percentile-based ones — the Edinburgh Tram Line 2 case is the canonical worked example (50th percentile →
40% contingency, 80th percentile → 57%; actual outcome exceeded even those).
[Reference class forecasting](https://en.wikipedia.org/wiki/Reference_class_forecasting)

**Structured expert judgment consolidates on quantiles + least-squares fitting + linear pooling — and admits
it is under-validated.** The NIHR reference-protocol review of structured expert elicitation in health-care
decision-making surveys quantile/bisection vs. chips-and-bins elicitation and least-squares vs.
method-of-moments fitting, and concludes that "only a small number of these methods have been evaluated and
compared," echoing O'Hagan's call for much more work before advocating any one method. Practical
consequence for this module: **report fit diagnostics and offer alternatives; do not present one family
choice as authoritative.**
[NIHR / NCBI Bookshelf NBK571048](https://www.ncbi.nlm.nih.gov/books/NBK571048/) ·
[SHELF R package overview](https://cran.r-project.org/web/packages/SHELF/vignettes/SHELF-overview.html)

**Proper scoring rules for intervals and distributions become standard practice.** CRPS and the Winkler
interval score are now the default way to evaluate probabilistic forecasts and prediction intervals, giving
this territory a rigorous self-evaluation loop (items 19, 20) that older elicitation work lacked.
[Scoring rule](https://en.wikipedia.org/wiki/Scoring_rule)

---

## 5. Cut list

| Cut | Why |
|---|---|
| **Cooke's classical model (performance weighting via seed questions)** | Requires a battery of calibration questions with known answers, plus a *panel*. A single agent has neither. MUST-CONSTRUCT-DATA at a scale that never happens inline. |
| **Delphi / IDEA multi-round protocols** | Human group processes. The maths is trivial; the value is entirely in the social round structure, which doesn't exist for one agent. |
| **Full Bayesian hierarchical elicitation / MCMC prior fitting** | Needs a sampler and diagnostics. Belongs to the Bayesian-workflow territory and violates the pure-inline premise. |
| **Copula families beyond Gaussian (t, Clayton, Gumbel) for dependent inputs** | The agent can rarely justify a correlation number, let alone a tail-dependence family. A single Gaussian rank correlation stays, folded into item 2. |
| **Imprecise probability / probability boxes / Dempster–Shafer** | Inputs (an interval *of* probabilities, belief/plausibility pairs) are things no agent can supply honestly. Doubles the interface complexity for no decision that changes. |
| **AHP pairwise comparison + consistency ratio** | The consistency ratio *is* a real coherence check on elicited ratios and is stdlib-feasible via power iteration — but it belongs to the multi-criteria decision territory, and the random-index constants are exactly the voodoo the project bans. |
| **Prospect-theory probability weighting function** | Describes how people distort probabilities; provides no defensible way to invert the distortion on a specific stated number. Diagnostic, not corrective. |
| **Maximum-entropy distribution from moment constraints** | For the constraint sets an agent can actually state it collapses to known families (bounds only → uniform; positive mean → exponential; mean + variance → normal). Keep maxent as a *selection rule* documented inside item 8; don't ship a solver. |
| **Dirichlet elicitation for multinomial beliefs** | Real (SHELF has a vignette for it) but rare in agent work, and item 7's simplex projection covers the practical need of "make my category probabilities coherent." |
| **Bayesian Truth Serum / prediction markets / peer prediction** | Require multiple self-interested respondents. |
| **Subjective hazard / survival-curve elicitation** | Niche; the two-quantile lognormal fit plus a scenario mixture covers the realistic agent cases. |
| **Anchoring-adjustment correction models** | The literature measures the bias well but offers no validated numeric correction for an arbitrary stated value. Ship it as a *protocol* note (elicit extremes before the central value) rather than a computation. |
| **Rule of three / Laplace rule of succession for zero-event probabilities** | Genuinely useful, but it takes *data* (n trials, k events). Belongs to the small-sample territory; cross-link only. |
| **Extremizing applied to a single agent's own estimate** | Not merely cut — actively banned in item 21's refusal list. The justification for extremizing is information diversity, which a single model does not have. |

---

## 6. Cross-territory overlaps

- **Bayesian inference / conjugate updating.** This territory *produces* the prior that territory consumes.
  Hard interface: item 1/8/15 must emit parameters in the exact form the conjugate updater takes (μ,σ for
  lognormal; α,β for beta; shape/rate for gamma). Item 15's beta fit and a Beta-Binomial updater must share
  one parameterisation or the two territories will silently disagree.
- **Monte Carlo / simulation.** Item 2 *is* the simulation engine, restricted to elicited-input propagation.
  Build it once; the seeding, convergence (MC standard error), and reproducibility policy must be shared.
- **Numerics core.** Incomplete beta/gamma (items 8, 12, 15), the root finder, and the small linear solver
  (item 16) are shared infrastructure with every distribution-bearing territory. Build in the core, not here.
- **Decision analysis / value of information.** EVPI and EVSI take an elicited distribution as their input;
  item 11 (variance contribution) is the cheap precursor to a full EVPI ("which input is worth measuring")
  and the two should route to each other.
- **Forecasting / time series.** Reference classes (item 6) are base rates; when a time series exists, that
  territory supersedes item 6's shipped tables.
- **Probabilistic forecast evaluation / calibration.** Brier, log score, CRPS, Winkler, and reliability
  diagrams (items 19, 20) are shared with any territory that emits a probabilistic prediction. Single
  implementation, consumed here as *self*-scoring.
- **Small-sample inference.** Rule of three, Laplace's rule, and Jeffreys intervals are the data-bearing
  siblings of items 4 and 15; the router must distinguish "I have zero data" (here) from "I have three
  observations" (there), because agents describe both as "I barely know anything."
- **Sensitivity analysis.** Item 11 is a first-order variance decomposition; Sobol indices and full tornado
  machinery live elsewhere and take over when there are enough inputs or enough nonlinearity.
- **Router / retrieval index.** Per §0.6 of `RESEARCH.md`, this territory contributes an unusually large
  share of the *situation phrasings* — its models are the ones an agent reaches for when it can't even name
  what it needs ("give me a range", "how many X are there"). Recall matters more than precision here, and
  item 7 (coherence audit) should be reachable as a background check from almost anywhere.

---

## 7. Sources

- [SHELF R package overview (CRAN vignette)](https://cran.r-project.org/web/packages/SHELF/vignettes/SHELF-overview.html) — families fitted, least-squares `fitdist`, quantile vs. probability questions, linear pooling, SSE feedback.
- [Eliciting a Dirichlet Distribution — SHELF vignette](https://cran.r-project.org/web/packages/SHELF/vignettes/Dirichlet-elicitation.html)
- [Jeremy Oakley — Expert elicitation research page, University of Sheffield](https://jeremy-oakley.sites.sheffield.ac.uk/research/expert-elicitation)
- [Developing a reference protocol for structured expert elicitation in health-care decision-making (NIHR / NCBI Bookshelf NBK571048)](https://www.ncbi.nlm.nih.gov/books/NBK571048/) — evidence review on elicitation level, fitting methods, and aggregation; the "only a small number of these methods have been evaluated" caveat.
- [Structured expert elicitation for healthcare decision making: A practical guide (CHE, University of York)](https://www.york.ac.uk/media/che/documents/Structured%20expert%20elicitation%20for%20healthcare%20decision%20making%20A%20practical%20guide.pdf)
- [O'Hagan, *Expert Knowledge Elicitation: Subjective but Scientific*, The American Statistician 2019](https://www.tandfonline.com/doi/full/10.1080/00031305.2018.1518265)
- [Keelin, *The Metalog Distributions* (2016)](https://www.researchgate.net/publication/311091031_The_Metalog_Distributions)
- [Metalog distribution — formulas, fitting, feasibility conditions](https://en.wikipedia.org/wiki/Metalog_distribution)
- [Keelin & Powley, *Quantile-Parameterized Distributions*, Decision Analysis](https://dl.acm.org/doi/10.1287/deca.1110.0213)
- [Perepolkin et al., *Quantile-Parameterized Distributions for Expert Knowledge Elicitation*, Decision Analysis 2024](https://doi.org/10.1287/deca.2024.0219)
- [Selby et al., *Had enough of experts? Quantitative knowledge retrieval from large language models* (arXiv 2402.07770)](https://arxiv.org/abs/2402.07770) — LLM priors, SHELF/histogram elicitation, effective sample size zero, prior–data conflict, α ≥ 1000 pathology.
- [Tian et al., *Just Ask for Calibration* (EMNLP 2023, arXiv 2305.14975)](https://arxiv.org/abs/2305.14975) — verbalized confidence beats logits for RLHF LMs, ~50% relative ECE reduction.
- [Halawi et al., *Approaching Human-Level Forecasting with Language Models* (arXiv 2402.18563)](https://arxiv.org/abs/2402.18563)
- [Three-point estimation — PERT and triangular formulas, aggregation caveats](https://en.wikipedia.org/wiki/Three-point_estimation)
- [Cost estimating: triangular vs PERT (Lumivero)](https://lumivero.com/resources/blog/cost-estimating-triangular-vs-pert/) — triangular overestimates tails, underestimates shoulders.
- [The Conundrum of Three Point Estimation and PERT (Planning Planet)](https://planningplanet.com/blog/conundrum-three-point-estimation-and-pert)
- [Reference class forecasting — method, Edinburgh Tram case, UK DfT 2004 guidance](https://en.wikipedia.org/wiki/Reference_class_forecasting)
- [Overconfidence effect — overprecision, 90% intervals with ~50% hit rates](https://en.wikipedia.org/wiki/Overconfidence_effect)
- [Words of estimative probability — Sherman Kent scale, NIC paradigm, PHIA yardstick, interpretation variance](https://en.wikipedia.org/wiki/Words_of_estimative_probability)
- [Mauboussin & Mauboussin, *If You Say Something Is "Likely," How Likely Do People Think It Is?* HBR 2018](https://hbr.org/2018/07/if-you-say-something-is-likely-how-likely-do-people-think-it-is) — paywalled; verify the survey n and per-phrase spreads before citing specific figures.
- [Propagation of uncertainty — delta method, product/quotient/power/log formulas, failure conditions](https://en.wikipedia.org/wiki/Propagation_of_uncertainty)
- [Fermi problem — log-space random walk, √n error growth, the 2^√9 = 8 worked bound](https://en.wikipedia.org/wiki/Fermi_problem)
- [Scoring rule — Brier, log, spherical, REL/RES/UNC decomposition, CRPS, Winkler interval score](https://en.wikipedia.org/wiki/Scoring_rule)
- [Dutch book — coherence conditions, multiplication rule, LP-style detection](https://en.wikipedia.org/wiki/Dutch_book)
- [ASA063 — regularized incomplete beta](https://people.math.sc.edu/Burkardt/py_src/asa063/asa063.html)
- [ASA032 — regularized incomplete gamma](https://people.math.sc.edu/Burkardt/c_src/asa032/asa032.html)
- [Python `random` module — stdlib variate generators](https://docs.python.org/3/library/random.html)
- [Python `statistics` module — `NormalDist`, `quantiles`](https://docs.python.org/3/library/statistics.html)

### Verification notes

- All numeric results in §3.1–§3.4 were computed with pure Python 3 stdlib during this research pass and are
  reproducible from the formulas as written.
- The Mauboussin HBR survey is cited from its landing page only; the specific sample size and per-phrase
  spreads sit behind a paywall and were **not** verified. Do not put those numbers in a shipped datafile
  without obtaining the article.
- UK DfT optimism-bias *uplift tables* exist and are referenced in the Wikipedia article, but the specific
  per-sector percentages were not verified in this pass. The Edinburgh Tram figures (£320m forecast; 50th
  percentile → 40% contingency; 80th → 57%; £776m actual) were verified.
- Web-search budget was exhausted mid-pass; several sources were retrieved by direct fetch instead. Two
  fetches failed (Taylor & Francis 403, arXiv HTML 404) and were replaced by equivalent sources.
