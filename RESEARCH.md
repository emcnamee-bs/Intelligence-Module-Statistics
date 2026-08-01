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
| 01 | Bayesian inference & decision theory | pending | — |
| 02 | Causal inference | ✅ `02-causal-inference.md` | 24 + 15 cut |
| 03 | Forecasting & time series | pending | — |
| 04 | Robust & nonparametric | pending | — |
| 05 | Extreme value & tail risk | ✅ `05-extreme-value-tail-risk.md` | 24 + 20 cut |
| 06 | Sequential design & stopping | ✅ `06-sequential-design-stopping.md` | 25 + 15 cut |
| 07 | Calibration & forecast scoring | ✅ `07-calibration-forecast-scoring.md` | 23 + 22 cut |
| 08 | Evidence synthesis & aggregation | ✅ `08-evidence-synthesis-aggregation.md` | 23 + 20 cut |
| 09 | Reliability, survival & duration | ✅ `09-reliability-survival-duration.md` | 23 + 22 cut |
| 10 | Decision, bandits & value of information | pending | — |
| 11 | Elicitation & subjective estimation | ✅ `11-elicitation-subjective-estimation.md` | 22 + 14 cut |
| 12 | Model selection & information theory | ✅ `12-model-selection-information-theory.md` | 22 + 20 cut |
| 13 | Monitoring, anomaly & changepoint | pending | — |

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
