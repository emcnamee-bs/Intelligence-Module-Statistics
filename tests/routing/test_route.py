"""L5 routing evals: recall AND false-positive control.

Both halves matter. A router that never misses but fires on everything converts the module into
noise and destroys the Tier 0 discipline the whole design rests on; cc-thinking-skills validates
its own router on exactly these two axes.

The no-match floor is recomputed here from the eval set rather than trusted, so it cannot drift
into being an unjustified constant.
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUERIES = json.loads((ROOT / "tests" / "routing" / "queries.json").read_text())
sys.path.insert(0, str(ROOT))

from route import NO_MATCH_FLOOR, load_registry, score_all, tokenize  # noqa: E402

REG = load_registry()


def top(query):
    scored = score_all(query, REG)
    return scored[0] if scored else (0.0, None)


class TestRecall(unittest.TestCase):
    def test_every_should_match_query_hits_its_model_first(self):
        misses = []
        for case in QUERIES["should_match"]:
            scored = score_all(case["q"], REG)
            if not scored or scored[0][1]["id"] != case["expect"]:
                got = scored[0][1]["id"] if scored else "nothing"
                misses.append(f"{case['q']!r} -> {got}, wanted {case['expect']}")
        self.assertEqual(misses, [], "recall@1 failures:\n" + "\n".join(misses))

    def test_every_should_match_query_hits_within_top_three(self):
        for case in QUERIES["should_match"]:
            ids = [m["id"] for _, m in score_all(case["q"], REG)[:3]]
            self.assertIn(case["expect"], ids, f"{case['q']!r} missed recall@3")

    def test_every_should_match_query_clears_the_floor(self):
        for case in QUERIES["should_match"]:
            s, _ = top(case["q"])
            self.assertGreaterEqual(s, NO_MATCH_FLOOR, f"{case['q']!r} scored {s:.3f}")


class TestFalsePositiveControl(unittest.TestCase):
    def test_no_unrelated_query_clears_the_floor(self):
        firing = [(c["q"], round(top(c["q"])[0], 3))
                  for c in QUERIES["should_match_nothing"] if top(c["q"])[0] >= NO_MATCH_FLOOR]
        self.assertEqual(firing, [], f"router fired on unrelated queries: {firing}")

    def test_unrelated_queries_report_no_confident_match_end_to_end(self):
        for case in QUERIES["should_match_nothing"][:4]:
            r = subprocess.run([sys.executable, str(ROOT / "route.py"), case["q"]],
                               capture_output=True, text=True, cwd=ROOT)
            self.assertIn("NO CONFIDENT MATCH", r.stdout, f"{case['q']!r}: {case['why']}")


class TestFloorIsCalibratedNotChosen(unittest.TestCase):
    """Recompute the calibration from the eval set and assert the shipped constant matches."""

    def test_floor_sits_between_the_two_populations(self):
        best_noise = max(top(c["q"])[0] for c in QUERIES["should_match_nothing"])
        worst_signal = min(top(c["q"])[0] for c in QUERIES["should_match"])
        self.assertLess(best_noise, worst_signal,
                        f"populations overlap: noise reaches {best_noise:.3f}, "
                        f"signal drops to {worst_signal:.3f} - no floor can separate them")
        self.assertGreater(NO_MATCH_FLOOR, best_noise)
        self.assertLessEqual(NO_MATCH_FLOOR, worst_signal)

    def test_shipped_constant_equals_the_recomputed_midpoint(self):
        best_noise = max(top(c["q"])[0] for c in QUERIES["should_match_nothing"])
        worst_signal = min(top(c["q"])[0] for c in QUERIES["should_match"])
        midpoint = (best_noise + worst_signal) / 2
        self.assertAlmostEqual(
            NO_MATCH_FLOOR, midpoint, delta=0.5,
            msg=f"NO_MATCH_FLOOR={NO_MATCH_FLOOR} has drifted from the calibrated midpoint "
                f"{midpoint:.3f} (noise ceiling {best_noise:.3f}, signal floor {worst_signal:.3f}). "
                f"Recalibrate or explain the deviation.")

    def test_separation_margin_is_reported_for_review(self):
        best_noise = max(top(c["q"])[0] for c in QUERIES["should_match_nothing"])
        worst_signal = min(top(c["q"])[0] for c in QUERIES["should_match"])
        # Not an assertion of quality - a guard that the margin has not collapsed to nothing as
        # the registry grows. A thin margin means the next model added will break routing.
        self.assertGreater(worst_signal - best_noise, 0.2,
                           f"separation margin is only {worst_signal - best_noise:.3f}")


class TestRegistryIntegrity(unittest.TestCase):
    def test_every_model_path_exists(self):
        for m in REG["models"]:
            self.assertTrue((ROOT / m["path"]).exists(), f"{m['id']} -> missing {m['path']}")

    def test_every_model_declares_a_selection_limb(self):
        # Spec section 8: no model ships without one. This is the selection principle enforced.
        for m in REG["models"]:
            self.assertIn(m.get("selection_limb"), ("a", "b", "c"), f"{m['id']}")

    def test_every_model_cites_its_evidence(self):
        for m in REG["models"]:
            self.assertTrue(m.get("evidence", "").strip(), f"{m['id']} has no evidence note")

    def test_every_model_has_at_least_three_situation_phrasings(self):
        for m in REG["models"]:
            self.assertGreaterEqual(len(m["situations"]), 3, f"{m['id']}")

    def test_every_family_referenced_is_declared(self):
        declared = {f["id"] for f in REG["families"]}
        for m in REG["models"]:
            self.assertIn(m["family"], declared, f"{m['id']}")

    def test_no_declared_family_is_empty(self):
        used = {m["family"] for m in REG["models"]}
        for f in REG["families"]:
            self.assertIn(f["id"], used, f"family {f['id']} has no models")

    def test_usage_strings_name_real_flags(self):
        """A usage line that does not match the script's argparse would send an agent in circles."""
        for m in REG["models"]:
            src = (ROOT / m["path"]).read_text()
            for flag in {w for w in m["usage"].split() if w.startswith("--")}:
                self.assertIn(f'"{flag}"', src, f"{m['id']} usage names {flag}, script does not")


