
# CityOps AI - Functional Specification

## Purpose
Demonstrate a small, testable agent workflow for municipal service complaints.

## Supported categories
- streetlight
- road_damage
- waste_collection
- unknown

## Routing rules
- streetlight -> Electrical Maintenance
- road_damage -> Road Maintenance
- waste_collection -> Sanitation
- unknown -> Manual Review

## Workflow
1. Validate the complaint description.
2. Classify using deterministic rules.
3. Optionally obtain an OpenAI classification suggestion.
4. Validate model output against an allowlist.
5. Coordinate triage, routing and safety review.
6. Save the proposed request and audit event.
7. Require human approval for eligible requests.

## Safety requirements
- Unknown requests must be escalated.
- Model output is a suggestion, not authorization.
- No request is dispatched automatically.
- The CLI approver name is not production authentication.
- API keys must not be stored in source code.
- Tests and evaluation must not require network access or a live model.

## Non-goals
- Real municipal integrations.
- Production identity-provider integration.
- Production database or immutable audit storage.
- Emergency response or emergency prioritization.
