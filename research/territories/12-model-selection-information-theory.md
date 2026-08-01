# Territory 12 — Model Selection, Information Theory, and Evidence for Explanations

Research pass for the Intelligence Module. Scope: what an agent should compute when it is choosing
between explanations, deciding whether a pattern is real, or pricing its own surprise — under the
hard constraint of **pure Python 3 stdlib** (`math`, `statistics`, `random`, `itertools`) at
**agent scale** (n of 3–200, 2–10 candidate models).

---

## 1. Territory summary

This territory answers four agent questions that unaided judgment gets systematically wrong: *which
of these explanations is better supported*, *is this pattern real or am I reading tea leaves*, *how
much does this extra factor actually explain*, and *how surprising is this observation*. The unifying
mathematics is that **evidence is measured in log-likelihood and paid for in bits**: every parameter
fitted, every model compared, and every pattern noticed after looking at the data has a price, and
the entire territory is bookkeeping on that price. An agent's dominant failure is not computing a
statistic wrongly — it is failing to charge itself for the search it already performed, so the
highest-value tools here are the ones that make the implicit comparison count explicit and refuse to
produce a number until the agent states it. Small-n behaviour inverts several textbook intuitions
(AIC is *stricter* than BIC below n≈7; plug-in mutual information is biased *upward* and is never
zero; leave-one-out cross-validation standard errors are meaningless below n≈15), so this library
must implement small-sample corrections as the default path, not as an option. Finally, most of this
territory can be implemented without any special functions at all — permutation, bootstrap,
sample-splitting, and e-values buy asymptotic-free validity with CPU cycles, which is exactly the
right trade at agent scale.

**Design consequence up front.** The only special function this territory genuinely needs is the
regularized upper incomplete gamma function (chi-square survival, for Wilks/G-tests). Rows 2, 3, 4,
7, 8, 9, 14, 17, 18 avoid it entirely. If that function is expensive or accuracy-risky to ship, a
credible 80% of this territory still ships on `math.log`, `math.lgamma`, and `random.shuffle`.

---

## 2. Ranked model table

Tiers: **INLINE** = a handful of numbers as CLI flags. **DATAFILE** = a small dataset in a file.
**MUST-CONSTRUCT-DATA** = the agent has to assemble a dataset (or a candidate-model list) that does
not yet exist before the tool is usable.

