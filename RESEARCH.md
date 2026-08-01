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

### 0.9 Sources

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
