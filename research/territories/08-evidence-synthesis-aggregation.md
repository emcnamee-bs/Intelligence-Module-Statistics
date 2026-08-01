# Territory 08 — Evidence Synthesis, Aggregation, and Combining Conflicting Sources

Research pass: 2026-07-31. Scope: pure-Python-3-stdlib models an agent invokes from the CLI when
2–50 sources disagree.

---

## 1. Territory summary

This is the territory the agent enters dozens of times a session and currently resolves by vibes:
three benchmarks report different numbers, two documents contradict each other, five sub-agents
return five answers, and the agent picks one or splits the difference in its head. The formal
machinery that exists — inverse-variance pooling, random-effects meta-analysis, p-value merging,
opinion pooling, belief functions — was almost all designed for k ≥ 10 sources, and the agent's
normal case is k = 3, where the between-source variance parameter τ² that the entire random-effects
edifice rests on is essentially unestimable. The single most valuable output of this territory is
therefore *not* a pooled point estimate but a **consistency verdict plus an honestly-wide interval**:
Cochran's Q tells you whether the stated uncertainties can explain the observed spread, the Birge /
PDG scale factor tells you how much to inflate the error bar when they cannot, and the order-statistic
interval gives an exact distribution-free answer at k = 3 with no assumptions at all. The second most
valuable output is a **refusal**: with 4 sources you cannot detect publication bias, cannot estimate
I² to better than "somewhere between 0 and 90%", and cannot run an outlier test with any power —
tools that print those numbers anyway are the main way this territory produces confident nonsense.
Three genuinely modern results make this territory much stronger than a 2010 textbook would suggest:
arbitrary-dependence p-merging (you can combine p-values with *no* independence assumption at a known
constant cost), weakly-informative-prior Bayesian hierarchical models (which handle k = 3 by refusing
to estimate τ² and integrating over it instead), and the empirical finding that the geometric mean of
odds beats the arithmetic mean of probabilities for aggregating forecasts.

---

## 2. Ranked model table

Tier key: **INLINE** = a handful of numbers as CLI flags. **DATAFILE** = a small file (CSV/JSON) the
agent writes. **MUST-CONSTRUCT-DATA** = the agent has to go build a dataset (e.g. scored calibration
questions) before the method is usable at all.