| # | Model / method | SITUATION (agent phrasing + alternates) | Minimum viable inputs + tier | Beats what | Stdlib feasibility + numerics | REFUSE conditions |
|---|---|---|---|---|---|---|
| 1 | **AICc + Akaike weights + evidence ratios** (Hurvich–Tsai; Burnham–Anderson) | "Which of these two/three explanations fits better without just being more complicated?" · "Is the extra term in this model earning its keep?" · "I have several competing stories for this data — rank them." | Per model: log-likelihood, k (params, **including σ² for Gaussian**), shared n. INLINE. Or raw data + candidate fits → DATAFILE. | Agents eyeball "model B fits better" from residuals and never price the extra parameters. Also beats plain AIC, which over-selects hard at agent n. | **EASY.** `exp`, `log`. AICc = −2lnL + 2k + 2k(k+1)/(n−k−1); w_i = exp(−Δ_i/2)/Σexp(−Δ_j/2). | n − k − 1 ≤ 0 (AICc undefined) → refuse. Models fit to **different data, different n, or different response transforms** (y vs log y without Jacobian) → refuse; the comparison is meaningless. Best model's weight < 0.6 → print the weight distribution, refuse to name a winner. Candidate set of 1 → refuse (nothing to select). |
| 2 | **Implicit-comparison audit** (garden of forking paths → Šidák/Bonferroni + Benjamini–Yekutieli FCR intervals) | "I noticed this pattern after looking at the data — how much should I discount it?" · "How many things could I have noticed that would have looked just as interesting?" · "Is this p-value honest given I went looking?" | Nominal p (or effect + SE), plus **m = number of analyses the agent could plausibly have run**. INLINE. | This is the single biggest agent self-deception. Unaided, the agent reports the nominal p from an analysis that was *chosen because it looked good*. Nothing else in the library corrects for that. | **EASY.** p_adj = 1 − (1−p)^m (Šidák) or min(1, m·p). FCR interval level = 1 − q·R/m. | **m not supplied or m = 1 when the tool detects the hypothesis was formed post-hoc → hard refuse.** The tool must interrogate: outcome choices × subgroup choices × cutoff choices × exclusion choices × direction. If the agent cannot bound m, it cannot have a number. Also refuse if p came from the same data that suggested the hypothesis and no split is available — route to row 4. |
| 3 | **Permutation / randomization test** | "Is this pattern real or am I reading tea leaves?" · "Could this association have happened by chance?" · "Would shuffling the labels produce something this strong?" | Two labelled columns, or paired x/y. n ≥ 5 per group. DATAFILE. | Beats any parametric test at tiny n because it makes no distributional assumption; beats the agent's intuition about "that looks like a trend" outright. | **EASY.** `random.shuffle` (or `itertools.permutations` for exact enumeration when C(n,k) ≤ 20000). p = (1 + #{T* ≥ T_obs})/(1 + B). | **Minimum achievable p > requested α → refuse.** With n₁=n₂=3 there are only C(6,3)=20 distinct splits, so the smallest two-sided p is 0.10 — the test *cannot* reject at 0.05 and must say so rather than print 0.10. Never report p = 0 (Phipson–Smyth +1). Refuse if the exchangeability assumption is broken (paired/time-ordered data shuffled as if independent). |
| 4 | **Split-sample validation of a post-hoc hypothesis** — incl. the **split likelihood-ratio test / universal inference** (Wasserman–Ramdas–Balakrishnan) | "I formed this theory from the data — how do I test it honestly?" · "Can I confirm the pattern I just found?" · "I want a real p-value for something I discovered by looking." | Dataset with ≥ 20 rows (10 per half), a hypothesis expressed as a fitted model, a null model. DATAFILE / MUST-CONSTRUCT-DATA. | The *only* fully honest answer to the forking-paths problem. Row 2 discounts; this one actually restores validity. Beats Wilks because it needs **no regularity conditions and no asymptotics** — finite-sample valid. | **EASY.** Split D into D₀/D₁; fit θ̂₁ on D₁ by any method; U = L_{D₀}(θ̂₁)/L_{D₀}(θ̂₀); reject at α when U ≥ 1/α. No incomplete gamma needed. U is also a valid e-value (composes with rows 8, 17). | n < 20 → refuse: neither half can support a fit. Refuse if the "held-out" half was inspected during hypothesis formation (the agent must attest, and the tool should ask). Refuse if the split is not random w.r.t. any ordering in the data. Report the power cost explicitly — this test is deliberately weaker than the dishonest one. |
| 5 | **Likelihood ratio test (Wilks)** | "Does adding this factor explain significantly more?" · "Is the richer model justified?" · "How much of the improvement is just extra parameters?" | lnL₀, lnL₁, df = k₁ − k₀. INLINE. Or data + two nested fits → DATAFILE. | Gives a calibrated p for the nested comparison that AICc only ranks. Agents habitually treat any lnL improvement as meaningful; a 2-parameter model *always* beats a 1-parameter nested model on lnL. | **MODERATE.** Λ = 2(lnL₁ − lnL₀); p = Q(df/2, Λ/2) — needs **regularized upper incomplete gamma** (ASA032 / Cephes `igamc`). Only special function in the territory. | Models **not nested** → refuse, route to row 11. Parameter **on the boundary** of its space (variance = 0, mixture weight = 0) → naive df is wrong (Self–Liang: 50:50 χ²₀/χ²₁ mixture) → refuse. n/df < 10 → refuse or downgrade to row 4 (asymptotics not credible at agent n). Λ < 0 → refuse; the fit failed to converge. |
| 6 | **BIC + Kass–Raftery Bayes-factor scale** | "How strongly does the data favour explanation A over B?" · "Is this evidence weak, positive, or decisive?" · "Give me odds, not a ranking." | Same as row 1: lnL, k, n per model. INLINE. | Converts an unscaled Δ into an interpretable evidence statement. BF₁₀ ≈ exp((BIC₀ − BIC₁)/2). Agents will read Δ = 3 as "much better"; the Kass–Raftery scale says "positive, not strong". | **EASY.** BIC = −2lnL + k·ln n. Scale on 2·lnBF: 0–2 bare mention, 2–6 positive, 6–10 strong, >10 very strong. | Same data/n/transform checks as row 1. Refuse to present BIC weights as posterior model probabilities unless the agent states equal prior model probabilities (they are only that under a unit-information prior and equal priors). **Refuse to describe Δ < 2 as evidence for anything.** |
| 7 | **Surprisal / self-information, with search correction** | "How surprising is this observation, really?" · "Is this a one-in-a-hundred event or a one-in-a-billion event?" · "Should I be alarmed by this number?" | p (or a reference distribution + observed value). INLINE. | Turns vague alarm into bits and a "1 in N" anchor. Crucially: if the agent scanned m things and reported the most extreme, the honest surprisal is **−log₂p − log₂m bits** — the information-theoretic form of Bonferroni. Agents never subtract the search cost. | **EASY.** I(x) = −log₂ p; N = 1/p. Tail-based for continuous variables. | **Density used in place of tail probability for a continuous variable → refuse** (a density is not a probability; it isn't even unitless). p = 0 → refuse, demand a smoothed/regularized model. m unspecified when the observation was selected as "the most extreme" → refuse, route to row 2. |
| 8 | **Holm step-down + Benjamini–Hochberg FDR (+ e-BH)** | "I checked forty metrics and three look anomalous — which do I believe?" · "I ran a bunch of tests, how many are real?" · "Which of these findings survive correction?" | A list of p-values (m ≥ 3) and a target α or FDR q. INLINE (short list) / DATAFILE. | Bonferroni alone is needlessly brutal; Holm strictly dominates it at no cost. BH answers the *right* question for an exploring agent ("what fraction of my flags are false") rather than the wrong one ("did I make any error at all"). | **EASY.** Sorting only. Holm: reject p₍ᵢ₎ while p₍ᵢ₎ ≤ α/(m−i+1). BH: largest i with p₍ᵢ₎ ≤ (i/m)q. e-BH: largest k with e₍ₖ₎ ≥ m/(kq) — valid under **arbitrary dependence**. | m = the number *reported*, not the number *run* → refuse; the tool must demand the true count. Strongly dependent p-values with BH → switch to Benjamini–Yekutieli (÷ H_m) or e-BH, don't silently use BH. m < 3 → refuse, use row 2 directly. Refuse if p-values came from tests whose assumptions were already violated (garbage in). |
| 9 | **Bootstrap model-selection stability** | "Am I overfitting this pattern to three data points?" · "If I had slightly different data, would I reach the same conclusion?" · "How fragile is this model choice?" | Dataset + ≥2 candidate models + a fit routine. DATAFILE / MUST-CONSTRUCT-DATA. | The most direct available answer to "am I overfitting". Resample n with replacement B≈1000 times, refit, record the AICc winner each time. A model that wins 52% of the time is *not* the answer, and no criterion value reveals that. | **EASY–MODERATE.** `random.choices` + refit loop. Cost is B × (fit cost); at agent n that is nothing. Report selection frequency + bootstrap distribution of Δ. | Winner frequency < 0.60 → **refuse to name a best model**; return the frequency table. n < 10 → refuse (bootstrap resamples of tiny n are degenerate; many resamples will be rank-deficient). Refuse if any resample fails to fit and failures exceed 5% — report the instability instead. |
| 10 | **LOO / k-fold CV with small-n guards and the one-SE rule** | "How well will this actually generalize?" · "Is this fit real or memorized?" · "What's my honest out-of-sample error?" | Dataset (n ≥ 15) + candidate models + a fit routine. DATAFILE / MUST-CONSTRUCT-DATA. | Direct out-of-sample estimate, no likelihood needed, no parametric form assumed. The one-SE rule (Breiman) prevents chasing a difference inside the noise. | **MODERATE.** n refits for LOO. Needs a clean fit/predict seam and a loss. | **n < 15 → refuse to print a CV standard error.** LOO folds share n−1 of n points, so fold errors are near-perfectly correlated and the naive SE (sd/√k) is not an SE of anything (Bates–Hastie–Tibshirani: naive CV intervals badly undercover even at large n). Refuse if any tuning/selection happens *inside* a fold's training set without being re-run per fold (Cawley–Talbot leakage) — the tool must wrap the whole pipeline. Refuse for time-ordered data unless blocked/forward-chaining CV is requested. |
| 11 | **Paired pointwise log-likelihood test (Vuong; or bootstrap/sign test on Δlnℓᵢ)** | "Model A has a lower AIC — but is that gap bigger than noise?" · "These two non-nested explanations are close; can I actually tell them apart?" · "Is the difference between these models meaningful?" | Per-observation log-likelihoods under both models (n values each). DATAFILE. | Fills the biggest hole in rows 1 and 6: AICc/BIC give a *ranking* with no uncertainty. This says whether the gap survives resampling. Also handles non-nested models, which Wilks cannot. | **EASY.** dᵢ = lnf₁(xᵢ) − lnf₂(xᵢ); z = Σdᵢ /(√n · sd(d)) → `NormalDist().cdf`. Robust variant: paired bootstrap or sign test on the dᵢ — no normality needed and preferred at agent n. | Models **nested** → refuse (Vuong's null is degenerate there; use row 5). Models overlapping/indistinguishable in the limit → known size distortion (Shi 2015) → report the robust bootstrap version only. n < 20 → use sign/bootstrap variant, refuse the z-statistic. Refuse if pointwise likelihoods came from different observation sets. |
| 12 | **Mutual information with Miller–Madow correction, permutation null, and the ln n ceiling** | "Are these two things actually related?" · "How much does knowing X tell me about Y?" · "Is this association real or an artifact of small counts?" | Two aligned categorical columns (or binned continuous). n, K_X, K_Y. DATAFILE. | Catches dependence that correlation misses (non-monotone, categorical). Critically: **naive plug-in MI is biased upward and is essentially never zero even for independent variables** — E[Î] ≈ I + (K_X−1)(K_Y−1)/(2n). An agent reading a raw MI of 0.15 nats off 20 samples of two independent variables will believe in a relationship that does not exist. | **MODERATE.** Î_MM = Î_plugin − (K_X−1)(K_Y−1)/(2n). Permutation null via `random.shuffle` of one column. Optional G-test: 2n·Î ~ χ²_{(K_X−1)(K_Y−1)}. | **Report above ln(n) nats → refuse.** McAllester–Stratos (2020): no distribution-free high-confidence lower bound on MI from n samples can exceed ln n; anything larger is unsupportable. n < 5·K_X·K_Y → refuse the point estimate, return only the permutation p-value. Continuous data silently binned without the agent choosing bins → refuse (MI is not bin-invariant). Any joint cell count of 0 with both marginals nonzero at small n → flag undersampling. |
| 13 | **Optimism / effective-df accounting (adjusted R², shrinkage, in-vs-out gap)** | "How much of this fit is real?" · "How much does this extra factor actually explain?" · "I added three variables and R² went up — did I learn anything?" | R², n, p (number of predictors). INLINE. Richer version: DATAFILE. | R² is monotone in p — it *cannot* go down when you add a variable, so it is worthless for the agent's actual question. Adjusted R² = 1 − (1−R²)(n−1)/(n−p−1) can go negative, and that negative number is a real, actionable signal. | **EASY.** Arithmetic only. Also serves as Van Houwelingen's shrinkage estimate of out-of-sample R². | n − p − 1 ≤ 0 → refuse (saturated/over-parameterized; R² = 1 is arithmetic, not evidence). **Adjusted R² < 0 → refuse to report any explanatory power**; state that the model predicts worse than the mean. Refuse if p counts only the variables *kept* rather than the variables *tried* — the effective df must include the search (route to row 19). |
| 14 | **Exact beta-binomial Bayes factor for rates and proportions** | "Is this success-rate difference real?" · "2 out of 3 vs 5 out of 6 — does that mean anything?" · "How much evidence do these counts give me?" | s₁, n₁, s₂, n₂ (+ optional prior a, b; default 1,1). INLINE. | **Exact** — no asymptotics, no normal approximation, valid at n = 3. This is the single most common agent situation (comparing two small success counts) and the one where χ²/z-tests are least valid. Usually returns "essentially no evidence", which is the correct and unwelcome answer. | **EASY.** `math.lgamma` only. Binomial coefficients cancel: BF_{sep:shared} = B(a+s₁,b+f₁)·B(a+s₂,b+f₂) / [B(a,b)·B(a+s₁+s₂, b+f₁+f₂)]. | Refuse if the counts were selected as the most extreme of several comparisons without m (route to row 2). Refuse to report a single BF without a **prior-sensitivity band** over at least Beta(1,1), Jeffreys Beta(½,½), and one informative prior — BFs are prior-sensitive and a diffuse prior mechanically favours the null (Lindley–Jeffreys). n = 0 in either arm → refuse. |
| 15 | **Multiverse / specification-curve enumeration** (Steegen et al.; Simonsohn et al.) | "My conclusion depends on choices I made arbitrarily — does it survive?" · "What if I'd binned/filtered/excluded differently?" · "Show me all the reasonable analyses, not just mine." | An enumerable set of defensible analysis choices + a dataset. MUST-CONSTRUCT-DATA (the agent must write the choice grid). | Converts the forking-paths problem from a *penalty* (row 2) into a *measurement*: run all 48 defensible pipelines, report the distribution of the result. If 40/48 agree, that is far stronger evidence than one p-value; if 25/48 do, the finding is a choice, not a fact. | **EASY–MODERATE.** `itertools.product` over the choice grid + repeated fits. Report median, IQR, and fraction of specs crossing zero / reaching significance. | Grid size > ~5000 → refuse (cost) or demand sampling. **Refuse if the grid was constructed after seeing which specs work** — the choices must be defensible a priori. Refuse to report only the fraction significant without the effect-size distribution (that reintroduces dichotomania). Refuse if any spec is not genuinely defensible (a stacked deck is worse than one analysis). |
| 16 | **KL divergence with support/smoothing guard** | "How far is what I observed from what I expected?" · "Has this distribution shifted?" · "How much information do I lose using my model instead of the truth?" | Two aligned discrete distributions (or counts + a model). DATAFILE / INLINE for small K. | Gives an interpretable bits-of-surprise-per-observation. Via Sanov, P(observing P̂) ≈ exp(−n·D(P̂‖Q)) — turns divergence directly into "how unlikely was this sample". | **EASY.** D = Σ p log(p/q). 2n·D (nats) ~ χ²_{K−1} → the G-test (needs row 5's incomplete gamma if a p-value is wanted). | **q = 0 where p > 0 → D is infinite → refuse** and demand smoothing (Laplace/Krichevsky–Trofimov) with the smoothing constant reported, because D is highly sensitive to it. Refuse to present D as symmetric or as a distance. Refuse if the two distributions are over different or reordered support. Refuse to interpret raw D without the n-scaled version — D alone has no significance meaning. |
| 17 | **e-values / likelihood-ratio evidence for repeated or sequential checking** | "I keep re-checking as more data arrives — when can I stop?" · "I've looked at this five times; is my p-value still valid?" · "Can I accumulate evidence as it comes in?" | Per-observation likelihood ratios under H₁ vs H₀ (or a chosen alternative), arriving in sequence. INLINE (streamed) / DATAFILE. | Repeated peeking destroys p-value validity, and an agent that polls a metric until it looks significant *will* find significance. e-values are **anytime-valid**: stop whenever, reject when e ≥ 1/α, type-I error still ≤ α (Markov). Nothing else in the territory survives optional stopping. | **EASY.** e = Π LRᵢ (product form) or average across studies (valid under arbitrary dependence). Composes with row 4's split-LRT and row 8's e-BH. | Refuse if the alternative was chosen **after** seeing the data (that voids the e-value; use a mixture/plug-in alternative instead). Refuse if the agent wants a p-value from a peeked-at process — offer 1/e as a conservative p bound and say so. Refuse to product-combine e-values from dependent sources; average instead. |
| 18 | **Savage–Dickey density ratio (conjugate cases only)** | "How much does the data favour 'no effect' over 'some effect'?" · "Can I get evidence *for* the null?" · "Is this parameter actually zero?" | Prior family + hyperparameters, data sufficient statistics, the null value θ₀. INLINE. | Frequentist tests cannot support a null; this can. BF₀₁ = posterior(θ₀)/prior(θ₀) — a division of two densities, no integration. Answers the very common agent question "is it fair to say nothing is going on here?" | **MODERATE.** Beta–binomial: Beta pdf via `lgamma`. Normal–normal (known σ): `NormalDist().pdf`. Beyond conjugate cases it needs quadrature or MCMC → out of scope. | Non-conjugate model → refuse (no honest closed form). **Nuisance-parameter priors differing between M₀ and M₁ → refuse** (Verdinelli–Wasserman compatibility condition; the naive ratio is wrong — Marin & Robert 2010). Prior density at θ₀ ≈ 0 → refuse (numerically and conceptually unstable). Mandatory prior-sensitivity band, as row 14. |
| 19 | **MDL two-part code length with explicit search cost** | "Formally, is the simpler explanation better here?" · "How do I charge myself for having searched?" · "Occam's razor, but with a number." | lnL, k, n, **and the size of the search space actually explored**. INLINE. | The value over BIC is the third input. Two-part MDL charges L(model) + L(data|model) in bits, and L(model) legitimately includes **log₂(number of candidate structures considered)** — e.g. picking the best 2 of 10 features costs log₂C(10,2) ≈ 5.5 bits. This is the rigorous, non-hand-wavy version of "you looked first", and it is additive with the parameter cost. | **EASY.** L = −log₂L̂ + (k/2)log₂n + log₂|search space|. (The first two terms are BIC/(2 ln2), which is the point.) | Refuse if the search-space size is unstated — without it this is just BIC with extra steps and the tool should say so and route to row 6. Refuse to compare code lengths computed with different coding conventions or different data encodings. Do not claim NML/stochastic complexity — the normalizing term is intractable here (see cut list). |
| 20 | **Entropy with Miller–Madow correction and undersampling refusal** | "How predictable/diverse is this set of outcomes?" · "How much uncertainty is there here?" · "How concentrated is this distribution?" | A list of categorical observations or counts. DATAFILE / INLINE for small K. | Plug-in entropy is biased **downward** by ≈ (K−1)/(2n) — an agent will systematically overstate how predictable a small sample is. Miller–Madow is the cheapest defensible fix. | **EASY.** Ĥ_MM = −Σ p̂ log p̂ + (K̂−1)/(2n), K̂ = observed non-empty bins. | **n < 3K → refuse the point estimate** and report bounds only; Miller–Madow does not rescue the severely undersampled regime and remains biased low. Refuse if a large fraction of observed bins are singletons (coverage collapse). Refuse to compare entropies across datasets with different K or different n without stating both. Refuse to report entropy of continuous data binned without an explicit, agent-chosen binning. |
| 21 | **Conditional entropy / Theil's U (uncertainty coefficient)** | "How much of the variation in Y does X explain?" · "What fraction of the uncertainty does this factor remove?" · "Is this the categorical version of R²?" | Two aligned categorical columns. DATAFILE. | U(Y|X) = I(X;Y)/H(Y) ∈ [0,1] — an interpretable "X removes 23% of the uncertainty in Y", asymmetric (unlike Cramér's V), and defined where R² is not. Directly serves "how much does this extra factor actually explain" for non-numeric data. | **MODERATE.** Built on row 12; inherits its bias correction and permutation null. | Inherits every row-12 refusal (bias, ln n ceiling, undersampling). Additionally: H(Y) ≈ 0 → refuse (dividing by near-zero uncertainty; U is undefined/unstable). Refuse to report U symmetrically — U(Y|X) ≠ U(X|Y) and conflating them is a common error. |
| 22 | **AIC-vs-BIC disagreement detector** | "My two criteria disagree — which do I trust?" · "Should I optimize for prediction or for finding the true model?" · "Why do I get different answers from different criteria?" | Both criteria's rankings from rows 1 and 6. INLINE. | Disagreement is *information*, not a tie to break by preference: AIC targets predictive accuracy (asymptotically efficient, minimizes expected KL to truth), BIC targets recovering the true model if it is in the candidate set (consistent). When they split, the honest report is "the data cannot distinguish; here is what each objective implies". | **EASY.** Comparison logic + one counterintuitive fact worth surfacing: the penalties are equal at k·ln n = 2k, i.e. **n = e² ≈ 7.39**. Below n ≈ 7, AIC penalizes complexity *more* than BIC. | Refuse to break the tie by fiat. Refuse to invoke BIC's consistency guarantee if the agent cannot claim the true model is in the candidate set (it usually is not) — then AIC's objective is the relevant one. Refuse to apply the "BIC is stricter" heuristic at n < 8 without flagging the inversion. |

---

## 3. Recent advances (~last 10 years)

**Universal inference / the split likelihood-ratio test (2020).** Wasserman, Ramdas & Balakrishnan
showed that splitting the sample, fitting the alternative on one half by *any* method, and evaluating
the likelihood ratio on the other half yields a test with finite-sample validity under **no
regularity conditions at all** — no Wilks asymptotics, no nesting requirement, no smoothness, valid
on the parameter-space boundary. For this library this is close to a gift: it removes the incomplete
gamma dependency, it is exactly the right medicine for post-hoc hypotheses, and the resulting
statistic is an e-value that composes with rows 8 and 17. Cost is power (roughly that of half the
data), which is an honest and explicit trade.
→ *PNAS* 117(29):16880–16890. https://arxiv.org/abs/1912.11436

**E-values, e-processes, and safe anytime-valid inference (2019–2024).** Vovk & Wang's e-values,
Grünwald–de Heide–Koolen's "Safe Testing", and Ramdas et al.'s game-theoretic framing give evidence
measures valid under optional stopping and optional continuation. Wang & Ramdas's **e-BH** procedure
controls FDR under *arbitrary dependence* with a three-line algorithm — strictly better suited to an
agent that checks many things with unknown correlation structure than BH is. This is the most
directly agent-relevant advance in the territory: agents poll, re-check, and accumulate evidence
incrementally, and classical p-values are simply invalid under that behaviour.
→ Vovk & Wang, *AoS* 49(3), https://arxiv.org/abs/1912.06116 · Wang & Ramdas, *JRSS-B* 84(3),
https://arxiv.org/abs/2009.02824 · Grünwald et al., *JRSS-B*, https://arxiv.org/abs/1906.07801 ·
Ramdas et al., *Statistical Science* 38(4), https://arxiv.org/abs/2210.01948

**Cross-validation does not estimate what you think (2021–2024).** Bates, Hastie & Tibshirani proved
that CV estimates the *average* prediction error over the population of training sets of that size —
not the error of the specific model you fit — and that naive CV confidence intervals undercover
substantially, because fold errors are correlated. At agent-scale n this is not a subtlety, it is
disqualifying for the standard error. It is the direct justification for row 10's refusal to print an
SE below n = 15.
→ *JASA* 119(546):1434–1445. https://arxiv.org/abs/2104.00673

**Formal limits on measuring mutual information (2020).** McAllester & Stratos proved that any
distribution-free high-confidence *lower* bound on MI computed from n samples cannot exceed ln n.
This converts a vague "small-sample MI is unreliable" warning into a hard, checkable refusal rule
(row 12) with a theorem behind it. It also explains why the neural MI estimators of the same era
(MINE, InfoNCE) saturate — they are bounded by log(batch size).
→ AISTATS 2020. https://arxiv.org/abs/1811.04251

**Selective / post-selection inference (2013–2016).** Berk et al.'s PoSI, Lee–Sun–Sun–Taylor's
polyhedral lemma for the lasso, and Taylor & Tibshirani's synthesis made "valid inference after
looking at the data" a rigorous field rather than a warning. The exact conditional machinery is out
of scope for pure stdlib (it needs the selection event's geometry), but the framing is the
intellectual backbone of rows 2, 4, and 19: **the selection event must enter the inference.**
→ Taylor & Tibshirani, *PNAS* 112(25):7629–7634 · Lee et al., *AoS* 44(3),
https://arxiv.org/abs/1311.6238

**Multiverse analysis and specification curves (2016–2020).** Steegen et al. and Simonsohn, Simmons &
Nelson turned analytic flexibility from a hazard into a deliverable: enumerate every defensible
pipeline and report the distribution of results. For an agent this is unusually natural — enumerating
a choice grid and running 50 small fits is a loop, not a research project. Row 15.
→ *Perspectives on Psychological Science* 11(5):702–712 · *Nature Human Behaviour* 4:1208–1214,
https://www.nature.com/articles/s41562-020-0912-z

**PSIS-LOO and the k̂ diagnostic (2017–2024).** Vehtari, Gelman & Gabry's PSIS-LOO, and the 2024 JMLR
paper's refinement of the threshold to **k̂ < min(1 − 1/log₁₀S, 0.7)** (replacing the fixed 0.5/0.7),
is the modern standard for Bayesian model comparison. It needs posterior draws, so it is out of scope
here — but the *design pattern* is squarely in scope and should be copied throughout: **ship a
self-diagnosing statistic that reports when it is not to be trusted, and make the threshold
sample-size dependent.** That is the architecture this whole library needs.
→ *Statistics and Computing* 27:1413–1432, https://arxiv.org/abs/1507.04544 · *JMLR* 25(72),
https://arxiv.org/abs/1507.02646 · thresholds: https://mc-stan.org/loo/reference/pareto-k-diagnostic.html

**Stacking beats selection (2018).** Yao, Vehtari, Simpson & Gelman showed that stacking LOO
predictive distributions outperforms both model selection and BMA when the true model is not in the
candidate set (the normal case). Full stacking needs a constrained optimizer, but for 2–3 candidates
a simplex grid search in pure Python is trivial — a plausible future row.
→ *Bayesian Analysis* 13(3):917–1007. https://arxiv.org/abs/1704.02030

**Bayesian entropy estimation.** NSB (Nemenman–Shafee–Bialek 2002) and Archer–Park–Pillow (2014)
substantially outperform Miller–Madow in the undersampled regime, but require numerical integration
over a Dirichlet hyperprior. Hausser & Strimmer's James-Stein shrinkage estimator (JMLR 2009) is the
best *cheap* alternative and is implementable in stdlib — a credible upgrade path for rows 12/20/21.
→ https://arxiv.org/abs/0811.3579

---

## 4. Cut list

- **WAIC / DIC** — require posterior draws; no MCMC in stdlib at usable quality.
- **Full PSIS-LOO** — same; needs posterior draws plus a GPD tail fit. The *diagnostic philosophy* is retained.
- **Bridge sampling / thermodynamic integration for marginal likelihoods** — requires MCMC.
- **Normalized maximum likelihood (NML) / stochastic complexity** — the normalizing constant is a sum over all datasets; intractable outside a few toy families. MDL is retained only in two-part form.
- **Minimum message length (MML)** — needs Fisher information determinants per model; too model-specific to expose generically.
- **Kolmogorov complexity / algorithmic Occam** — uncomputable. Cite as intuition, never as a tool.
- **Neural MI estimators (MINE, InfoNCE, CLUB)** — need a deep-learning stack, and are bounded by log(batch) anyway.
- **KSG k-nearest-neighbour MI for continuous variables** — genuinely implementable (O(n²) at agent n) but needs a digamma function that `math` does not provide, and is fragile below n≈100. **Revisit if a digamma lands in the numerics layer.**
- **Mallows' Cₚ** — equivalent to AIC for Gaussian models with known σ²; redundant with row 1.
- **Focused Information Criterion (FIC), TIC, EIC** — TIC needs a sandwich covariance estimate; FIC needs a declared focus parameter. Too much ceremony for the gain.
- **Bootstrap .632 / .632+ estimators** — marginal accuracy gain over LOO at agent n, with meaningfully more machinery and more ways to be silently wrong.
- **Nested cross-validation** — the correct fix for selection bias in CV, but needs two levels of splitting; at n < 100 it is vapour. Row 4 (split-sample) is the honest agent-scale substitute.
- **Storey q-values / π₀ estimation** — π₀ estimation is unstable below a few hundred p-values; agents have 5–50. BH/e-BH instead.
- **Reversible-jump MCMC, spike-and-slab, Bayesian variable selection** — far outside stdlib.
- **JZS / default Bayes factors for t-tests and correlations** — high value, but needs Gauss–Legendre or Simpson quadrature of a Cauchy-weighted integral. **Belongs to the hypothesis-testing territory; flag as a cross-territory candidate rather than cut outright.**
- **Full Bayesian model averaging with proper marginal likelihoods** — retained only in the BIC-weights approximation (row 6).
- **Cramér's V / Tschuprow's T** — symmetric association measures without the information-theoretic interpretation; row 21 dominates for the "how much does this explain" question.
- **Benjamini–Yekutieli FCR intervals as a standalone tool** — folded into row 2, where the selection context that makes them necessary actually lives.
- **Deviance residual diagnostics, Cook's distance, leverage** — regression diagnostics territory.
- **Log score / Brier decomposition / reliability diagrams** — calibration and scoring-rules territory, though they share the surprisal mathematics of row 7.

---

## 5. Cross-territory overlaps

| Overlapping territory | Shared machinery | Boundary to draw |
|---|---|---|
| Hypothesis testing & p-values | Permutation tests (row 3), Wilks LRT (row 5), G-test (rows 12, 16), multiplicity (rows 2, 8) | That territory owns "is this difference significant" for a *pre-specified* comparison. This one owns "how do I price the comparison I chose after looking". Multiplicity corrections should live **here** — they are the accounting layer, not the test layer. |
| Bayesian inference & priors | Bayes factors (rows 6, 14, 18), prior-sensitivity bands, conjugate updates | That territory owns posteriors and credible intervals for a single model. This one owns *comparison between* models. The beta-binomial and normal-normal conjugate machinery is shared code — build it once. |
| Resampling & the bootstrap | Bootstrap selection stability (row 9), paired bootstrap (row 11), permutation (row 3) | That territory owns CIs by resampling. This one owns resampling applied to *model choice*. Shared `random`-based resampling primitives. |
| Regression & effect size | Adjusted R², optimism, shrinkage (row 13), effective df | That territory owns fitting and coefficient inference. This one owns "how much of the fit is real" and the degrees-of-freedom ledger. |
| Calibration & scoring rules | Surprisal (row 7), log score, KL divergence (row 16) | Surprisal for a *single event* lives here; surprisal averaged over many predictions to assess a forecaster lives there. Same mathematics, different question. |
| Power & sample size | Minimum achievable permutation p (row 3), split-sample power cost (row 4), the ln n MI ceiling (row 12) | That territory answers "how much data do I need". This one answers "given the data I have, is any conclusion reachable at all" — a **pre-flight refusal check** that should probably be a shared primitive both territories call. |
| Causal inference & confounding | "How much does this extra factor explain" (rows 13, 21) | Sharp boundary: rows 13/21 measure *statistical* explanation only. Both tools must refuse causal language and say so in their output, or the agent will read "X explains 23% of Y" as a causal claim. |
| Anomaly & outlier detection | Surprisal (row 7), KL (row 16), multiplicity (rows 2, 8) | Detecting "the most extreme of m observations" is inherently a multiple-comparisons problem; that territory should be forced to route through row 2. |

---

## 6. Sources

**Information criteria**
- Akaike, H. (1974). A new look at the statistical model identification. *IEEE Trans. Automatic Control* 19(6):716–723.
- Hurvich, C. & Tsai, C.-L. (1989). Regression and time series model selection in small samples. *Biometrika* 76(2):297–307.
- Schwarz, G. (1978). Estimating the dimension of a model. *Annals of Statistics* 6(2):461–464.
- Burnham, K. & Anderson, D. (2004). Multimodel inference: understanding AIC and BIC in model selection. *Sociological Methods & Research* 33(2):261–304.
- Brewer, M., Butler, A. & Cooksley, S. (2016). The relative performance of AIC, AICc and BIC in the presence of unobserved heterogeneity. *Methods in Ecology and Evolution* 7(6). https://besjournals.onlinelibrary.wiley.com/doi/full/10.1111/2041-210x.12541

**Bayes factors**
- Kass, R. & Raftery, A. (1995). Bayes factors. *JASA* 90(430):773–795.
- Wagenmakers, E.-J., Lodewyckx, T., Kuriyal, H. & Grasman, R. (2010). Bayesian hypothesis testing for psychologists: a tutorial on the Savage–Dickey method. *Cognitive Psychology* 60(3):158–189.
- Verdinelli, I. & Wasserman, L. (1995). Computing Bayes factors using a generalization of the Savage–Dickey density ratio. *JASA* 90(430):614–618.
- Marin, J.-M. & Robert, C. (2010). On resolving the Savage–Dickey paradox. *Electronic Journal of Statistics* 4:643–654. https://arxiv.org/abs/0910.1452

**Cross-validation**
- Vehtari, A., Gelman, A. & Gabry, J. (2017). Practical Bayesian model evaluation using LOO-CV and WAIC. *Statistics and Computing* 27:1413–1432. https://arxiv.org/abs/1507.04544
- Vehtari, A., Simpson, D., Gelman, A., Yao, Y. & Gabry, J. (2024). Pareto smoothed importance sampling. *JMLR* 25(72). https://arxiv.org/abs/1507.02646
- Bates, S., Hastie, T. & Tibshirani, R. (2024). Cross-validation: what does it estimate and how well does it do it? *JASA* 119(546):1434–1445. https://arxiv.org/abs/2104.00673
- Cawley, G. & Talbot, N. (2010). On over-fitting in model selection and subsequent selection bias in performance evaluation. *JMLR* 11:2079–2107.
- Shao, J. (1993). Linear model selection by cross-validation. *JASA* 88(422):486–494.

**Multiplicity and the forking paths**
- Gelman, A. & Loken, E. (2013). The garden of forking paths. https://sites.stat.columbia.edu/gelman/research/unpublished/forking.pdf — published as *The statistical crisis in science*, *American Scientist* 102(6):460 (2014).
- Simmons, J., Nelson, L. & Simonsohn, U. (2011). False-positive psychology. *Psychological Science* 22(11):1359–1366.
- Holm, S. (1979). A simple sequentially rejective multiple test procedure. *Scandinavian Journal of Statistics* 6(2):65–70.
- Benjamini, Y. & Hochberg, Y. (1995). Controlling the false discovery rate. *JRSS-B* 57(1):289–300.
- Benjamini, Y. & Yekutieli, D. (2001). The control of the FDR under dependency. *AoS* 29(4):1165–1188.
- Benjamini, Y. & Yekutieli, D. (2005). FDR-adjusted multiple confidence intervals for selected parameters. *JASA* 100(469):71–81.
- Steegen, S., Tuerlinckx, F., Gelman, A. & Vanpaemel, W. (2016). Increasing transparency through a multiverse analysis. *Perspectives on Psychological Science* 11(5):702–712.
- Simonsohn, U., Simmons, J. & Nelson, L. (2020). Specification curve analysis. *Nature Human Behaviour* 4:1208–1214. https://www.nature.com/articles/s41562-020-0912-z

**Post-selection and assumption-free inference**
- Berk, R., Brown, L., Buja, A., Zhang, K. & Zhao, L. (2013). Valid post-selection inference. *AoS* 41(2):802–837.
- Lee, J., Sun, D., Sun, Y. & Taylor, J. (2016). Exact post-selection inference, with application to the lasso. *AoS* 44(3):907–927. https://arxiv.org/abs/1311.6238
- Taylor, J. & Tibshirani, R. (2015). Statistical learning and selective inference. *PNAS* 112(25):7629–7634.
- Wasserman, L., Ramdas, A. & Balakrishnan, S. (2020). Universal inference. *PNAS* 117(29):16880–16890. https://arxiv.org/abs/1912.11436
- Vovk, V. & Wang, R. (2021). E-values: calibration, combination, and applications. *AoS* 49(3):1736–1754. https://arxiv.org/abs/1912.06116
- Wang, R. & Ramdas, A. (2022). False discovery rate control with e-values. *JRSS-B* 84(3):822–852. https://arxiv.org/abs/2009.02824
- Grünwald, P., de Heide, R. & Koolen, W. (2024). Safe testing. *JRSS-B*. https://arxiv.org/abs/1906.07801
- Ramdas, A., Grünwald, P., Vovk, V. & Shafer, G. (2023). Game-theoretic statistics and safe anytime-valid inference. *Statistical Science* 38(4):576–601. https://arxiv.org/abs/2210.01948

**Entropy and mutual information**
- Miller, G. (1955). Note on the bias of information estimates. In *Information Theory in Psychology*.
- Paninski, L. (2003). Estimation of entropy and mutual information. *Neural Computation* 15(6):1191–1253. https://direct.mit.edu/neco/article-abstract/15/6/1191/6731/Estimation-of-Entropy-and-Mutual-Information
- Nemenman, I., Shafee, F. & Bialek, W. (2002). Entropy and inference, revisited. *NIPS*. https://arxiv.org/abs/physics/0108025
- Hausser, J. & Strimmer, K. (2009). Entropy inference and the James–Stein estimator. *JMLR* 10:1469–1484. https://arxiv.org/abs/0811.3579
- Archer, E., Park, I. M. & Pillow, J. (2014). Bayesian entropy estimation for countable discrete distributions. *JMLR* 15:2833–2868.
- McAllester, D. & Stratos, K. (2020). Formal limitations on the measurement of mutual information. *AISTATS*. https://arxiv.org/abs/1811.04251
- Discrete entropy estimation reference (Miller–Madow implementation notes): https://infomeasure.readthedocs.io/en/0.5.0/guide/entropy/discrete/

**MDL, non-nested comparison, and misc.**
- Rissanen, J. (1978). Modeling by shortest data description. *Automatica* 14(5):465–471.
- Grünwald, P. (2007). *The Minimum Description Length Principle*. MIT Press.
- Vuong, Q. (1989). Likelihood ratio tests for model selection and non-nested hypotheses. *Econometrica* 57(2):307–333.
- Shi, X. (2015). A nondegenerate Vuong test. *Quantitative Economics* 6(1):85–121.
- Self, S. & Liang, K.-Y. (1987). Asymptotic properties of MLE and LR tests under nonstandard conditions. *JASA* 82(398):605–610.
- Phipson, B. & Smyth, G. (2010). Permutation p-values should never be zero. *SAGMB* 9(1):39.
- Efron, B. (2004). The estimation of prediction error: covariance penalties and cross-validation. *JASA* 99(467):619–632.
- Yao, Y., Vehtari, A., Simpson, D. & Gelman, A. (2018). Using stacking to average Bayesian predictive distributions. *Bayesian Analysis* 13(3):917–1007. https://arxiv.org/abs/1704.02030
- Hoeting, J., Madigan, D., Raftery, A. & Volinsky, C. (1999). Bayesian model averaging: a tutorial. *Statistical Science* 14(4):382–401.
- Breiman, L., Friedman, J., Olshen, R. & Stone, C. (1984). *Classification and Regression Trees* — the one-standard-error rule.
