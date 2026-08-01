# Territory 07 — Calibration and Forecast Scoring

Research pass: 2026-07-31. Scope: proper scoring rules, calibration measurement, recalibration,
interval/quantile scoring, coverage testing, forecast comparison, and the minimum-evidence question.

---

## 1. Territory summary

This territory is the direct mathematical counterweight to the measured pathology that motivates the
whole module: LLM agents state confidences that are systematically higher than their realised
accuracy, with published ECE values on factual QA ranging from **0.17 to 0.57** — that is, a stated
90% that resolves at 33–73%. Almost everything worth computing here reduces to one of four
operations on a log of (stated probability, binary outcome) pairs: a **proper score** (Brier, log,
spherical), a **decomposition** of that score into miscalibration / discrimination / irreducible
uncertainty, a **recalibration map** fitted from the log, and a **skill comparison** against a
reference forecast. All four are pure-stdlib arithmetic — the hardest numerics needed are a
Newton solve on a 2×2 or 3×3 system, the pool-adjacent-violators algorithm, and a regularized
incomplete gamma for chi-square tails. The single most important structural fact, and the one that
reshapes the whole tool design, is that **an agent's forecast set is naturally discrete and sparse**
— LLMs emit roughly six to eight distinct confidence values (0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95,
0.99) — which dissolves the binning problem that makes ECE a contested metric in the deep-learning
literature: you do not bin, you group by unique stated value. The second most important fact is that
detecting the *actual* magnitude of LLM overconfidence requires far fewer resolved predictions than
the clinical-prediction literature's "200 events" rule of thumb suggests, because near p = 0.9 the
binomial variance p(1−p) is small — **n ≈ 16 suffices to detect a 25-point gap at 80% power**, while
n ≈ 315 would be needed for a 5-point gap.

---

## 2. Ranked model table

Tier key: **INLINE** = a few numbers or two short comma-separated lists as CLI flags.
**DATAFILE** = a small CSV/JSONL the agent points at. **MUST-CONSTRUCT-DATA** = the agent has to
build a prediction log first (which for this territory is the normal case, and is itself the
intervention).

Nearly every row is "DATAFILE, MUST-CONSTRUCT-DATA upstream" at root, because the prediction log
must exist. Where a row is genuinely INLINE, that means the summary statistics alone are sufficient.

