# Territory 05 — Extreme Value Theory and Tail Risk

Research pass for the Intelligence Module. Scope: block maxima / GEV, peaks-over-threshold / GPD,
threshold selection, return levels, tail index estimation, VaR / Expected Shortfall, heavy-tail
diagnostics, power laws (CSN), extreme quantiles from small samples, zero-event bounds, moment-based
worst-case bounds, and tail-latency estimation.

---

## 1. Territory summary

This territory answers the agent's four recurring catastrophe questions — *how bad can this plausibly
get*, *what is the p99 really*, *how often will this rare thing happen*, and *is one bad outcome
enough to change the decision* — and its single most valuable contribution is knowing when the honest
answer is "you cannot know that from this data." Extreme value theory is the only branch of
statistics with a limit theorem for the tail (Fisher–Tippett–Gnedenko for maxima, Pickands–Balkema–de
Haan for exceedances), which is why it beats an agent's unaided guess: the agent's default mental
model is Gaussian, and the Gaussian is wrong about tails by orders of magnitude in almost every
domain an agent operates in (latency, cost, incident severity, retry storms, file sizes, blast
radius). But EVT is also the branch with the worst small-sample behaviour in all of statistics — the
shape parameter ξ, which determines whether the tail is bounded, exponential, or infinite-mean, needs
hundreds of exceedances to pin down, and the entire answer is exquisitely sensitive to a threshold
choice that has no agreed-upon selection rule after fifty years of literature. Consequently the
ranking below deliberately puts *cheap exact distribution-free tools* (rule of three, order-statistic
quantile intervals, Wilks tolerance intervals, horizon-risk arithmetic, moment inequalities) above
*model-based extrapolation* (GPD, GEV, Hill), because at agent scale (n from 3 to a few thousand) the
cheap tools are usually the only ones that are actually valid, and they answer the decision question
directly. The unifying discovery of this pass: the rule of three, Wilks' distribution-free tolerance
interval, and "can I put an upper confidence bound on p99 at all" are all the same inequality,
`n ≥ ln(α)/ln(p)` — which means a single ~40-line module answers a surprisingly large fraction of the
tail questions an agent actually asks, exactly, with no distributional assumption whatsoever.

---

## 2. Ranked model table

Tier legend: **INLINE** = a handful of numbers as CLI flags · **DATAFILE** = a small dataset in a file
· **MUST-CONSTRUCT** = the agent has to generate/collect the data first.

Ranking criterion: (decision value to a domain-agnostic agent) × (validity at n ≤ a few thousand) ×
(stdlib feasibility), with a heavy penalty for methods that produce a confident number that is wrong.

