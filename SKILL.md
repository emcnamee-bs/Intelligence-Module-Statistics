---
name: statistical-judgment
description: >
  Checks whether a statistical claim is even reachable from the data at hand, corrects formulas that
  are commonly wrong, and refuses conclusions the evidence cannot support. Use when about to state a
  number, range, probability, or comparison that is not directly observed — a p-value, confidence
  interval, effect size, failure rate, estimate, forecast, or "X is better than Y" — and especially
  when the sample is small, when several things were compared or several checks run before a pattern
  was noticed, when combining results from multiple runs, agents, or sources, when deciding whether
  more data is worth collecting, or when asked how long something will take. Also use before
  concluding a search or investigation is complete.
---

# Statistical judgment

## Why this exists

Tools that supply *evidence* (search, retrieval) make agents more confident without making them more
right. Tools that *verify* — that check reasoning against something computable — improve calibration.
This is a verification tool.

But be clear about what it is for. **You can already compute most of this correctly.** Seven recorded
baselines (`evals/baselines/RESULTS.md`) show agents producing correct Welch t-tests, Wilson
intervals and exact binomial CDFs unaided, scoring 23 of 25. What those baselines could not do was
know a fact they were never told, notice a formula they had learned wrong, or catch themselves
concluding something the design could not support.

**So: don't reach for this to do arithmetic you can do. Reach for it when you are about to assert
something and are not certain the assertion is reachable at all.**

## Start here

One command. It costs no context until you run it, and it asks the gate question on the way past.

```bash
python3 route.py "is this 8% slowdown real or did I get unlucky"
```

It prints at most three matches with runnable commands, plus any hazards. If nothing fits it says
`NO CONFIDENT MATCH` rather than inventing a match — treat that as a real answer, usually meaning
this is not a question statistics decides.

`python3 route.py --family design` lists a family. `--id <model-id>` prints one usage block.

## Reading the output

Every script ends with a `REPORT AS:` line. **Say that sentence.** Do not paraphrase a number out of
the `RESULT` block on your own.

| Exit | Outcome | What it means |
|---|---|---|
| `0` | `ANSWER` | The number is the model's answer. `CAVEAT:` and `ROBUSTNESS:` lines qualify it. |
| `2` | usage error | You passed a bad flag. Fix the command. |
| `3` | `REFUSED` | Your inputs violate the model. **No number is printed.** Do what `DO INSTEAD` says. |
| `4` | `UNANSWERABLE` | The question has no answer regardless of data. Ask what `ASK INSTEAD` suggests. |
| `5` | `USE_SIMPLER` | A simpler approach wins. **The printed number is the simpler answer, not the model's.** |

Exit `5` is the one to be careful with: the number is real and usable, but it is not this model's
output, and reporting it as a statistical result would give a naive estimate false authority.

## What is here

| Family | The question it answers |
|---|---|
| [design](docs/families/design.md) | Can this comparison answer my question at all, and how much data do I need? |
| [estimation](docs/families/estimation.md) | How big is it, and how sure am I? |
| [causal](docs/families/causal.md) | Did X actually cause Y? |

Full catalogue: [INDEX.md](INDEX.md). These are generated from `registry.json`; do not edit them.

## Three things worth knowing before you compute anything

These change what you do *before* any script runs, which is why they are here and not behind a
command.

**1. Some conclusions are unreachable, whatever the data says.** With 3 runs per arm the smallest
two-sided p a permutation test can produce is 0.10. With 5 paired observations it is 0.0625. No
result can reach p<0.05 in those designs — not an unlucky one, *any* of them. Before running a small
comparison, run `minimum_attainable_p_for_design`. It answers in milliseconds and sometimes saves the
entire exercise.

**2. Count the comparisons you actually made, including the ones you abandoned.** If you scanned
twelve metrics and reported the one that looked different, the p-value on that one is not the p-value
of your procedure. This applies to noticing a pattern *after* looking at the data, which is the
normal way patterns get noticed. State the number of things you could have noticed, before you
compute anything.

**3. Several agents agreeing is not several sources agreeing.** Sub-agents querying one model are one
source sampled repeatedly. Pooling them as independent evidence compounds a single opinion into false
certainty, and the standard agreement statistics will report the correlation as corroboration. Before
combining results, ask whether they share a generator.

## When not to use this

- The answer is already determined — read the log, run the command, look it up.
- The decision is cheap to reverse. Statistical theater on a reversible call costs tokens and
  manufactures authority.
- You need a number you do not have. **This module never invents estimates.** It checks, propagates
  and stress-tests numbers you or the user supply; measured priors from language models have been
  found to carry effectively no information, so a number this module made up would be worse than
  your judgment, not better.
