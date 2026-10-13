
import json
from pathlib import Path
from unittest.mock import patch

import app


def evaluate_cases():
    cases = json.loads(
        Path("cases.json").read_text(encoding="utf-8")
    )
    results = []

    # Evaluation should be reproducible and offline, even if .env exists.
    with patch.object(app, "suggest_classification", return_value=None):
        for case in cases:
            plan = app.supervisor_plan(case["description"])
            classification = plan["classification"]
            safety = plan["safety"]

            actual_review = safety["decision"] == "escalate"

            passed = (
                classification["service_type"]
                == case["expected_service_type"]
                and classification["team"] == case["expected_team"]
                and actual_review == case["expected_review"]
            )

            results.append({
                "id": case["id"],
                "passed": passed,
                "actual_service_type": classification["service_type"],
                "actual_team": classification["team"],
                "safety_decision": safety["decision"],
            })

    passed_count = sum(item["passed"] for item in results)
    total = len(results)

    report = {
        "passed": passed_count,
        "total": total,
        "accuracy": round(passed_count / total, 3) if total else 0,
        "results": results,
    }

    print(json.dumps(report, indent=2))
    return 0 if passed_count == total else 1


if __name__ == "__main__":
    raise SystemExit(evaluate_cases())
