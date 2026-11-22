from typing import Any

from fastmcp import FastMCP

from mcp_common.location import resolve_current_location
from mcp_common.transport import run_server

mcp = FastMCP("geolocation")


@mcp.tool
def get_current_location() -> dict[str, Any]:
    """Return the server's approximate location based on its public IP address."""
    return resolve_current_location()


def main() -> None:
    run_server(mcp, default_port=8002)


if __name__ == "__main__":
    main()