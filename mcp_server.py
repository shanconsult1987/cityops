from mcp.server.fastmcp import FastMCP

import app


mcp = FastMCP("cityops-tools")


@mcp.tool()
def get_request_status(request_id: str) -> dict:
    """Return the current status of a CityOps request."""
    request = app.get_request(request_id)

    if request is None:
        return {"found": False, "request_id": request_id}

    return {
        "found": True,
        "request_id": request["request_id"],
        "service_type": request["service_type"],
        "team": request["team"],
        "priority": request["priority"],
        "status": request["status"],
    }


@mcp.tool()
def preview_routing(description: str) -> dict:
    """Preview a deterministic team assignment without creating a request."""
    if not description or not description.strip():
        return {"error": "Description cannot be empty."}

    result = app.classify_request(description)
    return {
        "description": description.strip(),
        **result,
        "creates_request": False,
        "requires_manual_review": result["service_type"] == "unknown",
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")