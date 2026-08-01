#!/usr/bin/env python3
# WHAT        Turns optimistic/likely/pessimistic estimates into a distribution with correct spread.
# WHEN        Asked how long something will take, or for a range from a three-point estimate.
#             Also whenever you are about to apply the textbook PERT standard deviation.
# INPUTS      --optimistic --likely --pessimistic (any consistent unit). --percentiles (default
#             50,80,90). --commit percentile to recommend committing to (default 80).
# OUTPUT      mean, sd, and the requested percentiles. Also textbook_sd and the error in using it.
# ASSUMPTIONS Beta-PERT: a single mode, bounded support, no multi-modal risk. Estimates are the
#             team's, not invented here.
# EXAMPLE     python3 models/estimation/three_point_estimate_to_range.py -o 4 -m 11 -p 18
"""Corrects a formula that is reproduced wrongly from training data.

The two textbook PERT formulas are mutually inconsistent. The beta-PERT with mode m and mean
(a+4m+b)/6 has alpha+beta = 6 and exact variance (mu-a)(b-mu)/7. The companion formula sigma =
(b-a)/6 is NOT that distribution's standard deviation. The ratio is exactly

    R(delta) = 5/7 + (16/7)*delta*(1-delta),   delta = (m-a)/(b-a)

which equals 1 at only two mode positions, delta = 0.14645 and 0.85355. At a symmetric mode the
textbook sigma is 11.8% BELOW the true value - optimistically narrow, in the common case.

The S5 baseline (evals/baselines/RESULTS.md) used (b-a)/6. This is limb (b) of the selection
principle: not a computation an agent cannot do, but a formula it reliably gets wrong.
"""
import argparse
import sys
from math import sqrt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from lib.report import answer, emit, refused  # noqa: E402
from lib.special import betaincinv  # noqa: E402

# The standard beta-PERT shape total. alpha = 1 + 4(m-a)/(b-a) and beta = 1 + 4(b-m)/(b-a), so
# alpha + beta is always exactly 6 - which is why the variance denominator is 7 (alpha+beta+1).
PERT_SHAPE_TOTAL = 6.0

# Below this the textbook error is under a percentage point and not worth a caveat line; above it
# the interval is materially misstated. Chosen as the point where the sd error reaches 1%.
TEXTBOOK_ERROR_CAVEAT_THRESHOLD = 0.01


def pert_shapes(a: float, m: float, b: float):
    span = b - a
    alpha = 1.0 + 4.0 * (m - a) / span
    beta = 1.0 + 4.0 * (b - m) / span
    return alpha, beta


def pert_mean(a: float, m: float, b: float) -> float:
    return (a + 4.0 * m + b) / 6.0


def pert_variance(a: float, m: float, b: float) -> float:
    """Exact: (mu-a)(b-mu)/7. Derived from Var = span^2 * ab/((a+b)^2 (a+b+1)) with a+b = 6."""
    mu = pert_mean(a, m, b)
    return (mu - a) * (b - mu) / 7.0


def variance_ratio(a: float, m: float, b: float) -> float:
    """R(delta) = 5/7 + (16/7) d (1-d): true variance over the textbook ((b-a)/6)^2."""
    d = (m - a) / (b - a)
    return 5.0 / 7.0 + (16.0 / 7.0) * d * (1.0 - d)


def pert_percentile(a: float, m: float, b: float, p: float) -> float:
    alpha, beta = pert_shapes(a, m, b)
    return a + (b - a) * betaincinv(alpha, beta, p)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Three-point estimate to a range, with correct spread.")
    ap.add_argument("-o", "--optimistic", type=float, required=True)
    ap.add_argument("-m", "--likely", type=float, required=True)
    ap.add_argument("-p", "--pessimistic", type=float, required=True)
    ap.add_argument("--percentiles", default="50,80,90")
    ap.add_argument("--commit", type=float, default=80.0,
                    help="percentile to recommend committing to (default 80)")
    ap.add_argument("--unit", default="", help="unit label for the report line, e.g. weeks")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    model = "Three-point estimate to a range (beta-PERT)"
    lo, mode, hi = a.optimistic, a.likely, a.pessimistic

    if not (lo <= mode <= hi):
        emit(refused(
            model=model,
            violation=f"estimates are not ordered: optimistic={lo}, likely={mode}, "
                      f"pessimistic={hi}",
            why_it_matters="The distribution is defined on [optimistic, pessimistic] with the mode "
                           "inside it; outside that order there is no distribution to describe.",
            do_instead="Check which value is which - optimistic is the fastest, pessimistic the "
                       "slowest - and re-run.",
        ), a.json)
    if lo == hi:
        emit(refused(
            model=model,
            violation="optimistic equals pessimistic, so the estimate has no spread",
            why_it_matters="A three-point estimate with zero range carries no uncertainty to "
                           "quantify, and every percentile is the same number.",
            do_instead=f"If you are genuinely certain, report {lo} and skip this. Otherwise widen "
                       f"the optimistic and pessimistic bounds to values you would actually bet on.",
        ), a.json)
    try:
        pcts = sorted({float(x) for x in a.percentiles.split(",")})
    except ValueError:
        emit(refused(
            model=model, violation=f"--percentiles could not be parsed: {a.percentiles!r}",
            why_it_matters="Percentiles determine the whole output.",
            do_instead="Pass a comma-separated list such as --percentiles 50,80,90.",
        ), a.json)
    if any(not 0 < q < 100 for q in pcts) or not 0 < a.commit < 100:
        emit(refused(
            model=model, violation="a percentile is outside (0, 100)",
            why_it_matters="Percentiles outside the open interval have no finite quantile here.",
            do_instead="Use values strictly between 0 and 100.",
        ), a.json)

    mu = pert_mean(lo, mode, hi)
    sd = sqrt(pert_variance(lo, mode, hi))
    textbook_sd = (hi - lo) / 6.0
    ratio = sqrt(variance_ratio(lo, mode, hi))
    err = textbook_sd / sd - 1.0  # negative => textbook is too narrow

    result = {"mean": mu, "sd": sd, "mode": mode}
    for q in pcts:
        result[f"p{q:g}"] = pert_percentile(lo, mode, hi, q / 100.0)
    result["textbook_sd_(b-a)/6"] = textbook_sd
    result["textbook_sd_error"] = err

    commit_at = pert_percentile(lo, mode, hi, a.commit / 100.0)
    unit = f" {a.unit}" if a.unit else ""

    caveat = None
    if abs(err) >= TEXTBOOK_ERROR_CAVEAT_THRESHOLD:
        direction = "too narrow" if err < 0 else "too wide"
        caveat = (f"The textbook PERT sd (b-a)/6 = {textbook_sd:.4g} is {abs(err) * 100:.1f}% "
                  f"{direction} here (true sd {sd:.4g}, ratio {ratio:.4f}). If you have seen a "
                  f"different range for this estimate, that is likely why.")

    skew_note = ""
    if mu > mode:
        skew_note = (f" Note the mean ({mu:.4g}{unit}) exceeds the most likely value "
                     f"({mode:.4g}{unit}) — the long tail moves the honest answer right.")

    emit(answer(
        model=model, result=result, caveat=caveat,
        report_as=f"Expected {mu:.4g}{unit}, but commit to {commit_at:.4g}{unit} for "
                  f"{a.commit:g}% confidence.{skew_note}",
    ), a.json)


if __name__ == "__main__":
    main()
