"""L2/L3/L4 tests for multiplicity_correction_for_search.

Sidak is verified against its own definition by simulation - generate k independent uniform
p-values under the null, count how often the minimum falls below the threshold - rather than
against the closed form restated. That catches an inverted exponent or an off-by-one in k, which a
self-comparison would not.
"""
import json
import random
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "models" / "design" / "multiplicity_correction_for_search.py"
sys.path.insert(0, str(ROOT))

from models.design.multiplicity_correction_for_search import (  # noqa: E402
    bonferroni, holm_adjusted, raw_p_needed, sidak,
)


def run(*args):
    r = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)
    return r.returncode, r.stdout


class TestSidakAgainstSimulation(unittest.TestCase):
    """Under the null, k independent p-values are uniform. Sidak(p,k) must be the probability
    that the smallest of them lands below p."""

    def test_matches_the_empirical_family_wise_rate(self):
        rng = random.Random(4242)
        for p, k in ((0.05, 5), (0.01, 20), (0.10, 3), (0.001, 50)):
            trials = 40000
            hits = sum(1 for _ in range(trials)
                       if min(rng.random() for _ in range(k)) < p)
            self.assertAlmostEqual(hits / trials, sidak(p, k), delta=0.01,
                                   msg=f"p={p} k={k}")

    def test_inverse_round_trips(self):
        for alpha in (0.01, 0.05, 0.10):
            for k in (1, 2, 7, 30, 200):
                self.assertAlmostEqual(sidak(raw_p_needed(alpha, k), k), alpha, places=12)


class TestCorrectionProperties(unittest.TestCase):
    def test_k_of_one_is_the_identity(self):
        for p in (0.001, 0.05, 0.5, 0.99):
            self.assertAlmostEqual(sidak(p, 1), p, places=14)
            self.assertAlmostEqual(bonferroni(p, 1), p, places=14)

    def test_sidak_never_exceeds_bonferroni(self):
        # Bonferroni is the union bound; Sidak is exact under independence, hence no larger.
        for p in (0.001, 0.01, 0.05, 0.2):
            for k in (1, 2, 5, 20, 100):
                self.assertLessEqual(sidak(p, k), bonferroni(p, k) + 1e-15, f"p={p} k={k}")

    def test_monotone_in_k(self):
        prev = -1.0
        for k in range(1, 100):
            v = sidak(0.01, k)
            self.assertGreater(v, prev)
            prev = v

    def test_stays_a_probability(self):
        self.assertLessEqual(sidak(0.9, 1000), 1.0)
        self.assertEqual(bonferroni(0.5, 1000), 1.0)

    def test_hand_derived_values(self):
        # Written as the arithmetic, not as remembered decimals.
        self.assertAlmostEqual(sidak(0.05, 20), 1 - 0.95 ** 20, places=14)
        self.assertAlmostEqual(raw_p_needed(0.05, 20), 1 - 0.95 ** (1 / 20), places=14)
        # Sanity on magnitude: looking at 20 things turns a 0.05 into a near-certainty.
        self.assertGreater(sidak(0.05, 20), 0.64)


class TestHolm(unittest.TestCase):
    def test_single_value_is_unchanged(self):
        self.assertAlmostEqual(holm_adjusted([0.03])[0], 0.03, places=14)

    def test_smallest_gets_the_full_bonferroni_factor(self):
        adj = holm_adjusted([0.01, 0.04, 0.03])
        self.assertAlmostEqual(adj[0], 0.03, places=12)  # 3 * 0.01

    def test_is_monotone_in_the_original_ordering(self):
        pvals = [0.001, 0.008, 0.039, 0.041, 0.9]
        adj = holm_adjusted(pvals)
        pairs = sorted(zip(pvals, adj))
        self.assertEqual([a for _, a in pairs], sorted(a for _, a in pairs),
                         "adjusted values must not invert the raw ordering")

    def test_never_below_the_raw_p(self):
        pvals = [0.001, 0.02, 0.3, 0.44]
        for raw, adj in zip(pvals, holm_adjusted(pvals)):
            self.assertGreaterEqual(adj, raw - 1e-15)

    def test_uniformly_at_least_as_powerful_as_bonferroni(self):
        pvals = [0.004, 0.011, 0.03, 0.2]
        m = len(pvals)
        for raw, adj in zip(pvals, holm_adjusted(pvals)):
            self.assertLessEqual(adj, min(1.0, m * raw) + 1e-15)

    def test_returns_in_input_order(self):
        adj = holm_adjusted([0.5, 0.001])
        self.assertGreater(adj[0], adj[1])


