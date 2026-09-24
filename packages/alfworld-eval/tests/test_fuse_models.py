"""Offline tests for the FUSE adaptation protocol models."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from alfworld_eval.fuse.models import (  # noqa: E402
    ClusterResult,
    DiagnosticResult,
    TagResult,
)


class TestDiagnosticResult(unittest.TestCase):
    def test_parses_each_decision(self):
        for decision in ("evolve", "no_change", "inconclusive"):
            result = DiagnosticResult.from_markdown(
                f"Decision: {decision}\n\n# Failure Summary\nbody"
            )
            self.assertEqual(result.decision, decision)
            self.assertIn("Failure Summary", result.markdown)

    def test_first_non_empty_line(self):
        result = DiagnosticResult.from_markdown(
            "\n\n   Decision: evolve   \nbody"
        )
        self.assertEqual(result.decision, "evolve")

    def test_rejects_missing_decision_prefix(self):
        with self.assertRaises(ValueError):
            DiagnosticResult.from_markdown("Evolve now\nbody")

    def test_rejects_unknown_decision(self):
        with self.assertRaises(ValueError):
            DiagnosticResult.from_markdown("Decision: maybe\nbody")

    def test_rejects_empty(self):
        with self.assertRaises(ValueError):
            DiagnosticResult.from_markdown("")

    def test_to_dict_roundtrip(self):
        result = DiagnosticResult.from_markdown("Decision: no_change\nwhy")
        self.assertEqual(result.to_dict()["decision"], "no_change")


class TestTagResult(unittest.TestCase):
    def _payload(self, **overrides):
        payload = {
            "schema_version": 1,
            "incident_id": "task__trial_1",
            "outcome": "failure",
            "capability_tags": ["locate an object by checking receptacles"],
            "capability_summary": "Find and heat the target object.",
        }
        payload.update(overrides)
        return payload

    def test_valid(self):
        result = TagResult.from_json(self._payload())
        self.assertEqual(result.incident_id, "task__trial_1")
        self.assertEqual(len(result.capability_tags), 1)

    def test_from_file(self):
        path = Path(PROJECT_ROOT) / "tests" / "_tmp_tags.json"
        path.write_text(json.dumps(self._payload()), encoding="utf-8")
        try:
            result = TagResult.from_json(path)
            self.assertEqual(result.outcome, "failure")
        finally:
            path.unlink()

    def test_rejects_empty_tags(self):
        with self.assertRaises(ValueError):
            TagResult.from_json(self._payload(capability_tags=[]))

    def test_rejects_missing_summary(self):
        with self.assertRaises(ValueError):
            TagResult.from_json(self._payload(capability_summary=" "))

    def test_rejects_bad_outcome(self):
        with self.assertRaises(ValueError):
            TagResult.from_json(self._payload(outcome="failed"))

    def test_rejects_non_string_tags(self):
        with self.assertRaises(ValueError):
            TagResult.from_json(self._payload(capability_tags=["ok", 3]))


class TestClusterResult(unittest.TestCase):
    def _payload(self, decision="merge", members=("a", "b")):
        return {
            "schema_version": 1,
            "capability_clusters": [
                {
                    "cluster_id": "capability-c001",
                    "label": "Heating objects",
                    "definition": "Heat an object with the correct appliance.",
                    "decision": decision,
                    "member_ids": list(members),
                }
            ],
        }

    def test_valid(self):
        result = ClusterResult.from_json(self._payload())
        self.assertEqual(result.capability_clusters[0].cluster_id, "capability-c001")

    def test_rejects_unknown_decision(self):
        with self.assertRaises(ValueError):
            ClusterResult.from_json(self._payload(decision="maybe"))

    def test_rejects_empty_clusters(self):
        with self.assertRaises(ValueError):
            ClusterResult.from_json({"capability_clusters": []})

    def test_membership_requires_every_incident(self):
        result = ClusterResult.from_json(self._payload(members=("a",)))
        with self.assertRaises(ValueError):
            result.validate_membership({"a", "b"})

    def test_membership_rejects_overlap(self):
        payload = {
            "capability_clusters": [
                {"cluster_id": "c1", "label": "l", "definition": "d",
                 "decision": "merge", "member_ids": ["a", "b"]},
                {"cluster_id": "c2", "label": "l", "definition": "d",
                 "decision": "merge", "member_ids": ["b", "c"]},
            ]
        }
        result = ClusterResult.from_json(payload)
        with self.assertRaises(ValueError):
            result.validate_membership({"a", "b", "c"})


if __name__ == "__main__":
    unittest.main()
