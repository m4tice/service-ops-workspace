from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastmcp import FastMCP

from mcp_common.location import resolve_current_location, resolve_named_location
from mcp_common.transport import run_server

mcp = FastMCP("time")


def _timezone_for_location(location: str) -> str:
    try:
        return ZoneInfo(location).key
    except ZoneInfoNotFoundError:
        return resolve_named_location(location)["timezone"]


@mcp.tool
def get_current_time(location: str | None = None) -> dict[str, str]:
    """Get the current time for an IANA timezone or a place name.

    If location is omitted, use the server's approximate public-IP location.
    """
    if location is None:
        current_location = resolve_current_location()
        timezone = current_location["timezone"]
        location_name = current_location["location"]
    else:
        timezone = _timezone_for_location(location)
        location_name = location

    now = datetime.now(ZoneInfo(timezone))
    return {
        "location": location_name,
        "timezone": timezone,
        "current_time": now.isoformat(timespec="seconds"),
    }


def main() -> None:
    run_server(mcp, default_port=8001)


if __name__ == "__main__":
    main()