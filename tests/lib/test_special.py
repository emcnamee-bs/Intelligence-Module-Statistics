"""L1 golden tests for lib/special.py.

Reference values are derived in CLOSED FORM inside the test, never copied from a table and never
compared against SciPy. For integer shape parameters the regularized incomplete beta and gamma both
have exact polynomial / finite-sum expressions, which makes this a genuinely independent check
rather than a restatement of the implementation.

This matters more than usual here: review 02 refuted four research findings whose conclusions were
right and whose numbers were wrong. A golden test copied from a half-remembered table would
reproduce exactly that failure.
"""
import math
import sys
from decimal import Decimal, localcontext
import unittest
from itertools import combinations  # noqa: F401  (kept for parity with enumeration tests)
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lib.special import (  # noqa: E402
    betainc, betaincinv, gammainc, gammaincinv, log_beta,
)


def beta_cdf_closed_form(a: int, b: int, x: float) -> float:
    """Exact I_x(a,b) for positive integer a, b.

    I_x(a,b) = sum_{j=a}^{a+b-1} C(a+b-1, j) x^j (1-x)^(a+b-1-j)
    i.e. the probability that a Binomial(a+b-1, x) is at least a. Standard identity, and derivable
    without reference to any incomplete-beta implementation.
    """
    n = a + b - 1
    return sum(math.comb(n, j) * x ** j * (1 - x) ** (n - j) for j in range(a, n + 1))


def gamma_cdf_closed_form(s: int, x: float) -> float:
    """Exact P(s,x) for positive integer s: 1 - e^-x * sum_{k=0}^{s-1} x^k/k!.

    Evaluated in 50-digit decimal, NOT double precision. For small x the identity subtracts two
    nearly-equal quantities - at P(4, 0.1) the true value is 7.75e-6 while the product being
    subtracted from 1 is 0.99999225, so double-precision rounding is amplified by ~1.3e5 and the
    reference lands ~1.5e-11 off. That is a hundredfold worse than the implementation it is meant
    to certify, which sums the series directly and never cancels.

    A golden test is only as good as its oracle. This one is computed at a precision where the
    cancellation cannot reach the digits being asserted.
    """
    with localcontext() as ctx:
        ctx.prec = 50
        dx = Decimal(x)
        total = sum((dx ** k) / Decimal(math.factorial(k)) for k in range(s))
        return float(Decimal(1) - (-dx).exp() * total)


class TestIncompleteBetaAgainstClosedForm(unittest.TestCase):
    def test_matches_binomial_identity_across_integer_shapes(self):
        for a in range(1, 9):
            for b in range(1, 9):
                for x in (0.01, 0.1, 0.25, 0.5, 0.75, 0.9, 0.99):
                    got = betainc(a, b, x)
                    want = beta_cdf_closed_form(a, b, x)
                    self.assertAlmostEqual(got, want, places=12,
                                           msg=f"I_{x}({a},{b}): {got} vs {want}")

    def test_specific_hand_derived_values(self):
        # Beta(2,3): pdf proportional to t(1-t)^2, B(2,3)=1/12, so CDF = 6x^2 - 8x^3 + 3x^4.
        self.assertAlmostEqual(betainc(2, 3, 0.5), 0.6875, places=13)
        # Beta(3,2): CDF = 4x^3 - 3x^4.
        self.assertAlmostEqual(betainc(3, 2, 0.5), 0.3125, places=13)
        # Beta(1,1) is uniform.
        for x in (0.0, 0.137, 0.5, 0.9, 1.0):
            self.assertAlmostEqual(betainc(1, 1, x), x, places=14)
        # Beta(1,2): CDF = 1-(1-x)^2.
        self.assertAlmostEqual(betainc(1, 2, 0.5), 0.75, places=14)

    def test_symmetry_identity(self):
        # I_x(a,b) = 1 - I_{1-x}(b,a) holds for non-integer shapes too, where no closed form exists.
        for a, b in ((0.5, 0.5), (2.7, 1.3), (13.4, 4.9), (1.0, 6.6)):
            for x in (0.05, 0.3, 0.5, 0.77, 0.95):
                self.assertAlmostEqual(betainc(a, b, x), 1.0 - betainc(b, a, 1.0 - x), places=12)

    def test_boundaries_and_monotonicity(self):
        self.assertEqual(betainc(2.5, 3.5, 0.0), 0.0)
        self.assertEqual(betainc(2.5, 3.5, 1.0), 1.0)
        prev = -1.0
        for i in range(201):
            v = betainc(2.5, 3.5, i / 200)
            self.assertGreaterEqual(v, prev)
            prev = v

    def test_domain_errors_raise_rather_than_returning_garbage(self):
        for bad in ((0, 1, 0.5), (1, 0, 0.5), (-1, 2, 0.5)):
            with self.assertRaises(ValueError):
                betainc(*bad)
        for bad_x in (-0.001, 1.001):
            with self.assertRaises(ValueError):
                betainc(2, 2, bad_x)


