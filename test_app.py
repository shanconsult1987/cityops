import json
import unittest
from contextlib import redirect_stdout
from io import StringIO
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import Mock, patch

import app


class ClassifyRequestTests(unittest.TestCase):
    def test_classifies_supported_service_types_case_insensitively(self):
        cases = [
            (
                "The STREET LIGHT outside my house is broken",
                "streetlight",
                "Electrical Maintenance",
            ),
            ("There is a pothole on Main Street", "road_damage", "Road Maintenance"),
            ("Please collect this rubbish", "waste_collection", "Sanitation"),
        ]

        for description, service_type, team in cases:
            with self.subTest(description=description):
                result = app.classify_request(description)

                self.assertEqual(result["service_type"], service_type)
                self.assertEqual(result["team"], team)
                self.assertEqual(result["priority"], "normal")

    def test_returns_manual_review_for_unknown_description(self):
        self.assertEqual(
            app.classify_request("A park bench needs repainting"),
            {
                "service_type": "unknown",
                "team": "Manual Review",
                "priority": "review",
            },
        )


class StateTests(unittest.TestCase):
    def test_load_state_returns_empty_state_when_file_does_not_exist(self):
        with TemporaryDirectory() as directory:
            with patch.object(app, "STATE_FILE", Path(directory) / "state.json"):
                self.assertEqual(app.load_state(), {"requests": []})

    def test_save_and_load_state_round_trip(self):
        state = {"requests": [{"request_id": "CITY-12345678"}]}

        with TemporaryDirectory() as directory:
            state_file = Path(directory) / "state.json"
            with patch.object(app, "STATE_FILE", state_file):
                app.save_state(state)
                loaded_state = app.load_state()

            self.assertEqual(loaded_state, state)
            self.assertEqual(json.loads(state_file.read_text(encoding="utf-8")), state)

    def test_write_audit_appends_json_record(self):
        with TemporaryDirectory() as directory:
            audit_file = Path(directory) / "audit.jsonl"
            with (
                patch.object(app, "AUDIT_FILE", audit_file),
                patch("app.utc_now", return_value="2026-10-13T06:30:00+00:00"),
            ):
                app.write_audit("request_planned", "CITY-12345678", {"team": "Road"})
                app.write_audit("request_approved", "CITY-12345678")

            records = [
                json.loads(line)
                for line in audit_file.read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(
            records,
            [
                {
                    "timestamp": "2026-10-13T06:30:00+00:00",
                    "event": "request_planned",
                    "request_id": "CITY-12345678",
                    "details": {"team": "Road"},
                },
                {
                    "timestamp": "2026-10-13T06:30:00+00:00",
                    "event": "request_approved",
                    "request_id": "CITY-12345678",
                    "details": {},
                },
            ],
        )


class RequestTests(unittest.TestCase):
    def test_create_request_persists_and_audits_planned_request(self):
        state = {"requests": []}
        fake_uuid = Mock(hex="abcd1234ffff")

        with (
            patch("app.uuid4", return_value=fake_uuid),
            patch("app.utc_now", return_value="2026-10-13T06:30:00+00:00"),
            patch("app.load_state", return_value=state),
            patch("app.save_state") as save_state,
            patch("app.write_audit") as write_audit,
        ):
            result = app.create_request("  Broken streetlight  ")

        expected = {
            "request_id": "CITY-ABCD1234",
            "description": "Broken streetlight",
            "service_type": "streetlight",
            "team": "Electrical Maintenance",
            "priority": "normal",
            "status": "planned",
            "approved_by": None,
            "created_at": "2026-10-13T06:30:00+00:00",
        }
        self.assertEqual(result, expected)
        self.assertEqual(state["requests"], [expected])
        save_state.assert_called_once_with(state)
        write_audit.assert_called_once_with(
            "request_planned",
            "CITY-ABCD1234",
            {"team": "Electrical Maintenance", "priority": "normal"},
        )

    def test_create_request_rejects_empty_description_without_loading_state(self):
        with patch("app.load_state") as load_state:
            for description in ("", "   ", None):
                with self.subTest(description=description):
                    with self.assertRaisesRegex(
                        ValueError, "Description cannot be empty."
                    ):
                        app.create_request(description)

        load_state.assert_not_called()

    def test_list_requests_returns_requests_from_state(self):
        requests = [{"request_id": "CITY-12345678"}]

        with patch("app.load_state", return_value={"requests": requests}):
            self.assertIs(app.list_requests(), requests)

    def test_get_request_returns_match_or_none(self):
        requests = [
            {"request_id": "CITY-11111111"},
            {"request_id": "CITY-22222222"},
        ]

        with patch("app.list_requests", return_value=requests):
            self.assertIs(app.get_request("CITY-22222222"), requests[1])
            self.assertIsNone(app.get_request("CITY-99999999"))


class ApproveRequestTests(unittest.TestCase):
    def setUp(self):
        self.request = {
            "request_id": "CITY-12345678",
            "service_type": "road_damage",
            "status": "planned",
            "approved_by": None,
        }
        self.state = {"requests": [self.request]}

    def test_approves_request_and_records_audit_event(self):
        with (
            patch("app.load_state", return_value=self.state),
            patch("app.utc_now", return_value="2026-10-13T06:45:00+00:00"),
            patch("app.save_state") as save_state,
            patch("app.write_audit") as write_audit,
        ):
            result = app.approve_request("CITY-12345678", "  Priya  ")

        self.assertIs(result, self.request)
        self.assertEqual(self.request["status"], "approved")
        self.assertEqual(self.request["approved_by"], "Priya")
        self.assertEqual(
            self.request["approved_at"], "2026-10-13T06:45:00+00:00"
        )
        save_state.assert_called_once_with(self.state)
        write_audit.assert_called_once_with(
            "request_approved",
            "CITY-12345678",
            {"approver": "Priya"},
        )

    def test_rejects_missing_approver_without_loading_state(self):
        with patch("app.load_state") as load_state:
            for approver in ("", "  ", None):
                with self.subTest(approver=approver):
                    with self.assertRaisesRegex(ValueError, "Approver is required."):
                        app.approve_request("CITY-12345678", approver)

        load_state.assert_not_called()

    def test_rejects_request_that_is_not_planned(self):
        self.request["status"] = "approved"

        with patch("app.load_state", return_value=self.state):
            with self.assertRaisesRegex(
                ValueError, "Only planned requests can be approved."
            ):
                app.approve_request("CITY-12345678", "Priya")

    def test_rejects_unknown_request_type(self):
        self.request["service_type"] = "unknown"

        with patch("app.load_state", return_value=self.state):
            with self.assertRaisesRegex(
                ValueError, "Unknown requests require manual investigation."
            ):
                app.approve_request("CITY-12345678", "Priya")

    def test_rejects_request_id_that_does_not_exist(self):
        with patch("app.load_state", return_value=self.state):
            with self.assertRaisesRegex(
                ValueError, "Request not found: CITY-99999999"
            ):
                app.approve_request("CITY-99999999", "Priya")


class MainTests(unittest.TestCase):
    def run_main(self, arguments):
        output = StringIO()
        with patch.object(app.sys, "argv", ["app.py", *arguments]):
            with redirect_stdout(output):
                app.main()
        return output.getvalue()

    def test_prints_commands_when_no_command_is_provided(self):
        output = self.run_main([])

        self.assertIn('python app.py create "Broken streetlight"', output)
        self.assertIn("python app.py list", output)
        self.assertIn("python app.py approve CITY-XXXXXXXX approver-name", output)

    def test_routes_create_command_and_prints_json(self):
        expected = {"request_id": "CITY-12345678"}

        with patch("app.create_request", return_value=expected) as create_request:
            output = self.run_main(["CREATE", "broken", "lamp"])

        create_request.assert_called_once_with("broken lamp")
        self.assertEqual(json.loads(output), expected)

    def test_routes_list_command_and_prints_json(self):
        expected = [{"request_id": "CITY-12345678"}]

        with patch("app.list_requests", return_value=expected) as list_requests:
            output = self.run_main(["list"])

        list_requests.assert_called_once_with()
        self.assertEqual(json.loads(output), expected)

    def test_routes_approve_command_and_prints_json(self):
        expected = {"request_id": "CITY-12345678", "status": "approved"}

        with patch("app.approve_request", return_value=expected) as approve_request:
            output = self.run_main(["approve", "CITY-12345678", "Priya"])

        approve_request.assert_called_once_with("CITY-12345678", "Priya")
        self.assertEqual(json.loads(output), expected)

    def test_reports_command_errors_and_exits(self):
        cases = [
            (["create"], "Provide a complaint description."),
            (["approve", "CITY-12345678"], "Provide request ID and approver name."),
            (["remove"], "Unknown command: remove"),
        ]

        for arguments, message in cases:
            with self.subTest(arguments=arguments):
                output = StringIO()
                with (
                    patch.object(app.sys, "argv", ["app.py", *arguments]),
                    redirect_stdout(output),
                    self.assertRaisesRegex(SystemExit, "1"),
                ):
                    app.main()

                self.assertEqual(output.getvalue().strip(), f"Error: {message}")

    def test_reports_invalid_state_json_and_exits(self):
        with patch("app.list_requests", side_effect=json.JSONDecodeError("bad", "", 0)):
            output = StringIO()
            with (
                patch.object(app.sys, "argv", ["app.py", "list"]),
                redirect_stdout(output),
                self.assertRaisesRegex(SystemExit, "1"),
            ):
                app.main()

        self.assertTrue(output.getvalue().startswith("Error: bad:"))


if __name__ == "__main__":
    unittest.main()
