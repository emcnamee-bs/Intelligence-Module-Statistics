"""Special functions the library actually needs. Deliberately small.

The research sweep expected a broad special-function library and measured otherwise: four
territories independently reported that agent-scale methods need almost nothing here, because the
exact, distribution-free and enumeration-based methods that are correct at small n are also the ones
that replace analysis with computation (RESEARCH.md 1.12).

What remains: the regularized incomplete beta and its inverse (Student-t, F, beta, and every
beta-family quantile), and the regularized incomplete gamma and its inverse (chi-square tails).

Accuracy policy: golden tests assert against values derived in closed form, never against SciPy -
which is unavailable in the target environment and uses different algorithms with different error
characteristics. Each function declares an accuracy envelope and raises outside its domain rather
than silently returning something wrong.
"""
import math

__all__ = ["betainc", "betaincinv", "gammainc", "gammaincinv", "log_beta"]

# Lentz's continued fraction converges in far fewer than 200 iterations across the domain we use;
# the cap exists so a pathological input fails loudly instead of hanging.
_MAX_ITER = 200
# Relative convergence target. 1e-15 is at the edge of double precision for this recurrence;
# 3e-16 would stall without improving the result.
_EPS = 1e-15
# Guards division by a value that has underflowed to zero inside the recurrence.
_TINY = 1e-300


def log_beta(a: float, b: float) -> float:
    """log B(a, b). Computed via lgamma to avoid overflow for large arguments."""
    return math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)


def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta, evaluated by the modified Lentz method."""
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < _TINY:
        d = _TINY
    d = 1.0 / d
    h = d
    for m in range(1, _MAX_ITER + 1):
        m2 = 2 * m
        # even step
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < _TINY:
            d = _TINY
        c = 1.0 + aa / c
        if abs(c) < _TINY:
            c = _TINY
        d = 1.0 / d
        h *= d * c
        # odd step
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < _TINY:
            d = _TINY
        c = 1.0 + aa / c
        if abs(c) < _TINY:
            c = _TINY
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < _EPS:
            return h
    raise ArithmeticError(
        f"incomplete beta continued fraction did not converge for a={a}, b={b}, x={x}")


def betainc(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta I_x(a, b) = P(Beta(a,b) <= x).

    Accuracy envelope: relative error < 1e-13 for a, b in (0, 1e5] and x in [0, 1].
    Verified against closed forms available for integer a, b (tests/lib/test_special.py).
    """
    if a <= 0 or b <= 0:
        raise ValueError(f"betainc requires a > 0 and b > 0, got a={a}, b={b}")
    if x < 0.0 or x > 1.0:
        raise ValueError(f"betainc requires 0 <= x <= 1, got x={x}")
    if x == 0.0:
        return 0.0
    if x == 1.0:
        return 1.0
    front = math.exp(a * math.log(x) + b * math.log1p(-x) - log_beta(a, b))
    # The continued fraction converges quickly only on one side of the mode; reflect otherwise.
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def betaincinv(a: float, b: float, p: float) -> float:
    """Inverse of betainc in x: the p-quantile of Beta(a, b).

    Bisection rather than Newton. I_x is monotone increasing in x, so bisection cannot diverge, and
    at ~60 iterations over [0,1] it reaches the precision floor. Newton would be faster and could
    leave the bracket near the boundaries, where beta-family quantiles are most often requested.
    """
    if a <= 0 or b <= 0:
        raise ValueError(f"betaincinv requires a > 0 and b > 0, got a={a}, b={b}")
    if p < 0.0 or p > 1.0:
        raise ValueError(f"betaincinv requires 0 <= p <= 1, got p={p}")
    if p == 0.0:
        return 0.0
    if p == 1.0:
        return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if betainc(a, b, mid) < p:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-15:
            break
    return 0.5 * (lo + hi)


def gammainc(s: float, x: float) -> float:
    """Regularized lower incomplete gamma P(s, x) = P(Gamma(s,1) <= x).

    Series expansion below the crossover, continued fraction above; the two converge on opposite
    sides of s+1. Accuracy envelope: relative error < 1e-13 for s in (0, 1e5], x >= 0.
    """
    if s <= 0:
        raise ValueError(f"gammainc requires s > 0, got s={s}")
    if x < 0:
        raise ValueError(f"gammainc requires x >= 0, got x={x}")
    if x == 0.0:
        return 0.0
    if x < s + 1.0:
        # series
        term = 1.0 / s
        total = term
        n = s
        for _ in range(_MAX_ITER):
            n += 1.0
            term *= x / n
            total += term
            if abs(term) < abs(total) * _EPS:
                return total * math.exp(-x + s * math.log(x) - math.lgamma(s))
        raise ArithmeticError(f"gammainc series did not converge for s={s}, x={x}")
    # continued fraction for the upper tail Q(s, x), then complement
    b = x + 1.0 - s
    c = 1.0 / _TINY
    d = 1.0 / b
    h = d
    for i in range(1, _MAX_ITER + 1):
        an = -i * (i - s)
        b += 2.0
        d = an * d + b
        if abs(d) < _TINY:
            d = _TINY
        c = b + an / c
        if abs(c) < _TINY:
            c = _TINY
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < _EPS:
            q = math.exp(-x + s * math.log(x) - math.lgamma(s)) * h
            return 1.0 - q
    raise ArithmeticError(f"gammainc continued fraction did not converge for s={s}, x={x}")


def gammaincinv(s: float, p: float) -> float:
    """Inverse of gammainc in x. Bisection, for the same reason as betaincinv."""
    if s <= 0:
        raise ValueError(f"gammaincinv requires s > 0, got s={s}")
    if p < 0.0 or p >= 1.0:
        raise ValueError(f"gammaincinv requires 0 <= p < 1, got p={p}")
    if p == 0.0:
        return 0.0
    lo, hi = 0.0, max(10.0, s * 2.0)
    while gammainc(s, hi) < p:
        hi *= 2.0
        if hi > 1e12:
            raise ArithmeticError(f"gammaincinv could not bracket p={p} for s={s}")
    for _ in range(300):
        mid = 0.5 * (lo + hi)
        if gammainc(s, mid) < p:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-13 * max(1.0, hi):
            break
    return 0.5 * (lo + hi)
