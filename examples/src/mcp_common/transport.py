import os


def run_server(server: object, default_port: int) -> None:
    transport = os.getenv("MCP_TRANSPORT", "http").lower()
    if transport not in {"http", "stdio"}:
        raise ValueError("MCP_TRANSPORT must be 'http' or 'stdio'")

    if transport == "stdio":
        server.run(transport="stdio")
        return

    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_PORT", str(default_port)))
    server.run(transport="http", host=host, port=port)