class TestOutcomes(unittest.TestCase):
    def test_missing_comparisons_refuses_rather_than_defaulting(self):
        # The refusal IS the feature: defaulting to 1 would reproduce the error silently.
        rc, out = run("--p", "0.03")
        self.assertEqual(rc, 3)
        self.assertNotIn("RESULT", out)
        self.assertIn("abandoned", out)

    def test_post_hoc_is_unanswerable(self):
        rc, out = run("--p", "0.03", "--post-hoc")
        self.assertEqual(rc, 4)
        self.assertNotIn("RESULT", out)
        self.assertIn("held-out", out)

    def test_single_comparison_defers_to_the_raw_p(self):
        rc, out = run("--p", "0.03", "--comparisons", "1")
        self.assertEqual(rc, 5)
        self.assertIn("NOT the model's", out)
        # It must still prompt the count check, since k=1 is the commonest wrong answer.
        self.assertIn("dropped them", out)

    def test_surviving_result_answers_and_reports_bonferroni(self):
        rc, out = run("--p", "0.0001", "--comparisons", "12")
        self.assertEqual(rc, 0)
        self.assertIn("still significant", out)
        self.assertIn("Bonferroni", out)

    def test_failing_result_names_the_threshold_it_missed(self):
        rc, out = run("--p", "0.03", "--comparisons", "12")
        self.assertEqual(rc, 0)
        self.assertIn("no longer significant", out)
        self.assertIn("ROBUSTNESS:", out)
        report = next(ln for ln in out.splitlines() if ln.startswith("REPORT AS:"))
        self.assertIn("p-value of the winner", report)

    def test_zero_comparisons_refuses(self):
        rc, _ = run("--p", "0.03", "--comparisons", "0")
        self.assertEqual(rc, 3)

    def test_p_outside_unit_interval_refuses(self):
        for bad in ("-0.1", "1.4"):
            rc, _ = run("--p", bad, "--comparisons", "3")
            self.assertEqual(rc, 3, f"p={bad}")

    def test_more_p_values_than_comparisons_refuses(self):
        rc, out = run("--p-values", "0.01,0.02,0.03", "--comparisons", "2")
        self.assertEqual(rc, 3)
        self.assertNotIn("RESULT", out)

    def test_p_value_set_uses_holm(self):
        rc, out = run("--p-values", "0.001,0.04,0.3", "--comparisons", "3", "--json")
        d = json.loads(out)
        self.assertEqual(rc, 0)
        self.assertEqual(len(d["result"]["holm_adjusted"]), 3)
        self.assertIn("any dependence", d["robustness"])

    def test_both_p_and_p_values_is_a_usage_error(self):
        r = subprocess.run([sys.executable, str(SCRIPT), "--p", "0.01",
                            "--p-values", "0.01,0.02", "--comparisons", "2"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)


class TestHeaderContract(unittest.TestCase):
    def test_header_fields_and_budget(self):
        header = [ln for ln in SCRIPT.read_text().splitlines()[1:14] if ln.startswith("#")]
        text = "\n".join(header)
        for field in ("WHAT", "WHEN", "INPUTS", "OUTPUT", "ASSUMPTIONS", "EXAMPLE"):
            self.assertIn(field, text)
        self.assertLessEqual(len(header), 12)

    def test_header_example_runs(self):
        example = next(ln for ln in SCRIPT.read_text().splitlines() if "# EXAMPLE" in ln)
        cmd = example.split("EXAMPLE", 1)[1].strip().split()
        r = subprocess.run([sys.executable, str(ROOT / cmd[1]), *cmd[2:]],
                           capture_output=True, text=True, cwd=ROOT)
        self.assertIn(r.returncode, (0, 3, 4, 5), r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
