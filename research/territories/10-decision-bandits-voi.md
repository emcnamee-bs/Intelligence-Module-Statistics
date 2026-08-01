# Territory 10 — Decision Under Uncertainty, Exploration/Exploitation, and the Value of Information

**Scope:** which option should I pick, and is it worth gathering more information first.
**Status:** research pass 1 (2026-07-31). Web-search budget for the session was exhausted partway;
remaining depth came from direct source fetches and from working the mathematics out explicitly.
Every formula below is stated so an implementer can code it without re-deriving; a few carry an
explicit "verify constants against the cited paper at implementation time" flag.

---

## 1. Territory summary

This territory answers two coupled questions an agent asks constantly and almost never formalises:
*given what I know, which option do I commit to?* and *is one more measurement worth its cost?*
The second question has a complete, exact, closed-form answer at agent scale — Expected Value of
Perfect/Sample Information — and the entire fifteen-year health-economics literature on approximating
EVSI exists only because their inner decision model is expensive to re-run, which for an agent with a
conjugate prior and 2–20 options it simply is not. The unifying identity for the whole territory is
that *every* "should I gather more" question reduces to comparing a marginal expected value of
information against a marginal cost, and the methods differ only in how the information is modelled:
a normal preposterior (closed form), a Beta-Binomial predictive (exact enumeration), a full inspection
(Weitzman reservation value), or a noisy test (two-branch arithmetic). The exploration/exploitation
half of the territory is smaller than it looks: at agent scale — tens to hundreds of trials over 2–20
options — the horizon is far too short for the log-*n* asymptotics that make UCB and Thompson sampling
famous, and the agent almost always wants *one option to commit to* rather than cumulative reward, so
best-arm identification with a confidence guarantee is the correct frame and regret-minimising bandits
are a supporting subcase. The multi-criteria half is dominated by one structural insight: dominance
screening and weight-robustness analysis are assumption-light and often decisive, while the weighted
scoring model everyone reaches for first is the single most error-prone tool in the territory and
should refuse to run at all unless criterion *ranges* are supplied alongside weights.

---

## 2. Ranked model table

Tier legend: **INLINE** = a handful of numbers as CLI flags · **DATAFILE** = a small CSV/JSON the agent
points at · **MUST-CONSTRUCT-DATA** = the agent has to run trials or build a structured spec first.