| # | Model / method | SITUATION (agent phrasing + alternates) | Minimum viable inputs + tier | Beats what | Stdlib feasibility + numerics | REFUSE-to-print conditions |
|---|---|---|---|---|---|---|
| 1 | **Calibration-in-the-large / overconfidence gap** — mean stated confidence minus realised hit rate, with a null-variance z and a bootstrap CI. Gap = p̄ − ȳ | "Am I overconfident?" · "When I say 80% how often am I actually right?" · "Is my confidence inflated on average?" · "Check my track record" | ≥10 (p, y) pairs. **INLINE** (two comma-separated lists) or **DATAFILE** | An agent's unaided impression of its own track record, which is subject to the same overconfidence bias being measured. Beats ECE at small n because it has one degree of freedom | **EASY.** `statistics.NormalDist` for the z tail; `random` for the bootstrap. Null sd = √(Σpᵢ(1−pᵢ))/n | n < 10. All outcomes identical AND n < 20 (gap is then an artefact of the outcome constant). Predictions not logged before resolution (retro-scored confidence). Log assembled by selective recall rather than an append-only file |
| 2 | **CORP score decomposition (MCB / DSC / UNC)** via pool-adjacent-violators — the modern, binning-free replacement for Murphy's decomposition. S̄ = MCB − DSC + UNC | "Is my problem calibration or discrimination?" · "Are my confidences actually informative?" · "Do my probabilities carry any signal or am I just repeating the base rate?" · "Break down my forecast error" | ≥25 (p, y) pairs. **DATAFILE** | Murphy's binned decomposition (bin-choice-dependent, components can go negative). Beats reporting a bare Brier score, which conflates three distinct failures | **EASY.** PAVA is a ~25-line loop. MCB = S̄ − S̄(PAV-recalibrated); DSC = S̄(base rate) − S̄(PAV); UNC = S̄(base rate). Both MCB and DSC are non-negative by construction | n < 25. Fewer than 3 distinct stated confidence values (DSC is then near-meaningless). All outcomes identical → UNC = 0, DSC undefined, skill ratio divides by zero |
| 3 | **Brier score + Murphy 3-way decomposition on natural groups** (reliability / resolution / uncertainty), grouped by *unique stated value* not by bins | "Score my past predictions" · "How good were my probability estimates?" · "Give me a single number for forecast quality" | ≥20 (p, y) pairs. **DATAFILE** | Accuracy alone, which ignores confidence entirely. Beats binned ECE because grouping on natural discrete values is exact, not an approximation | **EASY.** Pure arithmetic. REL = (1/n)Σₖnₖ(p̄ₖ−ōₖ)²; RES = (1/n)Σₖnₖ(ōₖ−ō)²; UNC = ō(1−ō) | n < 20. More than ~n/5 distinct confidence values (grouping degenerates to n groups → REL is upward-biased and RES saturates; fall back to row 2). Any group with n_k = 1 must be flagged, not silently included |
| 4 | **Spiegelhalter Z-test** — binning-free formal test of the null "these forecasts are calibrated" | "Is my miscalibration real or just noise?" · "Do I have enough data to say I'm overconfident?" · "Test whether my confidences are statistically off" | ≥15 (p, y) pairs. **DATAFILE** | Hosmer-Lemeshow (bin-dependent, low power). Beats eyeballing a reliability table, which over-reads 3-observation cells | **EASY.** Z = Σ(yᵢ−pᵢ)(1−2pᵢ) / √(Σ(1−2pᵢ)²pᵢ(1−pᵢ)); `NormalDist().cdf` for the p-value | n < 15. Any pᵢ = 0.5 exactly for all i (weights vanish, denominator → 0). Any pᵢ ∈ {0,1} (contributes but with zero variance — refuse or clip and say so). Known low power against prevalence shift — must print "non-significant ≠ calibrated" |
| 5 | **Recalibration table by unique stated value** — for each distinct confidence the agent emits, the empirical hit rate with a Wilson (or Jeffreys) interval, plus a shrunk posterior estimate | "What does my 90% actually mean?" · "Build me a correction table for my confidence statements" · "Map my stated confidence to real frequency" | ≥5 observations per value, ≥30 total. **DATAFILE** | The reliability diagram, which this *is* for discrete forecasts, without any binning choice. Beats a global scalar correction when miscalibration is non-monotone in p | **EASY.** Wilson closed form; Jeffreys needs the inverse regularized incomplete beta (bisection) or use the beta-binomial posterior mean (k+½)/(n+1) | Any cell with n_k < 5 → print the interval but suppress the point estimate. Total n < 30. Must refuse to present the raw cell rate as "my true accuracy at 90%" without the interval attached — the interval is the deliverable |
| 6 | **Skill score against a reference forecast** (base rate / climatology / constant-p), with the small-sample debiasing correction | "Am I better than just guessing the base rate?" · "Is stating a confidence adding anything?" · "Compare my forecasts to a dumb baseline" · "Do my probability estimates beat always saying 70%?" | ≥25 (p, y) pairs + the reference. **DATAFILE**, or **INLINE** if both mean scores are known | The Brier score in isolation, which is uninterpretable without a reference. Kills the most common false calibration claim: perfect calibration at the base rate is *zero skill* | **EASY.** BSS = 1 − BS/BS_ref. Debiasing: recompute BS_ref by repeated resampling from the empirical climatology at the same effective sample size | n < 25 (BSS has a documented negative small-sample bias, strongest at small n — refuse or force the debiased variant). Reference computed from the same data being scored (in-sample base rate → optimistic; use leave-one-out base rate). BS_ref = 0 |
| 7 | **Logistic recalibration = Cox intercept & slope = Platt scaling on the logit** (one model, three names). Fit logit(π) = a + b·logit(p) | "Correct my confidence going forward" · "Fit a correction to my stated probabilities" · "Am I over- or under-confident, and by how much per unit?" | ≥40 (p, y) pairs, ≥3 distinct p values, both outcomes present. **DATAFILE** | Ad-hoc "I'll subtract 15 points". Gives two interpretable diagnostics *and* the fix from one fit: a ≠ 0 = mean-level bias, b < 1 = confidences too spread out (over-extremised) | **MODERATE.** Newton-Raphson / IRLS on a 2×2 system; analytic 2×2 inverse, no linear-algebra library needed. Wald CIs from the inverse Hessian | n < 40. Complete or quasi-complete separation (coefficients diverge — detect via |b| > 10 or non-convergence in 25 iterations and refuse). Fewer than 3 distinct p. Any p ∈ {0,1} (logit infinite → clip to [ε, 1−ε] and print ε). Fitting and evaluating on the same data without a split |
| 8 | **Temperature scaling (1-parameter)** — logit(p′) = logit(p)/T, fit by minimising log loss over the scalar T | "Give me one number to fix my confidence" · "Soften my probabilities" · "Simplest possible calibration correction" | ≥20 (p, y) pairs. **DATAFILE** | Row 7 at small n: one parameter instead of two, so far less overfitting below n ≈ 40. The standard baseline in the ML calibration literature and hard to beat | **EASY.** 1-D convex problem; bisection on the log-loss derivative over T ∈ [0.1, 10], or golden-section. ~30 iterations | n < 20. T hitting a bracket boundary (indicates separation or degenerate data). Cannot fix non-monotone miscalibration — must refuse (or warn hard) if the CORP recalibration curve from row 2 is non-monotone in the raw p ordering |
| 9 | **Empirical coverage test for prediction intervals** — exact binomial + Kupiec unconditional-coverage LR | "My 90% ranges — do they actually contain the answer 90% of the time?" · "Are my estimate ranges too narrow?" · "Test my interval coverage" | Hits k out of n intervals + nominal level. **INLINE** | An agent's sense that its ranges are "about right". Directly attacks the interval analogue of verbal overconfidence | **EASY.** Exact binomial via `math.comb`; Kupiec LR_uc = −2ln[(1−α)^(n−x)α^x / ((1−x̂)^(n−x)x̂^x)] ~ χ²₁ (needs regularized lower incomplete gamma) | **n < 1/α.** With a 95% interval and n = 15 the expected miss count is 0.75 — you cannot distinguish 95% from 80% coverage; refuse outright. Prefer the exact binomial over the LR χ² below n = 50. Intervals adjusted after seeing outcomes |
| 10 | **Interval score (Winkler)** for a central (1−α) interval, decomposed into width + undercoverage penalty | "Score my range estimates" · "Was my 'this will take 3-5 hours' any good?" · "Compare two ways of giving ranges" | ≥10 (l, u, y, α) tuples. **DATAFILE**, small cases **INLINE** | Coverage alone, which a 0-to-∞ interval satisfies perfectly. Enforces sharpness-subject-to-calibration in one number | **EASY.** IS = (u−l) + (2/α)(l−y)·1{y<l} + (2/α)(y−u)·1{y>u}. Report mean IS plus the width / penalty split | Mixed α across rows without normalising. l > u. n < 10. Scale-dependent — refuse to compare interval scores across quantities with different units without an explicit relative/scaled variant |
| 11 | **Logarithmic score + log skill score** — strictly proper, locally sensitive, brutal on confident errors | "Score my predictions, punishing confident mistakes hard" · "Log loss on my forecast history" · "Which of my wrong calls cost the most?" | ≥20 (p, y) pairs. **DATAFILE** | Brier when the decision cost is asymmetric in confident errors. The per-item contribution is a natural "worst calls" ranking, which is the most behaviourally useful output for an agent | **EASY.** −[y·ln p + (1−y)·ln(1−p)]. Needs an explicit clipping policy | **Any p = 0 or 1 with the opposite outcome → infinite.** The tool must refuse to print a finite mean unless the agent explicitly accepts a clip, and must then print the clip value and how many items hit it. Unbounded score means one item can dominate — always print the max single contribution alongside the mean |
| 12 | **Sample-size / power planner for calibration claims** — how many resolved predictions before a calibration statement is meaningful | "How many predictions do I need before I can say anything?" · "Is 12 resolved calls enough?" · "What gap could I even detect with this much history?" | Target gap Δ, typical stated confidence p̄, α, power. **INLINE** | An agent asserting "I've been well calibrated lately" from 8 data points. This is the false-positive control for the whole territory and should be the *first* tool called | **EASY.** n ≥ [(z_{1−α/2}√(p̄(1−p̄)) + z_power√(π(1−π)))/Δ]², π = p̄ − Δ. `NormalDist.inv_cdf` | Should never refuse — it is the refusal oracle for everything else. Must decline to answer "how many for a full reliability curve" with a small number: that needs ≥100 of each outcome, ≥200 for a flexible curve |
| 13 | **PIT histogram + uniformity test** for continuous/numeric predictions | "Are my numeric estimates well calibrated?" · "Is my uncertainty about numbers too narrow?" · "Check the shape of my errors" | ≥20 PIT values (or ≥20 (forecast distribution, outcome) pairs). **DATAFILE** | Point-error metrics (MAE/RMSE) which say nothing about stated uncertainty. Diagnostic shape is directly actionable: U-shape = intervals too narrow (overconfident), hump = too wide, skew = biased | **MODERATE.** PIT = F(y). Uniformity via χ² on equal-width bins (needs incomplete gamma) or Kolmogorov-Smirnov (needs the KS asymptotic series). Chi-square is the safer stdlib route | n < 20. Discrete predictive distributions without randomised PIT (histogram is then artefactually non-uniform — refuse or apply randomisation and say so). Fewer than 5 expected per bin in the χ² version. PIT computed from a distribution fitted on the same data |
| 14 | **Pinball / quantile loss** on stated quantiles | "Score my 'p90 estimate'" · "Was my worst-case number honest?" · "Evaluate my percentile guesses" | ≥15 (τ, q, y) triples. **DATAFILE** | Absolute error, which implicitly assumes τ = 0.5. The only proper way to score a one-sided claim like "90% chance it's under X" | **EASY.** ρ_τ(y,q) = τ(y−q) if y ≥ q else (1−τ)(q−y) | n < 15 per quantile level. Pooling across τ without saying so. Scale-dependent — same caveat as row 10. τ ∉ (0,1) |
| 15 | **Diebold-Mariano test with Harvey-Leybourne-Newbold small-sample correction** | "Did my new approach actually forecast better?" · "Is method A's lower Brier score real?" · "Compare two forecasting strategies statistically" | ≥20 paired score differences. **DATAFILE** | Comparing two mean scores by eye. Handles the serial correlation that makes naive paired t-tests oversized on sequential agent runs | **MODERATE.** d̄ / √V̂, V̂ from Newey-West with h−1 lags; HLN factor √((n+1−2h+h(h−1)/n)/n); compare to t_{n−1} → needs regularized incomplete beta. For n < 20 use a Wilcoxon signed-rank or a paired bootstrap on d instead | n < 20 without the HLN correction (documented oversizing). Nested models (DM is invalid for nested forecasts — Giacomini-White or Clark-West needed; refuse). Negative long-run variance estimate (known failure at small n → fall back to the paired bootstrap). Non-paired data |
| 16 | **Paired bootstrap CI for any score or score difference** | "How uncertain is my Brier score?" · "Put error bars on my calibration numbers" · "Could this score difference be luck?" | ≥15 (p, y) pairs or paired scores. **DATAFILE** | Point estimates presented without uncertainty, which is exactly the reporting failure this module exists to prevent. Should be attached to *every* score this territory emits | **EASY.** `random.choices` with a fixed seed; BCa is nice-to-have, percentile is adequate. 2000–10000 resamples | n < 15 (bootstrap CIs are badly undercovered at very small n — use exact binomial where available instead). Resampling without preserving pairing. Bootstrapping a statistic with a boundary at the observed value (e.g. min/max). Unstated seed → non-reproducible |
| 17 | **Isotonic recalibration (PAVA) with cross-validated evaluation** | "Fit the best-possible correction to my confidences" · "Non-parametric confidence remap" · "What's the ceiling on how much recalibration can help me?" | ≥100 (p, y) pairs; ≥200 for a trustworthy curve. **DATAFILE** | Parametric maps when miscalibration is non-monotone or has a plateau. Its in-sample fit is also the exact quantity subtracted in the CORP MCB term (row 2), so it does double duty | **EASY** to fit (PAVA loop), **MODERATE** to validate (k-fold split logic) | n < 100 → refuse to output a map (isotonic overfits savagely; it can drive in-sample ECE to ~0 on noise). Reporting recalibrated score on the training data — must refuse the in-sample number and print only the CV number. Step function extrapolates flat beyond the observed p range — refuse to map inputs outside it |
| 18 | **Beta calibration (3-parameter)** — logistic regression of y on (ln s, −ln(1−s)) | "My confidence is squashed toward the extremes — fix it" · "Platt scaling is making things worse" · "Better correction than a sigmoid" | ≥100 (p, y) pairs. **DATAFILE** | Platt/logistic recalibration (row 7) when scores are pushed *toward* the extremes rather than compressed — the empirically typical LLM pattern. Contains the identity map (a=b=1, c=0) as a special case, so it cannot make an already-calibrated forecaster worse the way Platt can | **MODERATE.** Newton on a 3×3 system; analytic 3×3 inverse or Gaussian elimination | n < 100. Any p ∈ {0,1} (both features infinite). Separation. Must report a likelihood-ratio test against the identity map before recommending its use — otherwise it is three parameters fitted to noise |
| 19 | **Expected Calibration Error (equal-mass binning) + debiased estimator + bootstrap CI** | "What's my ECE?" · "Standard calibration metric" · "Compare my calibration to published numbers" | ≥50 (p, y) pairs, ≥10 per bin. **DATAFILE** | Nothing statistically — it is dominated by rows 2, 4 and 5. Included **only** for comparability with the LLM-calibration literature, which reports it universally | **EASY** to compute, **MODERATE** to debias (resample-based bias correction) | n / n_bins < 10. Equal-width binning when confidences cluster at the top (the standard LLM case) — force equal-mass. Must always print the bin count and binning scheme, and must print the standing caveat: **ECE = 0 is achievable by a constant forecaster at the base rate**, so a low ECE is not evidence of skill. Refuse to report ECE as the sole headline number |
| 20 | **Sharpness / resolution report** — variance of stated confidences, mean \|p − base rate\|, mean interval width, count of distinct values | "Am I hedging on everything?" · "Do I ever commit to a view?" · "Are all my confidences the same number?" | ≥15 forecasts (outcomes not required). **DATAFILE** or **INLINE** | Calibration metrics alone, which reward a coward. Catches the specific LLM pathology of collapsing onto 2–3 saturated values — a *property of the forecasts only*, so it needs no resolved outcomes and works at the smallest n in this territory | **EASY.** `statistics.pvariance`, a set() for distinct values | Fewer than 10 forecasts. Must never be reported as "good calibration" — sharpness is only meaningful *subject to* calibration, and the tool must print both or neither if outcomes are available |
| 21 | **CRPS for full distributional numeric forecasts** — empirical/ensemble form and closed-form Gaussian | "Score my whole distribution over a number" · "I gave a mean and a spread — how good was it?" · "Proper score for a numeric estimate with uncertainty" | ≥15 (predictive sample or (μ,σ), y). **DATAFILE** | Point error and interval score when the agent can state a full distribution. Generalises MAE, so it degrades gracefully to a familiar number | **EASY.** Ensemble: (1/m)Σ\|xᵢ−y\| − (1/2m²)ΣΣ\|xᵢ−xⱼ\|, O(m log m) via sorting. Gaussian: σ[z(2Φ(z)−1) + 2φ(z) − 1/√π] | Ensemble size m < 20 (estimator is biased low at small m — the fair/adjusted variant is needed). Mixing units across rows. σ ≤ 0. Scale-dependent, so no cross-quantity comparison without a skill score |
| 22 | **Christoffersen independence / conditional coverage test** | "Are my misses clustered?" · "Do I go wrong in streaks?" · "Is my calibration breaking down in a particular regime?" | ≥40 ordered hit/miss indicators. **DATAFILE** | Unconditional coverage (row 9), which passes a forecaster whose failures are all bunched in one context. Detects the exchangeability violation that invalidates every other tool here | **MODERATE.** Transition counts n₀₀,n₀₁,n₁₀,n₁₁; LR_ind ~ χ²₁; LR_cc = LR_uc + LR_ind ~ χ²₂. Needs incomplete gamma | n < 40. Any transition count = 0 (the LR is then degenerate — fall back to a runs test or a permutation test). Non-sequential data (order must be meaningful). Only detects *first-order* dependence — must state that regime shifts spanning more than one step can pass |
| 23 | **smoothECE (kernel-smoothed calibration error)** | "Binning-free calibration error" · "A calibration number that isn't an artefact of my bin choice" | ≥100 (p, y) pairs. **DATAFILE** | Binned ECE's discontinuity and bin-choice dependence; it is a *consistent* calibration measure (bounds the true distance-to-calibration), which binned ECE is not | **MODERATE-HARD.** Reflected Gaussian kernel smoothing, boundary reflection at 0 and 1, and an automatic bandwidth search. Feasible but the most numerics-heavy row here | n < 100. **Largely redundant for this project**: with only 6–8 distinct forecast values the binning problem it solves does not arise — rows 2 and 5 are exact. Include only if the agent's confidences become continuous |

