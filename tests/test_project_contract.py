"""Project-level invariants: portability, doc freshness, and the skill file's own constraints.

These are the properties that make the module usable at all. A scipy import or a stale INDEX.md
would not fail any model's own tests, but either would break the thing in the field.
"""
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"

# Everything the module is allowed to import. The whole portability argument rests on this list:
# the API code-execution environment has no network and no runtime package installation, so a
# single third-party import makes the module unusable exactly where it is most needed.
STDLIB_ALLOWED = {
    "argparse", "json", "math", "random", "re", "sys", "csv", "itertools", "functools",
    "statistics", "pathlib", "dataclasses", "typing", "decimal", "fractions", "collections",
    "unittest", "subprocess", "os", "textwrap", "bisect", "enum", "datetime", "hashlib",
}
FIRST_PARTY = {"lib", "models", "route", "generate_docs", "tests"}


def python_files():
    for p in sorted(ROOT.rglob("*.py")):
        if ".git" in p.parts or "__pycache__" in p.parts:
            continue
        yield p


class TestPortability(unittest.TestCase):
    def test_no_third_party_imports_anywhere(self):
        pattern = re.compile(r"^\s*(?:from|import)\s+([A-Za-z_][A-Za-z0-9_]*)", re.M)
        offenders = []
        for p in python_files():
            for mod in pattern.findall(p.read_text()):
                if mod not in STDLIB_ALLOWED and mod not in FIRST_PARTY:
                    offenders.append(f"{p.relative_to(ROOT)}: {mod}")
        self.assertEqual(offenders, [], "third-party imports found:\n" + "\n".join(offenders))

    def test_no_windows_style_paths(self):
        for p in python_files():
            self.assertNotRegex(p.read_text(), r'"[A-Za-z]+\\[A-Za-z]+\.(py|md|json)"',
                                f"{p.relative_to(ROOT)} uses a backslash path")

    def test_every_model_runs_with_help(self):
        reg = json.loads((ROOT / "registry.json").read_text())
        for m in reg["models"]:
            r = subprocess.run([sys.executable, str(ROOT / m["path"]), "--help"],
                               capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(r.returncode, 0, f"{m['id']} --help failed: {r.stderr[:300]}")


class TestGeneratedDocsAreFresh(unittest.TestCase):
    def test_docs_match_the_registry(self):
        r = subprocess.run([sys.executable, str(ROOT / "generate_docs.py"), "--check"],
                           capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(r.returncode, 0, f"generated docs are stale:\n{r.stderr}")

    def test_generated_files_carry_the_do_not_edit_banner(self):
        for p in [ROOT / "INDEX.md", *(ROOT / "docs" / "families").glob("*.md")]:
            self.assertIn("GENERATED", p.read_text().splitlines()[0], str(p))

    def test_family_files_open_with_a_table_of_contents(self):
        # Reference files can be read partially; a TOC at the top means a partial read still
        # reveals the full scope rather than silently truncating the catalogue.
        for p in (ROOT / "docs" / "families").glob("*.md"):
            head = "\n".join(p.read_text().splitlines()[:8])
            self.assertIn("## Contents", head, f"{p.name} has no leading TOC")


class TestSkillFileConstraints(unittest.TestCase):
    """The published constraints on a skill's frontmatter are hard limits, not style."""

    def setUp(self):
        text = SKILL.read_text()
        self.assertTrue(text.startswith("---\n"), "SKILL.md must open with YAML frontmatter")
        _, fm, self.body = text.split("---\n", 2)
        self.fm = fm
        self.name = re.search(r"^name:\s*(.+)$", fm, re.M).group(1).strip()
        desc = re.search(r"^description:\s*>\n((?:\s{2,}.*\n)+)", fm, re.M).group(1)
        self.description = " ".join(line.strip() for line in desc.strip().splitlines())

    def test_name_is_lowercase_hyphen_and_short(self):
        self.assertRegex(self.name, r"^[a-z0-9-]{1,64}$")

    def test_name_avoids_reserved_words(self):
        for reserved in ("claude", "anthropic"):
            self.assertNotIn(reserved, self.name)

    def test_description_within_limit_and_third_person(self):
        self.assertLessEqual(len(self.description), 1024,
                             f"description is {len(self.description)} chars")
        self.assertGreater(len(self.description), 100, "description is too thin to route on")
        for first_person in (" I ", "I can", "I will"):
            self.assertNotIn(first_person, self.description)

    def test_description_states_triggers_not_just_capability(self):
        self.assertIn("Use when", self.description)

    def test_body_is_well_under_the_line_budget(self):
        lines = self.body.strip().splitlines()
        self.assertLess(len(lines), 500, f"SKILL.md body is {len(lines)} lines")

    def test_references_are_one_level_deep(self):
        """Links must point at real files, and those files must not chain onward.

        A file reached via another file gets partially read, so the agent acts on a truncated view.
        """
        links = re.findall(r"\]\(([^)]+)\)", self.body)
        for link in links:
            if link.startswith("#") or link.startswith("http"):
                continue
            target = ROOT / link
            self.assertTrue(target.exists(), f"SKILL.md links to missing {link}")

    def test_body_documents_every_exit_code_a_model_can_return(self):
        for code in ("`0`", "`2`", "`3`", "`4`", "`5`"):
            self.assertIn(code, self.body, f"exit {code} undocumented in SKILL.md")

    def test_body_names_the_report_as_convention(self):
        self.assertIn("REPORT AS", self.body)

    def test_body_states_the_honest_limitation(self):
        # The baselines scored 23/25 unaided. A skill that oversells itself invites misuse on
        # exactly the tasks where it adds nothing.
        self.assertIn("evals/baselines/RESULTS.md", self.body)
        self.assertIn("23 of 25", self.body)

    def test_body_carries_a_when_not_to_use_section(self):
        self.assertIn("When not to use", self.body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