| # | Model / method | SITUATION (retrieval phrasings) | Minimum viable inputs + tier | Beats what | Stdlib feasibility + numerics | REFUSE conditions |
|---|---|---|---|---|---|---|
| 1 | **Inverse-variance pooling + Cochran's Q + Birge/PDG scale factor** — pool with `w_i = 1/s_i²`, `μ̂ = Σw_i y_i / Σw_i`, `SE = 1/√Σw_i`; `Q = Σw_i(y_i−μ̂)²` on `k−1` df; if `R_B = √(Q/(k−1)) > 1` inflate SE by `R_B` | "three sources give different numbers with error bars, what's the real value"; "combine measurements that disagree by more than their uncertainties"; "my estimates conflict — how wide should my interval actually be?"; "which number do I quote when the papers disagree" | `k` pairs of (estimate, standard error). **INLINE** (k ≤ ~8) or **DATAFILE** | Agent's default of "average them" (ignores precision) or "trust the tightest one" (ignores disagreement). Q converts "these look different" into a calibrated statement; the scale factor is the only principled small-k error inflation that works at k = 2 | **EASY**. Arithmetic + `chi2` upper tail. For even df use the closed form `P(χ²_{2m}>x)=e^{−x/2}Σ_{j<m}(x/2)^j/j!`; for odd df use `erfc` plus a finite sum. No special functions strictly required | Any `s_i ≤ 0` or missing. Estimates not on a common scale (mixed units, mixed effect metrics). `R_B > 3` or `Q > χ²_{k−1,0.999}` → data are irreconcilable; print the conflict, refuse a pooled value (this is PDG practice). One source with `s_i` more than `3√k ×` the smallest `s_i` → exclude it from the S computation or refuse |
| 2 | **Bayesian normal–normal hierarchical model with weakly-informative τ prior** — grid over τ ∈ [0, τ_max]; for each τ, `w_i(τ)=1/(s_i²+τ²)`, `V(τ)=1/Σw_i`, `μ̂(τ)=VΣw_i y_i`, marginal `L(τ) ∝ √V·Π√w_i·exp(−½Σw_i(y_i−μ̂)²)`; posterior of μ is a finite mixture of normals | "only 3 studies, random effects blows up, what do I do"; "combine a handful of noisy estimates properly"; "meta-analysis with too few studies"; "I don't have enough sources to estimate between-source variance" | `k ≥ 2` pairs (estimate, SE) + a prior scale for τ (half-normal scale, default ≈ half the typical `s_i`, or an empirical prior). **INLINE** | Every frequentist random-effects method at k ≤ 5, all of which either plug in a τ̂ that is mostly noise (DL) or blow the interval up by `t_{1,.975}=12.7` (HK at k=2). This is the honest k=3 answer: it *never estimates τ*, it integrates over it | **MODERATE**. 1-D grid (200–400 points) + trapezoid/Simpson; `NormalDist` for components; mixture quantiles by bisection on the mixture CDF. Everything else is closed form. ~120 lines | No defensible prior scale available and no empirical prior for the outcome type → refuse (at k ≤ 3 the answer is prior-dominated, so an arbitrary prior is a fabricated result). **Mandatory prior-sensitivity run**: re-fit at 0.5× and 2× the prior scale; if the interval width moves > 50%, suppress the headline number and report the range of answers instead |
| 3 | **Distribution-free interval for the consensus (order statistics / sign test) + median + MAD** — coverage of `(x_(r), x_(k+1−r))` for the population median is `1 − 2Σ_{j<r} C(k,j)/2^k`; for `(min,max)` this is `1 − 2^{1−k}` | "three benchmarks say 42, 47 and 61 and none of them gave me error bars"; "how confident can I be in the middle value"; "no uncertainty estimates, just numbers"; "what range should I actually quote from these results" | `k ≥ 2` bare numbers, **no SEs needed**. **INLINE** | Agent's "average of 42, 47, 61 is 50" with an invented confidence. This gives an *exact, assumption-light* statement: with 3 numbers, (min, max) is a 75% interval; with 5, 93.75%. Nothing else in the territory is exact at k=3 | **EASY**. `math.comb`, sorting, `statistics.median`. MAD needs `median(abs(x−median))`; scale by 1.4826 for normal-consistency | k = 1. Sources are not exchangeable draws (one is a rerun of another; one is a summary of the others) — the sign test assumes independence and this is the commonest violation. **Always print the caveat that this covers the median of the *source* distribution, not the truth** — shared bias across sources is invisible to it. Refuse to relabel it a CI for the truth |
| 4 | **Leave-one-out / tipping-point influence analysis** — recompute the pooled estimate (and the decision) dropping each source; report max shift in pooled-SE units and whether the sign or the threshold decision flips; also report how far one source would have to move to flip it | "is my answer driven by one source"; "how fragile is this conclusion"; "what if the outlier study is wrong"; "which of these sources actually matters" | Same inputs as #1 or #5, plus optionally a decision threshold. **INLINE** | Nothing — agents do not do this at all, and at k=3 it is often the *entire* finding ("drop source 2 and the conclusion reverses"). Cheap, exact, and honest at every k including k=2 | **EASY**. Loop over the pooler. No new numerics | k = 2 (LOO is just "report each one", which is still worth printing). Do not report a "significantly influential" verdict — there is no test here, only a sensitivity display |
| 5 | **Random-effects meta-analysis (Paule–Mandel or DerSimonian–Laird τ²) + modified Hartung–Knapp t interval** — `τ²_DL = max(0,(Q−(k−1))/C)`, `C = Σw_i − Σw_i²/Σw_i`; PM solves `Σ w_i(τ²)(y_i−μ̂)² = k−1` by bisection; `q² = Σw_i(y_i−μ̂)²/(k−1)`, `SE_HK = q·√(1/Σw_i)`, CI `= μ̂ ± t_{k−1,1−α/2}·SE_HK`, with **`q* = max(1,q)`** | "run a meta-analysis on these studies"; "pool effect sizes across experiments that don't agree"; "random effects model for my results"; "combine studies allowing for real differences between them" | `k ≥ 3` pairs (estimate, SE). **DATAFILE** (or INLINE for small k) | The classic DL + normal-z interval, whose 95% CIs actually cover ~92–93% at small k and much worse under heterogeneity. HKSJ consistently gives closer-to-nominal error rates. PM/REML dominate DL, which is biased downward exactly when k is small | **MODERATE**. Student-t quantile is the only hard piece: either the regularized incomplete beta (ASA063 / Cephes `incbet`) inverted by bisection, or a Cornish–Fisher/Hill approximation. PM needs bisection on a monotone function — trivial and robust | k < 3 → refuse, use #1 or #2. **Unmodified HK at k=2–3 has two opposite pathologies and both must be blocked**: when sources agree closely `q → 0` and the interval collapses to absurd narrowness (fixed by `max(1,q)`); when they disagree, `t_{1,.975}=12.7` produces an interval so wide it is uninformative (report it, but flag it as "no usable precision"). Very unequal `s_i` at k ≤ 5 → coverage degrades even with HK; downgrade to #1 or #2. Never print a τ² point estimate at k ≤ 5 without its (enormous) interval |
| 6 | **Log-odds / geometric-mean-of-odds pooling for probability forecasts, with correlation-aware extremization** — `logit p̄ = Σw_i logit p_i`; extremized `p* = logit⁻¹(a · Σw_i logit p_i)`, `a ≥ 1` | "five sub-agents gave me five probabilities"; "how do I combine confidence estimates from multiple models"; "average these forecasts"; "aggregate probability judgments from different experts" | `k ≥ 2` probabilities, optional weights, optional extremization factor `a`. **INLINE** | Arithmetic mean of probabilities, which is the agent's default and is demonstrably worse when any forecast is extreme. Log pooling is externally Bayesian (aggregate-then-update = update-then-aggregate) and minimises average KL to the inputs; arithmetic pooling is not and does not | **EASY**. `math.log`, `math.exp`. Needs clamping of `p ∈ {0,1}` to `[ε, 1−ε]` | Any `p_i ∈ {0,1}` with no clamp policy → refuse (log pooling gives a zero-preservation veto: one source saying 0 forces the pool to 0, which is almost never what the agent means). **Do not extremize when the sources are correlated** — `a > 1` is justified by *information diversity* across genuinely independent forecasters; k sub-agents on the same base model with the same context are near-perfectly correlated, and extremizing them manufactures confidence out of nothing. Default `a = 1` and require the caller to assert independence to raise it |
| 7 | **Arbitrary-dependence p-merging** — `p = min(1, 2·mean(p_i))` (valid under *any* dependence, and sharp); `p = min(1, k·min p_i)` (Bonferroni); `p = min(1, e·(Πp_i)^{1/k})` (geometric); Simes `min_i (k/i)p_(i)` for independent/PRDS only | "I have several p-values but I don't know if the tests are independent"; "combine significance across overlapping analyses"; "these tests used the same data, can I still combine them"; "merge p-values conservatively" | `k ≥ 2` p-values. **INLINE** | Fisher's method, which is *invalid* under dependence and is the agent's reflexive choice. The `2×mean` rule is a one-line, assumption-free, provably valid merge — exactly right for an agent that genuinely does not know its sources' dependence structure | **EASY**. Arithmetic only | Any `p_i` outside (0,1]. p-values from tests of *different* hypotheses (merging them answers a global-null question the agent probably didn't ask — force the caller to state whether the question is "is any of these real" vs "is the common effect real"). Report which rule was used and its dependence assumption on every line of output |
| 8 | **Stouffer weighted-Z** — `Z = Σw_i z_i / √Σw_i²`, `z_i = Φ⁻¹(1−p_i)`, optimal `w_i ∝ √n_i` | "combine results from several independent experiments"; "pool significance across replications"; "weighted combination of p-values by sample size"; "do these three runs together show an effect" | `k ≥ 2` one-sided p-values **with direction**, optional `n_i` or weights. **INLINE** | Counting how many were significant. Weighted-Z is directional and uses sample size, which is what the agent actually wants when three runs of different sizes all lean the same way | **EASY**. `statistics.NormalDist().inv_cdf` and `.cdf` are in stdlib | Two-sided p-values supplied without direction → **refuse**. This is the killer failure mode: two studies with opposite significant effects merge into a strongly "significant" combined result. Dependent tests → route to #7. Any `p_i = 0` (infinite z) |
| 9 | **Fisher's method** — `X = −2Σ ln p_i ~ χ²_{2k}` | "combine p-values from independent tests"; "Fisher's combined probability test"; "is the overall evidence significant across studies" | `k ≥ 2` independent p-values. **INLINE** | The agent eyeballing "two at 0.06 and one at 0.04 — probably real". Fisher is sensitive to a single very small p, which is sometimes what you want and sometimes a trap | **EASY** and notable: the χ² df is always *even* (2k), so the tail has the exact closed form `e^{−x/2}Σ_{j=0}^{k−1}(x/2)^j/j!`. No incomplete gamma needed at all | Dependence (route to #7 — under arbitrary dependence Fisher must be multiplied by a constant to stay valid). One p-value driving everything: always print the LOO Fisher result alongside. Not appropriate when the agent wants an effect *size* — a small combined p with three tiny effects is not a finding |
| 10 | **Prediction interval for the next source** — `μ̂ ± t_{k−2,1−α/2}·√(τ̂² + SE²)` (Higgins–Thompson–Spiegelhalter) | "what would a fourth benchmark probably report"; "range I should expect on a new run"; "how much will the next measurement differ"; "not the average — the spread I should plan for" | `k ≥ 4` pairs (estimate, SE); τ̂² from #5. **DATAFILE** | The confidence interval, which the agent routinely misreads as a prediction interval. This is usually the question actually being asked ("will my run land in this range?"), and 72% of statistically significant Cochrane meta-analyses have a PI containing the null | **MODERATE**. Needs the t quantile (same machinery as #5) | `k ≤ 3` → **refuse**, df = k−2 ≤ 1 is degenerate (at k=3, `t_{1,.975}=12.7` gives a meaningless interval; at k=2 it is undefined). Recommend `k ≥ 5`. The plug-in τ̂ makes coverage unreliable at small k — flag as approximate below k = 10, or use the parametric-bootstrap PI (feasible in stdlib with `random.gauss`). Do not compute a PI from a fixed-effect model |
| 11 | **Bayesian log-odds accumulation with a correlation (design-effect) discount** — `logit(post) = logit(prior) + (k_eff/k)·Σ log LR_i`, `k_eff = k/(1+ρ(k−1))` | "five articles all say the same thing but they might all be citing one source"; "how much should I update on repeated reports"; "sequential belief update from multiple documents"; "am I double-counting this evidence" | prior probability, `k` likelihood ratios (or `k` "how surprising would this be if false" judgments), and an assumed source correlation ρ. **INLINE** | Naive Bayes chaining, which is the agent's implicit model and is catastrophically overconfident with correlated sources — five 3:1 reports become 243:1 instead of ~5:1. Kish's design effect `1+ρ(m−1)` is the standard correction and maps exactly onto this | **EASY**. `math.log`, `math.exp` | ρ not supplied → refuse rather than defaulting to 0 (independence is the assumption that breaks). ρ ≥ 0.9 → report "effectively one source" and refuse a multi-source update. LRs supplied as vibes with no anchoring — require the caller to state, per source, the false-positive and true-positive rates that generate the LR |
| 12 | **Exact binomial sign test on direction (vote counting, done honestly)** — `p = 2·Σ_{j≥s} C(k,j)/2^k` | "all three sources agree so it must be right"; "how meaningful is unanimous agreement"; "does the direction of the effect replicate"; "4 out of 5 say yes, is that evidence" | `k` and the count agreeing on direction. **INLINE** | The single most common agent fallacy in this territory. Three-out-of-three agreement gives a two-sided p of **0.25**. Five-out-of-five gives 0.0625. Unanimity at k=3 is *not* evidence, and one line of `math.comb` proves it | **EASY**. `math.comb` only | Sources that are not independent (the usual case — refuse and say so). Only use when the direction is genuinely all the agent has; when magnitudes exist, vote counting throws away most of the information and #1/#5 dominate |
| 13 | **Q test + I² with its confidence interval** — `I² = max(0,(Q−(k−1))/Q)`; CI via Q-profile or the test-based (Higgins–Thompson) method | "are these sources actually measuring the same thing"; "how much do my sources disagree"; "should I use fixed or random effects"; "quantify the heterogeneity" | `k ≥ 3` pairs (estimate, SE). **INLINE** | The agent's qualitative "these seem pretty different". But its main value is the *interval*, not the point estimate | **MODERATE**. Q-profile needs χ² quantiles (invert the closed-form tails by bisection) | **Never print a bare I² at k ≤ 5.** The estimator is biased upward when k is small and true heterogeneity is low (k=7, true I²=0 → mean estimate ≈ 0.12), and the CI at k ≤ 5 typically spans nearly [0, 90%]. Print the interval or nothing. **Explicitly forbid the "I²>50% ⇒ random effects" rule** — Q has almost no power at small k, so a non-significant Q is not evidence of homogeneity |
| 14 | **Dempster–Shafer combination with explicit conflict mass** — `m₁₂(A) = Σ_{B∩C=A} m₁(B)m₂(C)/(1−K)`, `K = Σ_{B∩C=∅} m₁(B)m₂(C)`; plus Yager's rule (conflict → Θ) and Murphy's averaging rule | "sources disagree about which of several options is correct"; "combine evidence where some sources say 'I don't know'"; "conflicting categorical claims from different documents"; "reconcile mutually exclusive hypotheses" | `k` mass assignments over a frame of ≤ 4–5 hypotheses, including a mass on "unknown" (Θ). **DATAFILE** (JSON) | Probability averaging, which cannot represent ignorance separately from a 50/50 split — a real and frequent distinction for an agent ("the doc doesn't say" ≠ "the doc says it's a coin flip"). Belief/plausibility bracketing is the right output shape | **MODERATE**. Power-set enumeration with `frozenset`; combinatorial in `2^n`, so cap the frame at 5 hypotheses (32 subsets) | `K > 0.8` → **refuse Dempster's rule** and report the conflict plus Yager's result. This is Zadeh's paradox: two doctors who each think a tumour is very unlikely, combined by Dempster's rule, can yield 100% tumour. Frame > 5 hypotheses. Masses not summing to 1. Sources not independent (Dempster's rule assumes it; Murphy-style averaging is safer under doubt) |
| 15 | **Linear opinion pool + diversity decomposition** — `p̄ = Σw_i p_i`; crowd Brier error = mean individual error − diversity (`Σw_i(p_i−p̄)²`) | "average these forecasts and tell me if the disagreement is useful"; "how much is the spread across sources buying me"; "weighted average of expert opinions"; "is the crowd better than the best member" | `k` probabilities (or estimates) + optional weights; ground truth optional for the error half. **INLINE** | The bare average with no read on whether disagreement is signal or noise. The decomposition is exact and tells the agent that spread across sources *mechanically* reduces expected error — useful counterweight to "they disagree so I know nothing" | **EASY**. Arithmetic | Reporting the linear pool as if it were externally Bayesian (it is not — see #6). Weights invented ad hoc → require either equal weights or a documented weighting rule (#16/#17). The diversity term is not an error bar; do not present it as one |
| 16 | **Track-record weighting from Brier / log score** — `w_i ∝ exp(−λ·Brier_i)` or `w_i ∝ 1/MSE_i` (precision weighting on realised error) | "one of these sources has been reliable before"; "weight sources by how often they've been right"; "which model should I trust more based on past accuracy"; "downweight the source that keeps being wrong" | Per source: a history of ≥ ~10 predictions with realised outcomes. **MUST-CONSTRUCT-DATA** | Equal weighting, and the agent's memory-based "I think source B is usually good". But see the forecast combination puzzle: with few history points, estimated optimal weights are *worse* than equal weights because the weight estimates are pure noise | **EASY**. `statistics.mean`; Brier and log score are one-liners | Fewer than ~10 scored predictions per source → **refuse and return equal weights**, saying why. Non-overlapping question sets across sources (scores not comparable). Always report the equal-weight answer alongside the weighted one; if they differ materially and history is short, prefer equal weights |
| 17 | **Cooke's classical model (performance-weighted expert combination)** — calibration score = p-value of `2N·Σ s_j ln(s_j/p_j)` on χ²_{m−1}; information score = mean KL from a uniform background; `w_i ∝ C_i · I_i · 1{C_i ≥ α}` | "combine expert judgments weighted by demonstrated calibration"; "structured expert elicitation with seed questions"; "score my sources on questions where I know the answer, then weight them"; "performance-based weighting of opinions" | Per source: quantile judgments (e.g. 5/50/95) on ≥ 8–10 **calibration questions with known answers**, plus quantile judgments on the target. **MUST-CONSTRUCT-DATA** | Equal weighting, which it beats out-of-sample in 26 of 33 post-2006 studies (p ≈ 0.001 under the null). The agent *can* construct seed questions — this is the one heavyweight method whose data requirement an agent can genuinely satisfy by asking sub-agents questions it already knows the answer to | **MODERATE**. χ²_{m−1} tail (closed form for odd/even df via `erfc` + finite sums); KL is arithmetic; the "optimal α cutoff" search is a small loop | Fewer than 8 calibration variables → **refuse** (the calibration score is a p-value from a handful of hits; with 3 seeds it is noise). All experts failing the α cutoff → refuse, return equal weights. Calibration questions not drawn from the same domain as the targets. Note the documented out-of-sample penalty: performance weighting degrades relative to in-sample, so never report the in-sample fit as validation |
| 18 | **Harmonic mean p-value** — `HMP = Σw_i / Σ(w_i/p_i)`; asymptotically calibrated via the Landau distribution, or made arbitrary-dependence-valid with a `≈ e·ln k` multiplier | "combine p-values from overlapping or nested tests"; "many correlated significance tests, one headline answer"; "which subset of my tests is jointly significant"; "robust p-value combination under dependence" | `k ≥ 2` p-values, optional weights. **INLINE** | Bonferroni, which is very conservative, and Fisher, which is invalid under dependence. Uniquely, HMP is *multilevel-coherent*: you can test any subset and the headline result stays interpretable | **MODERATE**. The Landau distribution has no stdlib support; either implement the asymptotic approximation numerically or fall back to the conservative arbitrary-dependence multiplier (which is EASY) | Using the raw HMP as a p-value at anything but very small values — it is anti-conservative, and under arbitrary dependence needs an order-`log k` correction. If the Landau calibration is not implemented, refuse to print an "exact" p and print only the conservative bound. Recent work also shows HMP is only sub-uniform under restricted conditions — state the dependence assumption on every output |
| 19 | **Huber M-estimate of location (+ Winsorized mean)** — iteratively reweighted: `w_i = min(1, c·σ̂/|y_i−μ̂|)`, `c = 1.345`, σ̂ from the MAD | "one of my five sources is way off"; "robust average that ignores the outlier"; "consensus that isn't dragged by one weird result"; "trimmed or winsorized mean of these estimates" | `k ≥ 4` bare numbers. **INLINE** | The plain mean (breaks with one bad source) and the plain median (throws away too much at small k — the Huber estimator retains ~95% efficiency at the normal while bounding influence) | **EASY**. A 20-iteration fixed-point loop; MAD from `statistics.median` | `k ≤ 3` → refuse; with 3 points, Huber with any reasonable tuning is either the mean or the median and the choice is arbitrary. Bimodal sources (the "outlier" is a second cluster, not an error) — check the gap structure first and refuse if the spread is bimodal, because a robust *location* estimate of two clusters is a number that describes neither |
| 20 | **Pooling proportions on the logit scale** — `y_i = ln((x_i+0.5)/(n_i−x_i+0.5))`, `v_i = 1/(x_i+0.5)+1/(n_i−x_i+0.5)`; pool via #1 or #5, back-transform | "combine pass rates from several benchmark runs"; "pool percentages with different sample sizes"; "overall success rate across studies"; "aggregate accuracy across test suites" | `k` pairs `(successes, n)`. **INLINE** | Averaging the percentages, which ignores `n` entirely and is the agent's default. Also handles 0% and 100% cells, which naive pooling cannot | **EASY**. Reuses #1/#5 | Zero or full cells without a continuity correction. Very different `n_i` with a naive average (route to precision weighting). Do **not** use the Freeman–Tukey double-arcsine transform — its back-transformation is known to be unreliable and can produce nonsensical pooled proportions |
| 21 | **Egger regression / funnel asymmetry (refusal-first)** — regress `y_i/s_i` on `1/s_i`; test the intercept | "are the sources I found biased toward positive results"; "publication bias check"; "is there a file-drawer problem here"; "small-study effects" | `k ≥ 10` pairs (estimate, SE). **DATAFILE** | The agent's total blindness to selection effects — but only when k is large enough. Its dominant value here is as a *guard*: it tells the agent that with 4 sources, bias detection is not available | **EASY**. Weighted simple linear regression is closed-form; t-test on the intercept needs a t quantile | **`k < 10` → refuse outright.** Power is very low below 10 studies and Type I error is inflated at small k. High heterogeneity → refuse (asymmetry and heterogeneity are confounded). Binary outcomes with rare events (mathematical artefact asymmetry). Never report a non-significant Egger test as "no publication bias" |
| 22 | **Grubbs / discordancy check on a small set of estimates (refusal-first)** — `G = max|y_i−ȳ|/s`, critical value from `t_{k−2, α/2k}` | "is one of these numbers an outlier"; "should I drop the source that disagrees"; "test whether this value is anomalous"; "is that measurement a mistake" | `k ≥ 6` bare numbers. **INLINE** | The agent silently discarding the inconvenient source. Its real value is the refusal: **at k = 3 the maximum attainable Grubbs statistic is `(k−1)/√k = 1.1547` and the 5% critical value is ≈ 1.1543** — the test is degenerate and can essentially never fire | **EASY–MODERATE**. Needs a t quantile | `k ≤ 5` → **refuse and say the test has no power at this k**; route to #4 (leave-one-out) instead, which shows influence without pretending to test for it. Iterated deletion of multiple outliers (masking/swamping). Never let the tool delete a source — it reports, the caller decides |
| 23 | **Summary-statistic harmonization (feeder utility)** — median/IQR/range/n → mean and SD (Wan et al. 2014; Luo et al. 2018); CI → SE; t or p + n → SE | "the three papers report their numbers in different formats"; "convert median and range to mean and standard deviation"; "I have a confidence interval but need a standard error"; "make these results comparable so I can pool them" | Whatever each source reports + `n`. **DATAFILE** | The agent giving up on a source because it "doesn't have an SE", or worse, treating an IQR as an SD. This is what makes rows #1, #5 and #10 usable on real documents at all | **EASY**. Closed-form coefficient formulas + `NormalDist.inv_cdf` | `n` unknown. Strongly skewed underlying data (the median→mean conversions assume approximate normality and degrade badly on skew). Mixing effect metrics (odds ratio and risk difference) — refuse to pool across metrics. Always record and print the provenance of every derived SE, because a fabricated SE silently drives #1 |

---

## 2b. The k = 2–5 regime: what is honest

This is the agent's normal case and it deserves an explicit doctrine, because almost every method
above was validated at k ≥ 10.

**What breaks, and why.** The random-effects model has two unknowns (μ and τ²) and k observations.
At k = 3 there are 2 residual degrees of freedom for τ². DerSimonian–Laird's τ̂² is biased downward
and frequently pinned at exactly 0, which silently collapses random effects back into fixed effects
without telling anyone. The Hartung–Knapp fix buys correct coverage by using `t_{k−1}`, but
`t_{1,.975} = 12.706` and `t_{2,.975} = 4.303`, so at k = 2–3 the honest interval is enormous. The
prediction interval uses `t_{k−2}` and is undefined at k = 2 and degenerate at k = 3. I² is biased
upward at small k and its CI is nearly uninformative. Q has almost no power. Egger's test has almost
no power. Grubbs' test is arithmetically incapable of firing at k = 3. Trim-and-fill and p-curve
require a study distribution that does not exist at k = 5. Roughly half of Cochrane meta-analyses
have k = 2 or 3, so this is not a niche complaint.

**The four things that remain honest at k = 3:**

1. **Consistency, not heterogeneity.** Do not estimate τ². Ask the falsifiable question instead: *are
   the stated uncertainties large enough to explain the observed spread?* That is Q against
   `χ²_{k−1}`, and the Birge ratio `√(Q/(k−1))` is a defensible inflation factor at every k ≥ 2. At
   k = 2 it reduces to `|y₁−y₂|/√(s₁²+s₂²)`, which is exactly the right quantity and requires no
   asymptotics. Metrology and particle physics adopted this precisely because they routinely combine
   3–6 discrepant measurements.
2. **Integrate over τ, never estimate it.** The Bayesian normal–normal hierarchical model with a
   weakly-informative half-normal prior on τ (row #2) is the principled small-k answer. It is
   prior-dependent at k = 3 — which is the truth, not a defect — and the mandatory prior-sensitivity
   run makes that visible.
3. **Order statistics.** With 3 numbers and no error bars, `(min, max)` is an exact 75% interval for
   the source median; with 5, 93.75%. This is assumption-light, exact, and available when nothing
   else is. It is also the honest reply to "three benchmarks agree": the sign test says 3/3 agreement
   has a two-sided p of 0.25.
4. **Sensitivity, not inference.** Leave-one-out and tipping-point analysis (row #4) answer "how
   fragile is this?" without any distributional claim. At k = 3 this is frequently the only defensible
   output.

**What the tool must refuse at small k:** a bare I², a bare τ², any publication-bias verdict, any
outlier test, any prediction interval below k = 4, any extremization of correlated forecasts, and any
claim that a non-significant heterogeneity test establishes homogeneity.

**The correlation problem is worse for agents than for meta-analysts.** Medical trials are at least
run by different teams. Five sub-agents on the same base model with the same prompt and the same
retrieved context are close to one source sampled five times. Every method in this territory assumes
independence somewhere; the agent's most common violation is not heterogeneity but *pseudo-replication*.
Rows #7 (arbitrary-dependence merging) and #11 (design-effect discount) exist specifically for this,
and a good default is to demand that the caller state, per invocation, why the sources are independent.

---

## 3. Recent advances (last ~10 years)

**Small-k inference has been substantially rebuilt.**
- The Hartung–Knapp–Sidik–Jonkman t-interval moved from curiosity to default recommendation
  ([IntHout et al. 2014, BMC Med Res Methodol](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4015721/)),
  and Röver, Knapp & Friede (2015) documented its k = 2–3 pathologies and proposed the modified
  `q* = max(1,q)` rule, noting that the modification triggered in roughly 61% of their DL-based
  simulations ([BMC Med Res Methodol 15:99](https://pmc.ncbi.nlm.nih.gov/articles/PMC4647507/)).
- The τ² estimator question was settled empirically against DerSimonian–Laird in favour of
  Paule–Mandel and REML ([Veroniki et al. 2016, Res Synth Methods](https://onlinelibrary.wiley.com/doi/10.1002/jrsm.1164);
  [Langan et al. 2019](https://www.wvbauer.com/lib/exe/fetch.php/articles:langan2019.pdf)), with a
  large simulation series by Bakbergenuly, Hoaglin & Kulinskaya covering odds ratios, SMD, mean
  difference and log-response-ratio ([arXiv 1902.07154](https://arxiv.org/pdf/1902.07154),
  [1903.01362](https://arxiv.org/pdf/1903.01362), [1904.01948](https://arxiv.org/pdf/1904.01948)).
- von Hippel (2015) quantified I²'s small-k bias — with 7 studies and true I² = 0, the mean estimate
  is 0.124 — and argued for intervals over point estimates
  ([BMC Med Res Methodol 15:35](https://bmcmedresmethodol.biomedcentral.com/articles/10.1186/s12874-015-0024-z)).
- Prediction intervals became a routine recommendation
  ([IntHout, Ioannidis, Rovers & Goeman 2016, BMJ Open](https://pubmed.ncbi.nlm.nih.gov/27406637/):
  72% of significant Cochrane meta-analyses have a PI containing the null; median k ≈ 4), followed by
  bootstrap and confidence-distribution PIs that fix the plug-in coverage failure at small k
  ([Nagashima, Noma & Furukawa 2019](https://arxiv.org/pdf/1804.01054)).
- Bayesian small-k meta-analysis with weakly-informative heterogeneity priors became practical and is
  now the mainstream recommendation for k ≤ 5 (the `bayesmeta` line of work; and see the
  fixed-effect-for-few-studies counterargument, [arXiv 2002.04211](https://arxiv.org/pdf/2002.04211),
  and [likelihood-based methods with few studies](https://arxiv.org/pdf/1807.09037)).

**p-value merging got a real theory.**
- Wilson's harmonic mean p-value ([PNAS 2019](https://www.pnas.org/doi/10.1073/pnas.1814092116), with
  [correction](https://www.pnas.org/doi/10.1073/pnas.1914128116)) offered a dependence-robust,
  multilevel-coherent alternative to Fisher and Bonferroni.
- Vovk & Wang and Vovk, Wang & Wang then characterised *all* admissible merging functions under
  arbitrary dependence ([Admissible ways of merging p-values under arbitrary dependence, Ann. Statist.
  2022](https://projecteuclid.org/journals/annals-of-statistics/volume-50/issue-1/Admissible-ways-of-merging-p-values-under-arbitrary-dependence/10.1214/21-AOS2109.full);
  [arXiv 2007.14208](https://arxiv.org/abs/2007.14208)), establishing that twice the arithmetic mean of
  p-values is valid with *no* dependence assumption, that HMP needs an order-`log k` correction under
  arbitrary dependence, and that arithmetic averaging is the only admissible symmetric way to merge
  arbitrary e-values ([Biometrika 2025](https://academic.oup.com/biomet/article/112/2/asaf020/8086785)).
  Sub-uniformity of the HMP received further scrutiny in 2024
  ([arXiv 2405.01368](https://arxiv.org/pdf/2405.01368)).
- This is the single most agent-relevant theoretical development in the territory: it gives an
  assumption-free merge at a known, small, constant cost.

**Publication-bias tooling improved and p-curve was substantially discredited.**
- Robust Bayesian meta-analysis model-averages across selection models, PET-PEESE and no-bias models
  rather than picking one ([Bartoš et al. 2023, Res Synth Methods 14:99–116](https://onlinelibrary.wiley.com/doi/full/10.1002/jrsm.1594);
  Maier, Bartoš & Wagenmakers 2023, Psych Methods 28:107–122). Not stdlib-implementable, but it is the
  reason a stdlib tool should not present any single bias correction as authoritative.
- Morey & Davis-Stober (2025, JASA) show p-curve's tests are inadmissible, non-monotone in the
  evidence, and its power estimate inconsistent under heterogeneity
  ([On the Poor Statistical Properties of the P-Curve Meta-Analytic Procedure](https://www.tandfonline.com/doi/full/10.1080/01621459.2025.2544397)).
  Simulations show a 21-point upward bias in estimated power under realistic heterogeneity.

**Forecast aggregation.**
- Satopää, Baron, Foster, Mellers, Tetlock & Ungar formalised extremizing via a logit model and
  information diversity ([IJF 2014](https://www2.math.upenn.edu/~pemantle/papers/aggregation.pdf);
  [Combining and Extremizing Real-Valued Forecasts, arXiv 1506.06405](https://arxiv.org/abs/1506.06405)):
  any non-trivial weighted average is sub-optimal and must be extremized to behave as if it pooled
  information. Crucially, they also find that averaged *superforecaster* teams need little or no
  extremizing — the correction is a function of independence, not of forecaster skill.
- Empirical work on Metaculus data supports the geometric mean of odds as the default pool
  ([When pooling forecasts, use the geometric mean of odds](https://forum.effectivealtruism.org/posts/sMjcjnnpoAQCcedL2/when-pooling-forecasts-use-the-geometric-mean-of-odds)),
  while finding extremization's benefit inconsistent.
- Logarithmic pooling gained a learning-theoretic footing
  ([No-Regret Learning with Unbounded Losses: The Case of Logarithmic Pooling, arXiv 2202.11219](https://arxiv.org/pdf/2202.11219)).
- The forecast combination puzzle — equal weights beating estimated optimal weights — has been given a
  clean variance/estimation-error explanation and partial resolution
  ([Wang, Hyndman et al., Solving the Forecast Combination Puzzle, arXiv 2308.05263](https://arxiv.org/pdf/2308.05263);
  [Forecast combinations: an over 50-year review, arXiv 2205.04216](https://arxiv.org/pdf/2205.04216)).
  This is the direct justification for row #16's refusal to weight on short track records.

**Expert weighting.**
- Colson & Cooke provided the out-of-sample validation the classical model had been criticised for
  lacking: performance weighting beats equal weighting in 26 of 33 post-2006 studies (p ≈ 0.001), while
  honestly documenting the out-of-sample degradation of performance-weighted statistical accuracy
  ([Cross validation for the classical model of structured expert judgment, RESS 2017](https://rogermcooke.net/rogermcooke_files/Cross%20Validation%20SEJ%20RESS.pdf);
  [REEP 2018](https://strathprints.strath.ac.uk/62172/8/Colson_Cooke_REEP_2018_Expert_elicitation_using_the_classical_model_to_validate_experts_judgments.pdf)).

**Metrology / discrepant measurements.**
- Active work on alternatives to PDG scale factors ([Alternative to the application of PDG scale
  factors, EPJC 2020 / arXiv 2004.01219](https://arxiv.org/abs/2004.01219)) and on random-effects
  "dark uncertainty" models for fundamental constants ([Shades of Dark Uncertainty and Consensus Value
  for the Newtonian Constant of Gravitation, arXiv 1905.09551](https://arxiv.org/pdf/1905.09551)) —
  the same k = 3–10 discrepant-source problem the agent has, solved by people who cannot avoid it.
  Also a practical tool paper: [A simple tool for weighted averaging of inconsistent data sets, arXiv
  2406.08293](https://arxiv.org/pdf/2406.08293).

**Directly agent-adjacent.**
- [Meta-Analysis with Untrusted Data (arXiv 2407.09387)](https://arxiv.org/pdf/2407.09387) tackles
  synthesis when some inputs may be unreliable — the closest published analogue to an agent pooling
  web sources of unknown provenance.
- Belief-function research continues on conflict redistribution rather than Dempster normalisation
  ([improved conflicting-evidence combination via BPA redistribution, Applied Intelligence 2021](https://link.springer.com/article/10.1007/s10489-021-02404-4)).

---

## 4. Cut list

| Rejected | Why |
|---|---|
| **Trim-and-fill** | Needs k well above 10, is very sensitive to outliers, over-corrects under heterogeneity, and its authors intended it only as a sensitivity analysis. Would produce a confidently wrong "adjusted" estimate at agent scale. |
| **PET-PEESE** | Regression on SE with k = 3–10 is noise; known poor performance and unstable model-switching rule. |
| **p-curve / p-uniform*** | Inconsistent under effect-size or sample-size heterogeneity, upward-biased power estimates, and formally shown inadmissible and non-monotone (Morey & Davis-Stober 2025). Needs many significant results the agent will not have. |
| **Copas selection model** | Requires many studies plus unidentifiable sensitivity parameters; likelihood surface is nasty; not stdlib-tractable. |
| **Begg & Mazumdar rank-correlation test** | Strictly lower power than Egger, which itself already fails below k = 10. Nothing left to add. |
| **Rosenthal's fail-safe N** | Discredited; assumes unpublished studies average to exactly zero effect; produces reassuringly large numbers that mean nothing. |
| **Network / multi-treatment meta-analysis** | Requires matrix inversion and a consistency framework; well outside "handful of numbers on the CLI" and outside stdlib without numpy. |
| **Multivariate / multi-outcome meta-analysis** | Needs within-study correlation matrices the agent will never have, plus matrix algebra. |
| **Meta-regression with covariates** | Cochrane's own guidance is ≥ 10 studies per covariate; at k = 3–5 there are no residual degrees of freedom. Kept only as a refusal message. |
| **RoBMA / Bayesian model-averaged bias adjustment** | The right method scientifically, but requires MCMC and bridge sampling. Cited as the reason not to trust any single stdlib bias correction, not implemented. |
| **Full MCMC hierarchical models** | Sampler + convergence diagnostics in stdlib is a project, not a tool; the 1-D grid in row #2 gets the same answer for the normal–normal model exactly. |
| **Freeman–Tukey double-arcsine transform for proportions** | Back-transformation is unreliable and can yield out-of-range or nonsensical pooled proportions; logit pooling is strictly safer. |
| **Sidik–Jonkman / Hunter–Schmidt / empirical-Bayes τ² estimators** | Redundant. Offer DL (fast, transparent, known-biased) and PM (recommended) and stop; a menu of seven estimators invites the agent to shop for the answer it wants. |
| **"I² > 50% ⇒ use random effects" decision rule** | Actively harmful and widespread. Q has no power at small k, so this rule mostly selects fixed effects when heterogeneity is unmeasurable. Encoded as a *forbidden* pattern, not a tool. |
| **Vote counting as a primary synthesis method** | Throws away magnitude and precision; has the perverse property that power *decreases* as more small studies are added. Retained only as the exact sign test in row #12, which is a debunking tool. |
| **Bayesian truth serum / surprisingly popular** | Intriguing for sub-agent polling (ask each agent both its answer and its prediction of others' answers), but unvalidated at k = 3–5 and requires a second-order elicitation the agent must be trusted to run honestly. Revisit if sub-agent polling becomes a first-class pattern. |
| **Transferable Belief Model / pignistic transform** | Folded into the Dempster–Shafer row as an output option rather than a separate model. |
| **Prediction-market / LMSR aggregation** | Requires a market and a sequence of trades; no agent-scale analogue. |
| **Cohen's κ / Bland–Altman agreement** | Measures inter-rater or inter-method agreement, not synthesis of a common quantity. Belongs to a measurement-agreement territory. |
| **Dempster–Shafer over frames larger than 5 hypotheses** | 2^n mass assignments; the combination becomes both computationally and cognitively unmanageable, and elicitation of masses over 32+ subsets is fantasy. |

---

## 5. Cross-territory overlaps

- **Distributions & numerics layer.** Rows #5, #10, #13, #17, #21, #22 all need Student-t and/or χ²
  quantiles. Worth noting that Fisher's method (#9) needs only *even*-df χ² tails, which have an exact
  elementary closed form, and Cooke's calibration score needs odd-df χ² tails, expressible with
  `erfc` plus a finite sum. The full regularized incomplete beta (ASA063 / Cephes `incbet`) is only
  strictly required for the t quantile. Shared dependency — build once.
- **Bayesian inference territory.** Row #2 (normal–normal hierarchical) and row #11 (log-odds
  accumulation) are Bayesian models living here for situational reasons. Prior elicitation, prior
  sensitivity, and Bayes factors for heterogeneity are shared machinery. Decide which territory owns
  the prior-sensitivity harness.
- **Calibration & scoring territory.** Brier score, log score and reliability decomposition power row
  #16 and the calibration half of row #17. The diversity decomposition in row #15 is the
  Brier decomposition. Strong overlap — the scoring primitives should be shared, not duplicated.
- **Forecasting / prediction territory.** Extremization (#6), the forecast combination puzzle (#16)
  and prediction intervals (#10) sit on the boundary. Rule of thumb: this territory owns *combining
  multiple existing forecasts*; that one owns *producing* a forecast.
- **Multiple comparisons / FDR territory.** Bonferroni, Simes and Benjamini–Hochberg share exact
  machinery with row #7, and the dependence assumptions are the same. The distinction is the question:
  merging asks "is the global null false?", FDR asks "which ones are real?" Both should be reachable
  from the same p-value input file.
- **Robust statistics / outlier detection territory.** Rows #3, #19 and #22 (median, MAD,
  Hodges–Lehmann, Huber, Grubbs) are shared. This territory needs them for *consensus*; that one needs
  them for *contamination*.
- **Sample size & power territory.** "How many sources do I need before I can say anything?" is the
  design question behind every refusal here — the power of Q, of Egger, and of the sign test at given
  k are the answers, and they should be queryable directly ("how many independent sources before
  unanimity is evidence?" → 5, for p < 0.05 two-sided at 5/5).
- **Decision theory territory.** Row #4's tipping-point analysis is only meaningful relative to a
  decision threshold; the natural handoff is "here is the pooled interval, here is what it implies for
  the decision, here is how much one source would have to move to change it."
- **No meaningful overlap** with causal inference, time series, or experimental design beyond the
  shared numerics layer.

---

## 6. Sources

**Small-k meta-analysis and heterogeneity**
- Röver C, Knapp G, Friede T. *Hartung-Knapp-Sidik-Jonkman approach and its modification for
  random-effects meta-analysis with few studies.* BMC Med Res Methodol 15:99 (2015).
  https://pmc.ncbi.nlm.nih.gov/articles/PMC4647507/
- IntHout J, Ioannidis JPA, Borm GF. *The Hartung-Knapp-Sidik-Jonkman method... considerably
  outperforms the standard DerSimonian-Laird method.* BMC Med Res Methodol (2014).
  https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4015721/
- Veroniki AA et al. *Methods to estimate the between-study variance and its uncertainty in
  meta-analysis.* Res Synth Methods 7:55–79 (2016). https://onlinelibrary.wiley.com/doi/10.1002/jrsm.1164
- Langan D et al. *A comparison of heterogeneity variance estimators in simulated random-effects
  meta-analyses.* Res Synth Methods (2019). https://www.wvbauer.com/lib/exe/fetch.php/articles:langan2019.pdf
- von Hippel PT. *The heterogeneity statistic I² can be biased in small meta-analyses.* BMC Med Res
  Methodol 15:35 (2015). https://bmcmedresmethodol.biomedcentral.com/articles/10.1186/s12874-015-0024-z
- Bakbergenuly I, Hoaglin DC, Kulinskaya E. Simulation studies of between-study variance estimation:
  odds ratios https://arxiv.org/pdf/1902.07154 · SMD https://arxiv.org/pdf/1903.01362 · mean difference
  https://arxiv.org/pdf/1904.01948 · log response ratio https://arxiv.org/pdf/1905.01243
- *Fixed-effects model: the most convincing model for meta-analysis with few studies.*
  https://arxiv.org/pdf/2002.04211
- *Likelihood-based meta-analysis with few studies: empirical and simulation studies.*
  https://arxiv.org/pdf/1807.09037
- Cochrane Handbook, Chapter 10 (Analysing data and undertaking meta-analyses).
  https://training.cochrane.org/handbook/current/chapter-10
- *A new justification of the Hartung-Knapp method based on weighted least squares regression.*
  https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6973024/
- *Novel approaches for random-effects meta-analysis of a small number of studies under normality.*
  https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12657671/

**Prediction intervals**
- IntHout J, Ioannidis JPA, Rovers MM, Goeman JJ. *Plea for routinely presenting prediction intervals
  in meta-analysis.* BMJ Open 6:e010247 (2016). https://pubmed.ncbi.nlm.nih.gov/27406637/
- Nagashima K, Noma H, Furukawa TA. *Prediction intervals for random-effects meta-analysis: a
  confidence distribution approach.* https://arxiv.org/pdf/1804.01054
- *Assessing the properties of the prediction interval in random-effects meta-analysis.* Res Synth
  Methods. https://www.cambridge.org/core/journals/research-synthesis-methods/article/assessing-the-properties-of-the-prediction-interval-in-randomeffects-metaanalysis/2AB38E25F6E8A97FBD6CD13971AAC70E

**Combining p-values / e-values**
- Wilson DJ. *The harmonic mean p-value for combining dependent tests.* PNAS 116:1195–1200 (2019).
  https://www.pnas.org/doi/10.1073/pnas.1814092116 · correction
  https://www.pnas.org/doi/10.1073/pnas.1914128116
- `harmonicmeanp` vignette (definition, weighted HMP, α_L thresholds).
  https://cran.r-project.org/web/packages/harmonicmeanp/vignettes/harmonicmeanp.html
- Vovk V, Wang B, Wang R. *Admissible ways of merging p-values under arbitrary dependence.* Ann.
  Statist. 50(1) (2022). https://projecteuclid.org/journals/annals-of-statistics/volume-50/issue-1/Admissible-ways-of-merging-p-values-under-arbitrary-dependence/10.1214/21-AOS2109.full
  · preprint https://arxiv.org/abs/2007.14208 · PDF https://sas.uwaterloo.ca/~wang/papers/2021Vovk-Wang-Wang-AOS.pdf
- *The only admissible way of merging arbitrary e-values.* Biometrika 112(2), asaf020 (2025).
  https://academic.oup.com/biomet/article/112/2/asaf020/8086785
- Vovk V, Wang R. *Confidence and discoveries with e-values.* Statistical Science.
  https://sas.uwaterloo.ca/~wang/papers/2022Vovk-Wang-STS.pdf
- *Sub-uniformity of harmonic mean p-values.* https://arxiv.org/pdf/2405.01368
- *The Lévy combination test.* https://arxiv.org/pdf/2105.01501

**Publication and selection bias**
- Bartoš F, Maier M, Wagenmakers E-J, Doucouliagos H, Stanley TD. *Robust Bayesian meta-analysis:
  model-averaging across complementary publication bias adjustment methods.* Res Synth Methods
  14:99–116 (2023). https://onlinelibrary.wiley.com/doi/full/10.1002/jrsm.1594 · package
  https://fbartos.github.io/RoBMA/
- Morey RD, Davis-Stober CP. *On the Poor Statistical Properties of the P-Curve Meta-Analytic
  Procedure.* JASA (2025). https://www.tandfonline.com/doi/full/10.1080/01621459.2025.2544397 ·
  commentary https://statmodeling.stat.columbia.edu/2025/09/25/on-the-poor-statistical-properties-of-the-p-curve-meta-analytic-procedure/
- Simonsohn U, Nelson LD, Simmons JP. *P-curve: a key to the file-drawer.* JEP:General (2014).
  https://pages.ucsd.edu/~cmckenzie/Simonsohnetal2014JEPGeneral.pdf
- *Performance of the trim and fill method in the presence of publication bias and between-study
  heterogeneity.* https://www.researchgate.net/publication/6352841
- Stata `meta trimfill` manual entry (assumptions and limitations).
  https://www.stata.com/manuals/metametatrimfill.pdf
- Doing Meta-Analysis in R — §10.1 Detecting publication bias (the k ≥ 10 rule).
  https://cjvanlissa.github.io/Doing-Meta-Analysis-in-R/smallstudyeffects.html

**Opinion pooling, forecasting, expert weighting**
- Dietrich F, List C. *Probabilistic Opinion Pooling* (external Bayesianity vs marginalization).
  https://personal.lse.ac.uk/list/PDF-files/OpinionPoolingReview.pdf
- Satopää VA, Baron J, Foster DP, Mellers BA, Tetlock PE, Ungar LH. *Combining multiple probability
  predictions using a simple logit model.* IJF (2014). https://www2.math.upenn.edu/~pemantle/papers/aggregation.pdf
- Satopää VA, Ungar LH. *Combining and Extremizing Real-Valued Forecasts.*
  https://arxiv.org/abs/1506.06405
- Neyman E, Roughgarden T. *No-Regret Learning with Unbounded Losses: The Case of Logarithmic Pooling.*
  https://arxiv.org/pdf/2202.11219
- *When pooling forecasts, use the geometric mean of odds.* EA Forum.
  https://forum.effectivealtruism.org/posts/sMjcjnnpoAQCcedL2/when-pooling-forecasts-use-the-geometric-mean-of-odds
- AI Impacts. *Evidence on good forecasting practices from the Good Judgment Project.*
  https://aiimpacts.org/evidence-on-good-forecasting-practices-from-the-good-judgment-project/
- Colson AR, Cooke RM. *Cross validation for the classical model of structured expert judgment.* RESS
  (2017). https://rogermcooke.net/rogermcooke_files/Cross%20Validation%20SEJ%20RESS.pdf
- Colson AR, Cooke RM. *Expert Elicitation: Using the Classical Model to Validate Experts' Judgments.*
  REEP 12(1) (2018). https://strathprints.strath.ac.uk/62172/8/Colson_Cooke_REEP_2018_Expert_elicitation_using_the_classical_model_to_validate_experts_judgments.pdf
- Cooke RM. *Technical Details of the Classical Model.*
  https://rogermcooke.net/rogermcooke_files/SEJ%20-%20SI%20June%2022%202022.pdf
- Wang X, Hyndman RJ, Li F, Kang Y. *Forecast combinations: an over 50-year review.*
  https://arxiv.org/pdf/2205.04216
- *Solving the Forecast Combination Puzzle.* https://arxiv.org/pdf/2308.05263 · and
  https://economics.ucr.edu/repec/ucr/wpaper/202514.pdf
- Claeskens G et al. *The forecast combination puzzle: a simple theoretical explanation.* IJF (2016).
  https://www.sciencedirect.com/science/article/abs/pii/S0169207016000327

**Belief functions / conflicting evidence**
- Sentz K, Ferson S. *Combination of Evidence in Dempster-Shafer Theory.* Sandia SAND2002-0835.
  https://www.osti.gov/servlets/purl/800792/ · https://www.stat.berkeley.edu/~aldous/Real_World/dempster_shafer.pdf
- *Shedding new light on Zadeh's criticism of Dempster's rule of combination.*
  https://www.researchgate.net/publication/4221152
- *An improved conflicting-evidence combination method based on the redistribution of the basic
  probability assignment.* Applied Intelligence (2021). https://link.springer.com/article/10.1007/s10489-021-02404-4
- *A new combination approach based on improved evidence distance* (Murphy/Deng-style averaging).
  https://arxiv.org/pdf/1404.4789

**Metrology / discrepant measurements (the k = 3–10 problem, solved in practice)**
- Particle Data Group, *Review of Particle Physics*, Introduction §5 (scale factor S rules).
  https://pdg.lbl.gov/2019/reviews/rpp2019-rev-rpp-intro.pdf
- *Alternative to the application of PDG scale factors.* EPJC 80 (2020) / arXiv 2004.01219.
  https://arxiv.org/abs/2004.01219
- Bodnar O, Possolo A et al. *Shades of Dark Uncertainty and Consensus Value for the Newtonian Constant
  of Gravitation.* https://arxiv.org/pdf/1905.09551
- *A simple tool for weighted averaging of inconsistent data sets.* https://arxiv.org/pdf/2406.08293

**Agent-adjacent**
- Kaul S, Gordon GJ. *Meta-Analysis with Untrusted Data.* https://arxiv.org/pdf/2407.09387

**Summary-statistic conversion**
- Wan X, Wang W, Liu J, Tong T. *Estimating the sample mean and standard deviation from the sample
  size, median, range and/or interquartile range.* BMC Med Res Methodol 14:135 (2014).
- Luo D, Wan X, Liu J, Tong T. *Optimally estimating the sample mean from the sample size, median,
  mid-range, and/or mid-quartile range.* Stat Methods Med Res 27:1785–1805 (2018).
