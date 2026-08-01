#!/usr/bin/env python3
# WHAT        Whether your sample can bound a high quantile at all, and the bound if it can.
# WHEN        About to quote a p95/p99 latency, tail size, or worst case from a sample. Also when
#             asked "what is our p99" and you are not sure the data supports an answer.
# INPUTS      --quantile 0.99 --confidence 0.95, plus either --data v1,v2,... or just --n N to
#             ask the attainability question before collecting anything.
# OUTPUT      The order statistic serving as the upper bound and its value, or the n required.
# ASSUMPTIONS Observations are i.i.d. draws from the same distribution - not a drifting or
#             autocorrelated series. Distribution-free otherwise: no shape is assumed.
# EXAMPLE     python3 models/estimation/quantile_confidence_from_order_statistics.py --quantile 0.99 --n 100
"""A fact about what a sample can express, of the same shape as the p-value floor.

A one-sided upper confidence bound on the q-quantile is an order statistic X_(k), where k is the
smallest index with P(Bin(n,q) <= k-1) >= 1-alpha. Taking k = n - the sample maximum - gives the
most permissive case, which succeeds exactly when

    q^n <= alpha,  i.e.  n >= ln(alpha)/ln(q)

**That is cluster C1.** The same inequality is the rule of three (its q -> 1-p, zero-event case),
the Wilks one-sided tolerance interval, and reruns-to-confidence. C1 was asserted at 5/5 members
and verified at 4/6 - the two-sided Wilks interval is transcendental and does not reduce to this
form - so tests/models/ checks membership per member rather than trusting the family.

The consequence agents need: at n = 100 and 95% confidence, no quantile above **0.9705** can be
bounded at all. A "p99 from 100 samples" is not a statistic, however carefully it was computed.
"""
import argparse
import sys
from math import ceil, comb, log
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from lib.report import answer, emit, refused, unanswerable  # noqa: E402


def binom_cdf(k: int, n: int, p: float) -> float:
    """P(Bin(n,p) <= k), summed exactly. n is agent-scale, so exact beats any approximation."""
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))


def max_quantile_bounded(n: int, alpha: float) -> float:
    """Highest quantile any upper bound can reach with n observations: alpha^(1/n)."""
    return alpha ** (1.0 / n)


def min_n_for_quantile(q: float, alpha: float) -> int:
    """Smallest n admitting any upper bound on the q-quantile: ceil(ln(alpha)/ln(q))."""
    return int(ceil(log(alpha) / log(q)))


def bounding_order_statistic(n: int, q: float, alpha: float):
    """1-indexed rank of the order statistic that upper-bounds the q-quantile, or None.

    Smallest k with P(Bin(n,q) <= k-1) >= 1-alpha. None when even the maximum will not do.
    """
    for k in range(1, n + 1):
        if binom_cdf(k - 1, n, q) >= 1.0 - alpha:
            return k
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description="Can this sample bound that quantile, and how?")
    ap.add_argument("--quantile", type=float, required=True, help="e.g. 0.99 for p99")
    ap.add_argument("--confidence", type=float, default=0.95)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--data", help="comma-separated observations")
    src.add_argument("--n", type=int, help="sample size, to ask the attainability question only")
    ap.add_argument("--unit", default="")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    model = "Quantile upper bound from order statistics"
    q, conf = a.quantile, a.confidence
    alpha = 1.0 - conf

    if not 0 < q < 1:
        emit(refused(
            model=model, violation=f"--quantile is {q}, outside (0, 1)",
            why_it_matters="A quantile is a proportion; p99 is 0.99, not 99.",
            do_instead="Pass e.g. --quantile 0.99."), a.json)
    if not 0 < conf < 1:
        emit(refused(
            model=model, violation=f"--confidence is {conf}, outside (0, 1)",
            why_it_matters="Confidence is a probability.",
            do_instead="Pass e.g. --confidence 0.95."), a.json)

    values = None
    if a.data is not None:
        try:
            values = sorted(float(x) for x in a.data.split(",") if x.strip())
        except ValueError:
            emit(refused(
                model=model, violation=f"--data could not be parsed: {a.data!r}",
                why_it_matters="The observations are the input.",
                do_instead="Pass numbers separated by commas."), a.json)
        if len(values) < 1:
            emit(refused(
                model=model, violation="--data contained no values",
                why_it_matters="There is nothing to bound.",
                do_instead="Pass at least one observation."), a.json)
        n = len(values)
    else:
        n = a.n
        if n < 1:
            emit(refused(
                model=model, violation=f"--n is {n}, which is below 1",
                why_it_matters="A sample of zero bounds nothing.",
                do_instead="Pass a positive sample size."), a.json)

    k = bounding_order_statistic(n, q, alpha)
    q_max = max_quantile_bounded(n, alpha)
    unit = f" {a.unit}" if a.unit else ""

    if k is None:
        need = min_n_for_quantile(q, alpha)
        emit(unanswerable(
            model=model,
            why=f"with n={n} no upper confidence bound on the {q:g} quantile exists at "
                f"{conf:.0%} confidence. The highest quantile any bound can reach here is "
                f"{q_max:.4f}; even the sample maximum is not high enough for {q:g}",
            ask_instead=f"Either bound a lower quantile — up to {q_max:.4f} is available — or "
                        f"collect at least {need:,} observations, which is what the {q:g} quantile "
                        f"requires at this confidence. Reporting a p{q * 100:g} from {n} samples "
                        f"would be quoting an order statistic, not an estimate of the quantile.",
        ), a.json)

    result = {"n": n, "quantile": q, "confidence": conf,
              "bounding_order_statistic": k, "highest_quantile_bounded": q_max}
    if values is not None:
        result["upper_bound"] = values[k - 1]
        result["sample_max"] = values[-1]

    rank_note = "the sample maximum" if k == n else f"the {k}th smallest of {n}"
    robustness = (f"This is distribution-free — no shape is assumed. The binding constraint is "
                  f"sample size: at n={n} the highest quantile bounded at {conf:.0%} is "
                  f"{q_max:.4f}, and {q:g} sits under it.")

    if values is not None:
        emit(answer(
            model=model, result=result, robustness=robustness,
            report_as=f"With {conf:.0%} confidence the {q:g} quantile is at most "
                      f"{values[k - 1]:g}{unit} ({rank_note}).",
        ), a.json)

    emit(answer(
        model=model, result=result, robustness=robustness,
        report_as=f"{n} observations can bound the {q:g} quantile at {conf:.0%} confidence — the "
                  f"bound would be {rank_note}. Quantiles above {q_max:.4f} cannot be bounded at "
                  f"this n.",
    ), a.json)


if __name__ == "__main__":
    main()
