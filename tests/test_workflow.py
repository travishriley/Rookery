"""Workflow configuration regressions, not independent repository enforcement."""

from pathlib import Path
import re
import unittest

import yaml


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = (Path(__file__).resolve().parents[1] / ".github/workflows/fixtures.yml").read_text(encoding="utf-8")
        cls.workflow = yaml.safe_load(cls.text)

    def test_only_unprivileged_fixture_triggers_and_permissions(self):
        self.assertEqual(set(self.workflow["on"]), {"pull_request", "push"})
        self.assertEqual(self.workflow["on"]["push"], {"branches": ["main"]})
        self.assertEqual(self.workflow["permissions"], {"contents": "read"})
        self.assertNotIn("secrets.", self.text)
        self.assertEqual(set(self.workflow["jobs"]), {"design-contracts", "unit-fixtures"})

    def test_only_reviewed_immutable_actions_without_persisted_credentials(self):
        pins = {
            "actions/checkout": "3d3c42e5aac5ba805825da76410c181273ba90b1",
            "actions/setup-python": "5fda3b95a4ea91299a34e894583c3862153e4b97",
        }
        for job in self.workflow["jobs"].values():
            for step in job["steps"]:
                self.assertTrue(isinstance(step.get("run"), str) or "uses" in step)
                if "uses" not in step:
                    continue
                action, revision = step["uses"].split("@")
                self.assertTrue(re.fullmatch("[0-9a-f]{40}", revision))
                self.assertEqual(revision, pins[action])
                self.assertNotIn("token", step.get("with", {}))
                if action == "actions/checkout":
                    self.assertIs(step["with"]["persist-credentials"], False)

    def test_fixture_jobs_use_hosted_runners_and_real_tests(self):
        jobs = self.workflow["jobs"]
        self.assertEqual(jobs["design-contracts"]["runs-on"], "ubuntu-24.04")
        unit = jobs["unit-fixtures"]
        self.assertEqual(unit["runs-on"], "${{ matrix.os }}")
        self.assertEqual(unit["strategy"]["matrix"]["os"], ["ubuntu-24.04", "windows-2025"])
        for job in jobs.values():
            self.assertLessEqual(job["timeout-minutes"], 10)
            self.assertLessEqual(set(job), {"name", "runs-on", "timeout-minutes", "strategy", "steps"})
        commands = [step.get("run", "") for step in unit["steps"]]
        self.assertIn("python -m unittest discover -s tests -v", commands)
        self.assertIn("python -m pip check", commands)
        self.assertTrue(any(".whl" in command and "pip install" in command for command in commands))
        self.assertIn("No worker isolation", " ".join(commands))


if __name__ == "__main__":
    unittest.main()
