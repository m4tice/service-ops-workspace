import os

from fastmcp import FastMCP

mcp = FastMCP("replace-with-server-name")


@mcp.tool
def hello(name: str = "world") -> str:
    """Return a greeting for a name."""
    return f"Hello, {name}!"


def main() -> None:
    transport = os.getenv("MCP_TRANSPORT", "http").lower()
    if transport == "stdio":
        mcp.run(transport="stdio")
    elif transport == "http":
        mcp.run(
            transport="http",
            host=os.getenv("MCP_HOST", "127.0.0.1"),
            port=int(os.getenv("MCP_PORT", "8000")),
        )
    else:
        raise ValueError("MCP_TRANSPORT must be 'http' or 'stdio'")


if __name__ == "__main__":
    main()
