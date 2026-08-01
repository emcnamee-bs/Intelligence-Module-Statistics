"""L2/L3/L4 tests for benchmark_runs_needed.

The sample-size formula is verified by simulation rather than against a remembered constant: run
the implied experiment many times at the prescribed n and check the achieved power lands on target.
That catches an error in the formula, in the z-quantiles, or in the factor of 2, none of which a
closed-form self-comparison would.
"""
import json
import random
import subprocess
import sys
import unittest
from math import sqrt
from pathlib import Path
from statistics import NormalDist, mean, stdev

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "models" / "design" / "benchmark_runs_needed.py"
sys.path.insert(0, str(ROOT))

from models.design.benchmark_runs_needed import (  # noqa: E402
    CONVENTIONAL_DEFAULT_RUNS, chi2_quantile, runs_per_arm, sd_upper_bound,
)


def run(*args):
    r = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)
    return r.returncode, r.stdout


class TestSampleSizeAgainstSimulation(unittest.TestCase):
    """Prescribe n, then simulate the experiment and check the achieved power."""

    def _achieved_power(self, n, effect, sd, alpha, trials=6000, seed=7):
        rng = random.Random(seed)
        crit = NormalDist().inv_cdf(1.0 - alpha / 2.0)
        hits = 0
        for _ in range(trials):
            a = [rng.gauss(0.0, sd) for _ in range(n)]
            b = [rng.gauss(effect, sd) for _ in range(n)]
            se = sqrt(stdev(a) ** 2 / n + stdev(b) ** 2 / n)
            if abs(mean(b) - mean(a)) / se > crit:
                hits += 1
        return hits / trials

    def test_prescribed_n_achieves_the_requested_power(self):
        for effect, sd, power in ((0.08, 0.05, 0.80), (1.0, 1.0, 0.80), (0.5, 1.0, 0.90)):
            n = max(2, int(-(-runs_per_arm(effect, sd, power, 0.05) // 1)))
            got = self._achieved_power(n, effect, sd, 0.05)
            # Tolerance covers Monte Carlo error plus the normal-vs-t approximation at modest n.
            self.assertAlmostEqual(got, power, delta=0.06,
                                   msg=f"effect={effect} sd={sd} target={power} n={n} got={got}")

    def test_type_one_error_is_controlled_at_the_prescribed_n(self):
        n = max(2, int(-(-runs_per_arm(1.0, 1.0, 0.8, 0.05) // 1)))
        false_positives = self._achieved_power(n, 0.0, 1.0, 0.05, seed=99)
        self.assertLess(false_positives, 0.09)


class TestFormulaProperties(unittest.TestCase):
    def test_scales_with_square_of_sd(self):
        base = runs_per_arm(1.0, 1.0, 0.8, 0.05)
        self.assertAlmostEqual(runs_per_arm(1.0, 2.0, 0.8, 0.05), 4 * base, places=8)

    def test_scales_with_inverse_square_of_effect(self):
        base = runs_per_arm(1.0, 1.0, 0.8, 0.05)
        self.assertAlmostEqual(runs_per_arm(2.0, 1.0, 0.8, 0.05), base / 4, places=8)

    def test_more_power_needs_more_runs(self):
        self.assertGreater(runs_per_arm(1, 1, 0.95, 0.05), runs_per_arm(1, 1, 0.80, 0.05))

    def test_stricter_alpha_needs_more_runs(self):
        self.assertGreater(runs_per_arm(1, 1, 0.8, 0.01), runs_per_arm(1, 1, 0.8, 0.05))


class TestChiSquareQuantile(unittest.TestCase):
    def test_against_closed_forms(self):
        # df=2 is exponential with mean 2: quantile = -2 ln(1-p).
        from math import log
        for p in (0.05, 0.5, 0.95):
            self.assertAlmostEqual(chi2_quantile(p, 2), -2 * log(1 - p), places=9)

    def test_known_upper_quantile_one_df(self):
        # chi2(1) 95th percentile is the square of the normal 97.5th percentile.
        z = NormalDist().inv_cdf(0.975)
        self.assertAlmostEqual(chi2_quantile(0.95, 1), z * z, places=8)


class TestSdUpperBound(unittest.TestCase):
    def test_exceeds_the_point_estimate(self):
        for k in (2, 3, 5, 10, 50):
            self.assertGreater(sd_upper_bound(1.0, k), 1.0, msg=f"k={k}")

    def test_tightens_as_pilot_grows(self):
        bounds = [sd_upper_bound(1.0, k) for k in (3, 5, 10, 30, 100)]
        self.assertEqual(bounds, sorted(bounds, reverse=True))

    def test_has_the_expected_coverage(self):
        """90% of samples should have a true sd below the reported upper bound."""
        rng = random.Random(11)
        k, true_sd, trials = 6, 1.0, 4000
        covered = sum(1 for _ in range(trials)
                      if sd_upper_bound(stdev([rng.gauss(0, true_sd) for _ in range(k)]), k)
                      >= true_sd)
        self.assertAlmostEqual(covered / trials, 0.95, delta=0.02)


class TestOutcomes(unittest.TestCase):
    def test_known_sd_answers(self):
        rc, out = run("--effect", "0.08", "--sd", "0.05")
        self.assertEqual(rc, 0)
        self.assertIn("runs_per_arm", out)
        self.assertNotIn("CAVEAT:", out)

    def test_pilot_data_answers_with_uncertainty_caveat(self):
        # Wide spread relative to the effect, so the requirement exceeds the default.
        rc, out = run("--effect", "0.02", "--pilot", "1.02,0.98,1.11,1.05,0.99")
        self.assertEqual(rc, 0)
        self.assertIn("CAVEAT:", out)
        self.assertIn("upper", out.lower())

    def test_small_requirement_defers_to_the_conventional_default(self):
        # Large effect, tiny spread: the calculation says a handful, so it has not beaten
        # "just run 30" - and the default absorbs the sd uncertainty for free.
        rc, out = run("--effect", "1.0", "--pilot", "1.00,1.01,0.99,1.02,0.98")
        self.assertEqual(rc, 5)
        self.assertIn("USE_SIMPLER", out)
        self.assertIn(str(CONVENTIONAL_DEFAULT_RUNS), out)
        self.assertIn("NOT the model's", out)

    def test_undetectable_effect_is_unanswerable(self):
        rc, out = run("--effect", "0.00001", "--sd", "1.0")
        self.assertEqual(rc, 4)
        self.assertNotIn("RESULT", out)
        self.assertIn("ASK INSTEAD:", out)

    def test_both_sd_and_pilot_refuses(self):
        rc, out = run("--effect", "1", "--sd", "1", "--pilot", "1,2,3")
        self.assertEqual(rc, 3)
        self.assertNotIn("RESULT", out)

    def test_neither_sd_nor_pilot_refuses(self):
        rc, out = run("--effect", "1")
        self.assertEqual(rc, 3)

    def test_nonpositive_effect_refuses(self):
        for e in ("0", "-1"):
            rc, _ = run("--effect", e, "--sd", "1")
            self.assertEqual(rc, 3, f"effect={e}")

    def test_single_pilot_value_refuses(self):
        rc, out = run("--effect", "1", "--pilot", "1.0")
        self.assertEqual(rc, 3)
        self.assertNotIn("RESULT", out)

    def test_identical_pilot_values_refuse_rather_than_dividing_by_zero(self):
        rc, out = run("--effect", "1", "--pilot", "1.0,1.0,1.0")
        self.assertEqual(rc, 3)
        self.assertIn("resolution", out)

    def test_unparseable_pilot_refuses(self):
        rc, _ = run("--effect", "1", "--pilot", "1.0,oops,3")
        self.assertEqual(rc, 3)

    def test_out_of_range_power_refuses(self):
        rc, _ = run("--effect", "1", "--sd", "1", "--power", "1.5")
        self.assertEqual(rc, 3)


class TestAgainstTheRecordedBaseline(unittest.TestCase):
    """S1 gave 5 runs per arm and never asked how many were needed."""

    def test_s1_scenario_shows_five_runs_was_not_a_plan(self):
        # Baseline S1: sd ~0.052, and an 8% regression on a ~1.03s baseline is ~0.08s.
        rc, out = run("--effect", "0.08", "--sd", "0.052", "--json")
        d = json.loads(out)
        self.assertEqual(rc, 0)
        # The point is not the exact number but that it exceeds the 5 the baseline used.
        self.assertGreater(d["result"]["runs_per_arm"], 5)


class TestHeaderContract(unittest.TestCase):
    def test_header_fields_and_budget(self):
        header = [ln for ln in SCRIPT.read_text().splitlines()[1:14] if ln.startswith("#")]
        text = "\n".join(header)
        for field in ("WHAT", "WHEN", "INPUTS", "OUTPUT", "ASSUMPTIONS", "EXAMPLE"):
            self.assertIn(field, text)
        self.assertLessEqual(len(header), 12)

    def test_assumptions_warn_about_ordering(self):
        # The baseline itself identified sequential runs as the dominant real-world hazard.
        header = "\n".join(SCRIPT.read_text().splitlines()[1:14])
        self.assertIn("ordered", header)

    def test_header_example_runs(self):
        example = next(ln for ln in SCRIPT.read_text().splitlines() if "# EXAMPLE" in ln)
        cmd = example.split("EXAMPLE", 1)[1].strip().split()
        r = subprocess.run([sys.executable, str(ROOT / cmd[1]), *cmd[2:]],
                           capture_output=True, text=True, cwd=ROOT)
        self.assertIn(r.returncode, (0, 3, 4, 5), r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
