#!/usr/bin/env python3
# WHAT        How many runs per arm to detect a regression you would actually care about.
# WHEN        Before benchmarking, or when tempted to conclude from 5 runs. Ask this instead of
#             "is it slower?" - that question is unanswerable until you know what you can detect.
# INPUTS      --effect smallest difference worth acting on (same units as the metric).
#             --sd known run-to-run sd, OR --pilot v1,v2,... to estimate it. --power (0.8).
# OUTPUT      runs_per_arm needed. With --pilot, also the upper bound allowing for sd uncertainty.
# ASSUMPTIONS Runs are independent and identically distributed - not thermally drifting, not
#             ordered old-then-new. Violating that invalidates the number more than any n does.
# EXAMPLE     python3 models/design/benchmark_runs_needed.py --effect 0.08 --sd 0.05
"""Answers the question the agent skipped, not the one it asked.

Recorded baseline S1 (evals/baselines/RESULTS.md) computed a correct Welch t-test on 5 runs per arm
and never asked what size of regression would matter, nor how many runs would settle it. It scored
3/4 for exactly that omission. Computing the test is limb-free - the baseline did it correctly - so
this model ships the planning half only.

USE_SIMPLER fires when the calculation cannot beat the conventional default: if you need fewer runs
than you would have run anyway, the arithmetic bought nothing and the default already absorbs the
uncertainty in your sd estimate.
"""
import argparse
import sys
from math import sqrt
from pathlib import Path
from statistics import NormalDist, stdev

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from lib.report import answer, emit, refused, unanswerable, use_simpler  # noqa: E402
from lib.special import gammaincinv  # noqa: E402

# The conventional benchmark default. Justified rather than assumed: at 30 runs the relative
# standard error of the sd estimate is 1/sqrt(2*29) = 13%, so the sd itself is stable enough to
# plan from, and the t-distribution is within ~2% of normal. Below that both stop being true.
CONVENTIONAL_DEFAULT_RUNS = 30

# Above this the plan is not executable in any normal workflow, and quoting a precise figure would
# imply otherwise. Chosen as the point where a 1-second benchmark exceeds a working day per arm.
IMPRACTICAL_RUNS = 30_000


def chi2_quantile(p: float, df: int) -> float:
    """Chi-square quantile. chi2(df) is Gamma(df/2, scale 2), so x = 2 * Ginv(df/2, p)."""
    return 2.0 * gammaincinv(df / 2.0, p)


def runs_per_arm(effect: float, sd: float, power: float, alpha: float) -> float:
    """n = 2 sd^2 (z_{1-alpha/2} + z_{1-power})^2 / effect^2, for two arms of equal size."""
    z_a = NormalDist().inv_cdf(1.0 - alpha / 2.0)
    z_b = NormalDist().inv_cdf(power)
    return 2.0 * sd * sd * (z_a + z_b) ** 2 / (effect * effect)