| # | Model / method | SITUATION (agent phrasing + alternates) | Minimum viable inputs + tier | Beats what | Stdlib feasibility + numerics | Failure modes that must make the tool REFUSE |
|---|---|---|---|---|---|---|
| 1 | **EVPI from a decision table, opportunity-loss form** — `EVPI = E_θ[max_a v(a,θ)] − max_a E_θ[v(a,θ)]`, computed as the mean of the per-draw non-negative loss `d_s = max_a v[s][a] − v[s][a*]` with `a*` the prior-optimal index | "How much could *any* amount of extra research possibly be worth here?" · "Is it worth investigating before I decide?" · "What's the ceiling on the value of more information?" | Either (a) k options × S scenario values as a CSV, or (b) k options each with mean+sd and a distribution family → simulate S draws. INLINE for ≤4 options with mean/sd; **DATAFILE** otherwise | The agent's habit of researching by default. EVPI is a hard *upper bound* on every downstream tool in this table: if EVPI < the cost of the cheapest experiment, stop and decide now. Also beats "I'll gather more data" when the answer is provably worthless | **EASY.** `statistics.NormalDist` for sampling, `random`. MC standard error from `sd(d)/√S`; bootstrap CI optional | Refuse if EVPI < 2·SE (indistinguishable from zero — say "zero", not a number). Refuse if values across options are on different scales/units. Refuse if `a*` was chosen on the same sample and S < ~200 (optimism bias — require a split sample). Refuse if any option's value distribution was elicited as a point estimate (then EVPI is mechanically 0 and meaningless) |
| 2 | **Closed-form EVSI + ENBS for a two-option decision, via the unit normal loss integral** — with `D = v₁−v₂ ~ N(μ,σ²)`: `EVPI = σ·L(|μ|/σ)` where `L(z) = φ(z) − z(1−Φ(z))`; `EVSI(n) = σ_pre·L(|μ|/σ_pre)` with `σ_pre² = Var(D) − E[Var(D|X)] = σ₀²·n/(n₀+n)` and `n₀ = σ_d²/σ₀²`; `ENBS(n) = N·EVSI(n) − C(n)`, maximise over n | "How many more runs before I decide?" · "Is another benchmark round worth the time?" · "What sample size is actually justified here?" · "Should I measure more or just pick?" | Current mean difference μ, its sd σ₀, per-observation noise sd σ_d, cost per observation, number of future decisions this will inform. **INLINE** — five numbers | Power analysis, which answers "what n detects a difference" — the wrong question. EVSI answers "what n is *worth paying for*". Also beats round-number sample sizes (n=10, n=100) which have no justification | **EASY.** `NormalDist().pdf` and `.cdf` give φ and Φ. Optimal n by a 1-D scan over n=1..n_max. Exact, no simulation | Refuse if only two options and the scale of D is not a real quantity the agent can trade against cost (EVSI has units — if value is unitless, ENBS is meaningless). Refuse if σ_d is unknown and was guessed. Refuse to report EVSI(n) > EVPI (a bug indicator). Refuse if n₀ < 1 (the "prior" carries less than one observation — the normal preposterior is then a fiction) |
| 3 | **Exact Beta-Binomial EVSI by enumeration** — option j has `θ_j ~ Beta(α,β)`; the experiment is n Bernoulli trials of j. `P(X=x)` is the beta-binomial pmf via `lgamma`; posterior mean is `(α+x)/(α+β+n)`. `EVSI = Σ_{x=0}^{n} P(x)·max(f_j(post_x), M_{−j}) − max(f_j(prior), M_{−j})` | "Should I try this approach n more times before switching?" · "Is another batch of test runs worth it?" · "Will 20 more samples actually change my mind?" | α, β for the arm under test (or successes/failures so far), n proposed trials, the value of the best alternative, cost per trial. **INLINE** | Gut-feel batch sizes. This is *exact* — no Monte Carlo error — and cheap: O(n) `lgamma` calls. It is the discrete twin of #2 and the honest answer to "will more data flip me?" | **EASY.** `math.lgamma` only. log-sum-exp for numerical safety at large n | Refuse if `max_x post_mean(x)` still loses to `M_{−j}` **and** `min_x post_mean(x)` still loses — the experiment cannot flip the decision at *any* outcome, so EVSI = 0 exactly. Print that fact instead of a number. Same for the mirror case. Refuse if α+β is implausibly large relative to observed data (fabricated prior confidence). Refuse for n > ~10⁵ (enumeration cost) — switch to #2 |
| 4 | **Weitzman "Pandora's Box" reservation values** — for each candidate i with inspection cost `c_i` and value distribution `F_i`, solve `E[max(X_i − z_i, 0)] = c_i` for the index `z_i`. Optimal policy: inspect in decreasing `z_i`; stop and commit as soon as the best inspected value ≥ the largest remaining `z_i` | "Which of these approaches should I investigate first, and when do I stop investigating?" · "I have five candidate designs and limited time — what order and how far?" · "When do I stop researching options and pick one?" | Per candidate: inspection cost, and a prior on its value (mean+sd, or a few quantiles, or an empirical sample). **DATAFILE** for >3 candidates, INLINE for 2–3 | Ad-hoc "look at all of them" and "look at the most promising one." This is a *provably optimal* policy for the exact situation an agent is in when triaging approaches, and almost nobody in the decision-analysis mainstream uses it. Beats round-robin exploration when investigation costs differ across options | **EASY–MODERATE.** Bisection on z for `E[max(X−z,0)]`, which is closed-form for the normal case (`σ·L((z−μ)/σ)`) and a simple sum for an empirical/discrete distribution | Refuse if inspection is *partial* (reveals a noisy signal, not the true value) — Weitzman's optimality is lost; route to #22 or #2. Refuse if candidates are not mutually exclusive (you can only keep one). Refuse if inspection costs are not comparable in units to values. Refuse if any `F_i` was supplied as a point value (then `z_i = X_i − c_i` trivially and the tool adds nothing) |
| 5 | **Expected loss / P(best) from posterior draws** — with S posterior draws per option, `P(a best) = #{s: v[s][a] = max}/S`, and `EL(a) = E[max_b v_b − v_a]`. **Key identity: `min_a EL(a) = EVPI`**, attained at the posterior-mean-optimal option. Stopping rule: commit when `EL(a*) < ε`, the smallest difference worth caring about | "Which option is probably best and how confident am I?" · "Have I run enough A/B trials to call it?" · "What do I lose if I commit right now?" | Per-option observed successes/trials (Beta) or mean/sd/n (Normal). **INLINE** for ≤6 options, DATAFILE beyond | The p-value habit. Answers the decision question directly, is valid at any stopping time under a Bayesian reading, and its threshold ε is a *stated business quantity* rather than 0.05. The identity to EVPI means the industry-standard Bayesian A/B stopping rule is literally a VOI computation — which lets one tool serve both framings | **EASY.** `random.betavariate` / `random.gauss`, S = 20k draws is milliseconds. Report MC error on P(best) as `√(p(1−p)/S)` | Refuse if ε was not supplied — "expected loss below threshold" with an invented threshold is theatre. Refuse if P(best) is being read as a frequentist error rate. Refuse if any arm has 0 trials. Refuse if arms were selected for comparison *because* they looked good (winner's curse — require the candidate set be fixed in advance, or shrink toward a common prior) |
| 6 | **Bayesian abandonment rule ("should I give up on this?")** — required success rate `θ* = c/V` from cost c per attempt and value V of success. Posterior `θ ~ Beta(α+s, β+n−s)`. Abandon iff `max_m [EVSI(m) − m·c] ≤ 0`, and immediately if `EVPI < c`. Report `P(θ > θ*)` alongside | "Should I keep trying this or switch strategies?" · "How many more failures before I abandon this approach?" · "Is this a dead end?" | Attempts so far, successes so far, cost per attempt, value of eventual success. **INLINE** — four numbers | "Three strikes" and sunk-cost persistence in both directions. Crucially it is *not* just `P(success) < threshold` — it correctly values the option to learn, so it keeps you going longer than a naive rule when the posterior is wide and cuts you off faster when it is tight | **EASY.** Reuses #3's enumeration for EVSI(m); regularized incomplete beta for `P(θ>θ*)` — with integer α,β use the exact binomial-sum identity `I_x(a,b) = Σ_{j=a}^{a+b−1} C(a+b−1,j)x^j(1−x)^{a+b−1−j}`, otherwise ASA063 | Refuse if the agent's attempts are not exchangeable — if each attempt was a *different fix* rather than a repeat of the same one, Beta-Binomial is the wrong model and the tool is fabricating a rate. This is the dominant real-world failure and must be checked by an explicit question. Refuse if V or c is unknown. Refuse if s = n = 0 |
| 7 | **Successive elimination / racing, fixed confidence** — pull every surviving arm once per round; after t pulls each, eliminate arm i if `max_j μ̂_j − μ̂_i > 2c_t`; stop when one survives. Hoeffding+union radius `c_t = √(log(4Kt²/δ)/(2t))` for [0,1] rewards; prefer a time-uniform boundary (§3) | "Which of these k approaches is genuinely best, with 95% confidence, using as few runs as possible?" · "Stop wasting runs on the losers" · "How do I compare 6 configs without a full grid?" | k arms, a way to run one trial of an arm and get a bounded reward, δ. **MUST-CONSTRUCT-DATA** (agent runs trials) or DATAFILE of pre-run trial results | Fixed-budget grid search, which spends equally on obviously-bad options. Sample complexity `O(Σ_{i≠*} Δ_i⁻² log(K/(δΔ_i)))` — the gap-dependent saving is large when one or two options are clearly bad | **EASY.** Arithmetic + `math.log`, `math.sqrt`. No distributions needed | Refuse if rewards are unbounded or the bound is unknown (Hoeffding is invalid — require a range, or route to a sub-Gaussian variant with a stated σ). Refuse if trials are not i.i.d. (ordering effects, caching, warm-up) — this is extremely common in benchmark runs and silently destroys the guarantee. Refuse to report "arm X is best" when the budget ran out before elimination; report the surviving set instead |
| 8 | **Top-Two Thompson Sampling + GLR (Chernoff) stopping** — sample θ from the posterior, `I₁ = argmax`; with prob β=½ play `I₁`, else resample until `argmax ≠ I₁` and play that. Stop when `min_{b≠â} Z_{â,b}(t) > β(t,δ)`. Gaussian: `Z = (μ̂_â−μ̂_b)²/(2σ²(1/N_â+1/N_b))`. Bernoulli: `Z = N_a·kl(μ̂_a,μ̂) + N_b·kl(μ̂_b,μ̂)` with pooled μ̂ | "Find me the best of these options as fast as possible with a guarantee" · "Adaptive allocation for a fair comparison" · "Which config wins, and stop as soon as it's certain" | Same as #7, plus a prior per arm. **MUST-CONSTRUCT-DATA** | Successive elimination (#7) by a constant factor — it concentrates samples on the top-two boundary rather than spending uniformly on survivors. Near-optimal sample complexity with a ~10-line sampling rule, unlike full Track-and-Stop which needs a fixed-point solve for optimal weights | **EASY** sampling; **MODERATE** stopping (KL for Bernoulli, threshold bookkeeping). `β(t,δ) = log(2t(K−1)/δ)` is provably valid and conservative; `log((log t + 1)/δ)` is the aggressive heuristic — default to the valid one | Refuse if the resampling loop for the challenger exceeds a cap (one arm dominates the posterior); degrade to the posterior-mean runner-up and *say so*. Refuse for Bernoulli when any `μ̂ ∈ {0,1}` (KL is infinite — apply a +½ correction and flag). Refuse to use the aggressive threshold while claiming a δ guarantee. Same i.i.d. refusal as #7 |
| 9 | **Dominance screening + Pareto frontier + rank-order extreme-point dominance** — a dominates b if a ≥ b on every criterion and > on one. Then, given only an *ordinal* ranking of criterion importance (w₁≥w₂≥…≥w_m≥0, Σw=1), check weighted-sum dominance at the m simplex vertices `(1,0,…)`, `(½,½,0,…)`, `(⅓,⅓,⅓,0,…)`, … — dominance at all vertices implies dominance for every admissible weight vector | "Rank these options against several criteria" · "Which alternatives can I eliminate without arguing about weights?" · "Build me a comparison matrix" | Options × criteria score matrix with a direction per criterion. **DATAFILE** (or INLINE for 3×3) | Everything in the weighted-scoring family, because it needs *no weights at all* and is unarguable. Frequently reduces 8 candidates to 2, at which point the weighting argument was never needed. The extreme-point trick extends this to ordinal weight information for free and is genuinely obscure | **EASY.** Pure comparisons; the vertex set is the cumulative-average family, generated in a loop | Refuse if criterion directions (maximise/minimise) are not declared. Refuse if any criterion has missing values for any option. Refuse to report a single winner when the non-dominated set has >1 member — return the frontier and say weights are now unavoidable. Refuse if criteria are obviously correlated proxies (double counting inflates apparent dominance) |
| 10 | **SMAA — Stochastic Multicriteria Acceptability Analysis** — sample weight vectors uniformly from the simplex (Dirichlet(1,…,1), i.e. normalise m independent `expovariate(1)` draws), optionally sample scores from their uncertainty, and report the **rank acceptability index** `b_a^r = P(option a takes rank r)` plus each option's central weight vector | "I can't defend any particular set of weights — how robust is the ranking?" · "What fraction of reasonable priorities favour option A?" · "Does the winner depend on how I weight things?" | Same matrix as #9, plus optional score uncertainty and any ordinal/interval weight constraints. **DATAFILE** | A single weighted score, which hides that the winner may hold for only 30% of admissible weightings. Produces a defensible probabilistic statement instead of a fake point ranking | **EASY.** `random.expovariate` for uniform simplex sampling; rejection sampling for ordinal constraints (fine for m ≤ 6, flag acceptance rate) | Refuse if score normalisation was not specified (see #17 — SMAA inherits the normalisation problem entirely). Refuse if ordinal constraints make the acceptance rate < ~1% (say so and ask for the constraints to be relaxed or encoded directly). Refuse to report a winner when the top rank acceptability is < ~50% — report the distribution |
| 11 | **Thompson sampling (Beta-Bernoulli / Normal-Normal)** — sample one θ per arm from its posterior, play the argmax, update | "Allocate my next trial among these approaches" · "Balance trying new things against using what works" · "Route traffic/attempts adaptively" | Per-arm prior + running successes/failures (or mean/sd/n). **MUST-CONSTRUCT-DATA** for live use; DATAFILE to replay | ε-greedy, decisively. Asymptotically optimal regret (Agrawal & Goyal; Kaufmann et al.), naturally handles ties, and produces posteriors #5 can consume directly. Four lines of code | **EASY.** `random.betavariate`, `random.gauss` | Refuse if the horizon is short and the agent's actual goal is to *pick one* — route to #7/#8. Refuse for non-stationary rewards without a discount/sliding-window variant. Refuse if the reward scale is unknown for the Normal case (misspecified prior variance can lock TS onto a bad arm and the regret bound evaporates). Refuse if arms have wildly different trial costs — TS assumes uniform cost |
| 12 | **Explore-then-commit sample-size calculator + honest regret accounting** — with 2 arms, gap Δ, per-obs sd σ, horizon n, m pulls each: `R_n = mΔ + (n−2m)·Δ·Φ(−Δ√(m/2)/σ)`; optimal `m ≈ max(1, ⌈(4σ²/Δ²)·log(nΔ²/(4σ²))⌉)`, giving `R_n ≤ Δ + (4σ²/Δ)(1+max(0, log(nΔ²/(4σ²))))`; worst case over Δ is `Θ(n^{2/3})` vs UCB's `Θ(√(Kn log n))` | "How many trial runs each before I just commit to one?" · "What does it cost me to decide early?" · "Is a quick pilot enough?" | Δ (the difference worth caring about), σ, horizon n. **INLINE** | Guessing "let's do 10 each." Also the honest counterweight to bandit hype: it quantifies *exactly* what a simple two-phase design costs versus a fully sequential one, so the agent can decide whether the complexity is warranted | **EASY.** `NormalDist().cdf`, `math.log` | Refuse if Δ is unspecified — the optimal m depends on the unknown gap and there is no way around it; force the agent to name a difference it cares about. Refuse to claim optimality (ETC is provably suboptimal; Garivier & Lattimore 2016). Refuse if the agent will not actually stick with the committed arm |
| 13 | **UCB1 / UCB-tuned / KL-UCB** — `UCB1: μ̂_i + √(2 ln t / N_i)`; regret `≤ Σ_{Δ_i>0} 8 ln n/Δ_i + (1+π²/3)ΣΔ_i`. KL-UCB solves `max{q: N_i·kl(μ̂_i,q) ≤ log t + 3 log log t}` by bisection | "Deterministic, reproducible exploration schedule" · "Allocate trials with a guarantee, no randomness" · "Explain to me why it tried that option" | Per-arm running mean and count; reward range. **MUST-CONSTRUCT-DATA** | ε-greedy and round-robin. Deterministic, so runs are reproducible and the choice is *explainable* — which matters when an agent must justify its allocation. KL-UCB is materially better than UCB1 for Bernoulli rewards near 0 or 1 | **EASY** (UCB1) / **MODERATE** (KL-UCB: bisection on a KL, 30 iterations) | **Always also compute the trivial bound `n·Δ_max` and report the min** — at agent horizons (n ≈ 50–500, K ≈ 5) the UCB1 bound routinely exceeds the trivial one and is vacuous. Refuse to quote a regret bound as a *prediction*: it bounds expected pseudo-regret, not realised regret, and has no variance control. Refuse if rewards are not in the assumed range |
| 14 | **Sequential Halving / Successive Rejects (fixed budget BAI)** — SH: `R=⌈log₂K⌉` rounds, in round r pull each surviving arm `⌊T/(|S_r|·R)⌋` times, keep the top half. SR: `n_k = ⌈(T−K)/(l̄og(K)·(K+1−k))⌉` with `l̄og(K)=½+Σ_{i=2}^K 1/i`, reject the worst each phase | "I have budget for exactly 200 runs across 8 options — allocate them" · "Best answer I can get by the deadline" · "Fixed compute budget, pick the winner" | k arms, total trial budget T. **MUST-CONSTRUCT-DATA** | Uniform allocation, by a large factor when gaps are heterogeneous. The right tool when the constraint is a hard budget rather than a confidence target | **EASY.** Integer arithmetic and sorting | Refuse to attach a confidence level to the output — fixed-budget BAI gives an error *probability bound* in terms of the unknown hardness H₂, not a usable guarantee. And see §3: Degenne (2023) proved **no instance-optimal fixed-budget algorithm exists**, so refuse any claim that this allocation is "the best possible." Refuse if T < K·2⌈log₂K⌉ (some arms get zero pulls) |
| 15 | **EVIU — Expected Value of Including Uncertainty** — compare `E_θ[u(a_plug-in, θ)]` against `E_θ[u(a*, θ)]` where `a_plug-in` is the choice made from point estimates and `a*` maximises expected utility. EVIU = 0 means uncertainty is decision-irrelevant | "Does it even matter that I'm uncertain here?" · "Can I just use the point estimates?" · "Is this analysis worth doing at all?" | Same inputs as #1. **INLINE / DATAFILE** | Doing the whole analysis. This is the territory's own Tier-0 gate: if EVIU = 0, all of rows 1–8 are guaranteed to change nothing, and the agent should just decide. Costs one extra line on top of #1 | **EASY.** Falls out of the same simulation as #1 | Refuse if the utility function is linear *and* the option set is fixed — then EVIU = 0 by construction and reporting it is noise. Refuse if the point estimate used by the "plug-in" branch isn't the one the agent would actually have used |
| 16 | **Weight-stability intervals for the weighted-sum model** — for the current winner w and each criterion i, solve the linear equation in `w_i` (others rescaled proportionally) at which each rival overtakes; report the interval over which the winner is unchanged | "How much would my weights have to change to flip the answer?" · "Is this recommendation sensitive to my priorities?" · "Defend this ranking" | Weighted-sum inputs from #17. **DATAFILE** | A bare weighted score. Turns "A wins" into "A wins for any weight on cost between 0.18 and 0.61", which is the only defensible form of the claim | **EASY–MODERATE.** Closed-form for the weighted sum: each rival gives one linear crossing point per criterion | Refuse if a criterion's stability interval is empty or degenerate (the winner is knife-edge — report a tie). Refuse if the intervals are computed after min-max normalisation without re-normalising, which is a common and silent bug. Refuse if #9's dominance screen already settled it (don't run MCDA you don't need) |
| 17 | **SWING weighting + range-normalised additive value model** — weights are elicited as: "starting from all criteria at their worst level, which single criterion would you most want swung to its best? Give it 100. Score the rest relative to it." Weights then normalise to 1 and are applied to **range-normalised** scores | "Score these options on multiple criteria" · "Build a weighted decision matrix" · "Which vendor/library/design wins on balance?" | Options × criteria scores, criterion directions, **and the plausible range (worst, best) of each criterion**. **DATAFILE** | Ad-hoc "importance" weights, which are meaningless: a weight in an additive model is a *rate of exchange over the criterion's range*, not an abstract importance. Two analysts with identical preferences produce different weights under different elicitation protocols (Marsh et al. 2017) | **MODERATE.** Arithmetic is trivial; the difficulty is entirely in enforcing the protocol and refusing bad inputs | **Refuse to run at all if criterion ranges are not supplied** — this is the single highest-yield refusal in the territory. Refuse if weights were given as "importance" without a swing framing. Refuse to output one ranking under one normalisation: run min-max, z-score and ratio-to-max, and if they disagree, report the disagreement instead of a winner. Refuse if criteria are correlated (double counting). Refuse if any criterion has a hard veto threshold — that is a constraint, not a criterion, and additive models compensate it away |
| 18 | **Minimax regret + Hurwicz / maximin / maximax / Laplace under no probabilities** — regret matrix `R[a][s] = max_b A[b][s] − A[a][s]`; minimax regret picks `argmin_a max_s R[a][s]`. Report all five criteria side by side | "I genuinely have no idea how likely these scenarios are" · "Which choice is least likely to embarrass me?" · "Robust option under deep uncertainty" | Options × scenarios payoff matrix, no probabilities. **DATAFILE** (INLINE for 3×3) | Inventing probabilities to make expected value applicable. When the agent truly cannot assign probabilities, this is honest; when it can, expected value strictly dominates | **EASY.** Comparisons only | **Refuse if the agent can supply probabilities** — minimax regret discards them and is then just worse. Refuse to present minimax regret as *the* answer: it violates independence of irrelevant alternatives, so adding a new option can reverse the ranking of existing ones (demonstrate this in the output when it applies). Refuse if the scenario set was not constructed by a defensible process — the answer is entirely determined by which extremes you chose to enumerate, and there is no penalty for enumerating absurd ones. Refuse if any scenario is dominated by construction |
| 19 | **Certainty equivalent under CARA / CRRA** — CARA: `u(x) = −e^{−x/R}`, `CE = −R·ln(E[e^{−x/R}])`; CRRA: `u(x)=x^{1−γ}/(1−γ)`. Elicit R via "largest 50/50 win-X / lose-X/2 gamble you'd take" → `R ≈ X`. Rank by CE, not EV | "This option has higher expected value but could blow up — which do I take?" · "Account for the fact that I can't afford a disaster" · "Risk-adjusted comparison" | Per-option outcome distribution (draws or mean/sd) + one risk-tolerance number. **INLINE / DATAFILE** | Ranking by expected value when outcomes are skewed or a bad tail is unrecoverable. Makes risk aversion an explicit, single, auditable parameter rather than an unstated thumb on the scale | **EASY.** `math.exp`, `math.log`; log-sum-exp to avoid overflow in the CARA expectation | Refuse if R was not elicited or defaulted with a stated rationale (a "voodoo constant" — the project forbids these). Refuse CRRA if any outcome ≤ 0 (undefined). Refuse if outcome magnitudes exceed ~5R (the CARA expectation is then dominated by one tail draw — report the MC error). Refuse if the decision is repeated many times and outcomes are additive — then EV is closer to right and CARA over-penalises |
| 20 | **Decision tree rollback with expected utility + per-node EVPI** — recursive fold: chance node = `Σ p·EV(child)`, decision node = `max`. Report the optimal path, the EV, and the EVPI at each chance node (the value of resolving *that* uncertainty first) | "Map out this multi-stage decision" · "If I do A then learn X then choose B or C, what's best?" · "Should I do the cheap test first or commit?" | A JSON/YAML tree spec. **MUST-CONSTRUCT-DATA** | Reasoning about sequential decisions in prose, which reliably loses track of the option value of later choices. The per-node EVPI output is what turns it into a VOI tool: it tells the agent *which* uncertainty to resolve first | **MODERATE.** Recursion, schema validation, cycle detection | Refuse if any chance node's probabilities don't sum to 1 within 1e-9. Refuse if the tree has a cycle or an unreachable branch. Refuse if utilities span >3 orders of magnitude while the model is risk-neutral (flag and route to #19). Refuse if the same uncertain quantity appears at two chance nodes with independent probabilities (a correlation error that rollback will silently compound) |
| 21 | **Kelly / log-growth sizing, with the uncertainty treated correctly** — binary bet at net odds b: `f* = p − (1−p)/b`. General: maximise `g(f) = Σ_i p_i log(1 + r_i f)` by bisection on `g'(f) = Σ p_i r_i/(1+r_i f) = 0`. **Note: `g` is affine in `p`, so uncertainty in outcome *probabilities* does not change `f*` — plug in the posterior mean. Uncertainty in outcome *magnitudes* does reduce `f*`, via Jensen on the concave log** | "How much of my remaining budget/time do I commit to this?" · "How big should this bet be?" · "Position sizing under repeated similar decisions" | p (or successes/trials), payoff odds, current bankroll. **INLINE** | All-in / all-out sizing. The log-growth criterion is the right objective whenever the same class of decision recurs and losses compound | **EASY.** Bisection + `math.log` | **Refuse for one-shot, non-repeated decisions** — Kelly is a long-run growth criterion and is meaningless for a single non-compounding choice. This is the dominant misuse. Refuse if `f* > 0.25`, which almost always signals an overstated edge rather than a real one. Refuse if p was estimated from <~30 observations with no prior (shrink it first). Refuse to justify "half Kelly" as protection against estimation error in p — it is not (see the note); state instead that fractional Kelly λ is equivalent to CRRA risk aversion γ ≈ 1/λ, and route to #19 |
| 22 | **EVSI for a single imperfect test / noisy signal** — with prior π, sensitivity Se, specificity Sp: `EVSI = Σ_{r∈{+,−}} P(r)·max_a E[u(a,θ)|r] − max_a E[u(a,θ)]`. First compute the decision **threshold probability** `p*` and check whether the posterior after *either* result crosses it | "Would running this diagnostic actually change what I do?" · "Is this flaky/partial check worth running?" · "Is this metric informative enough to act on?" | π, Se, Sp, and the payoff of each action under each state. **INLINE** — six numbers | Running checks reflexively. The threshold-reachability pre-check is the killer feature: it proves in three lines that many measurements have EVSI exactly zero *at any accuracy*, and the agent can skip them entirely | **EASY.** Arithmetic | Refuse (with EVSI = 0, stated as a proof, not an estimate) if neither result moves the posterior across `p*`. Refuse if Se/Sp were guessed rather than measured. Refuse if the test's result would be correlated with the state through a path other than the modelled one. Refuse if there are >2 states and the agent supplied only Se/Sp (under-specified confusion matrix) |
| 23 | **Reservation-value sequential stopping (McCall / Chow–Robbins house-selling)** — with cost c per additional draw and value distribution F, the infinite-horizon reservation value solves `E[max(X − V, 0)] = c`; stop at the first draw ≥ V. Finite horizon: backward induction `V_k = −c + E[max(X, V_{k−1})]` | "How many candidate solutions should I generate before shipping one?" · "When do I stop looking for a better answer?" · "Is the next attempt worth making?" | Cost per attempt, plus an empirical sample or a distribution for attempt quality. **DATAFILE** (the sample of prior attempts) or INLINE (mean/sd) | "Generate three and pick the best," which has no justification. Note the reservation equation `E[max(X−V,0)] = c` **is** a marginal-EVSI-equals-marginal-cost condition — the same identity as #2, #4 and #6, which is the through-line of this whole territory | **EASY.** Bisection over V; `E[max(X−V,0)] = σ·L((V−μ)/σ)` for the normal case, a direct sum for an empirical sample | Refuse if candidates cannot be recalled *and* the agent assumed recall (or vice versa) — the two settings have different optimal rules. Refuse if attempt quality is not exchangeable across attempts (an agent that learns between attempts violates the i.i.d. assumption — this is very common and must be checked). Refuse if the empirical sample has n < ~10 |
| 24 | **Single-parameter EVPPI by sorted-window conditional expectation** — sort the S PSA draws by the parameter φ of interest, estimate `E[v_a|φ]` by a moving window (or optimal segmentation à la Sadatsafavi), then `EVPPI = mean_s(max_a Ê[v_a|φ_s]) − max_a mean(v_a)` | "Which single unknown is driving my indecision?" · "What should I go measure first?" · "Which assumption matters most?" | A PSA table: S draws × (parameters, per-option values). **DATAFILE / MUST-CONSTRUCT-DATA** | Ranking uncertainties by their variance, which is wrong — a high-variance parameter that never changes the chosen option has EVPPI zero. This ranks uncertainties by *decision relevance* | **MODERATE.** Sort + windowed means; window width by cross-validation. Multi-parameter EVPPI needs GAMs or Gaussian processes and is **out of reach for pure stdlib** — state that boundary honestly | Refuse for >2 parameters jointly (no stdlib GAM). Refuse if the EVPPI estimate is not stable across window widths (report the range instead of a number). Refuse to report EVPPI > EVPI (bias indicator — the window is too narrow). Refuse if S < ~1000 |
| 25 | **LinUCB (disjoint linear contextual bandit)** — per arm: `A_a = I_d + Σxxᵀ`, `b_a = Σr·x`, `θ̂ = A⁻¹b`, index `θ̂ᵀx + α√(xᵀA⁻¹x)`. Rank-1 Sherman–Morrison updates avoid re-inversion | "Which approach works best *for this kind of task*?" · "The right choice depends on the situation — learn the rule" · "Personalise the option choice by context" | Per-trial: a d-dim feature vector, the arm played, the reward. **MUST-CONSTRUCT-DATA** | A context-free bandit, but only once there is enough data. At agent scale that condition usually fails, which is why this ranks last | **MODERATE.** d×d Gauss–Jordan inverse or Sherman–Morrison; fine for d ≤ ~10 in pure Python | **Refuse if n < ~5d observations per arm** — below that LinUCB is strictly worse than context-free Thompson sampling and will confidently overfit. Refuse if features are collinear (check the condition number; a near-singular A produces enormous spurious confidence widths). Refuse if features were engineered after seeing the rewards. Refuse if α was not justified |

---

## 3. Recent advances (~last 10 years)

**Best-arm identification became a solved problem in the fixed-confidence setting — and provably
unsolvable in the fixed-budget one.** Garivier & Kaufmann's *Track-and-Stop* (COLT 2016) gave the first
algorithm matching the asymptotic instance-dependent lower bound `T*(μ)log(1/δ)` for fixed-confidence
BAI, pairing a Chernoff/GLR stopping rule with a sampling rule that tracks the optimal allocation
weights. The practical obstacle is the fixed-point solve for those weights. Russo's *Top-Two Thompson
Sampling* (2016; JMLR 2020) removed it: sample the posterior, and with probability β play the leader,
else the top challenger. Jourdan, Degenne, Baudry, de Heide & Kaufmann, *Top Two Algorithms Revisited*
(NeurIPS 2022), generalised the family — TTTS, T3C, TTUCB — and proved β-optimality with anytime
variants, making β=½ a defensible default. On the other side, Degenne, *On the Existence of a
Complexity in Fixed Budget Bandit Identification* (COLT 2023, arXiv:2303.09468), proved that for
several natural tasks — **including two-arm Bernoulli best-arm identification** — no complexity exists:
there is no single algorithm attaining the best possible error exponent on every instance. This is a
real design constraint: "give me the best arm within budget T" is a fundamentally worse-posed question
than "give me the best arm at confidence δ", which inverts the common intuition that a hard budget is
the simpler ask.

**Explore-then-commit was formally demoted, then partially rehabilitated.** Garivier, Kaufmann &
Lattimore, *On Explore-Then-Commit Strategies* (NeurIPS 2016), proved two-phase strategies cannot reach
the Lai–Robbins asymptotic optimum. Jin, Xu, Shi, Xiao & Gu, *Double Explore-Then-Commit* (2020,
arXiv:2002.09174), showed a two-stage ETC *does* match UCB asymptotically. For our purposes the useful
residue is the exact regret accounting in row 12 and the `n^{2/3}` vs `√n` worst-case comparison —
enough for an agent to decide whether sequential machinery is worth the complexity.

**Time-uniform confidence sequences replaced union bounds.** Howard, Ramdas, McAuliffe & Sekhon,
*Time-uniform Chernoff bounds via nonnegative supermartingales* (Probability Surveys 2020) and
*Time-uniform, nonparametric, nonasymptotic confidence sequences* (Annals of Statistics 2021), give
"stitched" boundaries that are valid at all stopping times and materially tighter than the
`log(4Kt²/δ)` union bound used in classical successive elimination. Ramdas, Grünwald, Vovk & Shafer,
*Game-theoretic statistics and safe anytime-valid inference* (Statistical Science 2023), frames the
same machinery as e-values/e-processes. All of it is arithmetic and belongs in rows 7 and 8.
*Implementation note: the published stitched sub-Gaussian boundary has specific constants (of the form
`1.7√((log log(2t) + 0.72·log(5.2/δ))/t)`); verify them against Howard et al. (2021) before shipping
rather than trusting a recollection.*

**EVSI moved from "computationally infeasible" to routine — via four approximations we mostly won't
need.** The decade produced: Strong, Oakley, Brennan & Breeze (2015) regression-based EVSI using GAMs
on a low-dimensional summary of the simulated future dataset; Menzies (2016) importance sampling,
reweighting EVPPI simulations by the data likelihood; Jalal & Alarid-Escudero (2018) Gaussian
approximation via a prior effective sample size; and Heath, Manolopoulou & Baio (2019) moment matching,
which cuts the nested Monte Carlo inner loop from ~1000 to Q≈30–50 simulations and then fits a Bayesian
non-linear regression of posterior variance against sample size so a *single* EVSI computation yields
the whole EVSI(n) curve. Kunst et al. (2020, *Value in Health*, ISPOR EVSI task force) compared all four
and published usability boundaries that transfer directly to our refusal logic: importance sampling
fails for n > 1000 (likelihood underflow); the Gaussian approximation fails when prior effective sample
size n₀ < 10; moment matching fails for n < 10 and when EVPPI/EVPI < ~40%; regression-based methods fail
silently when the GAM fit is poor and require residual diagnostics. Jackson et al. (2022) shipped the
`voi` R package and an *Annual Review of Statistics* survey. **The strategic point for this project:
every one of these methods exists to avoid re-running an expensive health-economic simulation model in
an inner loop. At agent scale with conjugate updates, the inner loop is a closed-form posterior mean, so
rows 2 and 3 compute the exact quantity these four methods approximate — for free, and with none of
their failure boundaries.**

**VOI extended from health policy to model selection.** Sadatsafavi, Yoon, Leung et al.,
*Uncertainty and Value of Information in Risk Prediction Modeling* (arXiv:2106.10721; *Medical Decision
Making*), and the follow-on work on VOI for external validation of prediction models, reframe "should I
collect more validation data before adopting this model?" as an EVPI/EVSI computation. That is
structurally identical to an agent asking "should I run more evals before adopting this approach?" —
the closest published analogue to our use case, and worth mining for the framing.

**Bandits arrived inside LLM systems.** *BanditSpec* (2025, arXiv:2505.15141) uses UCB and EXP3-style
algorithms to adapt speculative-decoding hyperparameters at inference time, training-free. Broader
survey work on bandit-based LLM routing appeared through 2025. The evidence that the framing transfers
to agent-runtime choices is now empirical, not just plausible.

**MCDA advanced on robustness rather than on new aggregation rules.** Weight stability intervals for
the weighted sum model received a closed-form treatment (*Expert Systems with Applications*, 2025), and
SMAA matured into the standard answer for unknown weights. Marsh et al. (2017, *Value in Health*) is the
key critical assessment: swing weighting and discrete-choice experiments are *both* prone to the same
elicitation biases, and different elicitation methods yield different weights from the same people
holding the same preferences — the empirical basis for row 17's refusals. Meanwhile no new aggregation
method displaced the weighted sum, and the rank-reversal literature continued to accumulate against
AHP and TOPSIS.

**Minimax regret got tractable in sequential settings.** Rigter, Lacerda & Hawes, *Minimax Regret
Optimisation for Robust Planning in Uncertain MDPs* (arXiv:2012.04626), and the adaptive robust
optimisation literature made minimax regret computable for structured sequential problems — beyond our
scale, but it confirms minimax regret as the mainstream less-conservative alternative to maximin.

**Kelly under parameter uncertainty was studied empirically and the folklore did not survive.**
Chapman (arXiv:1701.02814) and Downey's simulation study both find that uncertainty in the *probability*
estimate barely moves the optimal fraction (σ = 5% on p moves f* from 0.40 to 0.38; σ = 20% moves it to
0.36). That is exactly what the mathematics predicts — log-growth `Σ p_i log(1+r_i f)` is affine in p, so
the posterior mean is a sufficient statistic and probability uncertainty is *first-order irrelevant*.
The genuine reasons fractional Kelly helps are (a) upward *bias* in edge estimates from selection and
winner's-curse effects, which is fixed by shrinking p̄ rather than by scaling f; (b) risk preferences
more averse than log, for which fractional Kelly λ is equivalent to CRRA γ ≈ 1/λ; and (c) uncertainty in
outcome *magnitudes*, where log's concavity does bite. Row 21's refusal encodes this.

---

## 4. Cut list

- **AHP / pairwise comparison matrices** — documented rank reversal, an arbitrary eigenvector
  aggregation, and O(m²) elicitation burden; the consistency ratio measures self-consistency, not
  validity. Dominance (#9) plus SWING (#17) does the job with fewer assumptions.
- **TOPSIS / VIKOR / PROMETHEE / ELECTRE** — all rank-reversal-prone, all require normalisation and
  preference-function parameters the agent will invent. Zero incremental insight over #9 + #10 + #16.
- **Full Gittins index tables (discounted Bayesian bandit)** — computable by value iteration on a small
  Beta state grid, but the geometric-discount framing rarely matches an agent's actual horizon, the
  index is invalid the moment arms are correlated or the problem is finite-horizon-with-known-end, and
  #6 answers the practical "give up?" question directly. Cut for setup cost exceeding value.
- **POMDP solvers / full sequential VOI with adaptive experiment design** — correct in principle,
  intractable in stdlib, and beyond agent-scale need. #20's per-node EVPI is the affordable 80%.
- **Bayesian optimisation / GP-UCB / expected improvement** — requires a Gaussian process (Cholesky on
  an n×n kernel matrix) and targets continuous search spaces. Out of scope on both counts.
- **EXP3 / adversarial bandits** — `√(nK log K)` regret, strictly worse than stochastic algorithms, and
  agents rarely face a genuine adversary. Keep only as a footnote for the non-stationary case.
- **Non-stationary bandits (discounted UCB, sliding-window UCB, CUSUM-UCB)** — real, but folds in as a
  flag on rows 11/13 rather than a separate model.
- **Dueling bandits / preference-based bandits** — right model when only pairwise comparisons are
  available, which is a genuine agent situation (LLM-judge comparisons), but the sample complexity at
  2–20 options is prohibitive. Revisit if a pairwise-judgement use case appears.
- **Combinatorial / semi-bandits, cascading bandits** — no agent-scale use case identified.
- **Instance-optimal fixed-budget BAI** — cut because it is *proven not to exist* (Degenne 2023). Ship
  Sequential Halving with honest caveats instead.
- **Info-gap decision theory** — robustness curves are unfalsifiable without a probability model and the
  method has been criticised for reducing to a local sensitivity analysis around a point estimate.
  Minimax regret (#18) is the defensible deep-uncertainty tool.
- **Full Robust Decision Making (RDM) with scenario discovery / PRIM** — requires data-mining machinery
  and hundreds of scenarios; the scenario-generation step, not the analysis, is the bottleneck.
- **Prospect theory / cumulative prospect theory weighting** — descriptive of human bias, not normative.
  An agent should not import loss aversion.
- **Choquet integral / non-additive multi-attribute utility** — correctly handles criterion interaction,
  but elicitation requires 2^m capacity values. Handle interaction by merging or dropping correlated
  criteria instead.
- **Regret matching / counterfactual regret minimisation** — solves games against a strategic opponent;
  a different problem despite the shared word "regret".
- **Markowitz mean-variance portfolio optimisation** — continuous allocation requiring covariance
  estimation and matrix inversion; both the problem shape and the numerics are wrong for us.
- **Real-options / Black–Scholes framings of project decisions** — the geometric-Brownian assumptions
  are unjustifiable for agent tasks, and #20 with an explicit tree is more honest.
- **Multi-parameter EVPPI (GAM / Gaussian-process based)** — the honest stdlib boundary. Single-parameter
  EVPPI (#24) is in; two or more jointly is out, and the tool should say so rather than approximate.
- **Secretary problem / 1/e rule** — elegant, but its no-recall, ordinal-only, known-N assumptions almost
  never hold for an agent, which can usually recall earlier candidates. #23 dominates it in practice.
- **Satisficing as a standalone model** — Simon's aspiration-level rule is #23 with a fixed rather than
  an optimally-computed threshold. Ship the optimal version; mention satisficing as the degenerate case.

---

## 5. Cross-territory overlaps

- **Sequential testing / power analysis.** Rows 2, 7, 8 and 12 all compute sample sizes, but on a
  different criterion: power asks "what n detects a difference of size Δ", EVSI asks "what n is worth
  paying for". The two tools should cross-reference explicitly, and the router must not let a power
  query capture an EVSI situation. The time-uniform confidence sequences in §3 are shared machinery.
- **Bayesian inference / prior elicitation.** Rows 3, 5, 6, 8, 11 and 21 all consume posteriors. The
  regularized incomplete beta needed for `P(θ > θ*)` in row 6 is the same ASA063 dependency already
  flagged in RESEARCH.md §0.7. Prior elicitation quality is the binding constraint on half this table.
- **Forecasting and calibration.** Every VOI computation is only as good as the probability inputs; a
  miscalibrated agent will systematically underestimate EVPI (overconfident priors are too narrow, so
  the max-minus-mean gap shrinks). Worth a mandatory calibration caveat in the VOI tools' output.
- **"Is this difference real" / effect estimation.** Rows 5, 7 and 8 overlap heavily with A/B analysis;
  the identity `min_a EL(a) = EVPI` is the bridge, and the same posterior draws should serve both.
- **Risk and extreme values.** Row 19's certainty equivalent and row 21's ruin constraint need tail
  estimates; CARA with a heavy-tailed outcome distribution is dominated by rare draws and needs the
  tail-estimation territory's diagnostics.
- **Causal inference.** Bandit allocation induces confounding in the collected data (adaptively-collected
  data has biased sample means — see Nie et al. on conditional bias in bandits); any territory that later
  analyses bandit-collected logs must know they are not i.i.d.
- **Optimisation / search.** Rows 4 and 23 are search-theoretic rather than statistical and could
  plausibly live in a planning territory; they are here because their stopping conditions are VOI
  conditions.

---

## 6. Sources

**Bandits and best-arm identification**
- Lattimore, T. & Szepesvári, C. (2020). *Bandit Algorithms*. Cambridge University Press. https://tor-lattimore.com/downloads/book/book.pdf
- Auer, P., Cesa-Bianchi, N. & Fischer, P. (2002). Finite-time analysis of the multiarmed bandit problem. *Machine Learning* 47:235–256.
- Agrawal, S. & Goyal, N. (2013). Further Optimal Regret Bounds for Thompson Sampling. AISTATS. https://arxiv.org/pdf/1209.3353
- Even-Dar, E., Mannor, S. & Mansour, Y. (2006). Action elimination and stopping conditions for the multi-armed bandit and RL problems. *JMLR* 7:1079–1105.
- Audibert, J-Y., Bubeck, S. & Munos, R. (2010). Best arm identification in multi-armed bandits. COLT.
- Karnin, Z., Koren, T. & Somekh, O. (2013). Almost optimal exploration in multi-armed bandits. ICML.
- Garivier, A. & Kaufmann, E. (2016). Optimal Best Arm Identification with Fixed Confidence. COLT. https://arxiv.org/abs/1602.04589
- Garivier, A. & Lattimore, T. (2016). On Explore-Then-Commit Strategies. NeurIPS. https://www.semanticscholar.org/paper/e895237c53ac2844d2783684a88b398dd5c07944
- Jin, T., Xu, P., Shi, X., Xiao, X. & Gu, Q. (2020). Double Explore-then-Commit: Asymptotic Optimality and Beyond. https://arxiv.org/pdf/2002.09174
- Russo, D. (2020). Simple Bayesian Algorithms for Best-Arm Identification. *Operations Research* 68(6).
- Jourdan, M., Degenne, R., Baudry, D., de Heide, R. & Kaufmann, E. (2022). Top Two Algorithms Revisited. NeurIPS. https://arxiv.org/abs/2206.05979
- Degenne, R. (2023). On the Existence of a Complexity in Fixed Budget Bandit Identification. COLT. https://arxiv.org/abs/2303.09468
- Nie, X. et al. On conditional versus marginal bias in multi-armed bandits. https://arxiv.org/pdf/2002.08422
- Explore-then-commit algorithm (regret decomposition). https://en.wikipedia.org/wiki/Explore-then-commit_algorithm
- *BanditSpec: Adaptive Speculative Decoding via Bandit Algorithms* (2025). https://arxiv.org/pdf/2505.15141

**Anytime-valid inference and confidence sequences**
- Howard, S., Ramdas, A., McAuliffe, J. & Sekhon, J. (2021). Time-uniform, nonparametric, nonasymptotic confidence sequences. *Annals of Statistics* 49(2). https://arxiv.org/abs/1810.08240
- Ramdas, A., Grünwald, P., Vovk, V. & Shafer, G. (2023). Game-theoretic statistics and safe anytime-valid inference. *Statistical Science* 38(4). https://arxiv.org/abs/2210.01948

**Value of information**
- Expected value of perfect information (definitions, EVWPI/EMV form). https://en.wikipedia.org/wiki/Expected_value_of_perfect_information
- Analytica documentation, *Expected value of information — EVI, EVPI, and ESVI*. https://docs.analytica.com/index.php/Expected_value_of_information_--_EVI,_EVPI,_and_ESVI
- Kunst, N., Wilson, E. C. F., Glynn, D., Alarid-Escudero, F., Baio, G., Brennan, A., Fairley, M., Glynn, D., Goldhaber-Fiebert, J. D., Jackson, C., Jalal, H., Menzies, N. A., Strong, M., Thom, H. & Heath, A. (2020). Computing the Expected Value of Sample Information Efficiently: Practical Guidance and Recommendations for Four Model-Based Methods. *Value in Health* 23(6):734–742. https://pmc.ncbi.nlm.nih.gov/articles/PMC8183576/
- Heath, A., Manolopoulou, I. & Baio, G. (2019). Estimating the Expected Value of Sample Information across Different Sample Sizes Using Moment Matching and Nonlinear Regression. *Medical Decision Making* 39(4). https://arxiv.org/abs/1804.09590 · https://journals.sagepub.com/doi/10.1177/0272989X19837983
- Strong, M., Oakley, J. E., Brennan, A. & Breeze, P. (2015). Estimating the expected value of sample information using the probabilistic sensitivity analysis sample. *Medical Decision Making* 35(5).
- Menzies, N. A. (2016). An efficient estimator for the expected value of sample information. *Medical Decision Making* 36(3).
- Jalal, H. & Alarid-Escudero, F. (2018). A Gaussian approximation approach for value of information analysis. *Medical Decision Making* 38(2).
- Sadatsafavi, M., Bansback, N., Zafari, Z., Najafzadeh, M. & Marra, C. (2013). Need for speed: an efficient algorithm for calculation of single-parameter expected value of partial perfect information. *Value in Health* 16(2).
- Sadatsafavi, M. et al. (2021). Uncertainty and Value of Information in Risk Prediction Modeling. https://arxiv.org/pdf/2106.10721
- Jackson, C., Baio, G., Heath, A., Strong, M., Welton, N. & Wilson, E. (2022). Value of Information analysis in models to inform health policy. *Annual Review of Statistics and Its Application* 9. (`voi` R package.)
- Calculating EVSI adjusting for imperfect implementation. https://arxiv.org/pdf/2105.05901
- Raiffa, H. & Schlaifer, R. (1961). *Applied Statistical Decision Theory*. (Unit normal linear loss integral; preposterior analysis.)
- Morgan, M. G. & Henrion, M. (1990). *Uncertainty*. Cambridge University Press. (EVIU.)
- Dartmouth ENGS 41 lecture notes, *Decision Making: Value of Information*. https://cushman.host.dartmouth.edu/courses/engs41/Value-of-info.pdf

**Sequential search and stopping**
- Weitzman, M. L. (1979). Optimal Search for the Best Alternative. *Econometrica* 47(3):641–654.
- McCall, J. J. (1970). Economics of Information and Job Search. *Quarterly Journal of Economics* 84(1). (Reservation-value equation.)
- Chow, Y. S. & Robbins, H. (1961). A martingale system theorem and applications. (House-selling / optimal stopping.)

**Multi-criteria decision analysis**
- Marsh, K., van Til, J. A., Molsen-David, E. et al. (2017). MCDA swing weighting and discrete choice experiments for elicitation of patient benefit-risk preferences: a critical assessment. https://pubmed.ncbi.nlm.nih.gov/28696023/
- Weight stability intervals for multi-criteria decision analysis using the weighted sum model. *Expert Systems with Applications* (2025). https://www.sciencedirect.com/science/article/pii/S0957417425020792
- Parnell, G. S. & Trainor, T. E. Using the Swing Weight Matrix to Weight Multiple Objectives. INCOSE. https://web.mst.edu/lib-circ/files/Special%20Collections/INCOSE/Using%20the%20Swing%20Weight%20Matrix%20to%20Weight%20Multiple%20Objectives.pdf
- An improvement to swing techniques for elicitation in MCDM methods. *Knowledge-Based Systems* (2019). https://www.sciencedirect.com/science/article/abs/pii/S0950705119300012
- Comparison of weighting methods used in multicriteria decision analysis frameworks in healthcare. https://becarispublishing.com/doi/10.2217/cer-2018-0102
- Lahdelma, R., Hokkanen, J. & Salminen, P. (1998). SMAA — Stochastic multiobjective acceptability analysis. *European Journal of Operational Research* 106.

**Deep uncertainty and regret**
- Rigter, M., Lacerda, B. & Hawes, N. (2021). Minimax Regret Optimisation for Robust Planning in Uncertain Markov Decision Processes. https://arxiv.org/pdf/2012.04626
- Adaptive robust optimization with minimax regret criterion. *Computers & Chemical Engineering* (2017). https://www.sciencedirect.com/science/article/abs/pii/S0098135417303459
- Hall, J., Lempert, R. et al. Robust Climate Policies Under Uncertainty: A Comparison of Robust Decision Making and Info-Gap Methods. *Risk Analysis*.
- Decision-making under deep uncertainty: a methodology for the future-proof design of energy systems. https://www.sciencedirect.com/science/article/pii/S2212827126005767

**Kelly and risk preferences**
- Kelly, J. L. (1956). A New Interpretation of Information Rate. *Bell System Technical Journal* 35(4).
- Chapman, M. (2017). Kelly betting on horse races with uncertainty in probability estimates. https://arxiv.org/pdf/1701.02814
- Downey, M. Why fractional Kelly? Simulations of bet size with uncertainty and downside risk mitigation. https://matthewdowney.github.io/uncertainty-kelly-criterion-optimal-bet-size.html
- MacLean, L. C., Thorp, E. O. & Ziemba, W. T. (2011). *The Kelly Capital Growth Investment Criterion*. World Scientific.
