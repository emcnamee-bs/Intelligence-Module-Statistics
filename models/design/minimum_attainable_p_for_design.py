#!/usr/bin/env python3
# WHAT        The smallest p-value your design can produce, before seeing any data.
# WHEN        Before running or believing a small-sample comparison. If the floor exceeds your
#             threshold, no outcome can reach it and the test cannot support the conclusion.
# INPUTS      --n1/--n2 group sizes (two-sample), or --pairs count (paired/before-after).
#             --alpha threshold to reach (default 0.05). --sided 1 or 2 (default 2).
# OUTPUT      min_p: smallest attainable p. reachable: whether alpha is attainable at all.
#             If not, the smallest equal group size that would be.
# ASSUMPTIONS Exact rank/permutation test, no ties. Ties and mid-p only raise the floor, so this
#             is a lower bound on the floor: unreachable here means unreachable in practice.
# EXAMPLE     python3 models/design/minimum_attainable_p_for_design.py --n1 3 --n2 3
"""Encodes an arithmetic fact, not a computation: p<0.05 is unreachable at n1=n2=3.

The floor is the smallest tail probability the reference distribution contains. For a two-sample
permutation or Mann-Whitney test the null has C(n1+n2, n1) equally likely arrangements, so the most
extreme one-sided outcome has probability 1/C(n1+n2, n1). For a paired sign or signed-rank test
there are 2**pairs sign assignments, so the floor is 1/2**pairs. Two-sided doubles it.

No baseline in evals/baselines/ mentioned this. It is not something an agent computes wrongly - it
is something an agent has no way to know it should check.
"""
import argparse
import sys
from math import comb
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from lib.report import answer, emit, refused  # noqa: E402

# Searching past 200 per group is pointless: every design of interest has resolved long before,
# and a floor that needs n>200 to clear is a design problem, not a rounding problem.
MAX_SEARCH_N = 200


def two_sample_floor(n1: int, n2: int, sided: int) -> float:
    """1/C(n1+n2, n1) one-sided; the null has that many equally likely arrangements."""
    return min(1.0, sided / comb(n1 + n2, n1))


def paired_floor(pairs: int, sided: int) -> float:
    """1/2**pairs one-sided; each pair's sign flips independently under the null."""
    return min(1.0, sided / (2 ** pairs))


def smallest_reachable_n(alpha: float, sided: int, paired: bool):
    """Smallest per-group size (or pair count) whose floor clears alpha. None if beyond search."""
    for n in range(1, MAX_SEARCH_N + 1):
        floor = paired_floor(n, sided) if paired else two_sample_floor(n, n, sided)
        if floor <= alpha:
            return n, floor
    return None, None


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Smallest p-value a design can produce, before any data.")
    p.add_argument("--n1", type=int, help="size of group 1 (two-sample)")
    p.add_argument("--n2", type=int, help="size of group 2 (two-sample)")
    p.add_argument("--pairs", type=int, help="number of paired observations (paired design)")
    p.add_argument("--alpha", type=float, default=0.05, help="threshold to reach (default 0.05)")
    p.add_argument("--sided", type=int, choices=(1, 2), default=2, help="1 or 2 sided (default 2)")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)

    model = "Minimum attainable p-value for this design"
    paired = a.pairs is not None
    two_sample = a.n1 is not None and a.n2 is not None

    if paired and two_sample:
        emit(refused(
            model=model,
            violation="both --pairs and --n1/--n2 were given",
            why_it_matters="Paired and two-sample designs have different null distributions, so "
                           "the floor differs; guessing which you meant could understate it.",
            do_instead="Pass --pairs for a before/after design on the same items, or --n1 and "
                       "--n2 for two independent groups.",
        ), a.json)
    if not paired and not two_sample:
        emit(refused(
            model=model,
            violation="no design given",
            why_it_matters="The floor depends entirely on the design.",
            do_instead="Pass --pairs N, or --n1 N --n2 N.",
        ), a.json)
    if not 0 < a.alpha < 1:
        emit(refused(
            model=model,
            violation=f"--alpha is {a.alpha}, outside (0, 1)",
            why_it_matters="A threshold outside (0,1) is not a probability.",
            do_instead="Pass a value such as --alpha 0.05.",
        ), a.json)

    sizes = [a.pairs] if paired else [a.n1, a.n2]
    if any(n is None or n < 1 for n in sizes):
        emit(refused(
            model=model,
            violation=f"group size {min(n for n in sizes if n is not None)} is below 1",
            why_it_matters="A group with no observations has no null distribution.",
            do_instead="Pass sizes of at least 1 per group.",
        ), a.json)

    floor = paired_floor(a.pairs, a.sided) if paired else two_sample_floor(a.n1, a.n2, a.sided)
    reachable = floor <= a.alpha
    design = f"paired, {a.pairs} pairs" if paired else f"two-sample, n1={a.n1} n2={a.n2}"

    result = {
        "design": design,
        "sided": a.sided,
        "min_attainable_p": floor,
        "alpha": a.alpha,
        "reachable": reachable,
    }

    if reachable:
        emit(answer(
            model=model, result=result,
            report_as=f"This design can reach p<{a.alpha}: the smallest p it can produce is "
                      f"{floor:.4g}.",
        ), a.json)

    need_n, need_floor = smallest_reachable_n(a.alpha, a.sided, paired)
    unit = "pairs" if paired else "per group"
    if need_n is None:
        robustness = (f"No size up to {MAX_SEARCH_N} {unit} reaches alpha={a.alpha} at "
                      f"{a.sided}-sided.")
        fix = f"raise alpha, or use a 1-sided test if the direction was fixed in advance"
    else:
        robustness = (f"Reaching p<{a.alpha} requires at least {need_n} {unit} "
                      f"(floor then {need_floor:.4g}).")
        fix = f"collect at least {need_n} {unit}"

    emit(answer(
        model=model, result=result, robustness=robustness,
        report_as=f"With this design no result can reach p<{a.alpha} — the smallest p it can "
                  f"produce is {floor:.4g}. The comparison cannot support that conclusion "
                  f"whatever the data shows; to get there, {fix}.",
    ), a.json)


if __name__ == "__main__":
    main()