def sd_upper_bound(sample_sd: float, k: int, one_sided_conf: float = 0.95) -> float:
    """One-sided upper confidence bound on the true sd from k pilot runs.

    (k-1)s^2/sigma^2 ~ chi2(k-1), so the upper bound on sigma uses the LOWER chi-square quantile.
    Required n scales with sigma^2, which is why a shaky sd estimate is so expensive here.

    Note the confidence is ONE-SIDED: at 0.95 this is the upper limit of a two-sided 90% interval.
    An earlier version named the parameter `conf=0.90` and labelled the output "90pct", which
    understated the bound's actual coverage - the coverage test measures 95%.
    """
    df = k - 1
    return sample_sd * sqrt(df / chi2_quantile(1.0 - one_sided_conf, df))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Runs per arm needed to detect a regression.")
    ap.add_argument("--effect", type=float, required=True,
                    help="smallest difference worth acting on, in metric units")
    ap.add_argument("--sd", type=float, help="known run-to-run standard deviation")
    ap.add_argument("--pilot", help="comma-separated pilot measurements to estimate sd from")
    ap.add_argument("--power", type=float, default=0.80)
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--unit", default="")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    model = "Benchmark runs needed per arm"

    if (a.sd is None) == (a.pilot is None):
        emit(refused(
            model=model, violation="exactly one of --sd or --pilot is required",
            why_it_matters="Run-to-run spread sets the answer entirely; without it there is "
                           "nothing to compute, and with two sources there is no way to choose.",
            do_instead="Pass --sd if you know it, or --pilot with a few measurements.",
        ), a.json)
    if a.effect <= 0:
        emit(refused(
            model=model, violation=f"--effect is {a.effect}, which is not positive",
            why_it_matters="The minimum interesting effect is a magnitude; zero would require "
                           "infinitely many runs.",
            do_instead="State the smallest regression you would actually act on, as a positive "
                       "number in the metric's units.",
        ), a.json)
    if not 0 < a.alpha < 1 or not 0 < a.power < 1:
        emit(refused(
            model=model, violation=f"--alpha={a.alpha} or --power={a.power} is outside (0, 1)",
            why_it_matters="Both are probabilities.",
            do_instead="Use values such as --alpha 0.05 --power 0.8.",
        ), a.json)

    pilot_k = None
    if a.pilot is not None:
        try:
            vals = [float(x) for x in a.pilot.split(",") if x.strip() != ""]
        except ValueError:
            emit(refused(
                model=model, violation=f"--pilot could not be parsed: {a.pilot!r}",
                why_it_matters="The sd estimate comes entirely from these values.",
                do_instead="Pass numbers separated by commas, e.g. --pilot 1.02,0.98,1.11.",
            ), a.json)
        if len(vals) < 2:
            emit(refused(
                model=model, violation=f"--pilot has {len(vals)} value(s); at least 2 are needed",
                why_it_matters="A single measurement has no spread, and spread is the input.",
                do_instead="Collect at least 2 pilot runs, ideally 5 or more.",
            ), a.json)
        sd = stdev(vals)
        pilot_k = len(vals)
        if sd == 0:
            emit(refused(
                model=model, violation="every pilot measurement is identical, so the sd is zero",
                why_it_matters="A zero sd implies one run would settle any question, which is "
                               "almost certainly a measurement-resolution artefact rather than "
                               "true determinism.",
                do_instead="Check the timer resolution or units, then re-collect the pilot runs.",
            ), a.json)
    else:
        sd = a.sd
        if sd <= 0:
            emit(refused(
                model=model, violation=f"--sd is {sd}, which is not positive",
                why_it_matters="Standard deviation is non-negative, and zero implies no "
                               "variability to overcome.",
                do_instead="Pass the observed run-to-run spread as a positive number.",
            ), a.json)

    n = runs_per_arm(a.effect, sd, a.power, a.alpha)
    n_int = max(2, int(-(-n // 1)))  # ceiling, and at least 2 runs to have any spread at all
    unit = f" {a.unit}" if a.unit else ""

    result = {
        "runs_per_arm": n_int,
        "minimum_interesting_effect": a.effect,
        "sd_used": sd,
        "power": a.power,
        "alpha": a.alpha,
    }
    if pilot_k is not None:
        result["pilot_runs"] = pilot_k

    if n_int > IMPRACTICAL_RUNS:
        emit(unanswerable(
            model=model,
            why=f"detecting {a.effect:g}{unit} against a spread of {sd:.3g}{unit} would take "
                f"{n_int:,} runs per arm, which is not a benchmark you can run",
            ask_instead="Reduce the noise rather than the uncertainty: pin the CPU, interleave the "
                        "arms, use a lower-variance metric such as instruction count, or accept "
                        "that a difference this small is not measurable here.",
        ), a.json)

    if pilot_k is not None:
        sd_hi = sd_upper_bound(sd, pilot_k)
        n_hi = max(2, int(-(-runs_per_arm(a.effect, sd_hi, a.power, a.alpha) // 1)))
        result["runs_per_arm_upper_bound"] = n_hi
        result["sd_upper_bound_95pct_one_sided"] = sd_hi

        # If even the pessimistic requirement sits under the number you would have run anyway,
        # the calculation has not beaten the default - and the default absorbs the sd uncertainty.
        if n_hi <= CONVENTIONAL_DEFAULT_RUNS:
            emit(use_simpler(
                model=model,
                simpler_name=f"the conventional default of {CONVENTIONAL_DEFAULT_RUNS} runs "
                             f"per arm",
                simpler_result={"runs_per_arm": CONVENTIONAL_DEFAULT_RUNS},
                why=f"The calculation gives {n_int}, and even allowing for sd uncertainty from "
                    f"{pilot_k} pilot runs it gives at most {n_hi} — both under the default. "
                    f"Running {CONVENTIONAL_DEFAULT_RUNS} costs little more and needs no "
                    f"assumption about the sd being right.",
            ), a.json)

        caveat = (f"sd is estimated from {pilot_k} pilot runs, so it is uncertain: allowing for "
                  f"that, up to {n_hi} runs per arm may be needed. Required runs scale with the "
                  f"square of the sd, which is why a shaky estimate is expensive here.")
        emit(answer(
            model=model, result=result, caveat=caveat,
            report_as=f"Plan {n_hi} runs per arm to detect a {a.effect:g}{unit} regression "
                      f"(point estimate {n_int}, widened for sd uncertainty from {pilot_k} pilot "
                      f"runs).",
        ), a.json)

    emit(answer(
        model=model, result=result,
        report_as=f"Run {n_int} per arm to detect a {a.effect:g}{unit} regression with "
                  f"{a.power:.0%} power. Fewer runs than that cannot settle it.".replace("%", "%"),
    ), a.json)


if __name__ == "__main__":
    main()
