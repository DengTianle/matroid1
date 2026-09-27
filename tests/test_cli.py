"""Check persistent command behavior, not just the in-memory solver API."""
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from gf5minors.matroid import uniform


class CommandTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-m", "gf5minors", *map(str, args)],
                              text=True, capture_output=True, timeout=20,
                              cwd=Path(__file__).resolve().parents[1])

    def test_resume_and_refuse_changed_filters(self):
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            parent = tmp / "parent.json"
            parent.write_text(json.dumps(uniform(2, 6).to_record()))
            out = tmp / "extensions"
            result = self.run_cli("extend", parent, "--simple", "--max-models", 1, "--output", out)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads((out / "run.json").read_text())["status"], "MODEL_LIMIT")
            rejected = self.run_cli("extend", parent, "--resume", "--output", out)
            self.assertNotEqual(rejected.returncode, 0)
            result = self.run_cli("extend", parent, "--simple", "--resume", "--output", out)
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads((out / "run.json").read_text())
            self.assertEqual(summary["status"], "EXHAUSTED")
            self.assertEqual(summary["resumed_models"], 1)
            self.assertFalse(summary["global_complete"])
            self.assertEqual(len((out / "extensions.jsonl").read_text().splitlines()), 1)

    def test_fixture_and_recognition_commands(self):
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            result = self.run_cli("fixtures", "--output", tmp / "fixtures")
            self.assertEqual(result.returncode, 0, result.stderr)
            out = tmp / "representation"
            result = self.run_cli("represent", tmp / "fixtures" / "F7.json", "--output", out)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads((out / "result.json").read_text())["status"], "UNSAT")
            self.assertTrue((out / "provenance.json").exists())
            rejected = self.run_cli("represent", tmp / "fixtures" / "F7.json", "--output", out)
            self.assertNotEqual(rejected.returncode, 0)


if __name__ == "__main__":
    unittest.main()
