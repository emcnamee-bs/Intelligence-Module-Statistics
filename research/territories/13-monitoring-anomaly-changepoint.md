# Territory 13 — Monitoring, Anomaly Detection, and Changepoint Analysis

Research pass for the Intelligence Module. Scope: statistical process control, CUSUM/EWMA,
changepoint detection, runs/nonrandomness tests, robust anomaly scoring, seasonal-aware
detection, Poisson/rare-event monitoring, multiple-testing in monitoring, ARL-based threshold
selection, flaky-test adjudication, and benchmark-regression triage.

Constraint reminder: **pure Python 3 stdlib** (`math`, `statistics`, `random`, `itertools`,
`bisect`), series length 5 to a few thousand, invoked from a CLI by an agent.

---

## 1. Territory summary

This is the highest-yield territory in the whole module, because it is the one where an agent's
unaided intuition is not merely imprecise but *systematically wrong in a known direction*: agents
over-read single points, treat 3 benchmark runs as evidence, treat one error as a trend, and treat
"it failed once" as "it is flaky." The mathematics that fixes this is unusually cheap — the
decisive tools here are medians, absolute deviations, exact binomial and Poisson tail sums, a
permutation loop, and one closed-form ARL approximation, none of which need a matrix library. The
territory's organising idea is that **a detection rule is only meaningful once you can state its
false-alarm rate**, and the single most useful thing a tool can print is not a p-value but "at this
threshold you will page someone spuriously once every N days" — the Average Run Length framing
converts an unanswerable question ("is 3-sigma right?") into an answerable one ("how often do I want
to be wrong?"). Three sub-problems deserve disproportionate attention because agents meet them
daily and get them wrong almost every time: **benchmark regression from a handful of runs** (where
the honest answer is usually "your 3-vs-3 comparison cannot see anything smaller than ±9%"),
**flaky-vs-unlucky test adjudication** (where one failure in twenty runs is compatible with a true
flake rate anywhere from 0.1% to 25%), and **rare-event counts** (where seeing 1 event against an
expected 0.2 is *not* significant, p = 0.18, but seeing 2 is, p = 0.018). Finally, almost every
naive monitoring failure in practice traces to one of four assumption violations — autocorrelation,
skew, discreteness/ties, and multiplicity — so the refusal logic in this territory is not
decoration; it is most of the value.

---

## 2. Ranked model table

Tier key: **INLINE** = a handful of numbers as CLI flags · **DATAFILE** = a small series/table in a
file · **MUST-CONSTRUCT** = the agent has to go generate the data (re-run a benchmark, re-run a
test N times) before the tool can say anything.

| # | Model / method | SITUATION (agent phrasing + alternates) | Minimum viable inputs · tier | Beats what | Stdlib feasibility · required numerics | Failure modes that must force a REFUSAL |
|---|---|---|---|---|---|---|
| 1 | **Robust anomaly score** — modified z = 0.6745·(x−median)/MAD (Iglewicz–Hoaglin), with IQR-fence and Sn fallbacks | "is this spike an anomaly or normal variation?" · "this number looks way off, is it?" · "is 412ms unusual given these values?" · "flag the outliers in this list" | 1 candidate value + ≥7 baseline values, or just the series · **INLINE or DATAFILE** | Eyeballing; mean±3·SD, which is *masked* by the very outlier being tested (one bad point inflates SD so it hides itself); "it's 2x the average" | **EASY.** `statistics.median`, sorted list, constant 1.4826 (=1/Φ⁻¹(0.75)). Optional `NormalDist().cdf` for a p-value | **MAD == 0** (ties/rounded ms/integer counts) → score is ±∞; refuse and switch to IQR or Sn. n < 7 → MAD has no resolution. Visible skew (|median−mean|/IQR large, or Bowley skew > 0.3) → refuse symmetric two-sided limits, demand log scale or a one-sided rule. Series is a time series with trend → refuse; route to #18 Hampel |
| 2 | **Benchmark regression verdict** — CI on the *difference* (Welch, or BCa bootstrap on the median / Hodges–Lehmann shift), compared against a declared minimum-interesting effect | "is this change actually slower or is it noise?" · "my benchmark went from 100ms to 105ms — real regression?" · "did my optimization actually help?" · "should I trust this before/after benchmark?" | ≥3 before + ≥3 after timings, plus a practical threshold (e.g. "care about ≥3%") · **DATAFILE** (or INLINE for tiny n) | Comparing two means; comparing two single runs; "5% slower ⇒ regression"; p<0.05 with no effect size; treating overlapping-CI vs difference-CI as equivalent (they are not — overlapping CIs are the conservative, wrong test) | **EASY–MODERATE.** Welch df + Student-t quantile needs regularized incomplete beta `I_x(a,b)`; bootstrap path needs only `random.choice` and is the better default for skewed timings | n<3 per arm → refuse outright. **All runs from one process / not interleaved** → refuse or downgrade to "descriptive only": warmup, JIT, thermal throttling and page cache make within-process runs non-exchangeable. CI half-width > the effect being claimed → print the CI and the required-n from #3, suppress any verdict. Both arms have identical values (zero variance) → refuse |
| 3 | **Runs-needed / MDE planner for benchmarks** — n = 2σ²(z_{α/2}+z_β)²/Δ²; inverted to give the MDE at the runs you have | "how many benchmark runs do I need?" · "can 5 runs even detect a 2% regression?" · "what's the smallest slowdown I could detect here?" · "is it worth running this more times?" | pilot σ (or CV%) + target effect Δ + α, power · **INLINE** (σ from a pilot ⇒ **MUST-CONSTRUCT** if absent) | Running "a few times" and hoping; the universal agent default of n=3; declaring "no regression" from an underpowered test | **EASY.** `NormalDist().inv_cdf` only. Add a t-based iteration for n<30 | No σ and no pilot data → refuse and instruct the agent to collect ≥10 baseline runs first. σ estimated from n<5 → the estimate is itself ±50%; print an interval on n, not a point. Δ not supplied → refuse (there is no such thing as "enough runs" without a target effect) |
| 4 | **Exact Poisson rate check for rare events** — Garwood/exact CI via inversion of the Poisson CDF, plus one-sided exact tail p against an expected rate | "we got 2 errors this hour, is that bad?" · "is 1 crash in a week meaningful?" · "zero failures in 500 runs — how good is that really?" · "this count doubled, should I care?" | observed count x, exposure t, and either a baseline rate or a baseline (count, exposure) · **INLINE** | 3-sigma on counts (which for λ=1 gives a 2.7× inflated alarm rate and cannot alarm downward at all); percent-change on small counts ("errors up 100%!" = 1→2); the agent's instinct that any nonzero count is a signal | **EASY and exact.** Poisson pmf/CDF is a finite sum `exp(-λ)λ^k/k!` via `math.exp`, `math.lgamma`; CI by bisection on λ. No chi-square inverse needed | Exposure/denominator unknown or not comparable between periods → refuse (a rate needs a denominator). **Overdispersion**: if a baseline series is available and the dispersion test (#19) rejects Poisson, refuse the exact p and route to negative-binomial or an empirical quantile. Counts arising from a burst of one incident (not independent events) → refuse |
| 5 | **Flaky-or-unlucky** — Clopper–Pearson/Wilson/Jeffreys interval on the failure rate + rule of three + reruns-to-confidence | "is this test flaky or did I get unlucky?" · "it failed once out of 20, is it broken?" · "did my change break this or is it just flaky?" · "how many times do I rerun before I believe it passes?" | failures f out of n runs (optionally before/after split) · **INLINE**; a rerun budget makes it **MUST-CONSTRUCT** | "It failed, so it's broken"; "it passed on retry, so it's flaky"; picking a rerun count by feel; the near-universal error of treating 1/20 as "5% flaky" as if that were precise | **EASY and exact.** `math.comb` gives exact binomial tails; Clopper–Pearson by bisection on the tail sum; rule of three is `-ln(α)/n` | f=0 and n<10 → refuse a rate estimate; print only the rule-of-three upper bound. Runs are not independent (same machine, same seed, shared fixture, ordered suite) → refuse; flakiness inference assumes exchangeable reruns. Before/after run counts differ by >5× → warn and force the exact conditional test rather than comparing point rates |
| 6 | **Single changepoint: max-CUSUM / max-t binary segmentation + permutation p-value + location CI** | "did something change, and when?" · "when did this start getting worse?" · "is there a break in this series?" · "which deploy caused this?" | series of ≥12–15 points · **DATAFILE** | Eyeballing a chart; running a t-test at the visually-chosen split point (this is the classic error — the max over n split points is *not* t-distributed; it is a Brownian-bridge supremum, and the naive p-value is wildly anti-conservative) | **EASY.** Statistic T_τ = √(τ(n−τ)/n)·|x̄₁−x̄₂|/σ̂ maximised over τ; null distribution by 2,000 `random.shuffle` permutations. Location CI by bootstrap or by the profile-likelihood drop | Strong lag-1 autocorrelation (|ρ̂₁| > ~0.25) → **refuse plain permutation** (exchangeability is violated); switch to circular block permutation with block length ≈ 2·(1+ρ)/(1−ρ), or refuse. Changepoint located in the first or last 3 points → refuse (edge effects; the statistic is unstable and the "segment" has no data). n<12 → refuse. Monotone trend present → refuse; a trend fakes a level shift at the midpoint (route to #9) |
| 7 | **Threshold calibration by ARL / Monte Carlo false-alarm engine** — simulate any rule against the agent's own in-control history (bootstrap) or N(0,1); invert to find the threshold hitting a target ARL₀ | "what threshold should I alert at?" · "how often will this rule cry wolf?" · "is 3-sigma the right cutoff here?" · "I want at most one false page per month — what limit is that?" | a rule spec + either an in-control series or (μ,σ) + a check frequency · **DATAFILE preferred, INLINE possible** | Round numbers (3σ, "95th percentile", "2x baseline"); copying a threshold from a blog post; adding up per-rule false-alarm rates, which is invalid for overlapping run rules | **EASY.** `random.gauss` / `random.choice` for bootstrap, 10⁴–10⁵ replications, binary search on the threshold. Also supports the closed-form Siegmund CUSUM ARL (see §3.1) as a cross-check | In-control history shorter than ~50 points → the bootstrap null is too coarse; refuse a calibrated number and print only the analytic normal-theory one, flagged. History contains the anomaly you are trying to detect → refuse (contaminated null); require a clean window or a trimmed/robust fit. Check frequency not supplied → refuse to convert ARL into "alerts per day" |
| 8 | **Change-type discriminator** — fit {flat, single level shift, linear trend, variance change, single outlier} and rank by BIC/MDL; report the winner and the BIC gap | "what kind of change is this — a step, a drift, or just noisier?" · "did the level move or did the variance blow up?" · "is this one bad data point or a real shift?" · "is this a gradual degradation or a sudden break?" | series of ≥20 points · **DATAFILE** | The agent picking a narrative from the shape of a chart; running a mean-shift test on a series whose variance changed (which it will pass, wrongly); conflating "noisier" with "worse" | **MODERATE.** RSS for each model; BIC = n·ln(RSS/n) + k·ln(n), with the fitted changepoint location charged as an extra parameter. Variance-change model needs the Gaussian log-likelihood with two σ's | BIC gap between top two models < ~2 → **refuse to name a change type**; report the tie explicitly. n<20 → refuse (five competing models on 20 points is overfitting). Heavy tails / a single extreme point dominating RSS → refuse or rerun with a robust (biweight) loss and report both |
| 9 | **Mann–Kendall trend test + Theil–Sen slope** (with Hamed–Rao autocorrelation correction) | "is this metric drifting?" · "is memory usage creeping up?" · "is this trending or just wobbling?" · "how fast is it getting worse and when does it hit the limit?" | series of ≥8–10 ordered points · **DATAFILE** | Fitting OLS and reading the slope's p-value (fragile to outliers and non-normality); "the last 3 are higher so it's trending"; linear extrapolation from endpoints | **EASY.** S = Σ sign(x_j−x_i); Var(S) closed form with a tie correction; normal approximation for n≥10, exact enumeration for n<10. Theil–Sen = median of all pairwise slopes, O(n²) — fine to n≈2000 | Lag-1 autocorrelation > ~0.2 → the variance of S is understated and MK over-rejects; refuse or apply the Hamed–Rao effective-sample-size correction and say so. Seasonality present → refuse; route to seasonal Mann–Kendall (per-period S summed). n<8 → refuse. A single step change will register as a "trend"; if #8 prefers the step model, suppress the trend verdict |
| 10 | **Tabular CUSUM** (k, h in σ units) with Siegmund ARL | "is there a small persistent shift I'm missing?" · "the chart looks fine but is it slowly drifting off target?" · "detect a 1-sigma shift as fast as possible" · "my Shewhart chart never fires but something feels off" | in-control μ, σ (or a clean baseline window) + the ongoing series + target shift δ · **DATAFILE** | Shewhart charts, which are ~5× slower at a 1σ shift (ARL 43.9 vs 8.4); waiting for a point to cross 3σ | **EASY.** C⁺ᵢ = max(0, xᵢ−(μ+kσ)+C⁺ᵢ₋₁), C⁻ᵢ = max(0, (μ−kσ)−xᵢ+C⁻ᵢ₋₁), signal at hσ. ARL from Siegmund's closed form (§3.1) — no Markov chain needed | Baseline μ, σ estimated from <25 points → the ARL guarantee evaporates; refuse to quote an ARL. σ estimated by the sample SD of a series that already contains the shift → refuse; require moving-range σ̂ = MR̄/1.128. Autocorrelated input → refuse (see #16; CUSUM is *more* sensitive to this than Shewhart). Non-stationary/seasonal input → refuse |
| 11 | **EWMA chart** with exact time-varying limits | "smooth this and tell me if it's out of control" · "detect a small sustained change in a noisy metric" · "is the recent average drifting from baseline?" | in-control μ, σ + series + λ (default 0.2) · **DATAFILE** | Plain moving averages with ad-hoc limits; comparing "last 5 mean" to "overall mean" with no variance accounting | **EASY.** zᵢ = λxᵢ+(1−λ)zᵢ₋₁; limits μ ± L·σ·√(λ/(2−λ)·(1−(1−λ)^{2i})) — the transient term matters for the first ~10 points and is usually omitted, causing early false alarms. L from Lucas–Saccucci tables or from #7 by simulation | Same baseline-estimation refusals as #10. λ chosen without stating the shift size it targets → force the pairing (λ≈0.05–0.1 for ≤0.5σ, 0.2–0.4 for ≥1σ). Using the steady-state limit on the first few points → must use the exact form or refuse to evaluate i<10 |
| 12 | **Shewhart individuals (I–MR) chart with honest Western Electric accounting** | "set control limits on this metric" · "which of these points are out of control?" · "should I turn on the extra sensitivity rules?" · "how many alerts will these rules generate?" | ≥20–25 in-control points · **DATAFILE** | Global mean ± 3·SD (biased when a shift is present); switching on all Western Electric rules without knowing the cost | **EASY.** σ̂ = MR̄/1.128 (d₂ for n=2); the four WE zone rules; combined ARL₀ by simulation (#7) | **The headline refusal**: if the agent asks for WE rules, the tool must print that ARL₀ falls **370 → 91.75** — a 4× increase in false alarms — and require acknowledgement. Autocorrelated data → refuse; MR̄/1.128 estimates σ√(1−ρ), so at ρ=0.5 limits are 29% too tight and real ARL₀ ≈ 29, not 370 (§3.2). Skewed data → refuse symmetric limits (§3.3). <20 baseline points → refuse to call limits "control limits" |
| 13 | **Two-sample Poisson rate comparison — exact conditional binomial test** | "3 errors today vs 1 yesterday — is that a real increase?" · "did the error rate go up after the deploy?" · "compare these two event counts over different time windows" | x₁ over t₁, x₂ over t₂ · **INLINE** | Percent change on counts; a chi-square test on a 2×2 with expected cells <5; a z-test on rates when counts are small | **EASY and exact.** Conditional on x₁+x₂=n, x₁ ~ Binomial(n, t₁/(t₁+t₂)); exact tail by `math.comb`. Fall back to the E-test only if exposures are equal and counts are large | x₁ = x₂ = 0 → refuse (no information). Exposures unknown or not truly comparable (different traffic, different sampling) → refuse. Overdispersion detected in either baseline → refuse. Counts from overlapping/nested windows → refuse |
| 14 | **Benjamini–Hochberg FDR across simultaneously monitored metrics** (plus Bonferroni for the page/no-page decision) | "I'm checking 40 metrics — how many of these alerts are real?" · "I ran 200 microbenchmarks and 8 regressed, is that just chance?" · "correct for the fact that I looked at everything" · "which of these anomalies survive multiple testing?" | a list of p-values (or the number of tests + a threshold) · **INLINE or DATAFILE** | Reporting every metric that crossed a threshold; the agent's blind spot that scanning 40 metrics hourly at α=0.0027 yields ~2.6 false alarms/day and ~10.5/day with WE rules on | **EASY.** Sort, compare p₍ₖ₎ ≤ kα/m, take the largest k. BY variant multiplies by the harmonic sum Σ1/i for arbitrary dependence | p-values from tests whose assumptions were already violated → refuse (garbage in). Fewer than ~5 tests → BH is pointless; use Bonferroni or nothing. Metrics are strongly positively correlated *and* the agent needs FWER not FDR → refuse BH and say so. p-values from discrete tests (small-count Poisson/binomial) are conservative and lumpy → warn that BH is anti-conservative-corrected in the wrong direction; prefer mid-p |
| 15 | **Multiple changepoints: PELT / exact Opt with a BIC–MDL penalty and a CROPS penalty path** | "find all the shifts in this history" · "segment this series into stable periods" · "how many times has this changed over the last year?" · "which commits moved the needle?" | series of ≥50 points · **DATAFILE** | Repeated ad-hoc eyeballing; binary segmentation alone (greedy, misses close-together changes); picking a number of segments by feel | **MODERATE.** Cost per segment = m·ln(RSS/m) (unknown σ) or RSS/σ² (known); dynamic program is O(n²) worst case, PELT pruning gives near-linear. Penalty β = p·ln(n) | The number of changepoints is violently sensitive to β → **refuse a single segmentation**; require the CROPS path and report the range of segment counts, or refuse if the count changes by >2× across β ∈ [1.5ln n, 4ln n]. Heteroscedastic series → refuse the constant-variance cost. n<50 → route to #6. Any segment shorter than the minimum segment length (default 5) → refuse |
| 16 | **Autocorrelation diagnostic + effective sample size** — lag-1 ρ̂, Ljung–Box, n_eff = n(1−ρ)/(1+ρ) | "are these observations independent?" · "why is my chart alarming constantly?" · "can I treat these samples as independent?" · "how much real information is in this series?" | series of ≥20 points · **DATAFILE** | Assuming independence — the single most common cause of monitoring false alarms and of over-confident CIs on time-ordered data | **EASY.** ACF via the standard biased estimator; Ljung–Box Q = n(n+2)Σρ̂ₖ²/(n−k) ~ χ²_h needs the regularized incomplete gamma | This tool should rarely refuse — it *is* the refusal gate for #6, #9, #10, #11, #12. It must refuse only when n<20 (ρ̂₁ is badly biased) or when the series has an obvious changepoint (which manufactures spurious autocorrelation — run #6 first and re-test on residuals) |
| 17 | **Runs tests for nonrandomness** — Wald–Wolfowitz runs above/below the median; longest-run test | "does this pattern look random or is there structure?" · "8 points in a row above average — is that meaningful?" · "are these failures clustered in time?" · "is my randomization actually random?" | binary or numeric series of ≥10 · **DATAFILE or INLINE** | Human/agent pattern-matching, which invents structure in random sequences and also *under*-counts genuine clustering | **EASY.** μ_R = 2n₊n₋/N + 1; σ²_R = (μ−1)(μ−2)/(N−1); normal approximation for n₊,n₋ ≥ 10, exact via `math.comb` below that | n₊ or n₋ < 5 → refuse the normal approximation; use the exact distribution or refuse entirely. Ties at the median → the tool must state its tie rule and refuse if >20% of points tie. Series has trend or seasonality → refuse (both guarantee "too few runs"; test the residuals instead) |
| 18 | **Hampel filter** — rolling median ± t·1.4826·rolling MAD | "flag the weird points in this time series" · "clean this series before I analyze it" · "which of these readings are bad data?" · "find local spikes in a series that has a trend" | series of ≥3·(2k+1) points + window half-width k (default 3–7) · **DATAFILE** | A global MAD z-score, which flags every point in a trending or seasonal series; naive spike removal by fixed threshold | **EASY.** Rolling median and MAD; O(n·w) is fine at agent scale | Rolling MAD = 0 inside a window (flat/quantized stretch) → refuse for that window rather than emitting ∞. Window larger than the feature you are trying to detect → the filter erases real shifts; refuse if the window spans a detected changepoint. Fewer than ~3 windows of data → refuse |
| 19 | **Poisson dispersion / overdispersion test** — D = Σ(xᵢ−x̄)²/x̄ ~ χ²_{n−1}; variance-to-mean ratio | "are my error counts even Poisson?" · "can I use a rate model here?" · "why does my count chart alarm all the time?" · "are these events independent or bursty?" | ≥10 count observations · **DATAFILE** | Assuming Poisson for anything counted. Real error/crash/alert counts are bursty and overdispersed; a Poisson chart on them over-alarms badly | **EASY.** Sum of squares + regularized incomplete gamma for the χ² tail | n<10 counts → refuse. Mean count < 1 → the χ² approximation to D is poor; refuse and use a parametric bootstrap instead. Zero-inflation (many exact zeros) is a distinct pathology from overdispersion — the tool must distinguish them or refuse to name a cause |
| 20 | **Seasonal-aware robust anomaly scoring** — per-period median/MAD profile (STL-lite), residual scored by #1 or #21 | "is this spike just the usual Monday morning peak?" · "account for time-of-day before flagging" · "is traffic actually down or is it just the weekend?" · "seasonal anomaly detection" | series with a known period + ≥3 complete periods · **DATAFILE** | Flat thresholds on seasonal data (which alarm every night and miss every daytime anomaly); comparing to "last week same time" (n=1) | **MODERATE.** Per-phase median and MAD; optional robust trend by repeated median filtering. Avoids Loess entirely | <3 complete periods → refuse (you cannot separate seasonal from anomalous with 2 cycles). Period not supplied and not inferable → refuse; do **not** guess a period from a periodogram at n<200. Multiple nested periods (daily × weekly) with <3 weeks of data → refuse. Any phase bucket with <3 observations → refuse for that phase |
| 21 | **Generalized ESD (Rosner) for up to r outliers** | "how many outliers are in this set?" · "find all the bad values, not just the worst one" · "are there several anomalies here or one?" · "test for outliers without knowing how many" | series of ≥15 + an upper bound r on outliers · **DATAFILE** | Grubbs' test and single-outlier tests, which suffer **masking**: two adjacent outliers hide each other. GESD tests iteratively with the correct sequential critical values | **MODERATE.** Rᵢ = max|xᵢ−x̄|/s; λᵢ = (n−i)t_{p,n−i−1}/√((n−i−1+t²)(n−i+1)) with p = 1−α/(2(n−i+1)); needs the t quantile ⇒ inverse regularized incomplete beta | Assumes approximate normality of the bulk — refuse on visibly skewed data (route to #1 on the log scale). n<15 → refuse. r > n/4 → refuse; GESD's critical values assume outliers are a small minority. Time-ordered data with structure → refuse (GESD is for exchangeable samples) |
| 22 | **Error-budget burn-rate alert calculator** (multiwindow, multi-burn-rate) + minimum-traffic gate | "should I page someone about this?" · "is this error rate worth waking someone up for?" · "convert my SLO into an alert threshold" · "how long until I've burned the month's budget?" | SLO target, window, current error rate, traffic rate · **INLINE** | Static error-rate thresholds; paging on any error; paging on a 5-minute window that contains 40 requests | **EASY.** Burn rate = observed_error_rate / (1−SLO); Google's recommended pairs: 14.4× over 1h/5m (page), 6× over 6h/30m (page), 1× over 3d/6h (ticket). The **minimum-traffic gate** is a binomial power calculation | Traffic in the short window too low to distinguish the burn-rate threshold from the SLO rate → **refuse to alert**; print the minimum request count needed. E.g. SLO 99.9%, 14.4× ⇒ threshold 1.44% — with 100 requests in 5 min, 2 errors reads as 2% and is pure noise. No SLO declared → refuse (there is no principled threshold without a target) |
| 23 | **Sequential rerun rule (SPRT / Wald boundaries) for flakiness adjudication** | "how many more times should I rerun before deciding?" · "stop rerunning when I'm confident" · "cheapest way to tell flaky from broken" · "adaptive retry budget" | p₀ (acceptable flake rate), p₁ (unacceptable), α, β · **INLINE**, then **MUST-CONSTRUCT** (drives reruns) | Fixed rerun counts (3, 5, 10) chosen by convention; SPRT typically needs ~40–60% fewer runs for the same error rates | **EASY.** Sᵢ = Sᵢ₋₁ + ln(L₁/L₀); stop when S ≤ ln(β/(1−α)) or S ≥ ln((1−β)/α). Bernoulli likelihoods are trivial | p₀ and p₁ not both supplied → refuse (SPRT is a test between two specified rates, not an estimator). No maximum-runs cap → refuse; unbounded SPRT can run forever near p₀<p<p₁, so require a truncation and report the truncated error rates. Reruns not independent → refuse (same as #5) |
| 24 | **Bayesian Online Changepoint Detection (BOCPD)** — run-length posterior with a Normal–Gamma conjugate predictive | "give me a probability that something just changed" · "online / streaming change detection" · "how long has the current regime been stable?" · "detect the change as it happens, not in hindsight" | streaming series + hazard rate 1/λ + weak prior · **DATAFILE** | Retrospective changepoint methods when the agent needs an online verdict; threshold rules that give no probability | **MODERATE.** Message-passing recursion over run lengths; Student-t posterior predictive via `math.lgamma`. O(n²) time/memory unpruned — acceptable to n≈2000 with run-length pruning at 10⁻⁴ | Hazard rate not supplied and not derivable from a prior expected regime length → refuse (results are highly hazard-sensitive). Non-Gaussian / heavy-tailed data → the conjugate model gives confidently wrong changepoints; refuse or require a robustified likelihood. n<30 → refuse; the prior dominates. Must never report a MAP run-length without the posterior mass on it |

---

## 3. Technical notes that should become tool internals

These are the specific results that make the above implementable in stdlib and that a naive
implementation would get wrong.

### 3.1 Siegmund's closed-form CUSUM ARL — threshold selection without a Markov chain

For a one-sided tabular CUSUM with reference value *k* and decision interval *h* (both in σ units),
with *b* = *h* + 1.166 and Δ = δ − *k* (δ = true shift in σ units):

```
ARL₁(δ) ≈ ( exp(−2Δb) + 2Δb − 1 ) / (2Δ²)      ,  and ARL = b² when Δ = 0
```

Two-sided: 1/ARL = 1/ARL⁺ + 1/ARL⁻.

Verified against Montgomery's standard table for *k*=0.5, *h*=4:

| shift δ (σ) | Siegmund | Montgomery Table 9.3 |
|---|---|---|
| 0.00 | 169.0 | 168 |
| 0.50 | 26.7 | 26.6 |
| 1.00 | 8.34 | 8.38 |
| 2.00 | 3.22 | 3.34 |

and for *k*=0.5, *h*=5: Siegmund ARL₀ = 469 vs. tabulated 465.

This is a two-line function. It means the module can *invert* the question — "give me h such that I
get one false alarm per 500 checks at k=0.5" — instead of hardcoding h=4. Golden tests should
assert against Montgomery's published table, not against a reimplementation.

By comparison, the Shewhart individuals chart has ARL(δ) = 1/(Φ(−3−δ) + 1 − Φ(3−δ)):
ARL(0) = 370, ARL(0.5σ) = 155, ARL(1σ) = 43.9, ARL(2σ) = 6.3. **CUSUM is ~5× faster at a 1σ shift
and ~6× faster at 0.5σ**, which is the entire reason CUSUM exists and the reason an agent watching
a slowly degrading metric should not be using a Shewhart rule.

EWMA has no comparable closed form (it needs the Brook–Evans Markov-chain solve, ~51 states and a
linear system). **Recommendation: use Monte Carlo (#7) as the general ARL engine.** It handles
EWMA, Western Electric combinations, and — crucially — can bootstrap from the agent's own historical
data, making the calibration distribution-free.

### 3.2 Autocorrelation destroys control limits, and does it invisibly

For an AR(1) process with lag-1 correlation ρ, the moving-range estimator behaves as:

- xₜ − xₜ₋₁ ~ N(0, 2σₓ²(1−ρ))
- E[MR]/d₂ = σₓ·√(1−ρ)

So at ρ = 0.5 the estimated σ is **0.707 σₓ**, the "3-sigma" limits sit at ±2.12 σₓ, the per-point
alarm probability is 3.4% instead of 0.27%, and the true ARL₀ is **≈ 29, not 370** — a 13-fold
increase in false alarms, from an assumption the agent never checked. Server-side metrics (latency,
queue depth, memory, CPU) are essentially always positively autocorrelated. This is the most
important refusal in the territory, and it belongs in #10, #11, #12 as a hard gate, not a footnote.

Related: run rules (WE rule 4, "8 in a row on one side") become near-useless under positive
autocorrelation, since consecutive points are correlated by construction.

### 3.3 Why 3-sigma on skewed data is wrong — with numbers

- **Exponential** (mean 1/λ): μ+3σ = 4/λ, and P(X > 4/λ) = e⁻⁴ = **1.83%** — 13.6× the nominal
  0.135% upper-tail rate. Meanwhile μ−3σ = −2/λ < 0, so the chart can *never* signal a decrease.
- **Lognormal** (σ_log = 0.5): upper-side false alarm rate ≈ **1.5%**, ~11× nominal; lower limit is
  again negative.
- **Poisson** (λ=1): μ+3σ = 4, and P(X ≥ 5) = 0.366% — 2.7× nominal, plus discreteness means the
  achievable α jumps in large steps and no threshold delivers the requested rate.

Fixes, in preference order: (a) analyse on the log scale for multiplicative/positive data; (b) use
empirical or bootstrap quantiles of the in-control distribution (#7); (c) use the correct
distribution's tail (#4 for counts); (d) use asymmetric limits fitted to the actual distribution.
Never symmetric ±3σ on a positive, right-skewed metric.

### 3.4 Western Electric rules: the arithmetic of alert fatigue

Individual ARL₀ values (approximate, independent-point calculation):

| Rule | Per-point alarm prob. | ARL₀ alone |
|---|---|---|
| 1: one point beyond 3σ | 0.0027 | 370 |
| 2: 2 of 3 beyond 2σ, same side | 0.0031 | 327 |
| 3: 4 of 5 beyond 1σ, same side | 0.0055 | 181 |
| 4: 8 in a row, same side | 0.0078 | 128 |

Naively summing the rates gives ARL₀ ≈ 52. The **true combined ARL₀ is 91.75**, because the rules
use overlapping windows and are strongly positively dependent. Two lessons: (i) turning on the
sensitizing rules takes you from one false alarm per 370 points to one per 92 — a **4× increase**;
(ii) **you cannot compute the combined rate analytically by addition** — this must be simulated,
which is the strongest single argument for shipping the Monte Carlo ARL engine (#7) as a
first-class tool rather than a convenience.

Scaled to an agent monitoring 40 metrics hourly: 40 × 24 × 0.0027 = **2.6 false alarms/day** with
rule 1 alone; **10.5/day** with all four rules. Without #14 (FDR) this is indistinguishable from a
broken system.

### 3.5 The benchmark-regression arithmetic an agent needs to see

Typical scenario: 3 runs before (mean 100 ms), 3 runs after (mean 105 ms), benchmark CV ≈ 4%.

- SE of the difference = σ·√(2/3) = 3.27%; t₀.₉₇₅,₄ = 2.776 ⇒ **95% CI on the difference ≈ ±9.1%**.
  The observed 5% is comfortably inside noise. The correct output is "cannot distinguish; your
  resolution is ±9%", not "5% regression".
- To detect Δ = 3% at σ = 4% with 90% power, α = 0.05: n = 2σ²(1.960+1.282)²/Δ² = **38 runs per
  arm**. At 80% power, 28 per arm. Not 3.
- Corollary the tool must print: *"with the runs you have, the smallest regression you could detect
  is X%"* — this MDE number is the single most behaviour-changing output in the territory.

Design guidance the tool should enforce or refuse over:

1. **Interleave A/B/A/B** rather than running all of A then all of B. Between-run drift (thermal,
   noisy-neighbour, cache state) is the dominant nuisance and interleaving converts it into a
   blocking factor you can remove with a paired analysis.
2. **Benchmark timings are right-skewed** (a long tail of slow runs, a hard floor at the noise-free
   time). The mean is a poor summary. Prefer the median with a bootstrap CI, or the
   Hodges–Lehmann shift estimator. The *minimum* is a low-variance but biased estimator of the
   noise-free time — defensible when noise is strictly additive and positive, indefensible when the
   change alters variance.
3. **Suite-wide multiplicity**: 200 microbenchmarks at α=0.05 yields ~10 spurious "regressions."
   Route through #14.
4. Never compare "the best of 5 before" to "the best of 5 after" — selection on the minimum makes
   the comparison depend on n in a way that fakes regressions when the run counts differ.

### 3.6 Rare events: the 0, 1, 2 problem, worked

Exact two-sided 95% Poisson (Garwood) intervals for the count itself:

| observed x | 95% CI for λ |
|---|---|
| 0 | [0, 3.689]  (one-sided 95% upper: **2.996**) |
| 1 | [0.0253, 5.572] |
| 2 | [0.242, 7.225] |
| 3 | [0.619, 8.767] |

So **"zero errors this hour" is compatible with a true rate of up to ~3/hour.** An agent that reads
zero as "healthy" is over-reading its data.

One-sided exact tests against an expected λ₀ = 0.2:

- x = 1: p = 1 − e⁻⁰·² = **0.181** — not significant. An agent's instinct ("we never see these,
  and we just saw one!") is wrong here.
- x = 2: p = 1 − e⁻⁰·²(1 + 0.2) = **0.0175** — significant.

That single threshold between 1 and 2 is exactly the kind of judgment call this module exists to
make, and it is a three-line computation.

**Rule of three:** with 0 events in n trials, the 95% upper bound on the rate is 3/n
(more precisely −ln(0.05)/n = 2.996/n). Extensions: 97% → 3.51/n, 99% → 4.61/n.

### 3.7 Flaky-test arithmetic

- **1 failure in 20 runs.** Exact Clopper–Pearson 95% CI on the true failure rate: **[0.13%,
  24.9%]**. You cannot distinguish a 1%-flaky test from a 25%-flaky test with 20 runs. Any tool
  that prints "5% flaky" from this data is lying.
- **Reruns needed to expose a flake with 95% confidence**, n ≥ ln(0.05)/ln(1−p):

  | true flake rate p | reruns needed |
  |---|---|
  | 10% | 29 |
  | 5% | 59 |
  | 1% | 299 |
  | 0.1% | 2,995 |

  This is why rerun-based flake detection is expensive and why "we reran it 3 times and it passed"
  is nearly worthless evidence: it only rules out flake rates above ~63%.
- **Three consecutive failures** under a 20%-flaky null has probability 0.008 — decent evidence of
  a genuine break rather than flakiness. One failure has probability 0.20 — no evidence at all.
  The asymmetry between "1 failure" and "3 consecutive failures" is enormous and agents do not
  feel it.
- **Before/after comparison** (passed 50/50 before, fails 3/3 now) → exact Fisher/binomial
  conditional test, p = 1/C(53,3)-ish ⇒ strongly significant. This is the right tool for "did my
  change break it", distinct from "is it flaky".

### 3.8 The max-statistic trap in changepoint detection

The single most common statistical error in "when did this change?" analysis: locate the split
point that maximises the two-sample t statistic, then report that t's p-value. Under H₀ the maximum
over n−1 candidate splits of the standardised difference converges to the supremum of a
standardised Brownian bridge, not to a t distribution. The naive p-value is anti-conservative by
roughly an order of magnitude at n = 100.

Correct stdlib fix: **permutation.** Shuffle the series 2,000 times, recompute the max statistic
each time, and take the rank of the observed value. Exact under exchangeability, distribution-free,
and ~10 lines. Under autocorrelation, exchangeability fails — switch to circular block permutation
with block length ≈ 2(1+ρ)/(1−ρ), or refuse.

---

## 4. Recent advances (≈ last 10 years)

**4.1 E-values and e-detectors for sequential change detection (2022–2024).**
Shin, Ramdas & Rinaldo build change detectors from sums of *e-processes* (generalisations of
nonnegative supermartingales) started at consecutive times, yielding "clean, nonasymptotic bounds
on the average run length" and near-optimal detection delay, for nonparametric composite classes
(sub-Gaussian, sub-exponential, bounded) with no independence assumption. This is the first
principled ARL control for nonparametric change detection. Practically relevant here because the
e-detector recursion is as cheap as CUSUM's and the ARL bound is a formula, not a table.
<https://arxiv.org/abs/2203.03532>

**4.2 Anytime-valid inference / confidence sequences (2017–2021).**
Howard, Ramdas, McAuliffe & Sekhon's time-uniform confidence sequences, and Johari et al.'s
always-valid p-values / mSPRT, solve the exact problem an agent creates for itself when it runs
benchmarks "until the result looks clear." A confidence sequence is valid at *every* stopping time,
so peeking is free. This is arguably the most under-exploited idea for the benchmark and flaky-test
tools: it lets the agent add runs adaptively without inflating error, at the cost of ~1.5–2× wider
intervals than a fixed-n CI.
<https://arxiv.org/abs/1810.08240> · <https://arxiv.org/abs/1512.04922>

**4.3 Conformal p-values for outlier detection with FDR control (Bates, Candès, Lei, Romano,
Sesia, Annals of Statistics 2023).** Turns any anomaly score into a calibrated p-value using a
held-out reference set, and shows the resulting p-values are positively dependent, which permits
exact (marginal) FDR control via BH. Directly applicable: an agent with a clean baseline window can
convert *any* ad-hoc score (including a MAD z) into something BH-correctable.
<https://arxiv.org/abs/2104.08279>

**4.4 Changepoint detection consolidated (Truong, Oudre, Vayatis, *Signal Processing* 2020).**
The standard modern taxonomy — cost function × search method × penalty — plus the `ruptures`
reference implementation. Confirms that binary segmentation, window sliding, bottom-up, and
PELT/Opt are the four search strategies worth implementing, and that BIC/MDL and ℓ₀ are the
practical penalties. <https://arxiv.org/abs/1801.00718>

Follow-on work worth citing: **nonparametric PELT** using an empirical-distribution cost (Haynes,
Fearnhead & Eckley 2017), which removes the Gaussian assumption; **CROPS** (same authors), which
computes the *entire* segmentation path across a penalty range for the cost of a few runs — the
right answer to "how many changepoints?"; and **robust changepoint detection under outliers**
(Fearnhead & Rigaill, JASA 2019), replacing squared loss with a biweight loss so a single spike
does not manufacture two changepoints.

**4.5 Changepoint detection in production performance CI (Daly et al., 2020).**
MongoDB replaced threshold-based performance regression detection with E-Divisive Means changepoint
detection over the commit history, and reported that it "dramatically dropped our false positive
rate for performance changes" while catching *smaller* regressions than thresholds could. This is
the strongest industrial validation that the benchmark-regression problem should be framed as
changepoint detection over history rather than as a two-sample test on the last two commits — an
important design signal for tool #2/#6. DataStax's open-source `hunter` and Chromium's perf
regression pipeline use the same framing. <https://arxiv.org/abs/2003.00584>

**4.6 Streaming thresholds from extreme value theory (Siffer et al., KDD 2017).**
SPOT/DSPOT fits a Generalised Pareto Distribution to peaks over a high threshold and sets the alarm
level from a *target risk q* rather than a sigma multiple, with a drift-adaptive variant. The idea
(threshold ← declared tail risk) is exactly right and is what tool #7 does; the GPD machinery
itself is cut for us (see §5) because agent-scale series yield too few exceedances for a stable fit.
DOI: 10.1145/3097983.3098144

**4.7 The evaluation reckoning in time-series anomaly detection (2021–2022).**
Two results that should shape the module's posture:
- Wu & Keogh, *Current Time Series Anomaly Detection Benchmarks are Flawed* (TKDE 2021): the
  standard benchmarks (including parts of Numenta's NAB and Yahoo's S5) suffer triviality,
  mislabeled ground truth, and run-to-failure bias — and **one-line algorithms match or beat deep
  learning** on them.
- Kim et al., *Towards a Rigorous Evaluation of Time-Series Anomaly Detection* (AAAI 2022): the
  widely used "point-adjust" scoring protocol is so lenient that **an untrained random-scoring
  detector achieves state-of-the-art F1** on the standard datasets. Most reported deep-learning
  gains in this field were an artifact of the metric.
- Schmidl, Wenig & Papenbrock (VLDB 2022) evaluated 71 detectors on 976 series and found classical
  and simple statistical methods highly competitive with, and far cheaper than, deep methods.

Together these are the empirical licence for a stdlib-only, classical-methods module: on
univariate series of a few thousand points, the sophisticated methods do not measurably win.

**4.8 Online / streaming FDR (Ramdas et al., 2017–2018: LORD, LORD++, SAFFRON).**
Alpha-investing procedures that control FDR over an *unbounded stream* of hypothesis tests. This is
precisely the monitoring situation — "I run this check every hour, forever" — and neither Bonferroni
nor batch BH is well-defined there. Underused and directly implementable in stdlib (it is a running
alpha-wealth ledger).
<https://arxiv.org/abs/1710.00499> (SAFFRON) · <https://arxiv.org/abs/1603.09000> (LORD)

**4.9 Spectral Residual anomaly detection (Ren et al., Microsoft, KDD 2019).**
The SR component — saliency detection borrowed from computer vision, applied to the log-amplitude
spectrum — is unsupervised, has one parameter, and was deployed at scale in Azure monitoring. The
SR half is FFT-based and implementable in stdlib for power-of-two lengths, though it is a
lower-priority addition than anything in the ranked table.

**4.10 SRE alerting practice: multiwindow, multi-burn-rate (Google SRE Workbook, 2018).**
The now-standard formalisation of "should I page": alert only when both a long and a short window
exceed a burn-rate multiple, with tabulated (1h/5m, 14.4×), (6h/30m, 6×), (3d/6h, 1×) triples
mapped to page/ticket severity, evaluated explicitly on precision, recall, detection time and reset
time. The statistical gap this leaves — that short windows at low traffic contain too few requests
for the observed rate to mean anything — is what tool #22's minimum-traffic gate fills.
<https://sre.google/workbook/alerting-on-slos/>

---

## 5. Cut list

| Rejected | Why |
|---|---|
| Isolation Forest, LOF, one-class SVM, Robust Random Cut Forest | Multivariate ML; need numpy-scale data and tuning; on univariate n≤2000 they do not beat a MAD z-score (see §4.7) |
| LSTM / autoencoder / transformer anomaly detectors | Impossible in stdlib, and §4.7 shows the reported gains were largely an evaluation artifact |
| Full STL with Loess | Loess is ~200 lines of local regression for marginal gain over a per-phase median profile (#20) at agent scale |
| Prophet-style decomposition | Heavy, opinionated priors, needs a fitting library, designed for long business series |
| Matrix profile discords (STAMP/STOMP/SCRIMP) | O(n²m) and requires a subsequence length the agent cannot choose; only pays off on long series with genuinely repeating structure |
| V-mask CUSUM | Obsolete visual construction; tabular CUSUM is strictly better and printable |
| Hotelling T², MEWMA (multivariate SPC) | Needs a matrix inverse and a clean multivariate in-control covariance estimate the agent almost never has |
| Shiryaev–Roberts procedure | Performance essentially indistinguishable from CUSUM for these use cases; adds concepts, adds no decisions |
| Page–Hinkley test | Mathematically a CUSUM restatement; redundant with #10 |
| Kalman filter / structural time-series level-shift detection | Implementable but requires process- and observation-noise variances the agent cannot supply; silently sensitive to them |
| GLR sequential detection with unknown shift magnitude | Marginal gain over adaptive CUSUM; much harder to explain and to calibrate |
| ADWIN (adaptive windowing) | Designed for bounded-memory streaming; at agent scale the whole series is in a file, so offline binary segmentation (#6) strictly dominates and gives a p-value |
| E-Divisive Means (energy distance) | O(n²) with a permutation loop inside a recursion; #6 + #15 cover the same ground far cheaper. Cited as prior art (§4.5), not shipped |
| SPOT / DSPOT (GPD peaks-over-threshold) | GPD MLE needs ~hundreds of exceedances for a stable shape parameter; at n≈200 you get ~20. The good idea (threshold ← target risk) is absorbed into #7 via bootstrap quantiles |
| Grubbs' test, Dixon's Q | Grubbs is dominated by GESD (#21) because of masking; Dixon's Q needs lookup tables and only works at tiny n |
| Tukey boxplot fence as a standalone model | Kept as an internal fallback inside #1 when MAD = 0; not worth its own entry |
| Conformal anomaly detection as a shipped tool | Needs a clean calibration split; at n<1000 it reproduces the ranking of a robust z-score. Cited (§4.3) as the right way to add FDR control later |
| Numenta HTM / NAB detectors | Not stdlib; benchmark itself is contested (§4.7) |
| Two-sample KS / Cramér–von Mises as a distribution-change detector | Belongs to the distribution-comparison territory; listed as a cross-territory dependency |
| Wavelet / spectral changepoint methods | Require transform machinery and parameter choices with no agent-facing meaning |
| Cook's distance / leverage-based outlier detection | Regression-diagnostics territory, not monitoring |
| Percent-change alerting ("up 20% week over week") | Not a model; it is the failure mode the territory exists to replace. Explicitly named as an anti-pattern in tool output |

---

## 6. Cross-territory overlaps

- **Hypothesis testing & p-values** — Welch's t, exact binomial/Fisher, permutation tests are shared
  machinery. Tools #2, #5, #6, #13 all call into it. The monitoring-specific addition is that a
  p-value is never the output; the output is a decision plus a false-alarm rate.
- **Bootstrap & resampling** — #2 (BCa on the median difference), #6 (permutation null), #7
  (bootstrap ARL calibration), #20. Probably the single most-reused primitive in this territory.
- **Effect size, power & sample size** — #3 is entirely a power calculation wearing a monitoring hat;
  #23 is a sequential version. Shared: `NormalDist.inv_cdf`, Cohen's d, MDE.
- **Multiple comparisons** — #14 is imported wholesale; online FDR (§4.8) is the monitoring-native
  extension that the multiple-comparisons territory may not cover.
- **Time series & forecasting** — autocorrelation (#16), seasonality (#20), stationarity. Residuals
  from a forecasting model are the natural input to #1/#12; monitoring should *consume* that
  territory's decomposition rather than re-implement it.
- **Robust statistics** — median, MAD, trimmed means, Hodges–Lehmann, biweight loss, breakdown
  points. #1, #18, #21, and the robust changepoint cost all depend on it.
- **Counts, rates & proportions** — Poisson and binomial exact intervals (#4, #5, #13, #19, #22)
  overlap heavily with any territory covering discrete data. Recommend a single shared exact-tail
  module.
- **Bayesian inference** — #24 (BOCPD), Jeffreys intervals in #5, and beta-binomial flake-rate
  pooling across a test suite (a natural hierarchical extension).
- **Decision theory / expected value** — choosing a threshold by ARL is implicitly choosing a
  cost ratio between false alarms and missed detections. A tool that accepts "a false page costs
  me 30 minutes, a missed outage costs 4 hours" and returns the threshold is the honest version of
  #7 and belongs to whichever territory owns loss functions.
- **Regression** — trend estimation (#9's Theil–Sen), and the fact that a fitted changepoint model
  is a segmented regression.

---

## 7. Sources

Verified during this pass:

- [Western Electric rules — Wikipedia](https://en.wikipedia.org/wiki/Western_Electric_rules) (rule
  definitions; combined ARL₀ = 91.75 vs. 370 for rule 1 alone)
- [Control chart — Wikipedia](https://en.wikipedia.org/wiki/Control_chart) (0.27% / ARL 370.4;
  Shewhart's Chebyshev and Vysochanskii–Petunin rationale; poor sensitivity to 1–2σ shifts)
- [CUSUM — Wikipedia](https://en.wikipedia.org/wiki/CUSUM) (Page 1954; ARL as the design criterion)
- [NIST/SEMATECH e-Handbook §6.3.2.3 — CUSUM charts](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc323.htm)
- [NIST/SEMATECH e-Handbook §6.3.2.4 — EWMA charts](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc324.htm)
  (EWMA recursion; s²_ewma = [λ/(2−λ)]s²; λ ∈ [0.2, 0.3]; refers to Lucas & Saccucci 1990 for L)
- [NIST/SEMATECH e-Handbook §1.3.5.17.3 — Generalized ESD test](https://www.itl.nist.gov/div898/handbook/eda/section3/eda35h3.htm)
  (Rᵢ and λᵢ formulas, worked 54-point example)
- [Minitab — CUSUM chart methods and formulas](https://support.minitab.com/en-us/minitab/help-and-how-to/quality-and-process-improvement/control-charts/how-to/time-weighted-charts/cusum-chart/methods-and-formulas/methods-and-formulas/)
  (defaults h = 4, k = 0.5; one-sided recursions)
- [Median absolute deviation — Wikipedia](https://en.wikipedia.org/wiki/Median_absolute_deviation)
  (1.4826 = 1/Φ⁻¹(3/4), derivation)
- [Rule of three (statistics) — Wikipedia](https://en.wikipedia.org/wiki/Rule_of_three_(statistics))
  (3/n derivation; 3.51 / 4.61 / 5.3 for 97% / 99% / 99.5%)
- [Binomial proportion confidence interval — Wikipedia](https://en.wikipedia.org/wiki/Binomial_proportion_confidence_interval)
  (Wilson, Jeffreys Beta(x+½, n−x+½), Agresti–Coull; Wald's zero-width failure at p̂ = 0)
- [Poisson distribution — Wikipedia](https://en.wikipedia.org/wiki/Poisson_distribution)
  (variance-stabilising √ transforms; Poisson races)
- [StatsDirect — exact (Garwood) Poisson rate CI](https://www.statsdirect.com/help/rates/poisson_rate_ci.htm)
- [Wald–Wolfowitz runs test — Wikipedia](https://en.wikipedia.org/wiki/Wald%E2%80%93Wolfowitz_runs_test)
  (μ_R, σ²_R, normal approximation, small-n exact caveat)
- [False discovery rate — Wikipedia](https://en.wikipedia.org/wiki/False_discovery_rate)
  (BH step-up; BY harmonic-sum correction; FDR vs FWER)
- [Sequential probability ratio test — Wikipedia](https://en.wikipedia.org/wiki/Sequential_probability_ratio_test)
  (log-LR recursion; a = ln(β/(1−α)), b = ln((1−β)/α))
- [SAS — The Hampel filter for robust outlier detection](https://blogs.sas.com/content/iml/2021/06/01/hampel-filter-robust-outliers.html)
  (rolling median ± h·1.4826·MAD, h = 3, window 7)
- [twitter/AnomalyDetection — Seasonal Hybrid ESD](https://github.com/twitter/AnomalyDetection)
  (decomposition + GESD with median/MAD; `max_anoms`; piecewise trend)
- [Google SRE Workbook — Alerting on SLOs](https://sre.google/workbook/alerting-on-slos/)
  (burn rate; precision/recall/detection/reset; 14.4×–1h/5m, 6×–6h/30m, 1×–3d/6h)
- [Adams & MacKay — Bayesian Online Changepoint Detection](https://arxiv.org/abs/0710.3742)
- [Killick, Fearnhead & Eckley — Optimal detection of changepoints with a linear computational cost (PELT)](https://arxiv.org/abs/1101.1438)
  (JASA 2012, 107:1590–1598)
- [Truong, Oudre & Vayatis — Selective review of offline change point detection methods](https://arxiv.org/abs/1801.00718)
  (*Signal Processing* 2020; `ruptures`)
- [Shin, Ramdas & Rinaldo — E-detectors: a nonparametric framework for sequential change detection](https://arxiv.org/abs/2203.03532)
- [Bates, Candès, Lei, Romano & Sesia — Testing for outliers with conformal p-values](https://arxiv.org/abs/2104.08279)
  (*Annals of Statistics* 2023)
- [Daly, Brown, Ingo, O'Leary & Bradford — The Use of Change Point Detection to Identify Software Performance Regressions in a CI System](https://arxiv.org/abs/2003.00584)
  (E-Divisive Means; "dramatically dropped our false positive rate")
- [UCR Matrix Profile page](https://www.cs.ucr.edu/~eamonn/MatrixProfile.html) (discords; STAMP /
  STOMP / SCRIMP++; parameter-free except subsequence length)

Cited from the literature, not re-fetched in this pass:

- Montgomery, *Introduction to Statistical Quality Control* — Table 9.3 (CUSUM ARLs, k=0.5) is the
  golden-test oracle for §3.1; Brook & Evans (1972) Markov-chain ARL method for EWMA.
- Siegmund, *Sequential Analysis* (1985) — the closed-form CUSUM ARL approximation in §3.1.
- Lucas & Saccucci (1990), *Technometrics* 32:1–12 — EWMA ARL tables and (λ, L) pairs.
- Iglewicz & Hoaglin (1993), *How to Detect and Handle Outliers* — modified z-score, 0.6745
  constant, 3.5 threshold.
- Hamed & Rao (1998), *J. Hydrology* — autocorrelation-corrected Mann–Kendall variance.
- Georges, Buytaert & Eeckhout (2007), *Statistically Rigorous Java Performance Evaluation*,
  OOPSLA — the canonical statement that best-of-n and mean-of-few are invalid, and that comparisons
  need a CI on the *difference*, not overlapping CIs. <https://dri.es/files/oopsla07-georges.pdf>
- Luo, Hariri, Eloussi & Marinov (2014), *An Empirical Analysis of Flaky Tests*, FSE — flakiness
  taxonomy (async wait, concurrency, test-order dependency, resource leaks).
- Haynes, Fearnhead & Eckley (2017) — CROPS penalty path; nonparametric PELT.
- Fearnhead & Rigaill (2019), *JASA* — changepoint detection in the presence of outliers (biweight
  loss).
- Siffer, Fouque, Termier & Largouët (2017), *Anomaly Detection in Streams with Extreme Value
  Theory*, KDD — DOI 10.1145/3097983.3098144.
- Ren et al. (2019), *Time-Series Anomaly Detection Service at Microsoft*, KDD — Spectral Residual.
- Wu & Keogh (2021), *Current Time Series Anomaly Detection Benchmarks are Flawed*, IEEE TKDE.
- Kim, Choi, Choi, Lee & Yoon (2022), *Towards a Rigorous Evaluation of Time-Series Anomaly
  Detection*, AAAI — the point-adjust protocol makes a random detector look state-of-the-art.
- Schmidl, Wenig & Papenbrock (2022), *Anomaly Detection in Time Series: A Comprehensive
  Evaluation*, VLDB 15(9) — 71 algorithms, 976 series.
- Johari, Koomen, Pekelis & Walsh (2017/2022) — always-valid inference / mSPRT.
- Howard, Ramdas, McAuliffe & Sekhon (2021) — time-uniform confidence sequences.
- Ramdas, Zrnic, Wainwright & Jordan (2017/2018) — LORD++, SAFFRON online FDR.
