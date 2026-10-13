import json
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from io import StringIO
from unittest.mock import patch

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


class CreateRequestTests(unittest.TestCase):
    def test_creates_request_with_trimmed_description_and_utc_timestamp(self):
        created_at = datetime(2026, 10, 13, 5, 37, 44, tzinfo=timezone.utc)

        with patch("app.datetime") as datetime_mock:
            datetime_mock.now.return_value = created_at
            result = app.create_request("  Garbage has not been collected  ")

        self.assertEqual(
            result,
            {
                "request_id": "CITY-001",
                "description": "Garbage has not been collected",
                "service_type": "waste_collection",
                "team": "Sanitation",
                "priority": "normal",
                "status": "planned",
                "created_at": created_at.isoformat(),
            },
        )
        datetime_mock.now.assert_called_once_with(timezone.utc)

    def test_rejects_empty_or_whitespace_only_description(self):
        for description in ("", "   ", None):
            with self.subTest(description=description):
                with self.assertRaisesRegex(
                    ValueError, "Description cannot be empty."
                ):
                    app.create_request(description)


class MainTests(unittest.TestCase):
    def test_prints_usage_when_description_is_missing(self):
        output = StringIO()

        with patch.object(app.sys, "argv", ["app.py"]), redirect_stdout(output):
            app.main()

        self.assertEqual(
            output.getvalue().strip(),
            'Usage: python app.py "Streetlight is broken"',
        )

    def test_prints_created_request_as_json(self):
        output = StringIO()
        expected = {"request_id": "CITY-001", "description": "broken lamp"}

        with (
            patch.object(app.sys, "argv", ["app.py", "broken", "lamp"]),
            patch("app.create_request", return_value=expected) as create_request_mock,
            redirect_stdout(output),
        ):
            app.main()

        create_request_mock.assert_called_once_with("broken lamp")
        self.assertEqual(json.loads(output.getvalue()), expected)


if __name__ == "__main__":
    unittest.main()