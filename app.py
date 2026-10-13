
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from openai_client import suggest_classification


STATE_FILE = Path("cityops_state.json")
AUDIT_FILE = Path("cityops_audit.jsonl")

ALLOWED_CLASSIFICATIONS = {
    "streetlight": ("Electrical Maintenance", "normal"),
    "road_damage": ("Road Maintenance", "normal"),
    "waste_collection": ("Sanitation", "normal"),
    "unknown": ("Manual Review", "review"),
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def classify_request(description):
    text = description.lower()

    if any(word in text for word in ["streetlight", "street light", "lamp"]):
        return {
            "service_type": "streetlight",
            "team": "Electrical Maintenance",
            "priority": "normal",
        }

    if any(word in text for word in ["pothole", "road damage", "broken road"]):
        return {
            "service_type": "road_damage",
            "team": "Road Maintenance",
            "priority": "normal",
        }

    if any(word in text for word in ["garbage", "waste", "rubbish"]):
        return {
            "service_type": "waste_collection",
            "team": "Sanitation",
            "priority": "normal",
        }

    return {
        "service_type": "unknown",
        "team": "Manual Review",
        "priority": "review",
    }


def validate_classification(candidate):
    if not isinstance(candidate, dict):
        return None

    service_type = candidate.get("service_type")
    if service_type not in ALLOWED_CLASSIFICATIONS:
        return None

    expected_team, _ = ALLOWED_CLASSIFICATIONS[service_type]

    if candidate.get("team") != expected_team:
        return None

    priority = candidate.get("priority")
    if priority not in {"normal", "urgent", "review"}:
        return None

    if service_type == "unknown" and priority != "review":
        return None

    return {
        "service_type": service_type,
        "team": expected_team,
        "priority": priority,
    }


def load_state():
    if not STATE_FILE.exists():
        return {"requests": []}

    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


def save_state(state):
    STATE_FILE.write_text(
        json.dumps(state, indent=2),
        encoding="utf-8",
    )


def write_audit(event, request_id, details=None):
    record = {
        "timestamp": utc_now(),
        "event": event,
        "request_id": request_id,
        "details": details or {},
    }

    with AUDIT_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record) + "\n")


def triage_agent(description, rule_result, model_result):
    """Identify unknown classifications and disagreements."""
    validated_model = validate_classification(model_result)

    conflict = (
        validated_model is not None
        and validated_model != rule_result
    )

    return {
        "rule_classification": rule_result,
        "model_classification": validated_model,
        "classification_conflict": conflict,
        "requires_review": (
            rule_result["service_type"] == "unknown"
            or conflict
        ),
    }


def routing_agent(classification):
    """Recommend a team; this role cannot approve or dispatch."""
    return {
        "team": classification["team"],
        "service_type": classification["service_type"],
        "routing_action": (
            "manual_review"
            if classification["service_type"] == "unknown"
            else "recommend"
        ),
    }


def safety_reviewer(request, triage, routing):
    """Apply deterministic safety rules to the proposed plan."""
    reasons = []

    if request["service_type"] == "unknown":
        reasons.append("Unknown service type")

    if triage["requires_review"]:
        reasons.append("Triage requested human review")

    if request["priority"] == "review":
        reasons.append("Priority requires review")

    if routing["team"] == "Manual Review":
        reasons.append("No operational team can be assigned automatically")

    return {
        "decision": (
            "escalate"
            if reasons
            else "eligible_for_human_approval"
        ),
        "reasons": reasons,
        "can_auto_approve": False,
        "can_dispatch": False,
    }


def supervisor_plan(description):
    """Coordinate the specialist functions and assemble the plan."""
    rule_result = classify_request(description)
    model_result = suggest_classification(description)

    triage = triage_agent(
        description,
        rule_result,
        model_result,
    )

    # Deterministic rules remain authoritative in this workshop.
    classification = rule_result
    routing = routing_agent(classification)

    draft = {
        "description": description,
        **classification,
    }

    safety = safety_reviewer(draft, triage, routing)

    return {
        "classification": classification,
        "triage": triage,
        "routing": routing,
        "safety": safety,
    }


def create_request(description):
    if not description or not description.strip():
        raise ValueError("Description cannot be empty.")

    description = description.strip()
    plan = supervisor_plan(description)
    classification = plan["classification"]

    request_id = f"CITY-{uuid4().hex[:8].upper()}"

    request = {
        "request_id": request_id,
        "description": description,
        **classification,
        "status": "planned",
        "approved_by": None,
        "needs_review": (
            plan["safety"]["decision"] == "escalate"
        ),
        "agent_results": {
            "triage": plan["triage"],
            "routing": plan["routing"],
            "safety": plan["safety"],
        },
        "created_at": utc_now(),
    }

    state = load_state()
    state["requests"].append(request)
    save_state(state)

    write_audit(
        "request_planned",
        request_id,
        {
            "team": request["team"],
            "needs_review": request["needs_review"],
            "safety_decision": plan["safety"]["decision"],
        },
    )

    return request


def list_requests():
    return load_state()["requests"]


def get_request(request_id):
    for request in list_requests():
        if request["request_id"] == request_id:
            return request

    return None


def approve_request(request_id, approver):
    if not approver or not approver.strip():
        raise ValueError("Approver is required.")

    state = load_state()

    for request in state["requests"]:
        if request["request_id"] != request_id:
            continue

        if request["status"] != "planned":
            raise ValueError("Only planned requests can be approved.")

        if request["needs_review"] or request["service_type"] == "unknown":
            raise ValueError(
                "Safety review requires escalation; approval blocked."
            )

        request["status"] = "approved"
        request["approved_by"] = approver.strip()
        request["approved_at"] = utc_now()

        # This demonstration deliberately has no real dispatch operation.
        save_state(state)

        write_audit(
            "request_approved",
            request_id,
            {"approver": approver.strip()},
        )

        return request

    raise ValueError(f"Request not found: {request_id}")


def main():
    if len(sys.argv) < 2:
        print(
            "Commands:\n"
            '  python app.py create "Broken streetlight"\n'
            "  python app.py list\n"
            "  python app.py approve CITY-XXXXXXXX approver-name\n"
        )
        return

    command = sys.argv[1].lower()

    try:
        if command == "create":
            if len(sys.argv) < 3:
                raise ValueError("Provide a complaint description.")

            result = create_request(" ".join(sys.argv[2:]))

        elif command == "list":
            result = list_requests()

        elif command == "approve":
            if len(sys.argv) < 4:
                raise ValueError(
                    "Provide request ID and approver name."
                )

            result = approve_request(sys.argv[2], sys.argv[3])

        else:
            raise ValueError(f"Unknown command: {command}")

        print(json.dumps(result, indent=2))

    except (ValueError, json.JSONDecodeError) as error:
        print(f"Error: {error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
