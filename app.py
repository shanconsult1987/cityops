import json
import sys
from datetime import datetime, timezone


def classify_request(description):
    """Classify a citizen complaint using simple deterministic rules."""
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


def create_request(description):
    """Create a simple request record."""
    if not description or not description.strip():
        raise ValueError("Description cannot be empty.")

    classification = classify_request(description)

    return {
        "request_id": "CITY-001",
        "description": description.strip(),
        **classification,
        "status": "planned",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    if len(sys.argv) < 2:
        print('Usage: python app.py "Streetlight is broken"')
        return

    request = create_request(" ".join(sys.argv[1:]))
    print(json.dumps(request, indent=2))


if __name__ == "__main__":
    main()