| # | Model / method | SITUATION (agent phrasings) | Minimum viable inputs + tier | Beats what | Stdlib feasibility + numerics | REFUSE conditions |
|---|---|---|---|---|---|---|
| 1 | **Zero/few-event upper bound: rule of three, exact Clopper–Pearson upper limit, Bayesian predictive** | "we've run it 200 times with no failures — how safe is it?" · "zero incidents so far, what's the real failure rate?" · "how confident can I be that this never happens?" · "0 out of N, what's my upper bound?" | `n` trials, `k` events (usually 0), confidence level. **INLINE** | Agent's instinct to say "0% observed, so it's safe", or to quote 0/n as the rate. Gives the exact one-sided bound `p ≤ 1 − α^(1/n)` (≈ 3/n at 95%) and the predictive `P(≥1 in next m) = m/(n+m+1)` under a uniform prior | **EASY.** Exact binomial tail sums via `lgamma`; upper limit by bisection on the binomial CDF (equivalently Beta quantile). Bayesian variants need `lgamma` only | n < 1; k > n; user asks for a *point* rate when k = 0 (report the bound, never "0"); trials are not exchangeable (different configs/versions/loads pooled together); the "trials" were not independent opportunities for the event (e.g. 200 requests in one 5-minute window is not 200 independent chances at a daily-cycle failure) |
| 2 | **Nonparametric quantile confidence interval from order statistics (binomial / Thompson method)** | "what's the p99 latency, really?" · "how much do I actually know about the 95th percentile from these 300 samples?" · "is my measured p99 trustworthy?" · "give me error bars on this percentile" | Sample of values (n ≥ 5), target quantile p, confidence. **DATAFILE** | Reporting a raw empirical percentile with no uncertainty — the standard agent failure. Exact, distribution-free, no tail model needed | **EASY.** Sort + exact binomial CDF. Rank bounds: smallest `l` with `P(Bin(n,p) < l) ≥ α/2`, largest `u` with `P(Bin(n,p) ≥ u) ≥ α/2` | The required upper rank exceeds n — i.e. `n < ln(α)/ln(p)` — then there is **no** upper confidence bound and the tool must say so rather than reporting the max; ties/rounding dominate the tail; data are autocorrelated (see #17); values are censored by a timeout/cap |
| 3 | **Distribution-free tolerance interval / sample-size planner (Wilks)** | "how many runs do I need to trust the p99?" · "is 50 samples enough to characterise the tail?" · "how long do I have to soak-test this?" · "how many trials before I can claim a 1-in-1000 failure rate?" | Target quantile p, confidence γ. **INLINE** | Pure guessing at sample size. Exact: `n ≥ ln(1−γ)/ln(p)` — 299 for 95/99 one-sided, 2 995 for 95/99.9, 29 956 for 95/99.99 | **EASY.** Two logs. Two-sided version needs a small root-find on the incomplete beta | Nothing — this one is always safe to print. It should, however, refuse to *approve* an existing sample as adequate when n is below the bound |
| 4 | **Catastrophe break-even / evidence-sufficiency check** | "is one catastrophic outcome enough to change the decision?" · "how bad would this have to be for me to not do it?" · "we've never seen it fail — is that enough evidence to ship?" · "what failure rate would make this not worth it?" | Benefit of acting, loss if the catastrophe occurs, plus n trials and k events observed. **INLINE** | Verbal risk reasoning. Computes the break-even probability `p* = Δbenefit / L_catastrophe`, then compares it against the *upper* confidence bound on p from #1. Verdict is one of three: evidence sufficient, evidence insufficient, or evidence cannot ever be sufficient at this n | **EASY.** Reuses #1 | The loss is unbounded or non-monetisable (then p* = 0 and no amount of clean history suffices — say that); the catastrophe is a mechanism never observed in *any* form (EVT extrapolates the observed mechanism's tail, not new mechanisms); benefit and loss are on incommensurable scales |
| 5 | **Return period ↔ horizon risk conversion** | "it's a 1-in-100 event, should I care?" · "what's the chance this happens at least once this year?" · "how often will this rare thing actually bite us?" · "convert this return period to a probability over my planning horizon" | Return period T (or per-period probability), horizon m. **INLINE** | The near-universal error of reading "1-in-100-year" as "won't happen". `P(≥1 in m) = 1 − (1 − 1/T)^m`: a 1-in-100 event has a **26% chance** in 30 periods, 63% in 100 | **EASY.** One power | The per-period events are clustered rather than independent (see #17 — with extremal index θ, the effective count is θm); the period definition is ambiguous; T was itself estimated by extrapolating far beyond the data (then propagate #11's range instead of a single T) |
| 6 | **Heavy-tail diagnostic battery (gate for everything else)** | "is this a heavy-tail problem at all?" · "are these outliers or is this just what the distribution looks like?" · "can I use mean and standard deviation here?" · "does the average even mean anything for this data?" | Sample of values, n ≥ 30. **DATAFILE** | The agent's default assumption that mean ± 2sd covers the risk. Battery: max-to-sum ratios `R_n^(p) = max xᵢᵖ / Σxᵢᵖ` for p = 1..4 (non-convergence ⇒ that moment doesn't exist); mean-excess-function slope (`ξ ≈ s/(1+s)`); top-1 and top-1% share of total; log-log survival linearity; CV growth with n | **EASY.** Sorting, sums, a least-squares line. No special functions | n < 30 (the ratios are meaningless); data contain zeros/negatives when a positive-support diagnostic is applied without shifting; the sample is a mixture of obviously distinct regimes (report the mixture, not a tail index) |
| 7 | **Empirical VaR + Expected Shortfall with bootstrap CI, plus the subadditivity lesson** | "what's my worst-case loss at 95%?" · "if things go badly, how badly?" · "what's the average of the bad outcomes?" · "is VaR or ES the right number here?" | Loss sample, n ≥ 50, level q. **DATAFILE** | Quoting a single VaR number. ES (= mean of the worst 1−q fraction) is coherent/subadditive; VaR is not, and can say a diversified portfolio is riskier than a concentrated one. ES also *sees* the tail beyond the quantile, which VaR structurally cannot | **EASY.** Sort, average the tail, percentile bootstrap (needs `random`) | n(1−q) < 5, i.e. fewer than ~5 observations beyond the VaR level — the ES is then an average of 1–4 numbers and must not be printed; losses are censored/capped; the sample is autocorrelated (block-bootstrap or refuse) |
| 8 | **Moment-only worst-case bounds: Markov, Chebyshev, Cantelli, one-sided Vysochanskij–Petunin** | "I only know the mean and standard deviation — how bad can it get?" · "what's a hard upper bound on the probability of exceeding X?" · "worst case with no distributional assumption" · "bound the tail without data" | mean, sd, threshold (Markov: mean + threshold, nonneg support only). **INLINE** | Assuming normality. Cantelli: `P(X ≥ μ+kσ) ≤ 1/(1+k²)`. If unimodality is defensible, the one-sided Vysochanskij–Petunin bound (Mercadier & Strub 2021) is far tighter — the two-sided version replaces Chebyshev's 1/k² with 4/(9k²) for k ≥ √(8/3) | **EASY.** Arithmetic | sd was estimated from a small sample and the data look heavy-tailed (the sample sd is then a wild underestimate — #6 must pass first); the distribution may have infinite variance (`R_n^(2)` not converging) → Chebyshev/Cantelli are vacuous, only Markov survives; unimodality asserted without evidence for the VP bounds |
| 9 | **Tail-at-scale amplification (fan-out / max-of-k / repeated-exposure)** | "each service has a 10 ms p99 — what's the request p99 if I call 50 of them?" · "if I run this 10 000 times, what's the worst I'll see?" · "how does rare become common at scale?" · "one retry is fine, is 100?" | Per-unit exceedance probability (or per-unit quantile) and the multiplicity k. **INLINE** | The agent's intuition that a p99 component gives a p99 experience. `P(max > L) = 1 − (1−q)^k`: with k = 100 and q = 0.01, 63% of requests are slow. To hold a fan-out p99 you need per-component p99.99 (`p^(1/k)`) | **EASY.** Powers and logs | Components are correlated (shared queue, shared host, shared dependency) — then the formula is optimistic and the tool must say the independence assumption drives the whole answer; k is not actually the parallel fan-out |
| 10 | **POT / Generalized Pareto fit via L-moments (PWM), with Grimshaw MLE as fallback** | "model the tail of these numbers so I can extrapolate" · "fit a tail distribution to my exceedances" · "estimate the shape of the tail" · "how fat is this tail" | Sample n ≥ 150 with ≥ 30 exceedances above a threshold. **DATAFILE** | Any moment-matching or normal-tail approximation, and (at agent sample sizes) plain MLE. Closed form: `ξ̂ = 2 − ℓ₁/ℓ₂`, `σ̂ = ℓ₁(1−ξ̂)`, where ℓ₁, ℓ₂ are the first two sample L-moments of the excesses | **EASY** for L-moments (sort + two weighted sums, no optimizer). **MODERATE** for MLE — Grimshaw's (1993) reparameterisation reduces the 2-D likelihood to a 1-D root-find on (−∞, 1/x_max), solvable with Brent | fewer than 30 exceedances (report order statistics only); L-moment estimate implies ξ̂ ≥ 0.5 (PWM estimators lose consistency/finite variance there — switch to MLE and widen everything); fewer than ~10 distinct values among the exceedances; the sample max is a hard cap (timeout, buffer limit, quota) |
| 11 | **Threshold sensitivity scan (MRL plot + parameter stability + *quantile* stability)** | "how much does my tail estimate depend on where I drew the line?" · "is this return level robust?" · "which threshold should I use?" · "my answer changed when I changed the cutoff" | Sample n ≥ 150, target quantile. **DATAFILE** | Picking one threshold and reporting one number — the single largest source of silent error in this territory. The correct output is a *range over admissible thresholds*, not a chosen threshold. Useful finding from the 2026 review: shape estimates wander wildly while high-quantile estimates are often stable — scan the quantity you care about, not ξ | **MODERATE.** Repeated GPD fits over a grid of thresholds (u at the 70th–98th percentiles), keeping ≥ 30 exceedances | The target quantile varies by more than ~2× across the admissible threshold range → refuse a point estimate and return the interval; no threshold leaves ≥ 30 exceedances; MRL plot has no approximately linear region anywhere |
| 12 | **GPD tail quantile (VaR) and Expected Shortfall in closed form** | "estimate the p99.9 when I only have 500 samples" · "extrapolate past my worst observation" · "what's the expected loss given we're in the bad tail?" · "1-in-10 000 severity" | Fitted (u, σ, ξ), n, n_exceedances, target level. **DATAFILE** | Empirical percentiles, which cannot go beyond the observed max at all. `x̂_p = u + (σ/ξ)[((n/N_u)(1−p))^(−ξ) − 1]`; `ES_p = x̂_p/(1−ξ) + (σ − ξu)/(1−ξ)` | **EASY** given #10 | **ξ̂ ≥ 1 ⇒ the mean does not exist — refuse to print ES at all** and say so (this is a real finding, not an error); extrapolation factor `1/((1−p)·n) > 10` (i.e. asking for a level more than ~10× beyond the record length) — practitioners stop at 2–4×; ξ̂ CI spans 0 widely and the answer flips by an order of magnitude in sign of ξ |
| 13 | **Weissman semi-parametric extreme quantile** | "estimate a quantile way out past my data" · "1-in-a-million from 1 000 samples" · "extrapolate the tail without fitting a full model" | Sorted positive sample, k top order statistics, target p. **DATAFILE** | Empirical quantile beyond the max (undefined) and log-normal extrapolation (systematically optimistic for heavy tails). `x̂_p = X_(n−k) · (k/(n(1−p)))^{γ̂_Hill}` | **EASY** given Hill (#14) | Data not positive/heavy-tailed (Weissman assumes γ > 0 — refuse for bounded or exponential tails); k < 20 or k > n/5; same extrapolation-factor guard as #12; γ̂ unstable across k (see #14) |
| 14 | **Hill estimator + Hill-plot stability report** | "what's the tail index?" · "how heavy is this tail — does the variance even exist?" · "is this a power law tail?" · "alpha of the tail" | Positive sample n ≥ 100, sorted. **DATAFILE** | Fitting a normal or log-normal and reading off a tail. `γ̂_k = (1/k)Σ_{i=1..k} ln X_(n−i+1) − ln X_(n−k)`; `SE ≈ γ̂/√k` (k = 50 ⇒ ±14% relative; k = 20 ⇒ ±22%) | **EASY.** Logs and a running mean over k — compute the whole Hill plot in O(n) | **Must return a range across k, never a single number.** Refuse if the Hill plot has no region where γ̂ is flat within ±20% over a factor-of-2 range of k ("Hill horror plot"); refuse for non-positive data; refuse if the implied α < 1 without flagging that the mean is infinite; γ̂ is meaningless if the tail isn't regularly varying (check #6 first) |
| 15 | **Poisson rare-event rate: exact CI and horizon probability** | "we saw 2 incidents in 18 months — what's the real rate?" · "what's the chance of an outage next quarter?" · "how often does this happen?" · "rate from a small count over a known exposure" | count k, exposure T, horizon H. **INLINE** | Dividing k by T and treating it as known. Exact Garwood interval from the chi-square/gamma relation; zero-count case gives rate ≤ −ln(α)/T = 3/T | **EASY.** Exact Poisson tail sums, or inverse-gamma by bisection on the regularized incomplete gamma | Exposure is ill-defined or the events are clustered (one incident with 5 alerts is not 5 events); rate is clearly non-stationary over T (a deploy changed the system mid-window); overdispersion evident (then this is a negative-binomial problem — cross-territory) |
| 16 | **Gumbel-tail "worst-of-n" extrapolation (Jones et al. 2025 style)** | "we tested 500 prompts, what's the worst behaviour across 5 million?" · "extrapolate the worst case from a small eval to production scale" · "how bad will the worst one be if I run this a million times?" | The top ~10–50 values from an eval sample, plus the target scale n. **DATAFILE / MUST-CONSTRUCT** | Assuming the eval worst case is the production worst case. Transform to `ψ = −log(−log p)`, fit `log S(ψ) = aψ + b` on the top values, extrapolate. Reported ~72% of forecasts within one order of magnitude over 2–3 decades of extrapolation | **MODERATE.** Sort, transform, least squares; bootstrap for spread | Extrapolation beyond ~3 orders of magnitude; fewer than 10 top values; any distribution shift between the sample and the target population (the method assumes none, and this is its stated dominant failure); the score is bounded/saturating (do the fit in logit space or refuse) |
| 17 | **Extremal index and declustering (runs estimator, Ferro–Segers intervals estimator)** | "my latency spikes come in bursts — does that break my percentile math?" · "these exceedances aren't independent" · "how many *independent* bad events did I actually see?" · "adjust for clustering" | Time-ordered sample with a threshold. **DATAFILE** | Treating N_u exceedances as N_u independent observations, which inflates confidence by roughly 1/θ. θ ∈ (0,1] is the reciprocal of mean cluster size; effective sample size is θ·N_u; return periods scale by 1/θ | **MODERATE.** Runs estimator is trivial; the Ferro–Segers intervals estimator is a closed-form ratio of inter-exceedance time moments | θ̂ < 0.5 and the caller then asks for iid-based intervals — refuse and force declustering; fewer than 10 clusters; data have no meaningful time order (then the question is malformed) |
| 18 | **Block maxima / GEV fit + return levels with profile-likelihood CI** | "what's the worst day/week/month I should plan for?" · "annual maximum, 10-year worst case" · "design for the peak" · "return level for a 50-period event" | ≥ 25 block maxima. **DATAFILE / MUST-CONSTRUCT** (agent usually must define blocks and reduce raw data) | Taking the observed maximum as the planning value, and symmetric normal CIs on return levels (which are badly wrong — the true interval is strongly right-skewed) | **HARD.** 3-parameter Nelder–Mead on the GEV log-likelihood with support constraints, plus a 1-D root-find on the profile deviance for each CI endpoint. L-moment GEV estimates make excellent starting values and are worth reporting alongside | fewer than 25 blocks; blocks of unequal size or with missing data; return period requested > 4× the number of blocks; ξ̂ hits the optimizer boundary; the maximum occurs in the last 10% of the record (non-stationarity — see #19); **never** report a symmetric CI |
| 19 | **Records-based stationarity-in-extremes check** | "is the tail getting worse over time?" · "are these extremes drifting?" · "is my worst case trending up?" · "can I treat the history as one population?" | Time-ordered sample, n ≥ 20. **DATAFILE** | Fitting a stationary tail model to drifting data — the most consequential silent violation in this territory. In an iid sequence the expected number of running records is `H_n ≈ ln n + 0.5772`, with variance `≈ ln n − 1.645`; count the actual records and compare | **EASY.** One pass + a normal approximation | n < 20; heavy ties; the tool should *not* claim stationarity when it fails to reject — it should report the record count and the expected count and let the caller see the margin |
| 20 | **DKW / Massart simultaneous CDF confidence band** | "what can I guarantee about this distribution with no assumptions at all?" · "distribution-free bound on the whole CDF" · "worst case over all quantiles simultaneously" | Sample, confidence. **DATAFILE** | Nothing else gives a *simultaneous* distribution-free guarantee. Band half-width `√(ln(2/α)/(2n))` | **EASY.** One sqrt | Be blunt: at n = 100 the band is ±0.136, so it cannot distinguish p99 from the maximum, and at n = 1 000 it is still ±0.043. **Refuse to use it for anything above about the p90** — the exact order-statistic interval (#2) is pointwise-tighter and should be preferred for tail questions |
| 21 | **m-out-of-n bootstrap / subsampling for tail uncertainty** | "put error bars on my tail estimate" · "bootstrap the p99" · "how uncertain is this extreme quantile?" | Sample, statistic, n ≥ 200. **DATAFILE** | Naive n-out-of-n bootstrap, which is **inconsistent for the sample maximum and for extreme quantiles** (the resampled max is the observed max with probability 1 − (1−1/n)ⁿ ≈ 0.632) | **MODERATE.** `random.choices` + a subsample-size rule (m ≈ n^(2/3)) or a parametric bootstrap from the fitted GPD | Any bootstrap of the maximum or of quantiles beyond about `1 − 5/n`; autocorrelated data without block resampling; fewer than 500 resamples for a 95% interval |
| 22 | **Clauset–Shalizi–Newman power-law test suite** | "is this actually a power law?" · "is this scale-free / Pareto / 80-20?" · "someone claims a power law — check it" · "fit a Zipf exponent properly" | Positive sample, ≥ 50 observations in the tail. **DATAFILE** | Log-log least-squares slope fitting, which is biased and has no error theory — still the most common way power laws are wrongly claimed. Pipeline: MLE `α̂ = 1 + n/Σ ln(xᵢ/x_min)` with `SE ≈ (α̂−1)/√n`; x_min by KS minimisation; bootstrap goodness-of-fit p-value (reject if p < 0.1); Vuong likelihood-ratio tests against lognormal, exponential, stretched exponential, and power-law-with-cutoff | **MODERATE**, but **compute-heavy**: the semiparametric bootstrap needs ~(1/4)ε⁻² synthetic datasets for p-value precision ε (2 500 for two decimals), each with its own x_min scan. Restrict x_min candidates to ≤ 100 grid points and cap B; expect tens of seconds to minutes in pure Python at n ≈ 2 000 | fewer than 50 tail observations; **refuse to assert "power law" on a non-rejecting KS p-value alone** — the LR comparison against lognormal is mandatory, and lognormal is very rarely rejected in favour of power law; discrete data fitted with the continuous MLE; the caller wants a decision that only needs "heavy-tailed", in which case route to #6/#14 instead |
| 23 | **Automated threshold selection (Bader–Yan–Zhang ordered GoF with FDR; Murphy et al. QQ-distance)** | "pick the threshold for me" · "automate the cutoff choice" · "I don't want to eyeball a plot" | Sample n ≥ 500. **DATAFILE** | Eyeballing a mean-residual-life plot, and picking the lowest threshold that "looks linear" (which stability plots systematically encourage). Bader et al. run ordered Anderson–Darling/Cramér–von Mises GoF tests over candidate thresholds with a ForwardStop FDR correction; Murphy et al. minimise a bootstrapped QQ-plot distance and report lower quantile RMSE than Northrop et al. (2017) and Wadsworth (2016) | **HARD.** Needs GPD fits at every candidate, a GoF statistic with a simulated null, and an FDR stopping rule | n < 500; the caller wants a *single* threshold when #11 shows the answer is threshold-dependent — the sensitivity range must accompany any automated choice; time-series data without declustering |
| 24 | **Pickands estimator (sign-of-ξ cross-check only)** | "double-check the tail shape" · "second opinion on the tail index" · "is the tail bounded or unbounded?" | Sorted sample, n ≥ 4k. **DATAFILE** | Nothing on its own — it is dominated on variance by Hill and by GPD-MLE. Its one virtue is that it works for any ξ (including ξ < 0, where Hill is undefined), so it is a useful *agreement check* on the sign of ξ. `ξ̂ = log₂[(X_(n−k+1) − X_(n−2k+1))/(X_(n−2k+1) − X_(n−4k+1))]` | **EASY.** Three order statistics | Always refuse to print it as *the* answer; refuse if 4k > n; refuse if the middle difference is ≈ 0; if Pickands and GPD-MLE disagree on the sign of ξ, the tool should report "tail shape undetermined at this sample size" |

### 2.1 The refusal doctrine (this is the deliverable, not a caveat)

Prior-art evidence in `RESEARCH.md` §0.3 is that agents read the number and ignore the warning next to
it. In this territory that behaviour is actively dangerous, so refusal must suppress the headline
number, not annotate it. Global rules, in precedence order:

- **R0 — Mechanism boundary.** EVT extrapolates the tail of the *observed generating mechanism*. If
  the caller asks about a hazard with no representative in the data (a new failure mode, an adversary,
  a regime change), refuse. No amount of clean history bounds an unobserved mechanism.
- **R1 — Censoring/capping.** If the sample maximum coincides with a known cap (timeout, quota,
  buffer, rating scale, saturating classifier score), every tail statistic is a lie. Refuse or model
  the censoring. *A p99 latency measured under a 30-second client timeout is not a p99.*
- **R2 — The n ≥ ln(α)/ln(p) wall.** No upper confidence bound on the p-quantile exists below it.
  Print the wall, not a number.
- **R3 — Exceedance floor.** < 30 exceedances ⇒ no GPD parameters. < 25 blocks ⇒ no GEV.
  < 5 points beyond VaR ⇒ no ES.
- **R4 — Extrapolation factor.** Refuse levels beyond ~10× the record length; warn beyond 4×.
- **R5 — Moment existence.** ξ̂ ≥ 1 ⇒ refuse to print any mean or ES ("the mean does not exist" is the
  answer). ξ̂ ≥ 0.5 ⇒ refuse any variance-based standard error or normal-approximation CI.
- **R6 — Threshold instability.** Target quantity varying > 2× across admissible thresholds ⇒ return
  the range, suppress the point estimate.
- **R7 — Dependence.** θ̂ < 0.5 (clustered exceedances) ⇒ refuse iid intervals; decluster and shrink
  the effective n.
- **R8 — Non-stationarity.** Record count materially above expectation, or the maximum in the last
  10% of a long record ⇒ refuse stationary return levels.
- **R9 — Discreteness.** < 10 distinct values in the tail ⇒ continuous tail models are meaningless.
- **R10 — Never symmetric.** Return-level and extreme-quantile intervals are strongly right-skewed;
  emitting `estimate ± 1.96·SE` is itself a bug.

### 2.2 What sample size honestly buys you

The exact wall for a one-sided 95% upper confidence bound on the p-quantile is `p ≤ α^(1/n)`:

| n | Highest quantile with *any* 95% upper confidence bound | Blunt reading |
|---|---|---|
| 10 | p74 | You know essentially nothing about the tail. |
| 30 | p90.5 | You cannot bound the p95. |
| 100 | p97.0 | Your "p99" has no upper bound. Do not report one. |
| 300 | p99.0 | 299 is the classic Wilks 95/99 number. |
| 1 000 | p99.70 | p99 CI ≈ order statistics 984–996. |
| 3 000 | p99.90 | p99.9 is at the wall — point estimate only, no bound. |
| 10 000 | p99.97 | p99.9 CI ≈ ranks 9 984–9 996. |
| 30 000 | p99.990 | The regime where tail-*shape* comparisons become powered (see §3). |

Companion fact for shape: detecting a difference of Δξ = 0.10 at 80% power needs **≈ 1 570
exceedances per condition** (≈ 31 400 raw samples at a 95th-percentile threshold). At agent scale,
ξ is a *sign and an order of magnitude*, never a precise number.

---

## 3. Recent advances (~last 10 years)

**Threshold selection stopped being purely graphical.** Bader, Yan & Zhang (2018, *Annals of Applied
Statistics*) run ordered goodness-of-fit tests across candidate thresholds with a ForwardStop
false-discovery-rate correction; the 2026 review finds it has higher power than competitors with small
size distortion. Northrop, Attalides & Chavez-Demoulin (2017) use Bayesian leave-one-out
cross-validation and threshold *averaging* rather than selection; Wadsworth (2016) contributes a
white-noise likelihood diagnostic; Silva Lomba & Fraga Alves (2020) give an L-moment-based automatic
rule. The current state of the art is Murphy, Tawn & Varty (2024/2025, *Technometrics*), which
minimises a bootstrapped QQ-plot distance and reports lower quantile RMSE than both Northrop and
Wadsworth. The 2026 review *Choosing the threshold in extreme value analysis* (arXiv:2606.28540) is
the authoritative synthesis and its verdict is deflationary: no method is universally superior,
stability plots systematically pick thresholds that are too low because of penultimate-approximation
effects, Bayesian cross-validation gives highly variable choices, and — the most useful practical
finding for us — **shape estimates wander across thresholds while high-quantile estimates are often
stable**, so the sensitivity scan should be run on the decision quantity, not on ξ. It recommends
≥ 20 exceedances as a hard floor and intermediate sequences of the form `⌈n − n^q⌉` with q = 0.995 or
0.999.

**Expected Shortfall won the risk-measure argument, and the elicitability objection was resolved.**
ES is coherent (subadditive) where VaR is not; the counterargument from 2011 was that ES is not
elicitable and therefore allegedly not backtestable. Fissler & Ziegel (2016) showed ES is **jointly
elicitable with VaR** (a 2-dimensional consistent scoring function exists), and Acerbi & Székely
(2014, 2017) argued separately that elicitability governs *ranking* forecasts, not backtesting them,
and supplied direct ES backtests. Basel's FRTB completed the migration by replacing 99% VaR with
97.5% ES (the two coincide almost exactly under normality — 2.338 vs 2.326 — and diverge sharply
under heavy tails, which is the point). Kou & Peng's median shortfall persists as an elicitable,
robust alternative. Practical implication for the module: report ES by default and VaR only on
request, and never let the agent add VaRs across components.

**Power laws got both stricter and looser.** Broido & Clauset (2019, *Nature Communications*) applied
the CSN pipeline at scale and concluded "scale-free networks are rare". Voitalov, van der Hoorn, van
der Hofstad & Krioukov (2019, *Physical Review Research*) rebutted this by redefining the target as
**regular variation** rather than pure Pareto purity, identified three consistent tail-exponent
estimators, and found scale-free structure to be common under that definition. The lesson generalises
well beyond networks: *"is it exactly a power law"* is almost always the wrong question and almost
always answerable "no"; *"is the tail regularly varying with index α"* is the decision-relevant one.
Clauset's own extension to binned data (Virkar & Clauset, 2014) covers the histogram case agents often
face. A 2024 *American Statistician* contribution, "A Pareto Tail Plot Without Moment Restrictions",
gives a diagnostic plot valid even when moments don't exist.

**EVT moved into online systems and then into ML evaluation.** Siffer et al. (KDD 2017) introduced
SPOT/DSPOT — streaming peaks-over-threshold anomaly detection with no distributional assumption and
no hand-set threshold, parameterised only by a risk level; DSPOT adds drift handling via a moving
average. Amazon's spliced binned-Pareto model (2022) fits a flexible bulk with a GPD tail for
heavy-tailed time series. Most relevant to this project: EVT is now being used to forecast rare LLM
behaviour. Jones et al. (2025, *Forecasting Rare Language Model Behaviors*, arXiv:2502.16797)
extrapolate from 100–1 000 evaluation queries to 90 000 deployment queries using a Gumbel-tail fit on
`ψ = −log(−log p)` of elicitation probabilities, landing 72% of worst-query forecasts within one order
of magnitude and beating a lognormal baseline (mean log error 1.7 vs 2.4). And the essential
counterweight, arXiv:2606.16511 (*Tail-Shape Estimation in LLM Evaluation Is Fragile*), pre-registers
a gated protocol and **kills its own headline hypothesis**: a 2 000-prompt pilot showed Δξ̂ = 0.28
between conditions which shrank 30× to 0.009 at 30 000 prompts; three of four models failed GPD
goodness-of-fit because sigmoid classifier scores saturate near 1 and produce spurious ξ̂ ≈ −1; and a
"significant" single-threshold result at q = 0.97 evaporated under a stability scan. Zero of six model
pairs passed all gates. This paper is effectively an external validation of §2.1 and should be cited
in the module's documentation.

**Bias-corrected tail-index estimation matured but did not become usable at agent scale.** Danielsson
et al.'s double bootstrap for the optimal number of order statistics (2001, revisited 2019) minimises
the Hill estimator's asymptotic MSE, and a Bank of Canada working paper (Danielsson, Ergun, de Haan &
de Vries, 2019) proposes quantile-driven threshold selection. All of these rely on second-order
regular-variation parameters and need sample sizes in the tens of thousands; the 2026 review notes
their "inadequate finite-sample performance". They belong on the cut list for this module.

**Better bounds from moments.** Mercadier & Strub (2021, *European Journal of Operational Research*)
derived a one-sided Vysochanskii–Petunin inequality — Cantelli's bound sharpened under unimodality —
with an explicit VaR application. This is a genuinely useful, exactly computable, assumption-light
upgrade for the "I only have a mean and a standard deviation" case.

**Fat-tail pedagogy.** Taleb's *Statistical Consequences of Fat Tails* (2020, arXiv:2001.10488)
formalised the practical diagnostics — max-to-sum plots, κ-metric for the speed of convergence to the
CLT, "how many observations do you need before the mean means anything" — and Cirillo & Taleb (2020)
applied them to pandemic and war fatalities, concluding infinite mean for both. The MS plot in
particular (attributed by them to El Adlouni et al., 2008) is the single cheapest and most
agent-legible heavy-tail diagnostic available and is why #6 ranks where it does.

---

## 4. Cut list

- **Multivariate / spatial extremes (max-stable processes, Brown–Resnick, Hüsler–Reiss)** — requires
  data volumes and numerics far beyond stdlib and agent scale.
- **Conditional extremes (Heffernan–Tawn)** — same, plus needs a well-specified conditioning variable.
- **Tail-dependence copulas, Pickands dependence function, spectral measures** — bivariate extreme
  data an agent will essentially never hold.
- **GARCH-EVT / McNeil–Frey conditional VaR filtering** — needs a fitted volatility model; belongs to
  the time-series territory if anywhere.
- **Point-process / r-largest-order-statistics GEV formulations** — marginally more efficient than
  POT, materially more code, indistinguishable in output at n ≤ a few thousand.
- **Non-stationary GEV/GPD with covariates (trend in location/scale/shape)** — overfits catastrophically
  below ~50 blocks; the honest substitute is #19's stationarity check plus a refusal.
- **Full Bayesian MCMC for GEV/GPD** — implementable in stdlib but slow, and the answer is dominated by
  a prior on ξ that has no domain-agnostic justification. Profile likelihood gets the asymmetry for a
  tenth of the code.
- **Generalized maximum likelihood with a geophysical Beta prior on ξ (Martins & Stedinger)** — the
  prior is calibrated to hydrology; smuggling it into a domain-agnostic tool is dishonest.
- **Danielsson double-bootstrap / bias-corrected Hill requiring the second-order parameter ρ** — needs
  n in the tens of thousands; documented poor finite-sample behaviour.
- **de Haan moment estimator, kernel Hill, Zipf/least-squares tail estimators, averages of Hill** —
  marginal accuracy gains over Hill, each with its own tuning parameter, none resolving the
  instability that is the actual problem.
- **VaR backtesting suites (Kupiec POF, Christoffersen independence, Acerbi–Székely Z-tests)** —
  require a long history of *out-of-sample forecasts*, which an agent making a one-off judgment does
  not have.
- **Elicitability-based scoring-function model comparison** — same reason: needs repeated forecasts.
- **Distortion / spectral risk measures, Wang transform** — no agent-legible way to choose the
  distortion function.
- **t-digest, KLL, DDSketch and other streaming quantile sketches** — excellent engineering, but they
  are compression algorithms, not inference; they give you a point estimate with no uncertainty, which
  is the failure mode we exist to fix. Worth a documentation note only.
- **L-moment ratio diagrams for distribution family selection** — pretty, low decision value; the
  family choice rarely changes the action.
- **Extreme-value regression / extremal quantile regression** — needs covariates and n in the
  thousands.
- **Neural / deep EVT hybrids, EVT-GAN** — out of scope by construction (no numpy).
- **Peaks-over-random-threshold, trimmed and censored EVT likelihoods** — refinements to a step (#11)
  we are already choosing to report as a range rather than optimise.
- **Gumbel-only return levels (ξ forced to 0)** — historically common, systematically optimistic about
  the worst case, and exactly the error the module should prevent.
- **Ruin theory / Cramér–Lundberg, insurance premium principles** — needs a claims-arrival model and a
  reserve process; the decision-relevant part is already covered by #4.
- **"Black swan" quantification** — not a method. Handled by refusal rule R0.

---

## 5. Cross-territory overlaps

- **Proportions and binomial inference** — owns exact Clopper–Pearson/Wilson machinery; #1 and #4 are
  the tail-framed entry points to it. Share the binomial-CDF primitive; do not duplicate it.
- **Counts and Poisson processes** — #15 lives on the boundary; overdispersion, negative binomial, and
  rate-comparison tests belong there.
- **Bootstrap and resampling** — #21 must import that territory's block-bootstrap and BCa machinery,
  but this territory owns the *warning* that the ordinary bootstrap is inconsistent for maxima.
- **Distribution fitting and goodness-of-fit** — KS, Anderson–Darling, Vuong/likelihood-ratio model
  comparison, and AIC are shared primitives; #22 and #23 are heavy consumers.
- **Time series / autocorrelation** — effective sample size, declustering, and the extremal index
  (#17) are the tail-side face of the same problem; stationarity testing (#19) overlaps changepoint
  detection.
- **Decision theory and expected utility** — #4 is deliberately a bridge: tail probability × loss
  versus benefit. Break-even and value-of-information logic belongs there; the tail bound belongs here.
- **Sample size and experiment design** — #3 is the distribution-free tolerance-interval corner of
  that territory; the Δξ = 0.10 / 1 570-exceedance result is its tail-shape analogue.
- **Monte Carlo and simulation** — #22's semiparametric bootstrap, #16's uncertainty, and any parametric
  bootstrap for return levels depend on that territory's RNG discipline and reproducible seeding.
- **Benchmarking and performance measurement** — tail-latency percentiles (#2, #9) and the
  timeout-censoring trap (R1) are shared with whatever territory owns "is this speedup real".
- **Bayesian methods** — the predictive zero-event formula `m/(n+m+1)`, Jeffreys-prior variants, and
  threshold averaging all touch it; keep the priors explicit and defaults uninformative.

---

## 6. Sources

**Foundational**

- Clauset, A., Shalizi, C. R., & Newman, M. E. J. (2009). *Power-law distributions in empirical data*.
  SIAM Review 51(4), 661–703. https://arxiv.org/pdf/0706.1062 ·
  https://sites.santafe.edu/~aaronc/courses/5352/readings/Clauset_Shalizi_Newman_09_PowerlawDistributionsInEmpiricalData.pdf
- Hosking, J. R. M., & Wallis, J. R. (1987). *Parameter and quantile estimation for the generalized
  Pareto distribution*. Technometrics 29(3), 339–349. (L-moment/PWM estimators; small-sample
  superiority over MLE.)
- Grimshaw, S. D. (1993). *Computing maximum likelihood estimates for the generalized Pareto
  distribution*. Technometrics 35(2), 185–191. (1-D reduction used by #10.)
- Hill, B. M. (1975). *A simple general approach to inference about the tail of a distribution*.
  Annals of Statistics 3(5), 1163–1174.
- Davison, A. C., & Smith, R. L. (1990). *Models for exceedances over high thresholds*. JRSS-B 52(3),
  393–442. (Mean residual life.)
- Artzner, Delbaen, Eber & Heath (1999). *Coherent measures of risk*. Mathematical Finance 9(3),
  203–228. (Why ES is coherent and VaR is not.)
- Ferro, C. A. T., & Segers, J. (2003). *Inference for clusters of extreme values*. JRSS-B 65(2),
  545–556. (Intervals estimator of the extremal index.)
- Dean, J., & Barroso, L. A. (2013). *The Tail at Scale*. CACM 56(2), 74–80. (Fan-out amplification.)

**Threshold selection**

- *Choosing the threshold in extreme value analysis* (2026 review). https://arxiv.org/html/2606.28540 ·
  https://arxiv.org/pdf/2606.28540
- Murphy, C., Tawn, J. A., & Varty, Z. (2024/2025). *Automated threshold selection and associated
  inference uncertainty for univariate extremes*. Technometrics 66(3), 363–375.
  https://www.tandfonline.com/doi/full/10.1080/00401706.2024.2421744 · https://arxiv.org/pdf/2310.17999
- Bader, B., Yan, J., & Zhang, X. (2018). *Automated threshold selection for extreme value analysis via
  ordered goodness-of-fit tests with adjustment for false discovery rate*. Annals of Applied Statistics
  12(1). https://projecteuclid.org/journals/annals-of-applied-statistics/volume-12/issue-1/Automated-threshold-selection-for-extreme-value-analysis-via-ordered-goodness/10.1214/17-AOAS1092.pdf
- Silva Lomba, J., & Fraga Alves, M. I. (2020). *L-moments for automatic threshold selection in extreme
  value analysis*. SERRA 34. https://link.springer.com/article/10.1007/s00477-020-01789-x
- Danielsson, J., Ergun, L. M., de Haan, L., & de Vries, C. G. (2019). *Tail index estimation:
  quantile-driven threshold selection*. Bank of Canada SWP 2019-28.
  https://www.bankofcanada.ca/wp-content/uploads/2019/08/swp2019-28.pdf
- Danielsson, de Haan, Peng & de Vries (2001). *Using a bootstrap method to choose the sample fraction
  in tail index estimation*. https://riskresearch.org/files/DanielssonHaanPengVries2001.pdf

**Risk measures**

- Fissler, T., & Ziegel, J. F. (2016). *Higher order elicitability and Osband's principle*. Annals of
  Statistics 44(4), 1680–1707. (ES jointly elicitable with VaR.)
- Ziegel, J. F. (2016). *Coherence and elicitability*. Mathematical Finance 26(4), 901–918.
- Acerbi, C., & Székely, B. (2014). *Backtesting Expected Shortfall*. Risk Magazine; and (2017)
  *General properties of backtestable statistics*.
- Nolde, N., & Ziegel, J. F. (2017). *Elicitability and backtesting: perspectives for banking
  regulation*. Annals of Applied Statistics 11(4).
- *Elicitability and its application in risk management*. https://arxiv.org/pdf/1707.09604
- *Elicitability and identifiability of tail risk measures* (2024). https://arxiv.org/pdf/2404.14136
- Emmer, Kratz & Tasche (2015). *What is the best risk measure in practice? A comparison of standard
  measures*. Journal of Risk 18(2).

**Bounds and diagnostics**

- Mercadier, M., & Strub, F. (2021). *A one-sided Vysochanskii–Petunin inequality with financial
  applications*. European Journal of Operational Research 295(1).
  https://uca.hal.science/hal-03241628/document
- John D. Cook, *Vysochanskii–Petunin inequality: improving on Chebyshev*.
  https://www.johndcook.com/blog/2016/02/12/improving-on-chebyshevs-inequality/
- Taleb, N. N. (2020). *Statistical Consequences of Fat Tails*. https://arxiv.org/pdf/2001.10488
- Cirillo, P., & Taleb, N. N. (2020). *Tail risk of contagious diseases*. Nature Physics 16, 606–613.
  https://arxiv.org/pdf/2004.08658
- *A Pareto Tail Plot Without Moment Restrictions* (2024). The American Statistician.
  https://www.tandfonline.com/doi/full/10.1080/00031305.2024.2413081
- Massart, P. (1990). *The tight constant in the Dvoretzky–Kiefer–Wolfowitz inequality*. Annals of
  Probability 18(3), 1269–1283.
- Wilks, S. S. (1941). *Determination of sample sizes for setting tolerance limits*. Annals of
  Mathematical Statistics 12(1), 91–96.

**Zero events**

- Hanley, J. A., & Lippman-Hand, A. (1983). *If nothing goes wrong, is everything all right?
  Interpreting zero numerators*. JAMA 249(13), 1743–1745.
- Jovanovic, B. D., & Levy, P. S. (1997). *A look at the rule of three*. The American Statistician
  51(2), 137–139. https://www.tandfonline.com/doi/abs/10.1080/00031305.1997.10473947
- Tuyl, F., Gerlach, R., & Mengersen, K. (2008). *Posterior predictive arguments in favor of the
  Bayes–Laplace prior as the consensus prior for binomial sampling*.
- Cochrane Handbook §16.9.4, *Confidence intervals when no events are observed*.
  https://handbook-5-1.cochrane.org/chapter_16/16_9_4_confidence_intervals_when_no_events_are_observed.htm
- Wikipedia, *Rule of three (statistics)*. https://en.wikipedia.org/wiki/Rule_of_three_(statistics)

**Power laws, recent**

- Voitalov, I., van der Hoorn, P., van der Hofstad, R., & Krioukov, D. (2019). *Scale-free networks
  well done*. Physical Review Research 1, 033034. https://arxiv.org/pdf/1811.02071
- Broido, A. D., & Clauset, A. (2019). *Scale-free networks are rare*. Nature Communications 10, 1017.
- Virkar, Y., & Clauset, A. (2014). *Power-law distributions in binned empirical data*. Annals of
  Applied Statistics 8(1). https://arxiv.org/pdf/1208.3524
- Aaron Clauset's power-law resources page. https://aaronclauset.github.io/powerlaws/

**EVT in systems and ML**

- Siffer, A., Fouque, P.-A., Termier, A., & Largouët, C. (2017). *Anomaly detection in streams with
  extreme value theory*. KDD '17. https://www.eecs.yorku.ca/course_archive/2017-18/F/6412/reading/kdd17p1067.pdf
- Jones, E., et al. (2025). *Forecasting rare language model behaviors*. https://arxiv.org/html/2502.16797
- *Tail-shape estimation in LLM evaluation is fragile: a protocol for diagnosing false positives*
  (2026). https://arxiv.org/html/2606.16511
- *Estimating rare events in language models with proper evaluation* (2026).
  https://arxiv.org/html/2607.18454v1
- *Estimating tail risks in language model output distributions* (2026). https://arxiv.org/pdf/2604.22167
- *New statistical framework for extreme error probability in high-stakes domains for reliable machine
  learning* (2025). https://arxiv.org/html/2503.24262
- *Toward scalable risk analysis for stochastic systems using extreme value theory* (2022).
  https://arxiv.org/pdf/2203.12689
- Amazon Science, *Spliced binned-Pareto distribution for robust modeling of heavy-tailed time series*
  (2022). https://assets.amazon.science/1a/1d/949c6ec6471e805ef6ad909a1af7/spliced-binned-pareto-distribution-for-robust-modeling-of-heavy-tailed-time-series.pdf

**Textbooks**

- Coles, S. (2001). *An Introduction to Statistical Modeling of Extreme Values*. Springer.
- Embrechts, Klüppelberg & Mikosch (1997). *Modelling Extremal Events for Insurance and Finance*.
- McNeil, Frey & Embrechts (2015). *Quantitative Risk Management*, 2nd ed. Princeton.
- de Haan, L., & Ferreira, A. (2006). *Extreme Value Theory: An Introduction*. Springer.
