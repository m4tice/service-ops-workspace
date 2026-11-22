# Example Servers

These are local reference implementations of the time, geolocation, and gambling tools. They are intentionally outside `src/`, which is reserved for independent Git checkouts listed in `repositories.toml`. The examples are for MCP server maintainers learning the template contract; the workspace maintainer does not sync, provision, or monitor them as registered servers.

The examples share one development environment and are not monitored repositories. From this directory:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

On Windows PowerShell, use `.venv\Scripts\python.exe` instead of `.venv/bin/python`.