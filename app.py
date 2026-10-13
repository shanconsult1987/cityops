import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


STATE_FILE = Path("cityops_state.json")
AUDIT_FILE = Path("cityops_audit.jsonl")


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


def create_request(description):
    if not description or not description.strip():
        raise ValueError("Description cannot be empty.")

    request_id = f"CITY-{uuid4().hex[:8].upper()}"
    classification = classify_request(description.strip())

    request = {
        "request_id": request_id,
        "description": description.strip(),
        **classification,
        "status": "planned",
        "approved_by": None,
        "created_at": utc_now(),
    }

    state = load_state()
    state["requests"].append(request)
    save_state(state)

    write_audit(
        "request_planned",
        request_id,
        {"team": request["team"], "priority": request["priority"]},
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

        if request["service_type"] == "unknown":
            raise ValueError("Unknown requests require manual investigation.")

        request["status"] = "approved"
        request["approved_by"] = approver.strip()
        request["approved_at"] = utc_now()

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
                raise ValueError("Provide request ID and approver name.")

            result = approve_request(sys.argv[2], sys.argv[3])

        else:
            raise ValueError(f"Unknown command: {command}")

        print(json.dumps(result, indent=2))

    except (ValueError, json.JSONDecodeError) as error:
        print(f"Error: {error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()