class TestTokenizer(unittest.TestCase):
    def test_drops_stopwords_and_punctuation(self):
        self.assertEqual(tokenize("Is this the RIGHT one?"), ["right", "one"])

    def test_keeps_digits(self):
        self.assertIn("8", tokenize("an 8% slowdown"))


class TestCli(unittest.TestCase):
    def _run(self, *args):
        r = subprocess.run([sys.executable, str(ROOT / "route.py"), *args],
                           capture_output=True, text=True, cwd=ROOT)
        return r.returncode, r.stdout, r.stderr

    def test_precheck_is_always_printed_before_matches(self):
        rc, out, _ = self._run("how many runs do I need")
        self.assertEqual(rc, 0)
        self.assertLess(out.index("BEFORE YOU COMPUTE"), out.index("MATCHES"))

    def test_match_output_includes_a_runnable_command(self):
        rc, out, _ = self._run("how many times should I run the benchmark")
        self.assertIn("python3 models/design/benchmark_runs_needed.py", out)

    def test_composition_hazards_are_surfaced_with_the_match(self):
        rc, out, _ = self._run("could a confounder explain away this association")
        self.assertIn("HAZARD:", out)

    def test_family_listing(self):
        rc, out, _ = self._run("--family", "design")
        self.assertEqual(rc, 0)
        self.assertIn("minimum_attainable_p_for_design.py", out)

    def test_unknown_family_errors(self):
        rc, _, err = self._run("--family", "nope")
        self.assertEqual(rc, 1)
        self.assertIn("Families:", err)

    def test_id_lookup(self):
        rc, out, _ = self._run("--id", "three-point-estimate-to-range")
        self.assertEqual(rc, 0)
        self.assertIn("beta-PERT", out)

    def test_json_mode_omits_the_precheck_prose(self):
        rc, out, _ = self._run("how long will this take", "--json")
        d = json.loads(out)
        self.assertIn("matches", d)
        self.assertGreater(len(d["matches"]), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
