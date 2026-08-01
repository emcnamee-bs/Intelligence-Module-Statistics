# Territory 04 — Robust and Nonparametric Methods

**Scope:** bootstrap, permutation/randomization, exact tests, rank methods and their effect sizes,
robust location/scale, M-estimators, robust regression, outlier identification, heavy-tail
diagnostics, distribution-free tolerance/prediction intervals, conformal prediction.

**Status:** research complete. All feasibility and timing claims in this document were verified by
running pure-stdlib Python 3 on the target machine (see §6.1 for the measurement harness). Numbers
quoted as "verified" are measured, not estimated.

---

## 1. Territory summary

This is the territory that matches the agent's actual situation more often than any other: a handful
of numbers, no distributional warrant, and a decision that has to be made anyway. Its central asset
is that **exact, finite-sample-valid answers exist at n = 5** — permutation tests, order-statistic
intervals, the sign test and conformal prediction all have coverage guarantees that hold at any n
and under no distributional assumption whatsoever, whereas the bootstrap (the folk remedy for small
samples) is an asymptotic method that measurably fails there. The single highest-value thing this
territory can give an agent is not a better p-value but a **resolution guard**: at n₁=n₂=3 the
smallest attainable two-sided p is 0.10, so "the difference is significant" is arithmetically
impossible, and an agent that does not know this will say it anyway. Second highest is the shift
from "is it real" to "how big and in which direction" — Cliff's δ, the common-language effect size,
and the Hodges–Lehmann shift with an exact interval are all computable at n=5 and all beat a bare
p-value for decision-making. Everything in this territory is cheap in pure Python: exact permutation
enumeration to N=26, exact rank-test null distributions to n=100 by dynamic programming, Theil–Sen
at n=2000, and 10 000 bootstrap replicates on n=1000 all run in under half a second.

---

## 2. Ranked model table

Ranked by (frequency of the situation) × (margin over the agent's unaided guess) × (honesty at
n = 3–15). Tier legend: **INLINE** = a few numbers as CLI flags; **DATAFILE** = a small dataset in a
file; **MUST-CONSTRUCT** = the agent has to go collect/generate data first.