---

## 3. Recent advances (~last 10 years)

### 3.1 Measurement: the ECE critique and its resolution

- **Guo et al. (ICML 2017)** established that modern deep networks are badly miscalibrated and that
  **temperature scaling**, a one-parameter variant of Platt scaling, is surprisingly hard to beat.
  This is why row 8 outranks rows 17 and 18 at agent-scale n. (https://arxiv.org/abs/1706.04599)
- **Nixon et al. (2019)** and **Roelofs et al. (AISTATS 2022)** documented that binned ECE is a
  *biased* estimator, that the bias direction depends on the miscalibration pattern and sample size,
  and that it is **most strongly biased for a perfectly calibrated model** — i.e. the metric is worst
  exactly where you most need it to be right. Equal-mass binning has lower bias than equal-width;
  `ECE_sweep` picks the largest number of equal-mass bins keeping the calibration function monotone.
  (https://openreview.net/pdf?id=r1la7krKPS, https://openreview.net/forum?id=NgZKCRKaY3J)
- **Kumar, Liang & Ma (NeurIPS 2019), "Verified Uncertainty Calibration"** showed that the
  *continuous* recalibrators (Platt, temperature) whose calibration error people report are
  typically not actually verified, and introduced **scaling-binning** plus a debiased estimator with
  finite-sample guarantees. (https://arxiv.org/abs/1909.10155)
- **Błasiok, Gopalan, Hu & Nakkiran (STOC 2023)** gave a *unifying theory of distance from
  calibration*, defining what it means for a calibration measure to be **consistent** (polynomially
  related to the true L1 distance-to-calibration). Binned ECE fails this. **Błasiok & Nakkiran
  (ICLR 2024) smoothECE** is the practical consequence: RBF-kernel smoothing with a principled
  automatic bandwidth, satisfying (dCE − σ) ≤ smECE_σ ≤ (1 + 1/σ)·dCE.
  (https://arxiv.org/abs/2309.12236)
- **Dimitriadis, Gneiting & Jordan (PNAS 2021), "Stable reliability diagrams"** is arguably the most
  important practical advance in the territory: the **CORP** approach (Consistent, Optimally binned,
  Reproducible, PAV-based) replaces arbitrary binning with isotonic regression, and yields a
  score decomposition **S̄ = MCB − DSC + UNC** with both components non-negative by construction.
  **Gneiting & Resin (EJS 2023)** generalise it to arbitrary proper scores. This is row 2 and it is
  ~30 lines of stdlib Python. (https://www.pnas.org/doi/10.1073/pnas.2016191118,
  https://arxiv.org/abs/2108.03210)
- **Siegert (QJRMS 2017)** simplified and generalised Murphy's decomposition, showing reliability and
  resolution can be written as average score *differences* between the issued forecast, the
  recalibrated forecast, and the climatological forecast — the conceptual bridge to CORP.
  (https://doi.org/10.1002/qj.2985)

### 3.2 Recalibration

- **Kull, Silva Filho & Flach (AISTATS 2017), beta calibration.** Platt scaling assumes
  class-conditional Gaussian scores with equal variance and therefore *always* imposes an S-curve —
  it can make an already-calibrated forecaster worse. Beta calibration assumes two Beta
  distributions, reduces to a 3-parameter logistic regression on features (ln s, −ln(1−s)), and
  **contains the identity map as a special case**. Reported to beat both Platt and isotonic across a
  wide range of settings. (https://proceedings.mlr.press/v54/kull17a/kull17a.pdf)
- **Silva Filho et al. (Machine Learning, 2023), "Classifier calibration: a survey"** — the standard
  reference tying together measurement and correction. (https://arxiv.org/pdf/2112.10327)
- **Minderer et al. (NeurIPS 2021), "Revisiting the calibration of modern neural networks"** —
  partially reverses Guo et al.: the most recent non-convolutional architectures are among the
  best-calibrated, so "bigger = more overconfident" is not a law.
  (https://openreview.net/pdf?id=QRBvLayFXI)

### 3.3 Sample size for calibration claims

- **Riley et al. (Statistics in Medicine, 2021)** give minimum sample size formulae for external
  validation of a binary-outcome prediction model, targeting precise estimation of the calibration
  slope, calibration-in-the-large, and the C-statistic.
  (https://onlinelibrary.wiley.com/doi/full/10.1002/sim.9025)
- The standing rules of thumb — **≥100 events and 100 non-events** for stable performance estimates,
  **≥200 of each** for a flexible (non-parametric) calibration curve — originate from Vergouwe,
  Collins and Van Calster and are the correct thresholds for rows 17 and 18. Critically, they are
  *not* the threshold for rows 1 and 4, which target calibration-in-the-large only.
  (https://link.springer.com/article/10.1186/s12916-019-1466-7)
- **Huang, Li & Reynolds (JAMIA 2020)** is the best single tutorial on the measure/model split:
  Spiegelhalter Z, Cox intercept and slope, ECE/MCE, and the recalibration models, with the
  correct interpretation of a > 0 (overconfidence on average) and b < 1 (over-extremised
  probabilities). (https://academic.oup.com/jamia/article/27/4/621/5762806)

### 3.4 Forecast comparison and coverage

- **Harvey, Leybourne & Newbold (IJF 1997)** small-sample correction to Diebold-Mariano remains the
  operational standard; the modification is
  DM_HLN = √((T + 1 − 2h + T⁻¹h(h−1))/T) · DM, compared to t_{T−1} rather than N(0,1). Recommended
  whenever the test set is under ~20 observations or h > 1.
- **Diebold (JBES 2015), "Comparing predictive accuracy, twenty years later"** is the author's own
  warning about misuse — DM is a test about *forecasts*, not about *models*, and is invalid for
  nested model comparison. This is the refusal condition in row 15.
- Negative long-run variance estimates in small samples are a documented, common DM failure mode
  (https://www.sciencedirect.com/science/article/abs/pii/S0169207017300559) — hence the paired
  bootstrap fallback.
- **Weigel, Liniger & Appenzeller (MWR 2007)** documented the **negative small-sample bias of the
  Brier and ranked probability skill scores** and the resampling-based debiasing fix; recent work
  extends the debiased BSS to subseasonal forecasting
  (https://www.mdpi.com/2077-1312/13/6/1035). **Bradley et al. (WAF 2008)** give sampling
  uncertainty and confidence intervals for the Brier score and BSS directly.

### 3.5 LLM-calibration-specific findings (the reason this territory exists)

- **"The Confidence Dichotomy: Analyzing and Mitigating Miscalibration in Tool-Use Agents"
  (2026)** — the central result for this module. **Evidence-gathering tools (search, retrieval)
  induce overconfidence; verification tools improve calibration.** Measured with ECE, Brier and
  AUROC. The recommended mitigation is *embedding feedback mechanisms into agent workflows* so tools
  do not merely answer but let the agent assess confidence against a verification signal — which is
  precisely what this territory is. (https://www.arxiv.org/pdf/2601.07264)
- **"Wired for Overconfidence: A Mechanistic Perspective on Inflated Verbalized Confidence in LLMs"
  (COLM 2026)** — concrete magnitudes. Baseline ECE: Llama-3.2-3B **0.570** on PopQA, **0.507** on
  NQOpen, 0.171 on MMLU; Qwen2.5-3B **0.492** / **0.551** / 0.281. The high-confidence value set the
  models actually emit is {70, 75, 80, 85, 90, 99} and the low set {0, 10, 15, 20, 25, 30}. The
  paper localises "confidence mover" circuits comprising <0.6% of edges.
  (https://arxiv.org/pdf/2604.01457)
- **Sparsity of verbalized confidence.** Multiple 2025–2026 papers report that verbalized confidence
  **collapses onto a handful of saturated values** (commonly ~8 unique values across a whole
  benchmark, dominated by 0.9 and 1.0), which destroys its usefulness as a ranking or thresholding
  signal. This is the single most design-relevant empirical fact in the territory — see §6.
- **"Asking Is Not Enough: Protocol Sensitivity in LLM Confidence Calibration" (2026)** — the
  *elicitation protocol* (conditioning context, whether the scored answer is the sampled one, token
  readout method) **changes the sign of the ECE gap between verbalized and token-probability
  confidence**, while changing the ECE *estimator* barely matters. Direct implication: a calibration
  log is only valid if the confidences in it were elicited the same way every time. This is a
  data-collection precondition, not a statistical one, and belongs in the tool's refusal logic.
  (https://arxiv.org/pdf/2605.27752)
- **"On Verbalized Confidence Scores for LLMs" (2024)** — for instruction-tuned models, verbalized
  confidence is *better* calibrated than raw token logits, which is what makes this whole approach
  viable: the agent's stated number is a real signal, just a biased one.
  (https://arxiv.org/html/2412.14737v2)
- **"Taming Overconfidence in LLMs: Reward Calibration in RLHF" (2024)** traces inflated confidence
  partly to RLHF reward models preferring confident-sounding text; 2026 work shows **RL with a
  proper-scoring-rule reward** (log score or tokenized Brier) provably aligns expressed confidence
  with empirical accuracy. Note what this means for us: propriety is not an academic nicety, it is
  the property being exploited to fix the pathology. (https://arxiv.org/pdf/2410.09724)
- **"Mind the Confidence Gap" (2025)** and **ConfidenceBench (2026)** provide benchmark-level
  overconfidence measurements including on deliberately unknowable questions.
  (https://arxiv.org/pdf/2502.11028, https://arxiv.org/html/2607.20526)
- **"Large Language Models Are Overconfident in Their Own Responses" (2026)** — self-assessment of
  own output is worse-calibrated than assessment of others' output.
  (https://arxiv.org/pdf/2606.03437)

---

## 4. The practical judgment case

**Setup.** The agent has a log of N past predictions: a stated probability pᵢ and a resolved binary
outcome yᵢ. What can it legitimately conclude, and how should it change what it says next?

### 4.1 The decision ladder by N

The threshold that matters is not N in the abstract — it is N relative to the *size of the gap you
are trying to detect*, and the binomial variance at the confidence level you typically state. Using
n ≥ [(z_{0.975}√(p̄(1−p̄)) + z_{0.80}√(π(1−π)))/Δ]² with p̄ = 0.90 (a typical LLM stated confidence)
and π = 0.90 − Δ:

| True gap Δ (stated − actual) | N for 80% power, α = 0.05 |
|---|---|
| 0.30 | **11** |
| 0.25 | **16** |
| 0.20 | **24** |
| 0.15 | **40** |
| 0.10 | **85** |
| 0.05 | **315** |

Published LLM ECE on factual QA sits at 0.17–0.57. **The pathology as it actually exists in the wild
is detectable from 11–25 resolved predictions.** This is the most useful single number in the
territory and it flatly contradicts the "you need 200 events" intuition imported from clinical
prediction modelling — that rule is for *flexible calibration curves* (row 17), not for
calibration-in-the-large (rows 1 and 4).

Operational ladder:

- **N < 10 — nothing.** Print the raw tally ("8 predictions, mean stated confidence 0.86, 5 correct")
  and refuse every derived statistic. No score, no ECE, no correction.
- **N = 10–24 — calibration-in-the-large only.** Rows 1, 4, 12, 20. Legitimate conclusion:
  *"my mean stated confidence exceeds my hit rate by X, 95% CI [a, b]"*. Actionable **only if the CI
  excludes zero.** No per-confidence-level claims, no fitted correction.
- **N = 25–99 — score and decompose.** Add rows 2, 3, 6, 8, 15, 16. Legitimate conclusions: whether
  the failure is miscalibration (MCB) or lack of discrimination (DSC); whether the forecasts beat
  the base rate at all; a **one-parameter** temperature correction. Still no per-bin claims, no
  isotonic, no beta.
- **N = 100–199 — two-parameter correction.** Add rows 7, 18, and row 5 for confidence values with
  ≥5 observations each. Cox slope and intercept with Wald CIs become meaningful.
- **N ≥ 200 with ≥100 of each outcome — flexible curves.** Rows 17 and 23 become defensible; a full
  reliability diagram can be drawn; sub-group calibration claims become possible.

### 4.2 What the agent may *not* conclude

1. **"I am well calibrated" from a non-significant test.** Rows 4 and 9 have limited power; the
   Spiegelhalter Z is specifically known to be weak against prevalence shift. Absence of evidence is
   the default state at agent-scale n. The tool should print the *minimum detectable gap* at the
   observed n alongside every non-significant result.
2. **"My calibration is good because my ECE is low."** A constant forecaster emitting the base rate
   has ECE = 0, reliability = 0, and **resolution = 0** — perfectly calibrated and completely
   useless. This is the base-rate anchoring trap in its purest form, and it is the reason row 6
   (skill vs. reference) and row 20 (sharpness) are non-optional companions to any calibration
   claim. Calibration is necessary, not sufficient; the target is **sharpness subject to
   calibration** (Gneiting, Balabdaoui & Raftery 2007).
3. **"Recalibration improved me by X"** measured on the same data the recalibration was fitted to.
   This is circular and isotonic regression will happily drive in-sample ECE to near zero on pure
   noise. Only a cross-validated or held-out number may be printed.
4. **Anything transferred across task regimes.** A correction fitted on "will this test pass"
   predictions does not transfer to "is this API deprecated" predictions. Base rates, difficulty,
   and the elicitation protocol all differ. Row 22 exists to detect the clustered-failure signature
   of a pooled-regime log; the log format should carry a task-class tag and corrections should be
   fitted per class or not at all.
5. **Anything from a log assembled by recall.** Confidences must be written down *before* resolution,
   to an append-only file, with no gaps. A log of remembered predictions is selection-biased in the
   direction of the bias being measured. This is the one failure mode no statistic can repair, and
   it should be a hard precondition printed by every tool in the territory.
6. **Anything from a log with inconsistent elicitation.** Per the protocol-sensitivity finding, the
   *sign* of the calibration gap can flip with the conditioning context. Mixed elicitation → refuse.

### 4.3 How to adjust future statements

The correction must be **mechanical and written down**, not an intention. An agent cannot reliably
apply "be less confident" to itself — that is the pathology.

- **Emit a remap table, not a rule.** Because verbalized confidence is sparse (6–8 distinct values),
  the deliverable is a small lookup table: `stated 0.95 → 0.78`, `stated 0.90 → 0.71`, etc. This is
  row 5 plus row 8, and it is directly usable in a later prompt or a system note.
- **Shrink toward the prior.** A cell with 4 observations must not produce a wild remap. Use the
  beta-binomial posterior mean with a prior centred on the stated value and a strength of ~5
  pseudo-observations: corrected = (k + κ·p_stated)/(n_k + κ). This makes the correction converge
  smoothly from "no change" at n_k = 0 to the empirical rate at large n_k, and it makes the tool
  safe to run at every n rather than only above a threshold.
- **Prefer one parameter.** Below N = 100, a single temperature T (row 8) applied to all stated
  values is more likely to generalise than a per-value table. Report both; recommend the scalar.
- **For intervals, widen multiplicatively.** If empirical coverage of nominal 90% intervals is 62%
  over n = 30, do not restate the level — scale the half-widths by the factor that would have
  achieved nominal coverage on the log (a conformal-style adjustment), and report the achieved
  coverage of the scaled intervals under leave-one-out.
- **Check that the correction did not destroy sharpness.** After recalibration, recompute DSC (row 2)
  and the sharpness report (row 20). A correction that flattens all confidences toward the base rate
  has "fixed" calibration by destroying information — that is the underconfidence failure the
  Confidence Dichotomy paper attributes to verification tools, and this module is a verification
  tool. Guarding against overshoot is a first-class requirement, not an afterthought.
- **Re-derive, do not accumulate.** Corrections should be refitted from the full log each time, never
  stacked on top of a previous correction.

---

## 5. Cut list

- **Hosmer-Lemeshow test** — bin-dependent, low power, results change with the number of groups; superseded by Spiegelhalter Z, which needs no binning.
- **AUROC / C-statistic as a calibration metric** — it is a *discrimination* metric, invariant to any monotone recalibration; the DSC term already covers this and is on the score's own scale.
- **Histogram binning (Zadrozny-Elkan) as a recalibrator** — dominated by isotonic/PAV at every n, and reintroduces the binning choice.
- **Bayesian Binning into Quantiles (BBQ)** — model averaging over binnings; heavy, and the sparse-forecast structure makes it pointless here.
- **Dirichlet calibration, vector and matrix scaling** — multiclass methods needing thousands of examples; agent confidences are binary events.
- **Class-wise / top-label / multiclass ECE variants (ACE, TACE, SCE, MacroCE)** — solve a multiclass problem this territory does not have.
- **Kernel calibration error / MMD-based calibration tests** — O(n²) kernel matrices plus a bootstrap null for a test that Spiegelhalter Z already provides more cheaply at this n.
- **Venn-Abers predictors** — valid multiprobability output, but returns an interval-of-probabilities that an agent will misreport as a confidence interval; confusion risk outweighs the guarantee.
- **Conformal prediction (split/full)** — genuinely valuable but belongs to a coverage/prediction-set territory of its own; only the coverage-check half is retained here (row 9) and the multiplicative widening heuristic in §4.3.
- **Energy score, variogram score, multivariate proper scores** — no agent use case for jointly-scored multivariate forecasts.
- **Ranked Probability Score for ordered categories** — real but rare; the binary and continuous cases cover essentially all agent forecasts.
- **Murphy diagrams (elementary-score mixture representation)** — mathematically the right way to show dominance across all decision thresholds, but it is fundamentally a plot and an agent consumes numbers.
- **Spherical score** — strictly proper and mentioned in the brief, but offers nothing Brier and log do not, and has no established interpretation for practitioners; keep as a one-line option, not a tool.
- **Prequential / defensive forecasting (Foster-Vohra, Vovk)** — beautiful asymptotic calibration guarantees, entirely vacuous at n = 30.
- **Giacomini-White conditional predictive ability, Clark-West, Model Confidence Set** — the statistically correct answers for nested comparison and multi-model selection, but all need far more data than an agent will ever have.
- **Coverage Width-based Criterion (CWC) and similar coverage/width composites** — improper: they can be gamed by widening intervals, which is the exact opposite of what this territory is for.
- **PINAW / interval-width-only metrics** — sharpness without calibration; already folded into the interval score decomposition.
- **Rank histograms for ensembles** — the discrete analogue of the PIT histogram; same tool, and agents do not produce ensembles.
- **Threshold-weighted CRPS / weighted scoring rules** — niche tail-focused variants; the weighting choice is another lever to get wrong.
- **Bootstrap bias-corrected ECE as a headline metric** — the bias correction is real, but fixing the estimator of a metric that is conceptually wrong for sparse forecasts is not worth the code.
- **Kolmogorov-Smirnov for PIT uniformity** — the KS distribution series is more numerics than the chi-square route for no gain at n < 100, and KS is insensitive in the tails where interval overconfidence shows up.
- **Brier score variance decomposition into more than three components (Stephenson et al. two-extra-terms)** — corrects a within-bin bias that vanishes entirely when grouping on exact discrete values.
- **Logit-normal / Gaussian-process calibration maps** — more parameters, no closed form, no stdlib path.

---

## 6. Cross-territory overlaps

- **Binomial proportion inference** — Wilson, Jeffreys, Clopper-Pearson intervals and the exact
  binomial test are load-bearing in rows 5, 9, and 12. Should live once, in a proportions territory,
  and be imported here.
- **Bayesian inference / beta-binomial conjugacy** — the shrinkage estimator in §4.3 is a
  beta-binomial posterior mean. Priors, shrinkage strength, and hierarchical pooling across
  confidence levels all belong to the Bayesian territory; this territory is its highest-value
  consumer.
- **Logistic regression** — rows 7 and 18 are logistic regressions with fixed feature maps. The
  Newton/IRLS solver, separation detection, and Wald/profile CIs should be shared infrastructure.
- **Bootstrap and resampling** — row 16 is a general facility; the paired bootstrap, BCa, and seed
  discipline are cross-cutting.
- **Distribution functions layer** — this territory needs the normal CDF/quantile (stdlib), the
  regularized lower incomplete gamma (chi-square tails, rows 9/13/22), and the regularized
  incomplete beta (t-distribution for row 15, Jeffreys interval for row 5). These are the ASA032 /
  ASA063 dependencies already identified in RESEARCH.md §0.7.
- **Hypothesis testing and multiplicity** — running rows 1, 4, 6, 9, 15 and 22 on the same log is six
  tests; a false-discovery correction or an explicit "these are diagnostics, not confirmatory tests"
  framing is required.
- **Time series** — the Newey-West HAC variance in row 15 and the first-order Markov structure in
  row 22 are time-series machinery; autocorrelation of an agent's forecast errors across a session is
  a real phenomenon (same context, correlated mistakes).
- **Decision theory / expected value** — a calibrated probability only pays off when it enters a
  decision. The natural downstream consumer: expected-value calculations, cost-weighted thresholds,
  and value-of-information all require the probability entering them to have passed through this
  territory first.
- **Sequential testing and stopping rules** — an agent that re-runs its calibration check after every
  new resolved prediction is peeking. Either fix a review cadence or use an always-valid
  (e-value / confidence-sequence) formulation.
- **A/B testing and experiment design** — row 12 is a power calculation and shares all its
  machinery with sample-size planning elsewhere in the module.
- **The router / Tier-0 gate** — row 12 is arguably not a statistical model at all but a *gate*: it
  is the tool that tells the agent whether any other tool in this territory may run. It should
  probably be wired into the router rather than sitting in the catalogue.

---

## 7. Sources

**Foundational scoring and calibration theory**

- Brier, G. W. (1950). Verification of forecasts expressed in terms of probability. *Monthly Weather Review* 78(1), 1–3.
- Murphy, A. H. (1973). A new vector partition of the probability score. *Journal of Applied Meteorology* 12, 595–600.
- Gneiting, T. & Raftery, A. E. (2007). Strictly proper scoring rules, prediction, and estimation. *JASA* 102(477), 359–378. https://www.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf
- Gneiting, T., Balabdaoui, F. & Raftery, A. E. (2007). Probabilistic forecasts, calibration and sharpness. *JRSS-B* 69(2), 243–268. https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jrssb.pdf
- Bröcker, J. (2009). Reliability, sufficiency, and the decomposition of proper scores. https://pure.mpg.de/rest/items/item_2220390/component/file_2220389/content
- Siegert, S. (2017). Simplifying and generalising Murphy's Brier score decomposition. *QJRMS* 143, 1178–1183. https://rmets.onlinelibrary.wiley.com/doi/abs/10.1002/qj.2985
- Jordan, A., Krüger, F. & Lerch, S. (2019). Evaluating probabilistic forecasts with scoringRules. *JSS* 90(12). https://www.jstatsoft.org/article/view/v090i12

**Reliability diagrams and modern decomposition**

- Dimitriadis, T., Gneiting, T. & Jordan, A. I. (2021). Stable reliability diagrams for probabilistic classifiers. *PNAS* 118(8). https://www.pnas.org/doi/10.1073/pnas.2016191118
- Gneiting, T. & Resin, J. (2023). Regression diagnostics meets forecast evaluation: conditional calibration, reliability diagrams, and coefficient of determination. *EJS* 17(2). https://arxiv.org/abs/2108.03210

**ECE, its biases, and consistent alternatives**

- Guo, C., Pleiss, G., Sun, Y. & Weinberger, K. Q. (2017). On calibration of modern neural networks. *ICML*. https://arxiv.org/abs/1706.04599
- Nixon, J. et al. (2019). Measuring calibration in deep learning. https://openreview.net/pdf?id=r1la7krKPS
- Kumar, A., Liang, P. & Ma, T. (2019). Verified uncertainty calibration. *NeurIPS*. https://arxiv.org/abs/1909.10155
- Vaicenavicius, J. et al. (2019). Evaluating model calibration in classification. *AISTATS*. https://arxiv.org/abs/1902.06977
- Roelofs, R., Cain, N., Shlens, J. & Mozer, M. C. (2022). Mitigating bias in calibration error estimation. *AISTATS*. https://openreview.net/forum?id=NgZKCRKaY3J
- Błasiok, J., Gopalan, P., Hu, L. & Nakkiran, P. (2023). A unifying theory of distance from calibration. *STOC*. https://arxiv.org/abs/2211.16886
- Błasiok, J. & Nakkiran, P. (2024). Smooth ECE: principled reliability diagrams via kernel smoothing. *ICLR*. https://arxiv.org/abs/2309.12236
- Minderer, M. et al. (2021). Revisiting the calibration of modern neural networks. *NeurIPS*. https://openreview.net/pdf?id=QRBvLayFXI
- Understanding Model Calibration — ICLR 2025 Blogposts. https://iclr-blogposts.github.io/2025/blog/calibration/
- A comprehensive review of classifier probability calibration metrics (2025). https://arxiv.org/pdf/2504.18278

**Recalibration methods**

- Platt, J. (1999). Probabilistic outputs for support vector machines. *Advances in Large Margin Classifiers*.
- Zadrozny, B. & Elkan, C. (2002). Transforming classifier scores into accurate multiclass probability estimates. *KDD*.
- Kull, M., Silva Filho, T. & Flach, P. (2017). Beta calibration. *AISTATS* 54. https://proceedings.mlr.press/v54/kull17a/kull17a.pdf · https://betacal.github.io/
- Silva Filho, T. et al. (2023). Classifier calibration: a survey on how to assess and improve predicted class probabilities. *Machine Learning* 112. https://arxiv.org/pdf/2112.10327

**Clinical prediction: calibration measures, models, sample size**

- Spiegelhalter, D. J. (1986). Probabilistic prediction in patient management and clinical trials. *Statistics in Medicine* 5(5), 421–433.
- Huang, Y., Li, W., Macheret, F., Gabriel, R. A. & Ohno-Machado, L. (2020). A tutorial on calibration measurements and calibration models for clinical prediction models. *JAMIA* 27(4), 621–633. https://academic.oup.com/jamia/article/27/4/621/5762806
- Van Calster, B. et al. (2019). Calibration: the Achilles heel of predictive analytics. *BMC Medicine* 17, 230. https://link.springer.com/article/10.1186/s12916-019-1466-7
- Riley, R. D. et al. (2021). Minimum sample size for external validation of a clinical prediction model with a binary outcome. *Statistics in Medicine* 40(19). https://onlinelibrary.wiley.com/doi/full/10.1002/sim.9025
- Spiegelhalter's Z-test — calzone documentation. https://calzone-docs.readthedocs.io/en/latest/notebooks/spiegelhalter_z.html

**Skill scores, sampling uncertainty, forecast comparison**

- Weigel, A. P., Liniger, M. A. & Appenzeller, C. (2007). The discrete Brier and ranked probability skill scores. *MWR* 135(1), 118–124. https://journals.ametsoc.org/view/journals/mwre/135/1/mwr3280.1.pdf
- Bradley, A. A., Schwartz, S. S. & Hashino, T. (2008). Sampling uncertainty and confidence intervals for the Brier score and Brier skill score. *Weather and Forecasting* 23(5). https://journals.ametsoc.org/downloadpdf/view/journals/wefo/23/5/2007waf2007049_1.pdf
- Using the debiased Brier skill score to evaluate S2S tropical cyclone forecasting (2025). *JMSE* 13(6), 1035. https://www.mdpi.com/2077-1312/13/6/1035
- Diebold, F. X. & Mariano, R. S. (1995). Comparing predictive accuracy. *JBES* 13(3), 253–263.
- Harvey, D., Leybourne, S. & Newbold, P. (1997). Testing the equality of prediction mean squared errors. *IJF* 13(2), 281–291.
- Diebold, F. X. (2015). Comparing predictive accuracy, twenty years later. *JBES* 33(1). https://www.sas.upenn.edu/~fdiebold/papers/paper114/Diebold_JBES.pdf
- Forecast evaluation tests and negative long-run variance estimates in small samples. *IJF* (2018). https://www.sciencedirect.com/science/article/abs/pii/S0169207017300559

**Coverage testing**

- Kupiec, P. (1995). Techniques for verifying the accuracy of risk measurement models. *Journal of Derivatives* 3(2).
- Christoffersen, P. F. (1998). Evaluating interval forecasts. *International Economic Review* 39(4), 841–862.
- Winkler, R. L. (1972). A decision-theoretic approach to interval estimation. *JASA* 67(337).
- Overview of VaR backtesting (Kupiec / Christoffersen implementations). https://www.mathworks.com/help/risk/overview-of-var-backtesting.html

**LLM and agent calibration**

- The Confidence Dichotomy: Analyzing and Mitigating Miscalibration in Tool-Use Agents (2026). https://www.arxiv.org/pdf/2601.07264
- Wired for Overconfidence: A Mechanistic Perspective on Inflated Verbalized Confidence in LLMs. COLM 2026. https://arxiv.org/pdf/2604.01457
- Asking Is Not Enough: Protocol Sensitivity in LLM Confidence Calibration (2026). https://arxiv.org/pdf/2605.27752
- ConfidenceBench: Evaluating Confidence Calibration in Large Language Models (2026). https://arxiv.org/html/2607.20526
- Large Language Models Are Overconfident in Their Own Responses (2026). https://arxiv.org/pdf/2606.03437
- Mind the Confidence Gap: Overconfidence, Calibration, and Distractor Effects in LLMs (2025). https://arxiv.org/pdf/2502.11028
- Taming Overconfidence in LLMs: Reward Calibration in RLHF (2024). https://arxiv.org/pdf/2410.09724
- On Verbalized Confidence Scores for LLMs (2024). https://arxiv.org/html/2412.14737v2
- Xiong, M. et al. (2024). Can LLMs express their uncertainty? An empirical evaluation of confidence elicitation. *ICLR*. https://arxiv.org/abs/2306.13063
- Tian, K. et al. (2023). Just ask for calibration. *EMNLP*. https://arxiv.org/abs/2305.14975
- Lin, S., Hilton, J. & Evans, O. (2022). Teaching models to express their uncertainty in words. *TMLR*. https://arxiv.org/abs/2205.14334