class TestIncompleteBetaInverse(unittest.TestCase):
    def test_round_trips(self):
        for a, b in ((1, 1), (2, 3), (0.5, 0.5), (5.2, 1.8), (40, 12)):
            for p in (0.001, 0.05, 0.25, 0.5, 0.8, 0.95, 0.999):
                x = betaincinv(a, b, p)
                self.assertAlmostEqual(betainc(a, b, x), p, places=10,
                                       msg=f"a={a} b={b} p={p} x={x}")

    def test_median_of_symmetric_beta_is_one_half(self):
        for a in (0.5, 1, 2, 3, 10.5):
            self.assertAlmostEqual(betaincinv(a, a, 0.5), 0.5, places=12)

    def test_uniform_quantiles_are_the_identity(self):
        for p in (0.01, 0.3, 0.5, 0.87, 0.99):
            self.assertAlmostEqual(betaincinv(1, 1, p), p, places=12)

    def test_boundaries(self):
        self.assertEqual(betaincinv(2, 3, 0.0), 0.0)
        self.assertEqual(betaincinv(2, 3, 1.0), 1.0)


class TestIncompleteGammaAgainstClosedForm(unittest.TestCase):
    def test_matches_poisson_identity_across_integer_shapes(self):
        for s in range(1, 12):
            for x in (0.01, 0.5, 1.0, 3.0, 7.5, 20.0, 50.0):
                got = gammainc(s, x)
                want = gamma_cdf_closed_form(s, x)
                self.assertAlmostEqual(got, want, places=12, msg=f"P({s},{x})")

    def test_exponential_case(self):
        # s=1 is the exponential CDF.
        for x in (0.1, 1.0, 2.5, 10.0):
            self.assertAlmostEqual(gammainc(1, x), 1 - math.exp(-x), places=13)

    def test_chi_square_tail_via_gamma(self):
        # chi-square with k df is Gamma(k/2, scale 2), so CDF(x) = P(k/2, x/2).
        # For k=2 that is 1-exp(-x/2); for k=1, erf(sqrt(x/2)).
        for x in (0.5, 2.0, 6.0):
            self.assertAlmostEqual(gammainc(1.0, x / 2), 1 - math.exp(-x / 2), places=13)
            self.assertAlmostEqual(gammainc(0.5, x / 2), math.erf(math.sqrt(x / 2)), places=12)

    def test_no_algorithmic_seam_at_the_crossover(self):
        """The implementation switches series -> continued fraction at x = s+1.

        Comparing gammainc(s, x-h) with gammainc(s, x+h) does NOT test this: those are different
        points on a function with a nonzero derivative, and the difference is dominated by
        pdf(s,x)*2h regardless of whether a seam exists. An earlier version of this test asserted
        exactly that and failed on the function's own slope.

        The seam is tested by checking both branches against the exact closed form, which isolates
        algorithm error from the derivative.
        """
        s = 4
        for x in (s + 1 - 1e-9, s + 1, s + 1 + 1e-9, s + 1 + 0.5):
            got = gammainc(s, x)
            want = gamma_cdf_closed_form(s, x)
            self.assertLess(abs(got - want) / want, 1e-13,
                            msg=f"P({s},{x}) relative error exceeds the declared envelope")

    def test_declared_accuracy_envelope_holds_across_branches(self):
        # The docstring claims relative error < 1e-13. Assert it, rather than trusting the claim.
        for s in (1, 2, 4, 7, 10):
            for x in (0.1, 1.0, s + 1.0, 2 * s + 5.0, 40.0):
                want = gamma_cdf_closed_form(s, x)
                if want <= 0:
                    continue
                self.assertLess(abs(gammainc(s, x) - want) / want, 1e-13,
                                msg=f"P({s},{x})")

    def test_domain_errors_raise(self):
        with self.assertRaises(ValueError):
            gammainc(0, 1.0)
        with self.assertRaises(ValueError):
            gammainc(1.0, -0.5)


class TestIncompleteGammaInverse(unittest.TestCase):
    def test_round_trips(self):
        for s in (0.5, 1, 2.5, 10, 100):
            for p in (0.001, 0.05, 0.5, 0.95, 0.999):
                x = gammaincinv(s, p)
                self.assertAlmostEqual(gammainc(s, x), p, places=9, msg=f"s={s} p={p}")

    def test_known_chi_square_quantiles(self):
        # chi-square 95th percentile, 1 df, is 3.841458... derived here as 2*Ginv(0.5, 0.95)
        # and checked against the closed form for k=1: x such that erf(sqrt(x/2)) = 0.95.
        x = 2 * gammaincinv(0.5, 0.95)
        self.assertAlmostEqual(math.erf(math.sqrt(x / 2)), 0.95, places=10)
        self.assertAlmostEqual(x, 3.8414588, places=6)


class TestLogBeta(unittest.TestCase):
    def test_against_factorials_for_integers(self):
        for a in range(1, 8):
            for b in range(1, 8):
                want = math.log(math.factorial(a - 1) * math.factorial(b - 1)
                                / math.factorial(a + b - 1))
                self.assertAlmostEqual(log_beta(a, b), want, places=12)

    def test_handles_large_arguments_without_overflow(self):
        v = log_beta(1e5, 1e5)
        self.assertTrue(math.isfinite(v))


if __name__ == "__main__":
    unittest.main(verbosity=2)
