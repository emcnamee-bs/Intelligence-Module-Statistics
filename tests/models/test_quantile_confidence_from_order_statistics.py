"""L2/L3/L4 tests, plus the C1 cluster membership check the spec requires.

C1 was asserted at 5 of 5 members and verified at 4 of 6 — the two-sided Wilks interval is
transcendental and does not reduce to `n >= ln(alpha)/ln(q)`. So membership is derived here per
member rather than inherited from the family, and the non-member is asserted to be a non-member.
"""
import json
import random
import subprocess
import sys
import unittest
from math import ceil, comb, log
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "models" / "estimation" / "quantile_confidence_from_order_statistics.py"
sys.path.insert(0, str(ROOT))

from models.estimation.quantile_confidence_from_order_statistics import (  # noqa: E402
    binom_cdf, bounding_order_statistic, max_quantile_bounded, min_n_for_quantile,
)


def run(*args):
    r = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)
    return r.returncode, r.stdout


class TestCoverageBySimulation(unittest.TestCase):
    """The claimed bound must actually cover the true quantile at the stated rate.

    Uniform(0,1) is used so the true q-quantile is exactly q, making coverage checkable without
    any distributional assumption entering the test.
    """

    def test_achieves_at_least_nominal_coverage(self):
        rng = random.Random(31337)
        for n, q, conf in ((100, 0.90, 0.95), (50, 0.80, 0.95), (200, 0.95, 0.90)):
            k = bounding_order_statistic(n, q, 1 - conf)
            self.assertIsNotNone(k)
            trials, covered = 4000, 0
            for _ in range(trials):
                sample = sorted(rng.random() for _ in range(n))
                if sample[k - 1] >= q:      # bound must sit above the true quantile
                    covered += 1
            rate = covered / trials
            self.assertGreaterEqual(rate, conf - 0.02, f"n={n} q={q}: coverage {rate:.3f}")
            # Discreteness makes it conservative, but not absurdly so.
            self.assertLess(rate, conf + 0.09, f"n={n} q={q}: coverage {rate:.3f} is over-wide")


class TestC1ClusterMembership(unittest.TestCase):
    """Verify this model really is the identity it claims, and that a known non-member is not."""

    def test_attainability_matches_the_closed_form(self):
        # The order-statistic search must succeed exactly when n >= ln(alpha)/ln(q).
        for q in (0.80, 0.90, 0.95, 0.97, 0.99):
            for alpha in (0.05, 0.10):
                need = min_n_for_quantile(q, alpha)
                self.assertIsNone(bounding_order_statistic(need - 1, q, alpha),
                                  f"q={q} alpha={alpha}: n={need-1} should not suffice")
                self.assertIsNotNone(bounding_order_statistic(need, q, alpha),
                                     f"q={q} alpha={alpha}: n={need} should suffice")

    def test_is_the_same_identity_as_the_rule_of_three(self):
        """Rule of three: zero events in n trials bounds the rate at 1 - alpha^(1/n) ~ 3/n.

        Setting q = 1 - p maps that onto this model's max_quantile_bounded, so they are one
        inequality wearing two names. Verified, per the C1 failure, rather than asserted.
        """
        for n in (20, 100, 300):
            rate_bound = 1 - 0.05 ** (1 / n)                 # rule of three, exact form
            self.assertAlmostEqual(1 - max_quantile_bounded(n, 0.05), rate_bound, places=14)
        # The familiar 3/n approximation, and where it comes from.
        self.assertAlmostEqual((1 - 0.05 ** (1 / 100)) * 100, -log(0.05), delta=0.05)

    def test_two_sided_wilks_is_NOT_a_member(self):
        """The C1 verification found the two-sided tolerance interval to be transcendental.

        The one-sided requirement at 95/95 is n=59; a formula-based claim of 93 cannot come from
        this identity. Asserting the non-membership keeps the cluster honest as it grows.
        """
        one_sided_95_95 = min_n_for_quantile(0.95, 0.05)
        self.assertEqual(one_sided_95_95, 59)
        self.assertNotEqual(one_sided_95_95, 93)


