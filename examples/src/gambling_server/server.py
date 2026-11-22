import secrets

from fastmcp import FastMCP

from mcp_common.transport import run_server

mcp = FastMCP("gambling")


@mcp.tool
def roll_a_dice() -> int:
    """Roll a fair six-sided die and return a number from 1 through 6."""
    return secrets.randbelow(6) + 1


def main() -> None:
    run_server(mcp, default_port=8003)


if __name__ == "__main__":
    main()