| # | Model / method | SITUATION (retrieval phrasings) | Minimum viable inputs + tier | Beats what | Stdlib feasibility + numerics | REFUSE conditions (do not print a number) |
|---|---|---|---|---|---|---|
| 1 | **Exact-resolution guard** — minimum attainable p for the design, and n required to reach a target α | "can I conclude anything with this little data" · "is p<0.05 even reachable here" · "how many runs do I need before a difference could be significant" · "I only have 4 measurements per arm" | `n1`, `n2`, design (2-sample / paired / one-sample), α, sidedness. **INLINE** | The #1 observed agent failure: asserting significance in a design whose sample space cannot produce it. Beats every p-value tool by running *before* them | **EASY.** `math.comb` only. 2-sample: p_min = 2/C(n₁+n₂,n₁). Paired/sign: p_min = 2·2⁻ⁿ. Correlation: 2/n! | Never refuses — this *is* the refusal engine. Other tools call it as a precondition |
| 2 | **Two-sample permutation test, studentized** (Welch-type statistic permuted) | "is this difference real or just noise" · "A looks faster than B but I ran each 6 times" · "did my change actually improve anything" · "these two groups look different, are they" | Two lists of numbers. **INLINE** (n≤10/group) or **DATAFILE** | The agent's eyeball on two means; the t-test on skewed/outlier-laden data; any "12% faster" claim with no error bar | **EASY.** Exact by `itertools.combinations` when C(N,n₁) ≤ ~2×10⁶ (verified: C(24,12)=2.7M in 0.51 s; C(26,13)=10.4M in 2.1 s). Else Monte Carlo via `random.shuffle`, B=10⁴–10⁵. p = (1 + #{T*≥T})/(B+1), **never** #/B | Data are time-ordered with drift or autocorrelation (exchangeability dead — see #23); p_min from #1 exceeds α; **un-studentized statistic with visibly unequal spread** (Chung–Romano: the raw difference-in-means permutation test is not asymptotically level-α under unequal variances); >50% ties |
| 3 | **Mann–Whitney/WMW exact test + Hodges–Lehmann shift + exact CI** (single bundled call) | "is group A systematically higher than group B" · "compare two small samples without assuming normality" · "how much higher, in real units, and how sure" | Two lists. **INLINE**/**DATAFILE** | The t-test under non-normality (ARE ≥ 0.864 always, 0.955 under normality, >1 for heavy tails); a p-value alone — HL gives the shift **in original units** with a distribution-free interval | **EASY.** Exact null by 3-D DP over (i, j, U): verified m=n=30 in 0.027 s, m=n=10 instant. HL shift = median of all n₁n₂ pairwise differences; CI = the k-th and (n₁n₂+1−k)-th ordered differences where k comes from the exact null. Ties → fall back to permutation MC | Ties present *and* using the untied exact null (use the permutation MC branch); groups differ in spread but you want a *location* claim (WMW tests stochastic dominance, not medians — route to #9 Brunner–Munzel); p_min > α |
| 4 | **Cliff's δ, common-language effect size (Vargha–Delaney A), rank-biserial r** with CI | "how big is the difference, not just whether it exists" · "what's the chance a random A beats a random B" · "give me a magnitude I can act on" · "is this effect worth the engineering cost" | Two lists. **INLINE**/**DATAFILE** | Reporting p with no magnitude; Cohen's d on non-normal data; the agent's verbal "much better". δ = 2A − 1; A = P(X>Y) + ½P(X=Y) is directly decision-usable | **EASY.** δ = (#{x>y} − #{x<y})/(n₁n₂), O(n₁n₂) direct count. CI: Cliff's (1993) consistent variance estimator with the inverse-hyperbolic-tangent transform, or BCa bootstrap of δ. `NormalDist` suffices | At n₁=n₂=3, δ lives on a 19-point lattice with step 1/9 and its CI is [−1, 1] unless the samples are perfectly separated — **print δ, refuse the CI** below n₁n₂ ≈ 20. Refuse entirely if either group is empty or all values are tied |
| 5 | **Distribution-free CI for a median / any quantile from order statistics** | "what's the uncertainty on this median" · "give me an interval for the typical value without assuming a distribution" · "confidence interval for the 90th percentile latency" | One list, quantile q, confidence. **INLINE** | The normal-approximation median CI (1.253σ/√n) which needs n ≫ 30; the bootstrap of the median, which is degenerate at small n (see #12) | **EASY.** Coverage of (x₍ₖ₎, x₍ₛ₎) = P(k ≤ Bin(n,q) ≤ s−1). Exact, closed form, `math.comb` only. Verified: 95% median CI first becomes attainable at **n = 6** (= [min,max], coverage 0.9688); n=5 maxes out at 0.9375 | n < 6 for a 95% median CI — the interval **does not exist**, report the attainable level (e.g. 0.875 at n=4) instead of a fake 95%. For extreme quantiles, refuse when the required order statistic index exceeds n (e.g. no distribution-free upper 95% bound on the 99th percentile below n=299) |
| 6 | **Order-statistic prediction interval for one new observation** — [min, max] covers the next draw with prob (n−1)/(n+1) | "what range should the next measurement fall in" · "is this new value surprising given what I've seen" · "give me a sanity band for the next run" | One list. **INLINE** | The agent's "±2 standard deviations", which is a normality claim; also beats a CI, which the agent routinely misreads as a prediction interval | **EASY.** Sorting only. Exactly equals full conformal prediction with the absolute-residual score. Verified: coverage (n−1)/(n+1) → **n=19 for 90%, n=39 for 95%** | n < 19 if 90% is demanded: report honestly that [min,max] gives only (n−1)/(n+1) (n=6 → **71.4%**) and that no distribution-free 90% interval exists at this n. Refuse if data are ordered/trending |
| 7 | **Wilcoxon signed-rank exact test + Hodges–Lehmann (Walsh averages) + exact CI** | "did the before/after change do anything" · "paired measurements, same machine, two configs" · "each item measured twice, is there a shift" | Paired list of differences. **INLINE**/**DATAFILE** | The paired t-test on skewed differences; the sign test (signed-rank is far more powerful when symmetry holds) | **EASY.** Exact null by subset-sum DP over ranks 1..n — verified **n=100 in 0.010 s**. HL = median of the n(n+1)/2 Walsh averages (dᵢ+dⱼ)/2, i≤j — verified n=2000 in 0.30 s. CI endpoints = ordered Walsh averages at index k / M+1−k | n ≤ 5 (min two-sided p = 0.0625 at n=5, verified); **differences are visibly asymmetric** — signed-rank assumes symmetry of the difference distribution, route to the sign test #8; more than ~⅓ zero differences |
| 8 | **Sign test / exact binomial test** | "did it get better more often than not" · "8 of 10 runs improved, is that meaningful" · "I only have direction, not magnitude" · "test a proportion against a threshold" | Count of successes and trials, or a paired list. **INLINE** | Every method above when the data are ordinal, censored, or wildly heteroscedastic. Assumes only independence and P(tie)=0. The floor everything else stands on | **EASY.** `math.comb` and a sum. Two-sided by doubling the smaller tail (document the convention; the alternative is the minimum-likelihood method). Clopper–Pearson interval by inverting the binomial | n ≤ 5: min two-sided p = 0.0625 (verified) — cannot reach α=0.05. Ties/zeros: refuse to silently drop them; report how many were dropped and recompute n |
| 9 | **Brunner–Munzel test (permutation version for n<10) + P(X>Y) with CI** | "compare two groups that have different spread as well as different centre" · "nonparametric Welch" · "Mann-Whitney but the variances clearly differ" | Two lists. **DATAFILE** | Mann–Whitney, whose type-I error inflates badly under unequal variances even at large n (Karch 2021 argues BM should be the *default* nonparametric two-sample test). Tests stochastic equality P(X<Y)=P(Y<X) directly | **MODERATE.** Within-group and pooled ranks; Satterthwaite df; needs a Student-t CDF (regularized incomplete beta — already in the module's distribution layer per Part 0.7). For n < 10 use the studentized-permutation variant instead of the t-approximation | Either group's rank-variance estimate is 0 (complete separation, or all values tied within a group) — the statistic is undefined, **hard refuse**; n < 10 with the t-approximation (known liberal) — must switch to permutation |
| 10 | **Bootstrap-t (studentized bootstrap) CI for the mean** | "confidence interval for an average of skewed data" · "my data has a long right tail, what's the interval on the mean" · "CI without assuming normality" | One list (n ≥ ~15). **DATAFILE** | The t-interval on skewed data, and — decisively — the other bootstraps. **Measured coverage at nominal 95%, lognormal(0,1):** n=6 percentile 0.731 / BCa 0.753 / **boot-t 0.889**; n=10 → 0.800 / 0.828 / **0.905**; exponential n=10 → 0.869 / 0.883 / **0.953** | **EASY.** `random.choices` + `statistics.stdev`. Verified 10⁴ replicates on n=1000 in 0.42 s; on n=10, 0.006 s. Requires a per-resample SE, so it exists only for statistics with one | Statistic has no natural SE (median, quantiles, ratios) — refuse and route to #5; any resample has zero variance (all-equal resample) — this is common at n≤8 and must be handled, not divided by; **width warning**: boot-t buys coverage with length (n=6 lognormal mean width 8.32 vs percentile 2.15) — print the width ratio so the agent sees the price |
| 11 | **BCa bootstrap CI** (bias-correction + jackknife acceleration) | "bootstrap confidence interval done properly" · "CI for a statistic I can compute but can't write a formula for" · "correlation / ratio / trimmed mean interval" | One list or paired lists, plus a statistic name. **DATAFILE** | The percentile bootstrap (second-order accurate vs first-order); the plain t-interval for non-mean statistics | **MODERATE.** Needs z₀ = Φ⁻¹(#{θ*<θ̂}/B) and a = Σ(θ̄₍·₎−θ₍ᵢ₎)³ / 6(Σ(θ̄₍·₎−θ₍ᵢ₎)²)^{3/2} from the jackknife. `statistics.NormalDist.inv_cdf`/`cdf` cover the normal parts. Jackknife on n=1000 is instant | **B too small relative to the adjusted quantile**: BCa needs B ≫ 1/min(α,1−α); measured 2–3% of runs at n=20–40 push the adjusted quantile off the empirical grid — refuse rather than clamp. Jackknife denominator = 0 (all values identical). **n < 20**: measured coverage 0.75–0.88 — print the measured-coverage caveat or refuse. Lattice/discrete statistics |
| 12 | **Bootstrap validity gate** — decides *whether* to bootstrap at all, and which flavour | (called by #10/#11, and directly) "should I bootstrap this" · "will the bootstrap work on my data" | Statistic type, n, the data. **DATAFILE** | The universal agent assumption that "bootstrap = works on small samples". It is an **asymptotic** method and it is provably inconsistent for several everyday statistics | **EASY.** A rules table + cheap diagnostics. Hard-inconsistency list: sample **max/min** and any extreme quantile; the **mean under infinite variance** (bootstrap limit law is itself random); **tail-index** estimators; parameters on a boundary; **statistics that are non-smooth functionals** | Refuse-to-bootstrap when: statistic is an extremum or an extreme quantile; heavy-tail panel (#20) suggests α<2; n < 20 for any interval; **median/quantile at small odd n** — verified the bootstrap median takes exactly **n distinct values** at n=5,7,9 (5, 7, 9 values out of 20 000 resamples), so its "distribution" is 5 atoms and any quantile of it is meaningless. Route to #5 |
| 13 | **Split / full conformal prediction interval** | "prediction interval for the next value from my model" · "how wrong is my forecast likely to be" · "distribution-free uncertainty on a prediction" · "calibrate my model's error bars" | Calibration residuals (**DATAFILE**), or model + data (**MUST-CONSTRUCT**) | Every model-based prediction interval, all of which assume the model is right. Conformal's marginal coverage ≥ 1−α holds in **finite samples** under exchangeability alone, for **any** underlying predictor | **EASY** (split) / **MODERATE** (full). Split: sort |residual| scores, take the ⌈(n+1)(1−α)⌉/n empirical quantile. Guarantee is two-sided: 1−α ≤ coverage ≤ 1−α+1/(n+1) | **Hard arithmetic floor:** a finite interval requires n ≥ (1−α)/α — verified **n=9 for 90%, n=19 for 95%, n=99 for 99%**. Below that the conformal interval is (−∞, ∞) and the tool must say so, not shrink it. Also refuse if calibration data are not exchangeable with the test point (drift, ordering, distribution shift) |
| 14 | **Trimmed mean / Winsorized mean + Yuen–Welch comparison (permutation null at small n)** | "average with the outliers not wrecking it" · "typical value of a noisy benchmark" · "compare two groups where each has one crazy measurement" | One or two lists, trim fraction (default 0.20). **INLINE**/**DATAFILE** | The mean (breakdown 0) and the median (breakdown 0.5 but ~64% Gaussian efficiency). 20% trimming: breakdown 0.2, ~96% Gaussian efficiency, and far better type-I control than F/t under heavy tails | **EASY.** g = ⌊γn⌋; trimmed mean over x₍g+1₎..x₍n−g₎; Winsorized variance rescaled by (n−1)/(h−1) with h=n−2g; Yuen df by Welch–Satterthwaite (needs t CDF) or replace with a permutation null | **n ≤ 4 with γ=0.20: g=⌊0.8⌋=0, the "trimmed mean" silently equals the mean** — refuse or auto-report that no trimming occurred. At n=5, g=1 leaves 3 points; report h. Refuse Yuen's t-approximation at n<10 (use permutation) |
| 15 | **Robust scale: MAD, Sₙ, Qₙ with finite-sample bias correction** | "how spread out is this really, ignoring the outlier" · "robust standard deviation" · "the SD is inflated by one bad point" | One list. **INLINE**/**DATAFILE** | The sample SD, which one outlier can move without limit. All three have 50% breakdown; Gaussian efficiency **MAD 37%, Sₙ 58%, Qₙ 82%** | **MODERATE.** MAD = 1.4826·med|xᵢ−med(x)| (trivial). Sₙ = cₙ·1.1926·medᵢ medⱼ |xᵢ−xⱼ|, O(n²) naive — fine to n=2000. Qₙ = dₙ·2.2219·{|xᵢ−xⱼ|}₍ₖ₎ with k=C(h,2), h=⌊n/2⌋+1. **Must ship Akinshin (2022) finite-sample factors** (separate odd/even tables to n=100 + prediction equations); Rousseeuw–Croux's originals are rough approximations | **MAD = 0** whenever more than half the values tie at the median — verified this fires on ordinary discrete data like `[10,10,10,11,10,40]`. Every downstream z-score then divides by zero. **Hard refuse**, route to Qₙ (which survives some ties) or to an IQR-based scale. n < 5: all three are noise |
| 16 | **Outlier identification done properly: Hampel identifier + skew-adjusted boxplot (medcouple)** | "is this one weird point an outlier" · "should I drop this measurement" · "my data has a spike, is it real" · "clean this dataset" | One list. **INLINE**/**DATAFILE** | The 3σ rule (masking: outliers inflate the SD that is supposed to detect them) and the plain Tukey boxplot (flags ~⅓ of a right-skewed sample as outliers by construction) | **MODERATE.** Hampel: |xᵢ−med|/(1.4826·MAD) > 3. Adjusted boxplot (Hubert–Vandervieren 2008): fences [Q1 − 1.5e^{−4MC}·IQR, Q3 + 1.5e^{3MC}·IQR] for MC≥0. Medcouple naive O(n²) is fine at agent scale | **MAD = 0** (see #15). **n < 10: refuse to label anything an outlier.** With n=6, one point is 17% of the data; the Hampel identifier at n=5–8 has neither the breakdown headroom nor the resolution to distinguish "outlier" from "this distribution has a tail". Report the value's rank and its distance in MAD units, and *decline the label*. Never auto-delete |
| 17 | **Theil–Sen slope + distribution-free CI (Kendall-based) + median intercept** | "is there a trend in this series" · "fit a line that outliers can't drag" · "slope estimate I can trust with 12 noisy points" · "is this metric drifting up" | Paired (x,y) lists. **DATAFILE** | OLS (breakdown 0 — one leverage point owns the fit). Theil–Sen breakdown **29.3%**, and ~91% of OLS efficiency under normal errors | **EASY.** Median of C(n,2) pairwise slopes — verified **n=2000 (2.0M pairs) in 0.33 s**. CI: rank interval from Kendall's S, Cᵅ = z√Var(S), take ordered slopes at ranks (N−Cᵅ)/2 and (N+Cᵅ)/2. For n<10 replace the normal approximation with the **exact Kendall null via the Mahonian (inversion-count) DP** — verified n=60 in 0.043 s | n < 5 (the slope CI degenerates to the full range); duplicated x values dominating (zero denominators — count and report how many pairs were dropped); **serially correlated residuals** — the Kendall variance formula assumes independence; refuse or hand back the exchangeability verdict from #23 |
| 18 | **Fisher's exact test and Boschloo's unconditional exact test (2×2)** | "did the failure rate change" · "3 of 8 vs 7 of 9, is that real" · "compare two success rates with tiny counts" · "A/B test with almost no conversions" | Four counts. **INLINE** | The χ² test (invalid at small expected counts) and the normal two-proportion z-test. **Boschloo is uniformly more powerful than Fisher** — Fisher conditions on both margins and is consequently conservative | **MODERATE.** Fisher: hypergeometric via `math.comb`, trivial. Boschloo: use Fisher's p as the statistic in an unconditional test, maximizing the tail probability over the nuisance π on a grid. Verified: 1000-point grid over a 21×21 table in **0.010 s** — negligible. Barnard (Z-statistic version) is the same machinery | Any margin equal to 0 (no information in the table). Total n < 5 (report p_min from #1 first). Grid too coarse near the maximizing π — use ≥1000 points and report the maximizing π so the agent can see if it is at a boundary |
| 19 | **Kruskal–Wallis permutation test + ε² (and Dunn/Conover post-hoc with a permutation max-T correction)** | "are these three or four groups different" · "compare several configurations at once" · "which of my 5 variants is actually different" | k lists. **DATAFILE** | One-way ANOVA under non-normality; and the agent's habit of running 6 pairwise tests without correction | **EASY–MODERATE.** H statistic from ranks; Monte-Carlo permutation null (10⁵ shuffles on n=100 is well under a second). ε² = H/((n²−1)/(n+1)); η²_H = (H−k+1)/(n−k). Post-hoc: permutation max-T is exact-ish and strictly better than Bonferroni here | Any group with n<3; total N below the resolution floor from #1 (k=3 with 3 each → 1680 distinct arrangements, p_min=6×10⁻⁴, so this one is usually fine); ties >50%. **Refuse the omnibus-only answer** — an agent given only "H is significant" will invent which pair differs |
| 20 | **Heavy-tail / moment-existence diagnostic panel** | "does this data have crazy outliers or is it just heavy-tailed" · "can I trust a mean here at all" · "my average keeps moving as I add data" · "is the variance even finite" | One list. **DATAFILE** | The agent's use of **sample kurtosis**, which is *mathematically incapable* of the job at small n: b₂ = m₄/m₂² is bounded above by ≈ n−1. Verified: at n=10 the maximum possible b₂ ≈ 8.1, so a Cauchy sample (measured max 8.11 over 2000 draws) cannot look more extreme than a normal one (measured max 6.57). Overlapping distributions, no discriminating power | **EASY.** Panel of: (a) **max\|x\|/Σ\|x\|** — verified median 0.234 (normal) vs 0.409 (Cauchy) at n=10, and 0.018 vs 0.231 at n=200, so it separates where kurtosis cannot; (b) running-mean instability (does the mean jump at each new record?); (c) MAD/SD ratio; (d) Hill estimator **only if n ≥ 200** | **Refuse the Hill estimator below n≈200** — it needs k≈30–50 upper order statistics to mean anything and is severely biased below n=1000. **Refuse to report sample kurtosis as evidence at n<50** and say why. Below n≈20 the whole panel is suggestive only: report it as a flag that changes *which method to use*, never as a distributional conclusion |
| 21 | **Huber M-estimator of location (with MAD scale) — and Huber-loss regression by IRLS** | "average that's resistant but not as wasteful as the median" · "downweight the bad points instead of deleting them" · "robust fit without throwing data away" | One list (or x,y). **DATAFILE** | The trimmed mean when you want continuity (Huber's ψ is continuous, so the estimate does not jump when a point crosses a trim boundary) and ~95% Gaussian efficiency at c=1.345 | **EASY.** Iteratively reweighted mean: μₜ₊₁ = Σwᵢxᵢ/Σwᵢ with wᵢ = min(1, c·s/\|xᵢ−μₜ\|), s from MAD; converges in <20 iterations. Regression version is the same loop on residuals | s = 0 (MAD degeneracy, #15) — hard refuse. Non-convergence (oscillation) after N iterations — report the oscillation, do not return the last iterate. **Breakdown is 0 in the regression case** unless the scale is estimated robustly *and* leverage is bounded — do not sell Huber regression as outlier-proof in x |
| 22 | **HulC — confidence region from the convex hull of subsample estimates** | "confidence interval for something the bootstrap can't handle" · "interval for a weird estimator" · "the bootstrap gave a nonsense interval" | One list + any estimator. **DATAFILE** | The bootstrap, in exactly the cases where the bootstrap is inconsistent (extrema, boundary parameters, cube-root-rate estimators) — HulC needs neither a variance estimate nor knowledge of the convergence rate | **EASY.** Split the data into B disjoint batches, compute the estimator on each, return (min, max). For a median-unbiased estimator, non-coverage = 2^{1−B}, so **B = ⌈1 + log₂(1/α)⌉ = 6 for α=0.05** (coverage 0.969). Six estimator evaluations. That is the entire algorithm | Estimator is **not median-unbiased** — HulC's only real assumption, and the one that bites (use the Adaptive-HulC subsampling bias estimate, or refuse). **n < 6·(minimum n for the estimator)**: at n=6 with B=6 each batch has one point and the "interval" is just [min, max]. Refuse below n ≈ 30 for anything more complex than a mean |
| 23 | **Exchangeability / independence gate** — runs test + lag-1 rank autocorrelation + trend test | (precondition for #2, #3, #6, #7, #13, #17) "is my data ordered or drifting" · "are these measurements independent" · "did the machine warm up during the benchmark" | One list, in collection order. **DATAFILE** (order must be preserved) | The silent, universal, invisible failure of this entire territory. Permutation tests, conformal prediction and order-statistic intervals **all** assume exchangeability, and an agent's typical data (successive benchmark runs, log latencies, CI timings) routinely violates it | **EASY.** Wald–Wolfowitz runs test above/below the median (exact null by `math.comb`); lag-1 Spearman with an exact permutation null; Mann–Kendall trend test reusing the Mahonian DP from #17 | Order information not available (the agent pasted a set, not a sequence) — say loudly that exchangeability is **assumed and unverifiable**, do not certify it. n < 8: the runs test cannot detect anything; report "untestable", not "no evidence of dependence" |
| 24 | **Distribution-free tolerance interval (Wilks)** | "what range covers 95% of future values" · "spec limits from data without assuming a distribution" · "bound where almost all values will fall" | One list, content β, confidence γ. **INLINE** | The agent's conflation of a confidence interval with a coverage interval — and the "mean ± 2 SD covers 95%" reflex | **EASY.** Two-sided [min,max]: solve n·β^{n−1} − (n−1)·β^n = 1−γ. One-sided: 1 − β^n ≥ γ. Root-find on integers | The n requirements are brutal and the tool's main job is to say so: verified **n=93** for two-sided 95/95, **n=59** for one-sided 95/95, **n=473** for 99/95, **n=46** for 90/95. At the agent's usual n=6 nothing remotely useful exists — refuse and report the required n |
| 25 | **Least-absolute-deviations (L1) simple regression, exact** | "fit a line that ignores the one bad y value" · "median regression" · "robust line through 15 points" | Paired (x,y). **DATAFILE** | OLS on data with y-outliers. Complements Theil–Sen: L1 optimizes a stated criterion (Σ\|r\|) rather than taking a median of slopes, and extends to weights | **MODERATE.** The L1 optimum passes through ≥2 data points, so enumerate all C(n,2) candidate lines and take the min SAE: O(n³), practical to **n ≈ 300** (n=200 ≈ 4×10⁶ inner ops ≈ 2 s). Multiple regression needs Barrodale–Roberts simplex — **HARD**, cut | n > 300 for the exact enumeration (fall back to IRLS with wᵢ=1/max(\|rᵢ\|,δ), and *flag it as approximate* — IRLS for L1 is not guaranteed to converge to the optimum). Non-unique solution (very common with small integer data) — report the solution set, not one arbitrary line. **L1 has breakdown 0 in x**: one leverage point destroys it — refuse if any x has hat-value > 4/n and say why |
| 26 | **Anytime-valid sequential test (e-value / betting supermartingale)** | "should I run more trials or do I have enough" · "can I stop the benchmark now" · "I keep adding data and re-checking, is that cheating" · "monitor this until it's decided" | Stream of outcomes, or a list to replay. **MUST-CONSTRUCT** | The agent's actual, universal, invalid workflow: run some trials, peek, run more, peek again. Fixed-n p-values are destroyed by this; e-processes are valid at **every** stopping time, including adaptive ones | **MODERATE.** For a bounded/binary outcome, the simplest useful case is a betting martingale: E_t = Π(1 + λᵢ(Xᵢ − μ₀)) with λ chosen by GRAPA/Kelly; reject when E_t ≥ 1/α. Pure arithmetic. Confidence sequences by inverting. Sign-test-based e-values need nothing but products | The wealth process is degenerate (λ pushes a factor to ≤0) — clamp λ and say so. **Do not present 1/E as a p-value** — it is an evidence measure with a different (Ville-inequality) semantics, and an agent that reads it as a p-value will overstate. Refuse if the outcome is unbounded and no range is supplied |

---

## 3. Recent advances (last ~10 years)

### 3.1 Conformal prediction — the biggest change in the territory

Conformal prediction is the most important development for this project because it delivers what the
agent actually wants (an interval for the *next observation*) with **finite-sample, distribution-free
marginal coverage** under exchangeability alone, for an arbitrary underlying predictor. The split
(inductive) version is five lines of pure Python: compute nonconformity scores on a held-out
calibration set, sort them, take the ⌈(n+1)(1−α)⌉/n empirical quantile.

What matters operationally, and what a naive implementation gets wrong:

- **The hard floor.** A finite interval requires n ≥ (1−α)/α. Verified: **9 calibration points for
  90%, 19 for 95%, 99 for 99%.** Below that the correct output is (−∞, ∞). This is the single most
  useful thing to encode, because the agent's instinct is to compute *some* interval regardless.
- **Coverage is marginal and two-sided:** 1−α ≤ P(cover) ≤ 1−α+1/(n+1). It is *not* conditional on
  the calibration draw. Realized coverage for one particular calibration set fluctuates
  substantially at small n, which the [universal distribution of empirical coverage](https://arxiv.org/pdf/2303.02770)
  characterizes exactly (it is Beta-distributed). The recent **Small Sample Beta Correction (SSBC)**
  ([Probabilistic Conformal Coverage Guarantees in Small-Data Settings](https://arxiv.org/html/2509.15349))
  is a plug-and-play adjustment to the nominal α that converts the in-expectation guarantee into a
  training-conditional probabilistic one — directly relevant here and cheap to implement.
- **Full (transductive) conformal** avoids the data split and is therefore the right choice at agent
  n. For the simplest score (absolute deviation from the sample mean/median) it has a closed form
  and reduces exactly to the order-statistic interval in row #6.
- **Jackknife+** (Barber, Candès, Ramdas & Tibshirani, *Ann. Statist.* 49(1), 2021) uses leave-one-out
  predictions *at the test point* rather than just LOO residual quantiles, and thereby earns a
  worst-case 1−2α guarantee for any symmetric algorithm — where the plain jackknife has *no*
  guarantee and can have coverage that vanishes. At agent scale (n ≤ a few hundred, cheap models
  like OLS/Theil-Sen) the n refits are affordable.
- **Beyond exchangeability**: weighted conformal and the non-exchangeable variants
  ([Split Conformal Prediction and Non-Exchangeable Data](https://www.jmlr.org/papers/volume25/23-1553/23-1553.pdf),
  JMLR 2024) quantify how coverage degrades under distribution drift. Relevant because agent data
  usually *is* drifting. Also [Split Conformal Prediction under Data Contamination](https://arxiv.org/pdf/2407.07700) (2024).
- Textbook-level consolidation now exists: Angelopoulos & Bates' gentle introduction, and
  [Theoretical Foundations of Conformal Prediction](https://arxiv.org/pdf/2411.11824) (2024).

### 3.2 HulC (2021 arXiv / *JRSS-B* 86(3), 2024)

Kuchibhotla, Balakrishnan & Wasserman's HulC builds a confidence region as the **convex hull of
estimates computed on disjoint subsamples**. It requires no variance estimate, no knowledge of the
convergence rate, and **succeeds in a range of examples where the bootstrap provably fails**. For a
median-unbiased estimator, B = ⌈1 + log₂(1/α)⌉ subsamples suffice (6 for 95%). This is close to an
ideal fit for a stdlib agent library: six evaluations, no resampling loop, no distributional
machinery. The catch is the median-unbiasedness requirement; Adaptive HulC estimates the median bias
by subsampling. Reference implementation and notebooks at
[github.com/Arun-Kuchibhotla/HulC](https://github.com/Arun-Kuchibhotla/HulC).

### 3.3 E-values, test martingales, and safe anytime-valid inference

The Ramdas/Grünwald/Vovk/Shafer programme ([Game-theoretic statistics and safe anytime-valid
inference](https://arxiv.org/pdf/2210.01948), *Statistical Science* 38(4), 2023; Ramdas & Wang,
*Hypothesis testing with e-values*, FnT in Statistics, 2025) gives evidence measures that stay valid
under **optional stopping and continuous monitoring**. This maps onto an agent workflow that nothing
else in classical statistics covers: run trials, look, run more, look again, stop when convinced.
Rank-based sequential variants now exist
([A Rank-Based Sequential Test of Independence](https://arxiv.org/pdf/2305.13818), 2023;
[Real-time Program Evaluation using Anytime-valid Rank Tests](https://arxiv.org/pdf/2504.21595), 2025),
which places them squarely inside this territory rather than adjacent to it.

### 3.4 Studentized permutation and the Behrens–Fisher problem

Chung & Romano, [Exact and asymptotically robust permutation tests](https://arxiv.org/pdf/1304.5939)
(*Ann. Statist.* 41(2), 2013) is the result the library must encode as a *rule*: the permutation test
of a raw difference in means is exact only under full exchangeability (P = Q) and is **not**
asymptotically level-α when the two distributions differ in dispersion. Studentizing the statistic
restores asymptotic validity while preserving finite-sample exactness under P = Q — a genuinely
free lunch, and one that a naive permutation implementation throws away. The same logic drives the
studentized permutation Brunner–Munzel test for the nonparametric Behrens–Fisher problem
([Neubert & Brunner 2007]; [small-sample analysis, 2022](https://arxiv.org/pdf/2208.01231);
[compatible confidence intervals, 2025](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12598137/)).

Karch (2021), [Psychologists Should Use Brunner–Munzel's Instead of Mann–Whitney's U Test as the
Default Nonparametric Procedure](https://journals.sagepub.com/doi/10.1177/2515245921999602), is a
clean statement of why the default should change: WMW's type-I error can be substantially inflated
under unequal variances *even for large samples*, while BM is valid under finite variances.

### 3.5 Finite-sample Rousseeuw–Croux constants

Akinshin (2022), [Finite-sample Rousseeuw-Croux scale estimators](https://arxiv.org/abs/2209.12268),
supplies refined Monte-Carlo bias-correction factors and finite-sample Gaussian-efficiency values for
Sₙ and Qₙ at n ≤ 100 (plus prediction equations above), replacing Rousseeuw & Croux's original rough
approximations. Necessary if the library reports Sₙ/Qₙ at all — the asymptotic constants are simply
wrong at n < 20, and the odd/even distinction is real. Companion notes:
[bias factors](https://aakinshin.net/posts/rousseeuw-croux-finite-factors/),
[finite-sample efficiency](https://aakinshin.net/posts/rousseeuw-croux-finite-efficiency/).

### 3.6 Median-of-means and heavy-tail mean estimation

The heavy-tailed mean-estimation literature (survey: Lugosi & Mendelson,
[Mean Estimation and Regression Under Heavy-Tailed Distributions](https://link.springer.com/article/10.1007/s10208-019-09427-x),
*FoCM* 2019) shows the median-of-means estimator attains **sub-Gaussian deviation bounds assuming only
finite variance**, and is virtually tuning-free. It matters here as a principled answer to "my
average keeps moving". But the block count needed for a useful δ is k ≈ 8·log(1/δ) ≈ 24 for δ=0.05,
so it needs n ≥ ~50 to be more than theatre — it does not survive the n=3–15 cut and appears on the
cut list rather than the table. Efficiency-improved variants exist
([Efficient median of means estimator](https://arxiv.org/pdf/2305.18681), 2023).

### 3.7 Permutation p-value estimation

[permApprox: a general framework for accurate permutation p-value approximation](https://arxiv.org/pdf/2602.22975)
(2026) and the older Phipson & Smyth (2010) result are both about the same practical point: the
Monte-Carlo permutation p-value must be (b+1)/(B+1), never b/B. The latter can return exactly 0,
which an agent will happily report as "p = 0". This is a one-line fix with an outsized correctness
payoff.

### 3.8 Better bootstrap-t

[Better bootstrap t confidence intervals for the mean](https://arxiv.org/html/2508.10083v2) (2025)
addresses exactly the pathology measured in row #10: bootstrap-t buys coverage with enormous width on
skewed data at small n. Worth tracking; the plain version is already the best of the bootstraps at
agent scale.

---

## 4. Cut list

Considered and rejected, with the reason.

**Bootstrap variants**
- *Percentile bootstrap as a headline method* — measured coverage 0.73–0.87 at n=6–20 on skewed data (nominal 0.95). Kept only as a diagnostic output alongside boot-t/BCa, never as the answer.
- *Jackknife variance / jackknife CI* — inconsistent for the median and other non-smooth statistics; kept only as the internal acceleration input to BCa.
- *m-out-of-n bootstrap and subsampling* — the standard remedy for bootstrap inconsistency, but requires choosing m, and is itself "unreliable in other than very large samples". HulC (#22) dominates it for this use case.
- *Smoothed bootstrap* — needs a bandwidth choice; introduces a tuning parameter the agent cannot justify.
- *Bootstrap hypothesis tests* — permutation is exact at these n and strictly better.
- *Bias-corrected point estimates via bootstrap* — inflates variance, and an agent will report the corrected estimate without the inflated error.
- *Wild bootstrap, block bootstrap, sieve bootstrap* — all need n ≫ 100 and all belong to the regression / time-series territories.
- *Bayesian bootstrap* — belongs to the Bayesian territory.

**Robust regression**
- *MM-estimators, S-estimators, LTS/LMS regression* — require random subsampling with concentration steps; fragile, tuning-heavy, and non-deterministic at n < 50. Theil–Sen and L1 cover the agent's real need.
- *Repeated-median (Siegel) regression* — 50% breakdown vs Theil–Sen's 29.3%, but O(n²) with a nested median and rarely the binding constraint. Mention in docs, don't ship.
- *Multiple L1 regression (Barrodale–Roberts simplex)* — genuinely HARD in pure stdlib and error-prone. Cut; simple L1 only.
- *Quantile regression at τ ≠ 0.5* — needs a linear program.
- *Passing–Bablok, Deming regression* — method-comparison niche.

**Outlier tests**
- *Grubbs, Dixon's Q, Rosner's ESD* — all assume normality, which is the exact assumption in doubt. Dixon's Q is the only one designed for n=3–10, and even it is a normality test in disguise. Explicitly anti-recommend.
- *Tukey boxplot fences on skewed data* — flags a large fraction of any right-skewed sample by construction. Superseded by the skew-adjusted boxplot in #16.
- *Isolation Forest / LOF / DBSCAN-style detectors* — multivariate, need n in the hundreds, and are not inference.
- *Any automatic outlier deletion* — cut on principle. The library identifies and quantifies influence; it never deletes.

**Normality / distribution testing**
- *Shapiro–Wilk, Anderson–Darling, Kolmogorov–Smirnov, Jarque–Bera as gatekeepers* — the actively harmful case. At n < 15 they have near-zero power, so non-rejection is uninformative, yet an agent will read "p = 0.6" as "normality confirmed" and proceed to a t-test. Worse, at large n they reject trivial, harmless departures. The correct design is to **route by robustness, not by a normality test**. If any of these ship, they ship with the p-value suppressed and a power statement in its place.
- *Sample skewness/kurtosis as heavy-tail evidence at small n* — cut for the reason measured in #20: b₂ is bounded by ≈ n−1, so the statistic cannot express the thing being asked.

**Rank tests**
- *Mood's median test* — much lower power than WMW; dominated.
- *Ansari–Bradley, Mood, Siegel–Tukey (rank tests for scale)* — badly non-robust to an unequal-location nuisance; they routinely detect location differences and report them as scale differences.
- *Van der Waerden normal-scores test* — marginal power gain over WMW, extra machinery.
- *Jonckheere–Terpstra, Page's trend test, Quade test* — ordered-alternative and blocked designs are rare in agent judgment work.
- *Friedman test* — borderline; k≥3 repeated conditions on the same blocks does occur (same benchmark suite, 3 configs). Cut from the top 26 but the closest thing to a 27th row.

**Other**
- *Empirical likelihood* — genuinely attractive (Bartlett-correctable, no resampling, data-determined interval shape) but requires constrained convex optimization per interval endpoint. MODERATE-to-HARD in pure stdlib. Revisit if a solver layer appears.
- *Saddlepoint approximation to permutation distributions* — elegant way to skip enumeration, but the DP and Monte-Carlo routes are already fast enough (verified), so it buys nothing.
- *Median-of-means* — needs n ≥ ~50 for the block count to be meaningful; fails the n=3–15 test.
- *Hill estimator as a standalone tool* — kept only inside the #20 panel, gated at n ≥ 200.
- *Winsorized correlation, percentage-bend correlation* — Wilcox's robust correlations; reasonable, but Kendall's τ with an exact null covers the agent's need with less explaining.
- *Bootstrap for extreme quantiles / the sample maximum* — provably inconsistent; encoded as a refusal rule in #12, not as a method.
- *Non-parametric predictive inference (NPI, Coolen)* — imprecise-probability framing is powerful for future order statistics but the lower/upper probability output is easy for an agent to misread as an interval.

---

## 5. Cross-territory overlaps

| Overlaps with | Nature of the overlap | Who should own what |
|---|---|---|
| **Parametric inference (t/Welch/F)** | This territory is the fallback *and* the arbiter. The routing question "t-test or permutation test?" cannot be settled by a normality test (see cut list) — it must be settled by a **robustness-first default**: use the permutation/rank method unless n is large and the data are clean, since the cost is ~4.5% ARE under normality and the benefit is unbounded otherwise | Shared router. This territory owns the *decision rule*; parametric owns the t/F machinery it delegates to |
| **Effect sizes and power** | Cliff's δ / CLES / rank-biserial (here) vs Cohen's d / Hedges' g (there). Also ARE facts: WMW vs t has ARE 3/π = 0.955 under normality and **≥ 0.864 for any continuous distribution** (Hodges–Lehmann bound), often > 1 for heavy tails — these are the numbers that justify the robustness-first default | Effect-size territory owns the taxonomy; this territory owns the rank-based members and their exact small-n behaviour |
| **Multiple comparisons** | Permutation max-T and Westfall–Young step-down minP are robust-nonparametric methods that solve a multiplicity problem, and they exploit the correlation structure in a way Bonferroni cannot | Multiplicity territory owns it; imports the permutation engine from here |
| **Regression and model checking** | Theil–Sen, L1, Huber-IRLS, jackknife+, conformal residual scores, leverage/hat diagnostics | Split: regression owns OLS and diagnostics; this territory owns the robust fitters and the distribution-free intervals around them |
| **Bayesian methods** | Bayesian bootstrap; Beta-Binomial posterior vs Clopper–Pearson; the small-n regime where a weak prior is more honest than a distribution-free interval that is [−1,1] wide | Clean boundary. Worth a cross-reference note at n < 8, where exact frequentist intervals become vacuous and a prior is the only thing that adds information |
| **Sequential design / stopping rules** | E-values, confidence sequences, and "how many more runs do I need" — #1 (resolution guard) and #26 (anytime-valid) both live on this boundary | Sequential territory owns the design question; this territory owns the rank/sign-based e-values |
| **Time series / dependence** | The #23 exchangeability gate is the shared dependency. **Every** method in this territory dies under serial correlation, and agent data (successive benchmark runs, CI timings, log latencies) is frequently serially correlated | This territory owns the gate; time-series owns block resampling and the effective-sample-size correction |
| **Distribution fitting / EVT** | Hill estimator, tolerance intervals, tail-index estimation | EVT territory owns tail modelling; this one owns the "is the tail heavy enough to change my method" screening |
| **Categorical / count data** | Fisher, Boschloo, Barnard, binomial | Categorical owns the general contingency machinery; this territory owns the exact 2×2 case and the conditional-vs-unconditional argument |

---

## 6. Sources

### 6.1 Measurement harness

All timings measured with CPython 3 on the target machine (Darwin 25.5.0, Apple silicon), pure
stdlib, single-threaded, no numpy. Scripts: `/tmp/feas.py`, `/tmp/feas2.py`, `/tmp/facts.py`,
`/tmp/cov.py`, `/tmp/cov2.py`. Key results reproduced inline in the table; the coverage simulations
used 1200–2000 Monte-Carlo datasets with B = 1000 bootstrap replicates each.

Headline measurements:

| Operation | n | Time |
|---|---|---|
| 10 000 bootstrap replicates of the mean | 1000 | 0.42 s |
| Exact permutation enumeration C(24,12) = 2 704 156 | 24 | 0.51 s |
| Exact permutation enumeration C(26,13) = 10 400 600 | 26 | 2.12 s |
| Theil–Sen (all 2.0M pairwise slopes) | 2000 | 0.33 s |
| Hodges–Lehmann (all Walsh averages) | 2000 | 0.30 s |
| Exact Wilcoxon signed-rank null distribution (DP) | 100 | 0.010 s |
| Exact Mann–Whitney null distribution (DP) | 30 v 30 | 0.027 s |
| Exact Kendall τ null via Mahonian DP | 60 | 0.043 s |
| Boschloo-style nuisance grid, 1000 points, 21×21 table | 40 | 0.010 s |
| Brute-force n! permutation test for correlation | 10 | 0.19 s |

Measured coverage, nominal 95%, mean of a lognormal(0,1):

| n | percentile boot | BCa | bootstrap-t |
|---|---|---|---|
| 6 | 0.731 | 0.753 | **0.889** |
| 10 | 0.800 | 0.828 | **0.905** |
| 20 | 0.862 | 0.873 | **0.915** |
| 40 | 0.898 | 0.904 | **0.927** |

### 6.2 Conformal prediction and distribution-free prediction

- Barber, Candès, Ramdas & Tibshirani, *Predictive inference with the jackknife+*, Ann. Statist. 49(1):486–507, 2021 — https://arxiv.org/pdf/1905.02928 · https://projecteuclid.org/journals/annals-of-statistics/volume-49/issue-1/Predictive-inference-with-the-jackknife/10.1214/20-AOS1965.full
- *Distribution-Free Finite-Sample Guarantees and Split Conformal Prediction* — https://arxiv.org/abs/2210.14735
- *Universal distribution of the empirical coverage in split conformal prediction* — https://arxiv.org/pdf/2303.02770
- *Probabilistic Conformal Coverage Guarantees in Small-Data Settings* (Small Sample Beta Correction) — https://arxiv.org/html/2509.15349
- *Split Conformal Prediction and Non-Exchangeable Data*, JMLR 25, 2024 — https://www.jmlr.org/papers/volume25/23-1553/23-1553.pdf
- *Split Conformal Prediction under Data Contamination*, 2024 — https://arxiv.org/pdf/2407.07700
- *Theoretical Foundations of Conformal Prediction*, 2024 — https://arxiv.org/pdf/2411.11824
- *On Optimal Data Splitting for Split Conformal Prediction* — https://arxiv.org/pdf/2606.31600
- *Training-conditional coverage for distribution-free predictive inference* — https://arxiv.org/pdf/2205.03647
- *Methods to Compute Prediction Intervals: A Review and New Results* — https://arxiv.org/pdf/2011.03065

### 6.3 Bootstrap

- DasGupta, *The Bootstrap* (lecture notes, incl. inconsistency cases) — https://www.stat.purdue.edu/~dasgupta/bootstrap.pdf
- *Consistency of full-sample bootstrap for estimating high-quantile, tail probability, and tail index* — https://arxiv.org/pdf/2004.12639
- *Questionable Claims for Simple Versions of the Bootstrap*, J. Stat. Educ. 2019 — https://www.tandfonline.com/doi/full/10.1080/10691898.2019.1669507
- *Amortized Inference for Sampling Distributions Where the Bootstrap Fails* — https://arxiv.org/html/2607.16666v1
- *Better bootstrap t confidence intervals for the mean*, 2025 — https://arxiv.org/html/2508.10083v2
- BCa reference implementation and quantile-grid caveat — https://bootbca.r-forge.r-project.org/manual/BCa.html
- *Confidence interval of percentiles in skewed distribution* (coverage study) — https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6784425/

### 6.4 Permutation, randomization and exact tests

- Chung & Romano, *Exact and asymptotically robust permutation tests*, Ann. Statist. 41(2):484–507, 2013 — https://arxiv.org/pdf/1304.5939 · https://projecteuclid.org/journals/annals-of-statistics/volume-41/issue-2/Exact-and-asymptotically-robust-permutation-tests/10.1214/13-AOS1090.pdf
- *Randomization Inference: Theory and Applications*, 2024 — https://arxiv.org/pdf/2406.09521
- *permApprox: a general framework for accurate permutation p-value approximation* — https://arxiv.org/pdf/2602.22975
- Streitberg & Röhmel shift algorithm for exact rank-test null distributions (as implemented in `exactRankTests`/`coin`) — https://rdrr.io/cran/exactRankTests/man/wilcox.exact.html
- *On integer partitions and the Wilcoxon rank-sum statistic* — https://arxiv.org/pdf/2409.05741
- Geyer, Stat 5601 notes on permutation and signed-rank tests — https://www.stat.umn.edu/geyer/old/5601/examp/perm.html · https://www.stat.umn.edu/geyer/s06/5102/notes/rank.pdf
- Barnard's test overview and the conditional-vs-unconditional argument — https://en.wikipedia.org/wiki/Barnard's_test · https://www.nbi.dk/~petersen/Teaching/Stat2009/Barnard_ExactTest_TwoBinomials.pdf
- Fisher vs Barnard vs Boschloo comparison — https://metricgate.com/blogs/fishers-exact-vs-barnards-vs-boschloo/

### 6.5 Rank methods, Behrens–Fisher, effect sizes

- Karch, *Psychologists Should Use Brunner–Munzel's Instead of Mann–Whitney's U Test as the Default Nonparametric Procedure*, AMPPS 2021 — https://journals.sagepub.com/doi/10.1177/2515245921999602
- *The nonparametric Behrens–Fisher problem in small samples*, 2022 — https://arxiv.org/pdf/2208.01231
- *A New Approach to the Nonparametric Behrens–Fisher Problem With Compatible Confidence Intervals*, 2025 — https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12598137/
- *An unbiased rank-based estimator of the Mann–Whitney variance including the case of ties*, 2024 — https://arxiv.org/pdf/2409.05038
- `effectsize::rank_biserial` — dominance effect sizes, δ = 2A − 1 relations — https://easystats.github.io/effectsize/reference/rank_biserial.html
- Hodges–Lehmann estimator and Walsh-average CIs — https://search.r-project.org/CRAN/refmans/DescTools/html/HodgesLehmann.html · https://www.lexjansen.com/scsug/1997/SCSUG97019.pdf

### 6.6 Robust location, scale and regression

- Akinshin, *Finite-sample Rousseeuw–Croux scale estimators*, 2022 — https://arxiv.org/abs/2209.12268 · https://aakinshin.net/posts/rousseeuw-croux-finite-factors/ · https://aakinshin.net/posts/rousseeuw-croux-finite-efficiency/
- `robustbase::Sn` documentation (constants, breakdown, efficiency) — https://rdrr.io/cran/robustbase/man/Sn.html
- Hampel identifier — https://blogs.sas.com/content/iml/2021/06/01/hampel-filter-robust-outliers.html · https://en.wikipedia.org/wiki/Hampel_test
- Yuen's trimmed t / Wilcox's robust methods — https://www.sciencedirect.com/topics/mathematics/yuens-method · https://support.sas.com/resources/papers/proceedings14/1660-2014.pdf
- Sen (1968), *Estimates of the Regression Coefficient Based on Kendall's Tau* — https://www.semanticscholar.org/paper/Estimates-of-the-Regression-Coefficient-Based-on-Sen/e4f687ceaa5005c7cd332cf22a6a6c13d8b3d840
- Theil–Sen properties (29.3% breakdown, Kendall-based CI) — https://handwiki.org/wiki/Theil%E2%80%93Sen%20estimator · https://library.virginia.edu/data/articles/theil-sen-regression-programming-and-understanding-an-outlier-resistant-alternative-to-least-squares

### 6.7 Tolerance intervals and order statistics

- Wilks (1941/1942), via *A Graphical Determination of Sample Size for Wilks' Tolerance Limits*, Ann. Math. Statist. 20(2) — https://projecteuclid.org/journals/annals-of-mathematical-statistics/volume-20/issue-2/A-Graphical-Determination-of-Sample-Size-for-Wilks-Tolerance-Limits/10.1214/aoms/1177730044.full
- *Sample sizes for strong two-sided distribution-free tolerance limits*, Statistical Papers — https://link.springer.com/article/10.1007/BF02932595
- *Wilks' Formula Applied to Computational Tools: A Practical Discussion* — https://www.sciencedirect.com/science/article/am/pii/S0306454919302543
- `tolerance::nonpartol.int` — https://rdrr.io/cran/tolerance/man/nonpartolint.html
- Nonparametric predictive inference for future order statistics (Coolen school) — https://maths.dur.ac.uk/stats/people/fc/thesis-HNA.pdf

### 6.8 HulC, e-values, heavy tails

- Kuchibhotla, Balakrishnan & Wasserman, *The HulC: Confidence Regions from Convex Hulls*, JRSS-B 86(3):586, 2024 — https://arxiv.org/pdf/2105.14577 · https://academic.oup.com/jrsssb/article/86/3/586/7499155 · https://github.com/Arun-Kuchibhotla/HulC
- Ramdas, Grünwald, Vovk & Shafer, *Game-theoretic statistics and safe anytime-valid inference*, Statist. Sci. 38(4):576–601, 2023 — https://arxiv.org/pdf/2210.01948
- Wang, *A tiny review on e-values and e-processes*, 2023 — https://sas.uwaterloo.ca/~wang/files/e-review.pdf
- Ramdas, *Hypothesis testing using e-values, martingales & betting* (talk) — https://stat.cmu.edu/~aramdas/talks/JHU24.pdf
- *A Rank-Based Sequential Test of Independence*, 2023 — https://arxiv.org/pdf/2305.13818
- *Real-time Program Evaluation using Anytime-valid Rank Tests*, 2025 — https://arxiv.org/pdf/2504.21595
- Lugosi & Mendelson, *Mean Estimation and Regression Under Heavy-Tailed Distributions: A Survey*, FoCM 2019 — https://link.springer.com/article/10.1007/s10208-019-09427-x
- *Efficient median of means estimator*, 2023 — https://arxiv.org/pdf/2305.18681
- Danielsson, de Haan, Ergun & de Vries, *Tail Index Estimation: Quantile-Driven Threshold Selection* (Bank of Canada WP 2019-28) — https://www.bankofcanada.ca/wp-content/uploads/2019/08/swp2019-28.pdf