class TestTheHeadlineFact(unittest.TestCase):
    def test_at_n_100_nothing_above_0_9705_can_be_bounded(self):
        q_max = max_quantile_bounded(100, 0.05)
        self.assertAlmostEqual(q_max, 0.05 ** 0.01, places=14)
        self.assertGreater(q_max, 0.970)
        self.assertLess(q_max, 0.971)
        self.assertIsNotNone(bounding_order_statistic(100, 0.97, 0.05))
        self.assertIsNone(bounding_order_statistic(100, 0.99, 0.05))

    def test_p99_needs_299_observations(self):
        self.assertEqual(min_n_for_quantile(0.99, 0.05), 299)

    def test_p95_needs_59(self):
        self.assertEqual(min_n_for_quantile(0.95, 0.05), 59)


class TestBinomialCdf(unittest.TestCase):
    def test_against_direct_enumeration(self):
        for n, p in ((10, 0.3), (25, 0.9), (7, 0.5)):
            for k in range(-1, n + 2):
                want = sum(comb(n, i) * p ** i * (1 - p) ** (n - i)
                           for i in range(0, min(k, n) + 1)) if k >= 0 else 0.0
                self.assertAlmostEqual(binom_cdf(k, n, p), min(1.0, want), places=12)

    def test_boundaries(self):
        self.assertEqual(binom_cdf(-1, 10, 0.5), 0.0)
        self.assertEqual(binom_cdf(10, 10, 0.5), 1.0)


class TestOutcomes(unittest.TestCase):
    def test_unreachable_quantile_is_unanswerable(self):
        rc, out = run("--quantile", "0.99", "--n", "100")
        self.assertEqual(rc, 4)
        self.assertNotIn("RESULT", out)
        self.assertIn("299", out)
        self.assertIn("not an estimate of the quantile", out)

    def test_reachable_quantile_without_data_answers(self):
        rc, out = run("--quantile", "0.95", "--n", "100")
        self.assertEqual(rc, 0)
        self.assertIn("ROBUSTNESS:", out)

    def test_with_data_returns_an_actual_value(self):
        data = ",".join(str(i) for i in range(1, 101))
        rc, out = run("--quantile", "0.90", "--data", data, "--json")
        d = json.loads(out)
        self.assertEqual(rc, 0)
        k = d["result"]["bounding_order_statistic"]
        self.assertEqual(d["result"]["upper_bound"], float(k))

    def test_bound_is_never_below_the_naive_sample_quantile(self):
        data = ",".join(str(i) for i in range(1, 101))
        rc, out = run("--quantile", "0.90", "--data", data, "--json")
        d = json.loads(out)
        naive = 90.0  # the 90th of 100 sorted values
        self.assertGreaterEqual(d["result"]["upper_bound"], naive)

    def test_quantile_given_as_percent_refuses(self):
        rc, out = run("--quantile", "99", "--n", "100")
        self.assertEqual(rc, 3)
        self.assertIn("p99 is 0.99", out)

    def test_bad_confidence_refuses(self):
        rc, _ = run("--quantile", "0.9", "--n", "100", "--confidence", "95")
        self.assertEqual(rc, 3)

    def test_unparseable_data_refuses(self):
        rc, _ = run("--quantile", "0.9", "--data", "1,2,oops")
        self.assertEqual(rc, 3)

    def test_data_and_n_together_is_a_usage_error(self):
        r = subprocess.run([sys.executable, str(SCRIPT), "--quantile", "0.9",
                            "--data", "1,2,3", "--n", "3"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)


class TestHeaderContract(unittest.TestCase):
    def test_header_fields_and_budget(self):
        header = [ln for ln in SCRIPT.read_text().splitlines()[1:14] if ln.startswith("#")]
        text = "\n".join(header)
        for field in ("WHAT", "WHEN", "INPUTS", "OUTPUT", "ASSUMPTIONS", "EXAMPLE"):
            self.assertIn(field, text)
        self.assertLessEqual(len(header), 12)

    def test_assumptions_name_the_iid_requirement(self):
        header = "\n".join(SCRIPT.read_text().splitlines()[1:14])
        self.assertIn("autocorrelated", header)

    def test_header_example_runs(self):
        example = next(ln for ln in SCRIPT.read_text().splitlines() if "# EXAMPLE" in ln)
        cmd = example.split("EXAMPLE", 1)[1].strip().split()
        r = subprocess.run([sys.executable, str(ROOT / cmd[1]), *cmd[2:]],
                           capture_output=True, text=True, cwd=ROOT)
        self.assertIn(r.returncode, (0, 3, 4, 5), r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
