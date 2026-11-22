# FastMCP Server Template

This template is for the **MCP server maintainer**, who owns the server's code, dependency declarations, tests, and release branch. Copy this directory into its own Git repository to create a server. Rename `pyproject.toml.template` to `pyproject.toml`, give the distribution a unique name, rename the `mcp_server_template` package, and update the FastMCP server name and sample tool. Keep the console command named `mcp-server`; the workspace maintainer's manager uses it to launch the server.

The template defaults to Streamable HTTP on `MCP_HOST` and `MCP_PORT`, at the `/mcp` endpoint. It also accepts `MCP_TRANSPORT=stdio` for local subprocess integrations. Keep server implementation and dependency decisions in this repository. To make the completed server appear in the monitoring workspace, its maintainer gives the Git URL, checkout name, and requested port to the workspace maintainer, who adds them to `repositories.toml`.
