
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app


class CityOpsTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)

        self.state_patch = patch.object(
            app, "STATE_FILE", root / "state.json"
        )
        self.audit_patch = patch.object(
            app, "AUDIT_FILE", root / "audit.jsonl"
        )
        self.model_patch = patch.object(
            app, "suggest_classification", return_value=None
        )

        self.state_patch.start()
        self.audit_patch.start()
        self.model_patch.start()

    def tearDown(self):
        self.model_patch.stop()
        self.audit_patch.stop()
        self.state_patch.stop()
        self.temp_dir.cleanup()

    def test_streetlight_routing(self):
        result = app.classify_request("Broken streetlight")
        self.assertEqual(result["service_type"], "streetlight")
        self.assertEqual(result["team"], "Electrical Maintenance")

    def test_road_damage_routing(self):
        result = app.classify_request("Large pothole")
        self.assertEqual(result["team"], "Road Maintenance")

    def test_waste_routing(self):
        result = app.classify_request("Garbage was not collected")
        self.assertEqual(result["team"], "Sanitation")

    def test_unknown_request_escalates(self):
        plan = app.supervisor_plan("Something unusual")
        self.assertEqual(
            plan["classification"]["service_type"], "unknown"
        )
        self.assertEqual(plan["safety"]["decision"], "escalate")

    def test_empty_request_is_rejected(self):
        with self.assertRaises(ValueError):
            app.create_request("   ")

    def test_request_is_saved(self):
        request = app.create_request("Broken streetlight")
        self.assertEqual(
            app.get_request(request["request_id"]), request
        )

    def test_unknown_request_cannot_be_approved(self):
        request = app.create_request("Something unusual")

        with self.assertRaises(ValueError):
            app.approve_request(request["request_id"], "Reviewer")

    def test_valid_request_can_be_approved(self):
        request = app.create_request("Broken streetlight")
        approved = app.approve_request(
            request["request_id"], "Reviewer"
        )

        self.assertEqual(approved["status"], "approved")
        self.assertEqual(approved["approved_by"], "Reviewer")

    def test_audit_file_is_written(self):
        request = app.create_request("Broken streetlight")
        audit = app.AUDIT_FILE.read_text(encoding="utf-8")

        self.assertIn("request_planned", audit)
        self.assertIn(request["request_id"], audit)

    def test_invalid_model_team_is_rejected(self):
        invalid = {
            "service_type": "streetlight",
            "team": "Unapproved Team",
            "priority": "normal",
        }

        self.assertIsNone(app.validate_classification(invalid))

    def test_safety_reviewer_never_auto_approves(self):
        plan = app.supervisor_plan("Broken streetlight")
        self.assertFalse(plan["safety"]["can_auto_approve"])
        self.assertFalse(plan["safety"]["can_dispatch"])


if __name__ == "__main__":
    unittest.main()
