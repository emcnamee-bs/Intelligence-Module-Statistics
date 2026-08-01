# Research Log — Intelligence Module: Statistics

Living document. Appended to as research proceeds. Newest sections at the bottom of each part.

**Project:** a pure-stdlib, executable library of statistical models an AI agent can call to back its
judgment with mathematics, plus a skill that decides *whether statistics is warranted at all*.

**Repo:** https://github.com/emcnamee-bs/Intelligence-Module-Statistics

---

## Part 0 — Prior art and skill-authoring craft (2026-07-31)

Purpose of this pass: before designing the module, find out (a) how deep skills are actually built
by people who have measured results, and (b) whether this already exists.

### 0.1 What already exists

| Prior art | What it is | Deps | Executable? | Gap it leaves |
|---|---|---|---|---|
| [`bayesian-workflow`](https://learnbayesstats.com/blog-posts/bayesian-workflow-agent-skill-pymc-arviz) (Andorra / PyMC Labs) | Skill enforcing a 9-step Bayesian workflow: generative story → priors → PyMC impl → prior predictive → NUTS → convergence diagnostics → posterior predictive + LOO-PIT → LOO/ELPD comparison → report | PyMC, ArviZ, nutpie | Workflow prose, agent writes the model | Enforces *process* for one paradigm. Not a callable model library; no "should I even do this" gate |
| [`cc-thinking-skills`](https://github.com/tjboudreaux/cc-thinking-skills) | 28 mental-model frameworks (first-principles, pre-mortem, Cynefin, probabilistic reasoning, margin-of-safety, red-team…) with a `thinking-model-router` meta-skill | none | **No — prose only** | Qualitative frameworks with no arithmetic. Nothing computes |
| Marketplace `statistical-analysis` skills (several) | t-test / ANOVA / chi-square / regression / power analysis with APA-style reporting | scipy, statsmodels, pandas | Yes | Academic hypothesis-testing framing; assumes a dataset and a research paper. Not decision-framed. Heavy deps |
| [`awesome-claude-skills`](https://github.com/BehiSecc/awesome-claude-skills) catalogs | CSV summarizers, evidence-grading research skills, weighted-criteria vendor scoring | mixed | Mixed | Nothing quantitative under uncertainty |

**Conclusion: the niche is real and unoccupied.** No one ships a *pure-stdlib, executable, routed
library of decision-relevant statistical models with a gating doctrine*. The three closest things
each solve one third of it — process rigor (bayesian-workflow), routing across a reasoning catalog
(cc-thinking-skills), and actual computation (marketplace stats skills) — and none combine them.

### 0.2 The strongest scientific justification for the project

From [Analyzing and Mitigating Miscalibration in Tool-Use Agents](https://www.arxiv.org/pdf/2601.07264):
there is a **confidence dichotomy by tool type**. *Evidence tools* (web search, retrieval)
systematically induce **overconfidence** — the agent mistakes information availability for
correctness. *Verification tools* (code interpreters, anything that checks reasoning against a
ground truth) **improve calibration**. The paper's design recommendation is to embed feedback
mechanisms into agent workflows: tools should not merely answer but let the agent assess confidence
against a verification signal.

This module is squarely a **verification tool**. That is the thesis, and it should be stated in
SKILL.md as the rationale — it tells the agent *why* the detour is worth the tokens.

Supporting: LLMs are [overconfident in their own responses](https://arxiv.org/pdf/2606.03437) and
[wired for inflated verbalized confidence](https://arxiv.org/html/2604.01457); verbalized confidence
is nonetheless better calibrated than raw logits for instruction-tuned models
([On Verbalized Confidence Scores](https://arxiv.org/html/2412.14737v2)). So the agent *can* state a
number — it just needs the number to come from somewhere real.

### 0.3 Measured effects of a deep skill (the one hard datapoint)

`bayesian-workflow`, tested across 6 scenarios:

- **Task success: 90.5% without → 100% with**
- **Cost: +29% execution time, +87% token usage**

Failure modes observed in agents *without* the skill — all directly reusable as our misuse guards:

1. Omitted coordinates/dimensions from model definitions (silent shape errors)
2. Used **frequentist language for Bayesian results** ("statistically significant" on a posterior)
3. **Ignored diagnostics signalling unreliable results** (high divergence counts) and reported anyway
4. Failed to prefer the simpler model when the data couldn't distinguish alternatives

(3) is the important one for us: agents will read a number off a tool and use it *even when the tool
said the number is untrustworthy*. Warnings printed alongside a result are not enough. This is an
argument for **refusing to emit a headline number** when assumptions are violated, not just
annotating it.

The +87% token figure is also the empirical case for the Tier 0 gate. A skill this expensive must
not fire on trivia.

### 0.4 Official skill-authoring constraints (Anthropic)

Source: [Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)

Hard rules:
- `name`: ≤64 chars, **lowercase letters/numbers/hyphens only**, no XML tags, **cannot contain the
  reserved words "anthropic" or "claude"**
- `description`: ≤1024 chars, non-empty, third person, states **both what it does and when to use it**
- SKILL.md body **under 500 lines**
- **File references one level deep from SKILL.md.** Nested references cause partial reads — the agent
  `head -100`s a file reached via another file and acts on incomplete information
- Reference files >100 lines **must open with a table of contents**, so partial reads still reveal scope
- Forward slashes in all paths

Design guidance that maps directly onto this project:
- **Degrees of freedom should match task fragility.** Fragile, consistency-critical, error-prone
  operations → *low freedom*: a specific script with few parameters, invoked exactly. Statistical
  computation is the textbook case. Validates scripts-over-prose.
- **Scripts are executed, not read.** Bash execution costs zero context; only stdout is charged.
  Reference files cost nothing until opened. This is the whole token-efficiency answer.
- **grep-based navigation of reference files is an officially recommended pattern** (`grep -i "revenue"
  reference/finance.md`). Validates the generated-markdown mirror alongside the router.
- **"Solve, don't punt."** Scripts must handle their own error conditions rather than emitting a
  traceback for the agent to interpret.
- **No voodoo constants** (Ousterhout). Every threshold documented with its reasoning. "If you don't
  know the right value, how will the agent determine it?"
- **Build evaluations first**, before writing documentation: identify gaps by running the agent on
  representative tasks *without* the skill, build ≥3 scenarios, measure baseline, then write the
  minimum content that closes the gap.
- Descriptions should be slightly **"pushy"** — Claude tends to *under*-trigger skills.
- Test across Haiku / Sonnet / Opus; what suits Opus may underspecify for Haiku.
- **Plan-validate-execute** for high-stakes multi-step work: emit a structured plan file, validate it
  with a script, then execute.

### 0.5 The runtime constraint that settles the dependency question

> **Claude API: has no network access and no runtime package installation.**
> claude.ai: can install from npm/PyPI.

A scipy-dependent statistics skill is *structurally unusable* in the API code-execution environment.
Pure stdlib is not merely convenient here — it is the only choice that makes the module portable
across every environment an agent runs in. Every scipy-based prior-art skill in §0.1 fails this test.

Corroborating pressure: a **Snyk ToxicSkills audit (Feb 2026) of 3,984 skills found 36% with at least
one security flaw, 13.4% critical, and 76 confirmed malicious payloads** (credential theft,
backdoors, exfiltration). A self-contained module with no network calls, no installs, and no
third-party code is trivially auditable. Worth stating as a property, not an accident.

Also relevant: Agent Skills became an **open standard (agentskills.io) in Dec 2025** — building to the
spec makes this portable beyond Claude Code.

### 0.6 Routing / discovery research

[Skill Retrieval Augmentation for Agentic AI](https://arxiv.org/pdf/2604.24594) frames skill selection
as an information-retrieval problem and finds retrieval method measurably changes task completion.
Documented failure modes of naive selection:

- **Limited discoverability** — relevant skills missed when terminology doesn't align
- **Context insensitivity** — basic matching ignores nuanced requirements
- **Scalability collapse** — manual/exhaustive approaches break down as the library grows

Implication for `route.py`: keyword matching on model names will not survive. The registry needs
**situation phrasing** — the words an agent would actually use to describe its predicament ("is this
slowdown real", "should I trust this benchmark", "how many runs is enough") — indexed alongside
formal model names, with synonym coverage. The registry is a retrieval index, not a catalog.

`cc-thinking-skills` independently arrived at a router meta-skill, and validates it with **"routing
evaluations ensuring skill discoverability and false-positive control."** Both halves are test
categories we should adopt — false-positive control is precisely the Tier 0 gate.

### 0.7 Numerics: pure-stdlib feasibility and golden-test sources

`math` already provides `lgamma`, `gamma`, `erf`, `erfc`; `statistics` provides `NormalDist` with
`inv_cdf`. The missing pieces for the distribution layer are the regularized incomplete beta and
gamma functions, which unlock Student-t, F, chi-square, beta, and gamma.

Published algorithms with reference test values, suitable as golden-test oracles:
- **ASA063** — incomplete beta function (Applied Statistics Algorithm 63)
- **ASA032** — incomplete gamma function (Applied Statistics Algorithm 32)
- Cephes `incbet` (continued-fraction incomplete beta) — the algorithm behind many implementations
- [John D. Cook's notes on gamma functions in Python](https://www.johndcook.com/blog/gamma_python/)

Note the accuracy caveat: these classical algorithms have *different* accuracy characteristics from
SciPy's Boost-backed implementations. Our golden tests must therefore assert against **published
reference values**, not against SciPy output, and each function must declare its accuracy envelope.

### 0.8 Net changes to the design from this pass

1. **Evals before code.** Wave 0 starts by running representative judgment tasks *without* the module
   and recording the baseline failures verbatim. Both Anthropic's guidance and the superpowers
   TDD-for-skills method insist on this, and `bayesian-workflow` is the proof it pays.
2. **Assumption violations suppress the headline number** rather than merely warning next to it —
   because observed agent behaviour is to report the number anyway.
3. **The registry is a retrieval index keyed on situation phrasing**, not a catalog keyed on model
   names, and routing quality gets its own eval set covering both recall and false-positive control.
4. Minor but binding: skill `name` cannot contain "claude"/"anthropic"; family reference files link
   directly from SKILL.md (one level) and each opens with a TOC.

### 0.9 Sources (Part 0)

- [Skill authoring best practices — Claude Docs](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
- [Agent Skills overview — Claude Docs](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
- [I Taught My Coding Agent to Think Like a Bayesian — Learning Bayesian Statistics](https://learnbayesstats.com/blog-posts/bayesian-workflow-agent-skill-pymc-arviz)
- [tjboudreaux/cc-thinking-skills](https://github.com/tjboudreaux/cc-thinking-skills)
- [Analyzing and Mitigating Miscalibration in Tool-Use Agents](https://www.arxiv.org/pdf/2601.07264)
- [Skill Retrieval Augmentation for Agentic AI](https://arxiv.org/pdf/2604.24594)
- [Large Language Models Are Overconfident in Their Own Responses](https://arxiv.org/pdf/2606.03437)
- [Wired for Overconfidence: A Mechanistic Perspective](https://arxiv.org/html/2604.01457)
- [On Verbalized Confidence Scores for LLMs](https://arxiv.org/html/2412.14737v2)
- [BehiSecc/awesome-claude-skills](https://github.com/BehiSecc/awesome-claude-skills)
- [obviousworks/Claude-AI-skills-collection-2026](https://github.com/obviousworks/Claude-AI-skills-collection-2026)
- [Python `statistics` module docs](https://docs.python.org/3/library/statistics.html)
- [ASA063 — incomplete beta](https://people.math.sc.edu/Burkardt/py_src/asa063/asa063.html)
- [ASA032 — incomplete gamma](https://people.math.sc.edu/Burkardt/c_src/asa032/asa032.html)
- [Gamma functions in Python — John D. Cook](https://www.johndcook.com/blog/gamma_python/)

---

## Part 1 — Territory sweep (13 parallel reports)

Full reports live in `research/territories/`. This section records only **cross-cutting findings that
change the design**; per-model detail stays in the territory files.

### Status

| # | Territory | Report | Models |
|---|---|---|---|
| 01 | Bayesian inference & decision theory | ✅ `01-bayesian-decision-inference.md` | 26 + 26 cut |
| 02 | Causal inference | ✅ `02-causal-inference.md` | 24 + 15 cut |
| 03 | Forecasting & time series | ✅ `03-forecasting-time-series.md` | 23 + 22 cut |
| 04 | Robust & nonparametric | ✅ `04-robust-nonparametric.md` | 26 + 30 cut |
| 05 | Extreme value & tail risk | ✅ `05-extreme-value-tail-risk.md` | 24 + 20 cut |
| 06 | Sequential design & stopping | ✅ `06-sequential-design-stopping.md` | 25 + 15 cut |
| 07 | Calibration & forecast scoring | ✅ `07-calibration-forecast-scoring.md` | 23 + 22 cut |
| 08 | Evidence synthesis & aggregation | ✅ `08-evidence-synthesis-aggregation.md` | 23 + 20 cut |
| 09 | Reliability, survival & duration | ✅ `09-reliability-survival-duration.md` | 23 + 22 cut |
| 10 | Decision, bandits & value of information | ✅ `10-decision-bandits-voi.md` | 25 + 19 cut |
| 11 | Elicitation & subjective estimation | ✅ `11-elicitation-subjective-estimation.md` | 22 + 14 cut |
| 12 | Model selection & information theory | ✅ `12-model-selection-information-theory.md` | 22 + 20 cut |
| 13 | Monitoring, anomaly & changepoint | ✅ `13-monitoring-anomaly-changepoint.md` | 24 + 21 cut |

### 1.1 Design implication: prefer breakdown values to pass/fail assumption checks

**Source:** territory 02. Roth (2022) shows the pre-trend test an analyst would naturally reach for is
underpowered enough that **conditioning on having passed it makes bias worse**. Screening on a
low-power assumption test is not a neutral filter — it selects for datasets where the violation
happened to be invisible.

This generalizes well beyond difference-in-differences, and it refines the refusal semantics in
§8 of the spec. The three-level OK / CAVEAT / REFUSED ladder is still right for *structural*
violations — inputs that are inconsistent, degenerate, or outside a function's domain. But for
*assumption* violations that are matters of degree, a binary check is the wrong instrument. Those
should instead report a **breakdown value**: how strong would the violation have to be to overturn
the conclusion?

Concretely, the E-value answers "how strong would unmeasured confounding have to be to explain away
this effect" in a single number computable from three inputs. That is far more useful to an agent
than "assumption check: passed."

**Action:** §8 gains a fourth output mode alongside OK / CAVEAT / REFUSED — models whose assumptions
are matters of degree emit a `ROBUSTNESS:` line quantifying what it would take to overturn the
result, rather than asserting the assumption holds. Where a breakdown value is computable, it is
preferred to an assumption test. To be folded into the spec before Wave 0.

### 1.2 Design implication: some naive answers are wrong, not merely imprecise

**Source:** territory 02. Two-way fixed effects with staggered treatment timing can return an estimate
**outside the convex hull of every unit's true effect, including the wrong sign**, because it
silently uses already-treated units as controls (Goodman-Bacon; Callaway–Sant'Anna; Sun–Abraham).

Most of this library's value proposition is "the model is more precise than intuition." This is a
different and stronger category: cases where the obvious approach is *actively misleading*. Those
models deserve priority in Wave 1 regardless of how often the situation arises, and the registry
should mark them so the router can surface the warning even on a weak match.

**Action:** add a `naive_answer_is_wrong: true` flag to the registry schema for models in this class.

### 1.3 Ranking inversion worth noting

Territory 02 ranks **sensitivity analysis and bounds above every estimator**, on the grounds that the
agent's modal input is "an effect size and a story," not a panel dataset. Two of its top five require
*no data at all*: the back-door criterion with good/bad-control classification is pure graph
algorithms over a stated causal structure.

This is evidence the INLINE tier is richer than assumed at design time, and that "no data" does not
mean "no rigorous answer available." Watch whether other territories replicate the inversion.

### 1.4 Cross-territory hazard logged

Using a **detected** changepoint as the intervention date in an interrupted time series invalidates
the inference — the date must be specified a priori. This couples territory 13 (changepoint
detection) to territory 02 (ITS), and is exactly the kind of composition error an agent chaining two
tools would make. Candidate for an explicit warning in both models' output.

### 1.5 Design implication: the modern methods are the cheap ones

**Source:** territory 06. The single most useful finding of the sweep so far.

I assumed the pure-stdlib constraint would push us toward classical, textbook methods and away from
recent literature. **The opposite is true in this territory.** Anytime-valid inference — betting
confidence sequences, empirical-Bernstein confidence sequences, the Wang–Ramdas anytime-valid t-test
— needs only `log`, `exp`, `sqrt` and running plug-in estimators. No incomplete beta, no noncentral
t, no multivariate-normal orthant integration.

The hard numerics in this territory are all in the *classical* rows: exact t-test power, group
sequential boundaries via alpha spending. So the methods that are **better suited to an agent** (stop
as soon as convinced, peek as often as you like, no pre-committed sample size) are also the
**cheapest to implement and the easiest to test**.

**Action:** Wave 1 leads with the anytime-valid family rather than treating it as advanced material.
Reconsider whether classical power analysis is even worth shipping beyond the sample-size planning
case, given it is both harder to implement and answers a question the agent rarely gets to ask
(agents almost never get to fix n in advance).

This also weakens the §9 dependency between models and `lib/special.py`: if the flagship
evidence-sufficiency tools need no special functions at all, the highest-risk component of the
project is less load-bearing than the design assumed.

### 1.6 Design implication: two hard REFUSEs identified

**Source:** territory 06. Both are cases where an agent's *default workflow* is the failure mode.

1. **Post-hoc power** — computing achieved power from the observed effect. It is a deterministic
   function of the p-value and carries no information; it reliably misleads. Hard refuse.
2. **Fisher's method (and friends) for pooling adaptively-run studies.** "Decide whether to run study
   k+1 based on how study k came out" is *exactly* the agent's natural behavior, and it breaks every
   classical pooling method. The fix is e-value products, which remain valid under adaptive stopping.

(2) matters beyond this territory: it is a **composition hazard** between the synthesis family
(territory 08) and the evidence-sufficiency family. Any pooling model must ask whether the inputs
were collected adaptively, and refuse if so, pointing at the e-value route instead. Logging alongside
the ITS/changepoint hazard in §1.4 — a pattern is forming where the dangerous errors are in *chaining
two tools*, not in either tool alone.

**Action:** add a `composition_hazards` field to the registry schema, naming model ids that must not
be chained into this one and why. The router prints these when it returns a match.

### 1.7 Newly-published work worth tracking

- Chugg & Ramdas, arXiv:2512.21300 — closed-form empirical-Bernstein confidence sequence, removes the
  grid search from the prior construction.
- Schultzberg, arXiv:2606.18366 — first closed-form sample-size correction for *planning* a sequential
  design; 8–20% saving over the naive last-point rule.
- Waudby-Smith & Ramdas 2024 — betting/hedged-capital confidence sequences for a bounded mean; the
  flagship "can I stop now" tool.

### 1.8 Design implication: self-calibration is practical, not aspirational

**Source:** territory 07. Potentially the highest-value finding of the whole sweep.

The received wisdom — imported from clinical prediction modelling — is that you need ~200 resolved
events before saying anything about calibration. On that basis, an agent auditing its own confidence
would need a prediction log it will never have, and the calibration family would be decorative.

**That rule does not apply here.** It governs *flexible calibration curves* (isotonic, beta). For
**calibration-in-the-large** — the single question "am I systematically overconfident, and by how
much" — the arithmetic is completely different, for two reasons: binomial variance `p(1-p)` is small
near p = 0.9 where agents actually make claims, and the effect being detected is enormous (published
ECE for LLM verbalized confidence runs 0.17–0.57).

Detecting the overconfidence gap **as it actually exists** needs:

| Gap to detect | Resolved predictions needed (80% power) |
|---|---|
| The real, published gap | **N ≈ 11–25** |
| 10 points | N ≈ 85 |
| 5 points | N ≈ 315 |

**An agent that has logged ~20 resolved predictions can legitimately measure and correct its own
overconfidence.** That is within reach of a single long session, let alone a project. This promotes
the calibration family from "nice if we ever get data" to a Wave 1 candidate.

### 1.9 Design implication: LLM confidence is sparse, so bin nothing

**Source:** territory 07. The entire ECE-binning controversy (bin count artifacts, boundary
sensitivity, the well-known critiques of ECE as a metric) is **irrelevant to this use case**.

LLM verbalized confidence is not continuous. It concentrates on 6–8 distinct values — the COLM 2026
mechanistic paper observes {70, 75, 80, 85, 90, 99}. So the right operation is **grouping by exact
stated value**, which is exact rather than approximate, has no tuning parameter, and sidesteps the
entire literature. Fewer lines of code *and* more correct.

Corollary: the CORP decomposition via pool-adjacent-violators gives a binning-free
miscalibration/discrimination/uncertainty split in roughly 30 lines of stdlib, and should replace the
classical Murphy decomposition as the default.

### 1.10 Design implication: a calibration number alone is a lie

**Source:** territory 07. Two refusal rules, both structural rather than degree-of-violation:

1. **ECE = 0 is achievable by a constant forecaster that always predicts the base rate.** A
   calibration statistic is therefore meaningless without a companion **skill-vs-base-rate score** and
   a **sharpness/resolution** term. No model in this family may print a calibration number alone.
   This is the "reliability without resolution is worthless" point, enforced in the output contract.
2. **Recalibration gains must never be reported in-sample.** Fitting a recalibration map and then
   scoring on the same data always shows improvement.

Plus a **protocol precondition** that is stronger than a refusal-on-violation: per the 2026
protocol-sensitivity paper, the *sign* of the calibration gap flips with elicitation context. A log
assembled from mixed elicitation protocols, or reconstructed from recall, must be **refused
outright** — no statistic repairs it. This is the first case in the sweep where the tool must
interrogate *how the data was collected* before touching it, which suggests the registry needs a
`data_provenance_required` marker.

### 1.11 Pattern emerging across territories

Three territories in, the dangerous failures are consistently **not** in choosing the wrong model.
They are:

- **Composition errors** — chaining two individually-valid tools invalidly (§1.4 changepoint→ITS,
  §1.6 adaptive collection→pooling).
- **Provenance errors** — running a valid model on data whose collection process breaks it (§1.10
  mixed elicitation, §1.6 adaptive stopping).
- **Incomplete reporting** — a technically correct number that misleads alone (§1.10 calibration
  without resolution, §1.1 assumption checks without breakdown values).

None of these are addressed by the current spec, which guards mainly against *bad inputs to a single
model*. The registry schema additions now pending — `composition_hazards`, `data_provenance_required`,
`naive_answer_is_wrong`, plus the `ROBUSTNESS:` output mode — all exist to close this gap. Worth
consolidating into a spec revision once the sweep completes rather than patching it three more times.

### 1.12 Architectural finding: the numerics core is far smaller than the spec assumed

Four territories now independently report that the methods best suited to agent-scale problems need
almost no special functions. This is the single biggest de-risking of the project so far, because
`lib/special.py` was named as the top risk in the design spec (§13).

| Territory | What it actually needs |
|---|---|
| 06 sequential | `log`, `exp`, `sqrt` + running estimators. The *classical* rows need the hard numerics; the modern anytime-valid rows need none |
| 12 model selection | Only the regularized upper incomplete gamma (chi-square survival). 9 of 22 rows avoid even that via permutation / bootstrap / sample-splitting / e-values. ~80% ships on `log`, `lgamma`, `random.shuffle` |
| 05 tail risk | Closed-form L-moment GPD (`ξ̂ = 2 − ℓ₁/ℓ₂`) *beats* MLE at agent sample sizes and needs no optimizer. The workhorse tail fit is EASY, not HARD |
| 09 reliability | Regularized incomplete gamma + its inverse, `NormalDist`, `math.erfc`. The log-rank χ²₁ tail is closed-form as `erfc(√(x/2))` |

**Convergent conclusion.** `lib/special.py` reduces to essentially two functions — regularized
incomplete gamma (with inverse, for χ² quantiles) and regularized incomplete beta — rather than the
broad special-function library the spec envisaged. Meanwhile `lib/resample.py` rises in importance:
at agent-scale n, permutation and bootstrap buy *asymptotics-free validity* for CPU cycles that cost
nothing.

The reason is not a coincidence. Methods that are exact, distribution-free, or resampling-based are
simultaneously (a) the right choice at small n, where asymptotic approximations fail, and (b) trivial
to implement, because they replace analysis with computation. The pure-stdlib constraint and
statistical correctness at agent scale point the same direction.

**Action:** revise spec §9 and §13. Downgrade `lib/special.py` from top risk; promote
`lib/resample.py` into the Wave 0 core (already there) and treat exactness-by-resampling as the
library's default idiom rather than a fallback.

### 1.13 Design implication: trust thresholds must scale with n

**Sources:** territories 12, 05, 09. A hard-coded threshold is a voodoo constant in disguise when the
quantity it guards is sample-size dependent.

- **PSIS-LOO k̂** was revised in 2024 from a flat 0.7 to `min(1 − 1/log₁₀S, 0.7)` — explicitly
  sample-size dependent (territory 12).
- **Permutation tests**: with n₁ = n₂ = 3 the minimum achievable p is 0.10, so the test *cannot* reject
  at α = 0.05. Not a caveat — an arithmetic impossibility (territory 12).
- **Mutual information**: McAllester & Stratos (2020) proved no distribution-free lower bound on MI
  from n samples can exceed `ln n`. A theorem-backed refusal rule, not a heuristic. Plug-in MI is also
  biased *upward* by `(K_X−1)(K_Y−1)/2n`, so it is essentially never zero even for independent
  variables (territory 12).
- **Order statistics**: at n = 100 there is **no** upper confidence bound available on any quantile
  above p97. A reported "p99 from 100 samples" is not a statistic (territory 05).
- **AIC vs BIC**: the penalties cross at `n = e² ≈ 7.39`. Below n ≈ 7, **AIC penalizes complexity more
  than BIC** — the universal "BIC is the conservative one" intuition inverts precisely in the small-n
  regime agents live in (territory 12).

**Action:** every threshold in the library is a documented function of n where the statistics say it
should be, and the L1 test suite includes cases at the crossover points above.

### 1.14 New refusal category: the question itself has no answer

Distinct from refusing on bad inputs. Here the inputs are fine and the model is right — but the
question as posed is malformed, and answering it at all would mislead.

- **"When should I give up on this long-running process?"** has no threshold answer in general: the
  optimal policy is determined by hazard shape, and under *decreasing* hazard it is degenerate —
  never abandon, because every minute survived improves the outlook. The tool must say so. This
  directly contradicts the agent's instinct to kill a long-running process (territory 09).
- **Reliability-growth extrapolation**: the National Academies (2015) formally state they "do not
  support the use of these models for such predictions." Crow-AMSAA forecasting becomes a hard
  refusal, not a caveat (territory 09).
- **Tail shape at agent scale**: arXiv:2606.16511 pre-registered a tail-shape protocol on LLM
  evaluations and killed its own hypothesis — Δξ̂ = 0.28 at 2,000 prompts collapsed **30×** to 0.009 at
  30,000. Detecting Δξ = 0.10 needs ~1,570 exceedances. External validation that ξ is a *sign*, not a
  number, at our scale (territory 05).

**Action:** §8 output contract gains a `NO ANSWER EXISTS` mode alongside OK / CAVEAT / ROBUSTNESS /
REFUSED, which explains *why the question is unanswerable* and what decidable question to ask
instead. This is arguably the highest-value thing the module can do for an agent's judgment, because
it is the failure mode no amount of computation fixes.

### 1.15 Consolidation candidates spotted

Territory 05 reports that the rule of three, Wilks' 95/99 tolerance interval (n = 299), and "can I put
an upper CI on p99" are **the same inequality**, `n ≥ ln(α)/ln(p)`. One ~40-line module answers a
large fraction of tail questions exactly, with zero distributional assumptions.

Territory 09 independently ranks the zero-failure bound (`p ≤ 3/n`, `MTBF ≥ T/3` at 95%) as the
highest intuition-to-arithmetic gap in its territory — the same inequality again.

This is the first strong signal that the registry will contain **duplicate mathematics under
different names across families**, exactly as the cross-territory-overlap sections were meant to
surface. Dedup pass required before the registry is written: one implementation, multiple registry
entries pointing at it with family-specific `situations` phrasing. The router should route on the
situation; the code should exist once.

### 1.16 The most important finding of the sweep: pseudo-replication

**Source:** territory 08. The agent's dominant assumption violation when combining sources is **not**
heterogeneity — the thing every meta-analysis textbook prepares you for. It is **pseudo-replication**:
k sub-agents querying one base model are near-perfectly correlated, so they are not k independent
sources. They are approximately one source sampled k times.

Consequences, in order of severity:
- **Naive Bayesian chaining is catastrophic.** Updating on k correlated reports as though independent
  compounds the same evidence k times and drives posteriors to certainty on no new information.
- **Extremization is actively harmful.** The Good Judgment Project's extremizing transform assumes
  diverse, partially-independent forecasters. Applied to correlated agents it amplifies a shared
  error.
- Standard heterogeneity statistics (Q, I², τ²) will report *agreement*, which looks like corroboration
  and is actually the symptom.

This is the module's single highest-leverage guard, because the failure is invisible: correlated
agents agreeing looks exactly like independent agents converging on truth, and the naive statistics
actively reassure you.

**Note on this research sweep itself.** Thirteen agents on one base model produced these reports. The
finding applies. Where two territories independently converged (e.g. §1.12's numerics conclusion, the
rule-of-three appearing in both 05 and 09), that convergence is **weaker evidence than it appears** —
shared priors, not independent confirmation. Treated accordingly: convergent findings are logged as
hypotheses to verify against primary sources during implementation, not as settled.

**Action:** the synthesis family must ask for source independence before pooling, and refuse — or
apply a correlation-adjusted effective-k — when sources share a generator. Registry gains an
`independence_required` marker alongside `data_provenance_required` (§1.10).

Mitigation available and cheap: **Vovk & Wang (AoS 2022) — twice the arithmetic mean of p-values is a
valid p-value under *arbitrary* dependence.** One line of code, no independence assumption. That is
precisely the agent's epistemic position, and it should be the default pooling method with
independence-assuming methods as the opt-in.

### 1.17 Design implication: the module consumes stated numbers, it must not generate them

**Source:** territory 11. Measurement (arXiv:2402.07770) finds LLM-elicited priors frequently have
**effective sample size zero** — worse than uninformative, beaten immediately by minimal real data.
Observed pathologies include prior–data conflict, absurd tail concentration (one model emitting beta
α ≥ 1000), and expert role-play prompting having no measurable effect.

This is the elicitation territory's own warning label, and it sets a hard boundary for the module:
**take stated numbers as input; spend all effort checking, propagating, and stress-testing them;
never invent them.** A script that asks the agent for a prior is fine. A script that generates one on
the agent's behalf is a liability.

This also resolves an ambiguity in the design: the INLINE tier is not "the agent makes up numbers."
It is "the agent or user states numbers, and the module does the arithmetic they cannot do reliably
in their head."

### 1.18 Two headline results worth putting in SKILL.md verbatim

Both from territory 11; both are cases where agent intuition is wrong by orders of magnitude.

1. **Uncertainty does not compound the way it looks like it should.** k factors each uncertain by a
   factor of f multiply to a spread of `f^√k`, **not** `f^k`. Four factors each ±3× give a **9×**
   product spread, not 81×. Nine factors give 27×, not 19,683×. Errors partially cancel in log space.
   Agents get this wrong in *both* directions — over-widening Fermi estimates and under-widening
   sequential ones.
2. **Averaging scenario point estimates deletes most of the uncertainty.** In a worked three-scenario
   example, **92% of total variance is between-scenario** — exactly the term discarded when you
   average the three midpoints.

### 1.19 Stdlib windfall

`random` already ships `betavariate`, `gammavariate`, `lognormvariate`, `triangular`, `gauss`,
`expovariate`, `weibullvariate`, `paretovariate`. The entire Monte Carlo propagation layer is
therefore **free** — no distribution sampling to implement. Combined with §1.12, the build cost of
`lib/` keeps falling as research lands.

### 1.20 Research-quality caveats logged

- Territories 08 and 11 both hit a 200-call web-search session cap; some sources were covered from
  domain knowledge rather than fresh citation. Flagged for verification before those models ship.
- Territory 11 flags two specific unverified sources — the Mauboussin HBR per-phrase probability
  spreads (paywalled) and the UK DfT per-sector optimism-bias uplift table. **Neither may enter a
  shipped datafile as-is.** Any lookup table the module ships must have a verified primary source,
  since an agent will treat a shipped number as authoritative.

### 1.21 Design implication: Tier 0 becomes computable

**Source:** territory 10. The most consequential finding for the skill's architecture.

The gating doctrine (spec §5) currently asks the agent to judge whether statistics is warranted —
"is the decision reversible", "would a number change the action". Those are heuristics an
overconfident agent can talk itself past in either direction.

**Value-of-information theory makes the gate arithmetic.** Compute the decision threshold first, then
check reachability: for many proposed measurements the Expected Value of Sample Information is
**exactly zero at any accuracy** — no amount of data can move the decision — and this is *provable in
about three lines*. Territory 10 ranks this as the highest-yield refusal in its territory.

This reframes Tier 0 entirely. Instead of "use judgment about whether to use judgment", the skill can
say: run the EVPI check. If EVPI is zero or below the cost of measuring, stop — and you now have a
number justifying stopping rather than a vibe.

**Action:** promote an EVPI/EVSI reachability check to the **first tool the skill reaches for**, ahead
of any model selection. It is simultaneously the Tier 0 gate, the Tier 3 escalation trigger ("is
constructing this dataset worth it?"), and a model in its own right. Spec §5 to be rewritten around
it.

This also supplies the honest answer to the +87%-token cost concern in §0.3: the module's first act
is to check whether it should act at all, and that check is cheap.

### 1.22 Second consolidation cluster confirmed

Territory 10 reports that five of its rows (closed-form EVSI/ENBS via the unit normal loss integral,
exact Beta-Binomial EVSI by enumeration, Weitzman reservation values, and two others) are **the same
condition under different information models**: *marginal EVSI = marginal cost*. Recommends building
one engine, not five models.

This is the second such cluster, after §1.15's `n ≥ ln(α)/ln(p)` identity spanning the rule of three,
Wilks tolerance intervals, quantile upper bounds, and zero-failure MTBF.

Two clusters found in nine territories suggests the eventual registry has substantially fewer
*implementations* than *entries* — which is the right shape. One tested implementation, many registry
entries with family-specific `situations` phrasing routing into it. Confirms the dedup pass as a
required step before any code is written, and reduces the true build cost of Wave 1.

### 1.23 Design implication: asymptotic guarantees are mostly vacuous at agent scale

**Source:** territory 10, corroborating §1.13. At agent scale — tens to hundreds of trials, 2 to 20
options — the log-*n* asymptotics behind UCB and Thompson sampling **never bite**. The famous regret
bound is routinely worse than the trivial bound, so any tool reporting it must print
`min(UCB bound, n·Δ_max)` or it is quoting a guarantee that is arithmetically vacuous.

Further, the agent usually wants **one committed answer**, not maximized cumulative reward across a
long horizon. That makes **best-arm identification** the correct frame and regret-minimizing bandits a
supporting subcase — an inversion of how the literature is usually presented.

### 1.24 A widely-repeated piece of folklore is wrong

**Source:** territory 10. "Use half-Kelly to protect against estimation error" is wrong *as stated*.

Log-growth `Σ pᵢ log(1 + rᵢ f)` is **affine in p**, so parameter uncertainty in the outcome
*probabilities* does not change the optimal fraction at all — plug in the posterior mean. Simulation
confirms: σ = 20% on p moves f\* only from 0.40 to 0.36.

Fractional Kelly is really a CRRA risk-aversion statement (γ ≈ 1/λ), not an estimation-error hedge.
The actual defence against bad estimates is **shrinking p̄**, not scaling f.

Worth shipping precisely because it is a case where the agent's likely prior belief is confidently
wrong — the §1.2 `naive_answer_is_wrong` category.

### 1.25 An honest capability boundary

**Source:** territory 10. Single-parameter EVPPI is feasible in stdlib (sorted-window conditional
expectation). **Multi-parameter EVPPI needs GAMs or Gaussian processes and is out of reach.**

The correct behaviour is for the tool to *say so* rather than silently approximate. This is the first
clean instance of a boundary the module should advertise rather than paper over, and it belongs in
the `NO ANSWER EXISTS` output mode (§1.14) with a note on what would be needed.

### 1.26 Systemic research-quality caveat

Three territories (08, 10, 11) exhausted a 200-call web-search session budget, and territory 10 hit
its cap after only 8 searches, completing largely via direct source fetches and explicit derivation.

Consequence: **citation density is uneven across the sweep, and some findings rest on domain knowledge
rather than fresh verification.** Every territory report flags its own unverified constants. These are
not blocking — the mathematics in the affected rows was derived explicitly rather than recalled — but
verification against primary sources is a required step before any affected model ships, and is
folded into the Wave 1 definition of done rather than left implicit.

Compounding factor from §1.16: these reports are not independent evidence of each other.

### 1.27 CORRECTION to §1.12: permutation is exact, the bootstrap is not

Territory 04 measured what §1.12 assumed. §1.12 concluded that "exactness by resampling" should be
the library's default idiom and grouped permutation and bootstrap together as interchangeable
small-sample workhorses. **That conflation was wrong, and the error matters.**

Measured coverage of a nominal 95% CI for a lognormal mean at **n = 6** (pure-stdlib harness, run by
the territory agent rather than estimated):

| Method | Actual coverage |
|---|---|
| Bootstrap percentile | **0.731** |
| Bootstrap BCa | **0.753** |
| Bootstrap-t | 0.889 |

The two flavours an agent reaches for first are the two that fail hardest, and bootstrap-t only
closes the gap by producing an interval roughly 4× wider. Worse, the **bootstrap of a median at odd n
is degenerate**: at n = 5, 7, 9 it takes exactly 5, 7, 9 distinct values across 20,000 resamples, so
any quantile computed from it is meaningless — it looks like a distribution and is not one.

The distinction §1.12 missed: **permutation tests are exact** because they enumerate a null that is
true by construction under exchangeability. **The bootstrap is an asymptotic approximation** that
happens to be implemented by resampling. They share a mechanism and not a guarantee.

**Corrected position:** exactness comes from *enumeration under exchangeability* (permutation,
Mann–Whitney, signed-rank, order statistics, `math.comb` combinatorics) — not from resampling as
such. The bootstrap is a Wave 2 tool with loud small-n refusals, not a Wave 0 core primitive.

**Action:** revise spec §9 and Wave 0. `lib/resample.py` splits into `lib/exact.py` (permutation
enumeration, rank-statistic null distributions by dynamic programming, order-statistic intervals) for
the core, and a separate bootstrap module that refuses below a measured n floor. §1.12's headline —
that the numerics core is smaller than specced — survives; its stated reason was partly wrong.

This is also a live demonstration of §1.16: §1.12 was a convergent conclusion across four territories
and was still wrong in a detail none of them checked. Measurement beat convergence.

### 1.28 Design implication: do not route on assumption tests

**Source:** territory 04, and the strongest anti-recommendation in the sweep.

At n < 15, Shapiro–Wilk has near-zero power. Non-rejection is therefore **uninformative** — but an
agent reads "p = 0.6" as normality confirmed and proceeds to a t-test. The test manufactures false
license precisely where the agent most needs restraint.

This is the same structure as Roth's pre-trend result in §1.1 — screening on a low-power assumption
test is worse than not testing — now confirmed in a second, unrelated territory. It has become a
general principle rather than a quirk of difference-in-differences.

**Corrected routing doctrine:** route on **robustness-first defaults**, never on an assumption test.
Cost under normality is ~4.5% asymptotic relative efficiency. Benefit when the assumption fails is
unbounded. That trade is not close.

**Action:** no model in this library may branch on the result of a normality or assumption test, and
`route.py` must never ask one. Where an assumption genuinely matters, report a breakdown value
(§1.1), not a test.

### 1.29 Hard arithmetic floors to hardcode as refusals

**Source:** territory 04. These are not conventions or thresholds — they are facts about what the
design can express, and every one is a refusal the library should ship.

| Situation | Floor |
|---|---|
| Two-sided p < 0.05, two-sample | Unreachable at n₁ = n₂ = 3 (min p = 0.10) |
| Two-sided p < 0.05, paired | Unreachable at n ≤ 5 (min p = 0.0625) |
| 95% distribution-free median CI | First exists at **n = 6** |
| Split conformal, 95% | Needs **n ≥ 19** |
| `[min, max]` as a prediction interval | Covers only (n−1)/(n+1) = **71% at n = 6**; needs n = 39 for 95% |
| Two-sided 95/95 Wilks tolerance interval | Needs **n = 93** |
| Robust z-score via MAD | MAD hits **exactly 0** on ordinary discrete data such as `[10,10,10,11,10,40]`, killing every downstream calculation |
| Heavy-tail detection via kurtosis | Sample kurtosis is bounded above by ≈ n−1, so at n = 10 a Cauchy sample **cannot** look heavier-tailed than a normal one (measured maxima 8.11 vs 6.57, fully overlapping). Use `max|x| / Σ|x|` instead — separates cleanly (0.409 vs 0.234), one line |

The kurtosis result is another §1.2 `naive_answer_is_wrong` entry: the standard diagnostic is not
merely weak at small n, it is arithmetically incapable of detecting the thing it is used to detect.

### 1.30 Feasibility is now measured, not assumed

Territory 04 ran pure-stdlib timing harnesses rather than estimating. **Nothing in the territory is
computationally hard:**

- Exact permutation enumeration, C(24,12) = 2.7M: **0.51 s**
- Exact Mann–Whitney null via DP, 30 v 30: **0.027 s**
- Exact signed-rank null, n = 100: **0.010 s**
- Theil–Sen, n = 2000: **0.33 s**
- Boschloo's nuisance-parameter grid: **0.010 s**

This is the standard the rest of the sweep should be held to, and it retires the concern that pure
Python would force approximations. At agent scale it does not.

**New candidate flagged:** **HulC** (Kuchibhotla et al., JRSS-B 2024) — builds a confidence interval
from ~6 subsample estimates with **no variance estimate at all**, and is valid in settings where the
bootstrap provably is not. Given §1.27, this is the strongest new entrant in the sweep and a direct
replacement for the role the bootstrap was going to play.

### 1.31 The anomaly-detection benchmark literature is broken, which is licence to stay classical

**Source:** territory 13. Under the standard point-adjust evaluation protocol, a **random-scoring
detector achieves state-of-the-art F1** (Wu & Keogh; Kim et al., 2021–22).

The practical consequence is liberating rather than depressing: reported gains from sophisticated
learned anomaly detectors are substantially protocol artifacts, so there is **empirical licence to
ship classical methods** — robust z-scores, CUSUM, EWMA, exact Poisson tails — without apologising for
the absence of anything learned. This retires a worry that the pure-stdlib constraint was costing
real capability in this family. It isn't.

### 1.32 A false-alarm engine is worth more than another detector

**Source:** territory 13. Two results that together argue for shipping an **average-run-length engine**
as a first-class tool rather than as a helper.

- **Siegmund's CUSUM ARL approximation** reproduces Montgomery's published table to within 1–4% in
  *two lines of Python*. Threshold selection by declared false-alarm rate — rather than by round
  numbers like "3 sigma" — is therefore trivially shippable. This directly retires a voodoo constant
  the library would otherwise have had to invent.
- **The Western Electric rules drop ARL₀ from 370 to 91.75** — four times more false alarms than the
  base chart. Critically, that figure **cannot be obtained by adding the per-rule rates**: naive
  addition gives 52, because the rules use overlapping windows and are not independent.

The second is another composition hazard (§1.4, §1.6, §1.16): individually valid rules combined
naively give an answer that is wrong by ~76%. It is also the cleanest argument in the sweep for a
Monte Carlo engine — the exact answer is analytically awkward and trivially simulable.

**Action:** ship `average_run_length` as a first-class model. Every monitoring tool that asks for a
threshold takes a target false-alarm rate instead and derives the threshold, rather than accepting a
sigma multiplier.

### 1.33 Convergence on the agent's actual daily questions

Territory 13's top five are unusually concrete, and three of them are the situations that motivated
this project in the first place:

- **Benchmark regression verdict** — a CI on the *difference* against a **declared minimum-interesting
  effect**, rather than a significance test. Requiring the agent to state what size of regression
  would matter *before* computing is itself the guard against p-value theatre.
- **Flaky-or-unlucky** — Clopper–Pearson on the failure rate, the rule of three, and reruns-to-confidence.
  Third independent appearance of the `n ≥ ln(α)/ln(p)` identity (§1.15, §1.22), now from a completely
  different direction.
- **Exact Poisson rate check** for the 0/1/2-event case (Garwood CI plus exact tail).

Also note the **robust anomaly score ships with an IQR fallback for when MAD = 0** — territory 13
independently hit and solved the degenerate-MAD problem territory 04 flagged in §1.29. Two territories
converging on the same failure *and* the same fix is worth more than either alone, with the §1.16
caveat still applying.

Numerics requirement confirms §1.12 unchanged: regularized incomplete beta (t quantiles) and
incomplete gamma (χ² tails). Nothing else.

### 1.34 The standard correctness test has a blind spot aimed exactly at our worst failure

**Source:** territory 01. This is a direct hit on the verification design in spec §11.

Simulation-based calibration (SBC) is the field's standard test for "is this posterior implementation
correct", and it was the natural candidate for L2/L3 in this library. Modrák et al. (2023) showed
that **an implementation whose posterior simply equals the prior passes classic rank-based SBC
perfectly.**

That is precisely the failure this project most needs to catch. A model that silently ignores its
data and returns the prior would produce confident, well-formed, plausible output — and would sail
through the test we were going to trust. It is the worst possible combination: a tool that looks
authoritative while contributing nothing, handed to an agent already prone to overconfidence.

**Action:** any SBC harness in this library must include **data-dependent test quantities** — the
joint log-likelihood at minimum — not parameter ranks alone. Added to spec §11 as a stated
requirement rather than an implementation detail, because the failure mode is invisible without it.

Generalisable lesson, and the second time in two territories that a standard diagnostic has failed in
the small/adversarial regime (§1.28 Shapiro–Wilk, now SBC): **a passing assumption or correctness
check is not evidence unless its power against the specific failure has been established.** Worth
stating as a project-wide principle in the spec, since it has now bitten in routing, in assumption
testing, and in correctness testing.

### 1.35 Build-order finding: grid before MCMC

**Source:** territory 01, measured rather than estimated.

- Pure-Python MCMC at **7 parameters, 60,000 iterations: 0.14 s.** Compute is a non-issue. The
  engineering budget goes to R̂/ESS gating and refusal logic, not to optimisation.
- **At ≤ 3 parameters, a grid removes the entire diagnostic layer.** No PSIS, no k̂, no R̂, no ESS, no
  divergences. Power-scaling sensitivity, Savage–Dickey ratios, hierarchical τ integration and LOO all
  become **exact quadrature**.

Since the overwhelming majority of agent-scale Bayesian questions are 1–3 parameters, the grid engine
is both the common path and the one with no diagnostics to get wrong.

**Action:** build the grid engine first; MCMC becomes the 4–10 parameter fallback, shipped later and
behind convergence gating. This further shrinks Wave 0 — `lib/mcmc.py` moves out of the critical path
entirely, consistent with §1.12 and §1.27.

### 1.36 A specific agent failure mode with a specific fix

**Source:** territory 01. Agents habitually conflate **the posterior for a parameter** with **the
posterior predictive for the next observation** — reporting the uncertainty in the mean when the
question was about the next value. The two differ by exactly the observation noise, which is usually
the larger term.

The fix is structural rather than educational: the Normal-Inverse-Gamma model ships **both**, labelled
distinctly, always. A tool that emits only one invites the substitution.

This is the §1.10 "incomplete reporting" pattern again — a technically correct number that misleads
by omission — and the same remedy applies: make the output contract carry both quantities so the
agent cannot silently pick the wrong one.

Also flagged and worth carrying into the decision family: `P(A > B)` alone is **not** a sufficient
stopping quantity, because it is magnitude-blind. It must be paired with **expected loss**, which is
what actually answers "can I act on this yet". Territory 01 and territory 10 converge here from
opposite directions (§1.16 caveat applies).

Nice concrete instance for SKILL.md: **"what timeout should I set" is a newsvendor problem** — an
asymmetric-loss Bayes action, not a percentile lookup.

### 1.37 VERIFIED BUG CLASS: textbook PERT variance is internally inconsistent

**Source:** a subagent of territory 03. **Independently re-derived and numerically confirmed by the
orchestrator** — this one does not carry the §1.16 pseudo-replication caveat, because it was checked
by derivation and simulation rather than accepted.

Standard beta-PERT, given optimistic `a`, most likely `m`, pessimistic `b`:
- `α = 1 + 4(m−a)/(b−a)`, `β = 1 + 4(b−m)/(b−a)`, so **α + β = 6** (not 8)
- mean `μ = (a + 4m + b)/6`
- **exact variance `= (μ−a)(b−μ)/7`**

The classical companion formula `σ = (b−a)/6` **is not the standard deviation of that distribution.**
The two textbook formulas are mutually inconsistent. With `δ = (m−a)/(b−a)`, the variance ratio is
exactly:

```
R(δ) = Var_true / Var_classical = 5/7 + (16/7)·δ(1−δ)
```

Verified to machine precision at every mode position, plus a 4M-draw Monte Carlo check at the
symmetric case:

| Mode position δ | R(δ) | SD ratio | Effect of using (b−a)/6 |
|---|---|---|---|
| 0.0 or 1.0 (extreme) | 0.7143 | 0.8452 | **overstates SD by 18.3%** |
| 0.14645 / 0.85355 | 1.0000 | 1.0000 | exact — the only two points where it is right |
| 0.25 or 0.75 | 1.1429 | 1.0690 | understates by 6.5% |
| **0.5 (symmetric)** | 1.2857 | 1.1339 | **understates by 11.8%** (true SD is 13.4% higher) |

**Why this matters for this library.** Three-point estimation is one of the most-reached-for tools in
the whole catalog — "give me a range for how long this will take" is the archetypal agent question,
and territory 11 ranks PERT-family estimation highly. Anyone implementing the textbook formula gets a
variance wrong by −18% to +29% depending on mode position, and **in the common symmetric case the
error is optimistic — the interval is too narrow.**

An overconfidence-correcting module that ships a silently over-narrow interval on its most-used
estimator would be actively counterproductive. This is the §1.2 `naive_answer_is_wrong` category, and
it is the strongest single argument in the sweep for the L2 requirement that every model carry golden
cases checked against published reference values rather than against a remembered formula.

**Action:** ship `(μ−a)(b−μ)/7`. Where the classical `(b−a)/6` is expected by a user, print both and
label the discrepancy. Add the R(δ) identity to the L1 test suite at δ ∈ {0, 0.14645, 0.5, 0.85355, 1}.

### 1.38 Process note: the forecasting territory over-delegated

Territory 03 spawned its own subagents and then spent effort on inter-agent addressing rather than
research, with two subagents surfacing routing questions to the orchestrator instead of findings. The
research content was sound; the coordination was waste.

Recorded because it is the same class of failure the module is meant to guard against elsewhere:
**work expanded to fill an available mechanism without anyone checking whether it improved the
answer.** The value-of-information check in §1.21 is the formal version of the question that should
have been asked before delegating.

Two citation corrections surfaced by that chain, worth keeping:
- Jewell/Lewnard/Jewell IHME critique is **Annals of Internal Medicine 173(3):226–227**, not JAMA.
- Ioannidis/Cripps/Tanner (2022) contains **no numeric forecast-error magnitudes**; citable for its
  failure taxonomy and its "model predictive distributions, not point estimates" prescription only.

### 1.39 Territory 03 closing findings

- **The gate for the whole family**: rolling-origin backtest with a **MASE scorecard**. `MASE ≥ 1`
  means the model does not beat the naive forecast, and the tool should **print the naive forecast
  instead**. A hard, computable, non-negotiable edge — the forecasting family's own Tier 0.
- **Theta / SES-with-drift** (M3 winner) is ~40 lines, works at n = 5, and degrades gracefully toward
  naive as noise rises. **Damped-trend exponential smoothing** is described in the literature as "a
  benchmark for all others to beat." Both trivially stdlib.
- **12 of M4's 17 most accurate methods were combinations.** Simple mean/median combination is a
  top-5 method on its own.
- The territory's central pathology is that **prediction intervals are systematically too narrow**;
  empirical/conformal intervals are the fix. Third territory to land on conformal methods (with 04
  and 09).
- **M5's "pure ML finally wins" result does not transfer.** It depended on 42,840 related series plus
  exogenous variables. An agent holding one 12-point series has neither.
- Independently re-derived the §1.37 PERT result to machine precision.
- **Exemplary integrity handling**: the report ships a per-source verification ledger, tags the M4/M5
  headline numbers and SBC routing cutoffs (ADI 1.32 / CV² 0.49) as UNVERIFIED inline, and
  **deliberately quotes no OWA/sMAPE point values at all** rather than cite unverifiable figures. One
  gap named honestly: no published constant exists for how much of a growth curve must be observed
  before capacity K is estimable, so that refusal rule is labelled a geometric heuristic, not a
  citable constant. This is the standard for the rest of the project.

---

## Part 2 — Synthesis

**Sweep complete: 13 territories, 310 models ranked, 266 explicitly cut, 576 candidates evaluated.**

### 2.1 Ten principles the sweep produced

These emerged from the territories rather than being imposed on them, and several arrived from two or
more independent directions. They govern the library.

| # | Principle | Origin |
|---|---|---|
| **P1** | **Exactness comes from enumeration under exchangeability, not from resampling.** Permutation, rank-statistic DP, order statistics, `math.comb` — these are exact. The bootstrap is an asymptotic approximation that merely shares the mechanism, and it fails hardest at agent-scale n | §1.27 (measured) |
| **P2** | **Never route on an assumption test.** A passing check is not evidence unless its power against the specific failure has been established. Failed three times independently: Shapiro–Wilk at n<15, pre-trend tests, rank-based SBC | §1.1, §1.28, §1.34 |
| **P3** | **Trust thresholds scale with n**, and several are arithmetic impossibilities rather than conventions (p<0.05 unreachable at n=3; no upper CI above p97 at n=100; AIC/BIC penalties cross at n=e²) | §1.13, §1.29 |
| **P4** | **Report breakdown values, not pass/fail.** "How strong would the violation have to be to overturn this?" beats "assumption: OK" | §1.1 |
| **P5** | **The dangerous failures are composition, provenance, and incomplete reporting — not model choice.** Five composition hazards found | §1.11, §1.32 |
| **P6** | **Pseudo-replication is the dominant violation when combining sources.** k agents on one base model are one source sampled k times | §1.16 |
| **P7** | **The module consumes stated numbers; it never generates them.** LLM-elicited priors measure at effective sample size zero | §1.17 |
| **P8** | **The decision to use statistics is itself computable.** EVPI reachability replaces the judgment heuristic | §1.21 |
| **P9** | **Every model declares the baseline it must beat, and prints the baseline instead when it doesn't.** MASE ≥ 1 → print the naive forecast | §1.39 |
| **P10** | **Big-data ML benchmark results do not transfer to agent scale.** M5 needed 42,840 series; a random-scoring anomaly detector hits SOTA under the standard protocol | §1.31, §1.39 |

P9 deserves emphasis: it generalizes the forecasting family's MASE gate into a library-wide contract.
Every registry entry names a `baseline_to_beat`, and every model computes it. A statistical model that
cannot beat the naive alternative on the data in hand is not a better answer — it is a more expensive
one wearing better clothes, which is exactly the failure mode this project exists to prevent.

### 2.2 Identity clusters — the registry has fewer implementations than entries

Three clusters of "different models that are the same mathematics" surfaced independently:

| Cluster | The single identity | Appears as |
|---|---|---|
| **C1** | `n ≥ ln(α)/ln(p)` | rule of three; Wilks tolerance intervals; upper CI on a high quantile; zero-failure MTBF bound; flaky-or-unlucky reruns-to-confidence |
| **C2** | marginal EVSI = marginal cost | closed-form EVSI/ENBS; exact Beta-Binomial EVSI; Weitzman reservation values; optimal sample size; stop-or-continue |
| **C3** | exact null by dynamic programming over rank statistics | permutation test; Mann–Whitney; Wilcoxon signed-rank; exact CI by test inversion |

C1 alone spans four families (tail-risk, reliability, monitoring, evidence-sufficiency) and was found
by three territories that did not talk to each other.

**Consequence for the build:** one tested implementation, many registry entries with family-specific
`situations` phrasing routing into it. This substantially reduces the true cost of Wave 1 and is the
reason a dedup pass must run before any code is written.

### 2.3 Composition hazards — the errors no single model can catch

| Hazard | Consequence |
|---|---|
| Detected changepoint → interrupted time series | Invalidates the inference; the date must be a priori |
| Adaptive collection → classical pooling | Breaks every method; e-value products are the fix |
| Correlated sources → Bayesian chaining or extremizing | Compounds one piece of evidence into false certainty |
| Overlapping monitoring rules → additive false-alarm rates | ARL₀ 370→91.75, but naive addition gives 52 (wrong by ~76%) |
| Parameter posterior → next-observation question | Omits observation noise, usually the larger term |

These motivate the `composition_hazards` registry field and are the strongest argument that this is a
**skill** and not a folder of scripts. No individual model can detect any of them.

### 2.4 Net effect on the build

Every territory that reported on feasibility **shrank** the estimated core:

- `lib/special.py` → two functions (regularized incomplete beta, incomplete gamma + inverse)
- `lib/mcmc.py` → out of the Wave 0 critical path; grid quadrature covers ≤3 parameters exactly
- `lib/resample.py` → splits; `lib/exact.py` into the core, bootstrap demoted behind refusals
- Distribution sampling → free; `random` already ships what is needed
- Measured timings confirm nothing is computationally hard in pure Python at agent scale

The pure-stdlib constraint cost the project **almost nothing in capability** and bought portability,
auditability, and — via P1 and P10 — methods that are *more* correct at the sample sizes agents
actually face.

### 2.5 Standing caveats carried into implementation

1. **§1.16 applies to this whole document.** Thirteen agents on one base model are not thirteen
   independent sources. Convergent findings are hypotheses, not confirmations. The two findings
   verified by independent derivation (§1.27 measured, §1.37 re-derived) are the exceptions.
2. **Citation density is uneven.** Five territories exhausted their web-search budget. Every report
   flags its own unverified constants; territory 03 ships a per-source ledger and is the model.
3. **No unverified constant may enter a shipped lookup table.** An agent treats a shipped number as
   authoritative.
4. **Wave 1 definition of done includes primary-source verification** of every constant in every
   model that ships.

---

## Part 3 — Review findings

Five adversarial reviews run against the completed sweep and the revised spec. Full reports in
`research/reviews/`. This section records only what changes the project.

### 3.1 My territory design had gaps at the seams

**Source:** review 04. The 13 territories collectively defer work to **six territories that were
never commissioned**: regression, effect-size, multiple-testing, measurement-agreement,
distribution-comparison, and prediction/coverage. A cut reading "belongs to territory X" where X does
not exist is a **silent deletion**, and these account for roughly half the coverage gaps.

This is a design error in how I partitioned the research, not a failure of any agent. Thirteen
well-executed territories with unowned seams lose material that no individual report is responsible
for noticing.

### 3.2 Fifteen uncovered situations, several of them daily

Review 04 brainstormed 55 agent situations *blind* — without reading the catalog — then checked each
against the 310 ranked models. Fifteen had no adequate model. The ones that matter most are things
agents hit constantly and that the commissioned territories had no natural home for:

| Uncovered situation | Method |
|---|---|
| "My last 5 greps found nothing new — have I found everything?" | Good–Turing / Chao1 discovery saturation |
| "Two reviewers found 2 of the same bugs — how many are left?" | Capture–recapture |
| "A scored 40/50, B scored 43/50 **on the same items**" | McNemar (paired binary) |
| "Three configs across twenty benchmarks" | Friedman (blocked k-sample) |
| "Is this O(n²) or O(n log n)?" | Scaling-exponent fit |
| "Do these two LLM judges agree?" | κ / Krippendorff α / ICC |
| "Rank these from pairwise comparisons" | Bradley–Terry |
| "I keep running checks — how do I not fool myself?" | Online FDR over an unbounded stream |
| "How many records must I audit?" | Hypergeometric audit sampling |

The discovery-saturation and capture–recapture entries are notable: both answer *"is my search
finished?"*, which is among the most common judgment calls an agent makes, and neither appeared
anywhere in 310 ranked models.

### 3.3 Nine head-to-head contradictions between territories

The territories do not merely overlap — in nine cases they **disagree**, which means at least one side
is wrong and §1.16's convergence caveat does not apply. Notable:

- **T06 vs T10** cut each other's stopping model. T06 cut Weitzman/Pandora's box as "almost never
  available to an agent"; T10 ranked it **4th of 25** as "the exact situation an agent is in."
- **T06 vs T09** on censoring: "agents almost never have censored data" versus "censoring is the
  normal case." T09 is right — "still running, hasn't failed yet" is the agent's default data shape.
- **T04** ranked Kruskal–Wallis while self-flagging Friedman as a 27th row it wanted; for the common
  blocked design (k configs × n benchmarks) Kruskal–Wallis is simply **the wrong test**.
- **KSG mutual information** cut for lacking `digamma`, which T09 needs anyway and reports as ~15 lines.
- **Fault trees** cut because "agents do independent-probability arithmetic correctly unaided" — which
  the existence of T05's row 9 contradicts.

### 3.4 Nine more identity clusters — two larger than C1

This is the most consequential finding for the build. §2.2 found three clusters; review 04 found nine
more, and the largest subsumes the one I built the pilot around:

| Cluster | Identity | Span |
|---|---|---|
| **C4** | exact discrete-tail inversion | **11 territories** — and **C1 is merely its k = 0 case** |
| **C5** | `1 − (1−p)^k` | fan-out amplification ≡ return period ≡ **Šidák correction** ≡ reruns-to-confidence |
| **C6** | design effect / effective n | **6 territories** — *cut* in T06, flagship in T08 |
| **C7** | test inversion by bisection | 8 territories |
| **C8** | **extremizing ≡ inverse temperature scaling** | a correctness hazard, not just duplication |

Plus the Brier decomposition duplicated verbatim across T07/T08/T11, PAVA, the arithmetic-floor
engine, and e-processes across five territories.

**This changes the shape of the build entirely.** If one exact discrete-tail inversion engine spans
eleven territories, the library is not 30 models over a thin numerics core — it is **roughly six
well-tested engines** with many thin, situation-specific entry points routing into them. That is a
smaller, more coherent, far more testable project than the spec describes.

### 3.5 Thin families are thin from tier mismatch, not under-research

- **Calibration**: only 4 rows usable at N < 25, and *all* of them blocked on having a prediction log.
  Review 04's conclusion is sharp: **its Wave 1 deliverable is a logging protocol, not statistics.**
  There is nothing to compute until the agent has been recording predictions and outcomes.
- **Forecasting**: 23 rows collapse to 6 at n = 5–12.
- **Causal**: 24 rows collapse to 6 INLINE, and it is a *sensitivity* family, not an estimation one.

**Over-represented**: causal panel estimators (11), model-based EVT (11), bandit + MCDA variants (7),
model-choice (4). Roughly 35 rows freed — which comfortably funds the ~15 additions, all of which are
cheaper to build.

### 3.6 The spec revision regressed the part that matters

**Source:** review 03. Commit `cf1ecf9` replaced §5 "The skill" with §5 "The gate" and dropped §7
entirely. The consequence: the spec now pins `lib/special.py` to the function level while the skill
`name`, `description`, SKILL.md body structure, router output contract, and no-match floor are all
**unspecified**. The only part an agent touches is the part with no specification.

Also deleted: the guidance-form principle (conditionals on observable predicates, not prohibitions) —
and the replacement gate is precisely the shape that principle warned against.

### 3.7 The gate does not work

**Sources:** reviews 01 and 03, independently.

1. **EVPI was conflated with EVSI.** Under the specced CLI the loss table is fully determined, so
   EVPI = min(p, 1−p)·L — nonzero unless p ∈ {0,1} or L = 0. Wave 0's acceptance criterion
   ("must produce EVPI = 0") is **unsatisfiable under its own interface**. The three-line zero result
   in §1.21 is *EVSI threshold reachability*, which needs the test's informativeness.
2. **The routing table has an invalid direction.** EVSI(n) ≤ EVPI, so only the *stop* direction holds.
3. **It is unpopulable**: 0 of 6 baseline scenarios cleanly, 5 requiring fabricated inputs — and it
   demands exactly the class of number **P7 forbids the module from generating**, mandatorily and
   first. EVPI is monotone in those fabricated inputs, so the verdict is set by the guess while
   presenting as computed.
4. **Nothing enforces it**, and the agent reaches the skill *because* it already decided statistics
   were warranted, so the gate relitigates a decision one turn old.

### 3.8 `BASELINE_WINS` is actively harmful as specified

It prints a number at exit 0, indistinguishable from `OK`, so `if rc == 0: use the number` hands the
agent the **baseline's** answer carrying the module's authority. A naive estimate acquiring false
statistical provenance is worse than not running the module — this is §0.3's own refusal logic applied
inconsistently to the mode most exposed to it. Separately, `baseline_to_beat` has no computable
definition outside forecasting, and L4 contradicts §9 on whether the mode emits a number at all.

### 3.9 The token claim was not honest

Traced end to end: **~4,600 tokens favorable, ~8,000 realistic** — the same order as the +87%
precedent cited as the thing to avoid, not "near-zero." Structurally, SKILL.md is the largest line
item and is charged *before* the gate runs: the gate cannot save the tokens spent by the document
telling it to run the gate.
