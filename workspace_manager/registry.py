import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse


_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")


@dataclass(frozen=True)
class ManagedService:
    name: str
    url: str
    port: int
    kind: Literal["mcp", "web"] = "mcp"
    command: tuple[str, ...] = ()
    health_path: str | None = None


def load_registry(path: Path) -> list[ManagedService]:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ValueError(f"Unable to read server registry at {path}: {error}") from error

    if "services" in data and "servers" in data:
        raise ValueError("Use [[services]] entries; do not mix them with legacy [[servers]] entries")
    legacy_servers = "servers" in data
    entries = data.get("servers", []) if legacy_servers else data.get("services", [])
    if not isinstance(entries, list):
        raise ValueError("Registry entries must use [[services]] tables")

    services: list[ManagedService] = []
    names: set[str] = set()
    ports: set[int] = set()

    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Each [[services]] entry must be a table")

        name = entry.get("name")
        url = entry.get("url")
        port = entry.get("port")
        kind = entry.get("type", "mcp" if legacy_servers else None)
        command = entry.get("command", [])
        health_path = entry.get("health_path")
        if not isinstance(name, str) or not _NAME_PATTERN.fullmatch(name):
            raise ValueError(f"Invalid service name: {name!r}")
        if name in names:
            raise ValueError(f"Duplicate service name: {name}")
        if not isinstance(url, str) or not url.strip():
            raise ValueError(f"Service {name} must have a non-empty Git URL")
        parsed_url = urlparse(url)
        if parsed_url.scheme not in {"https", "ssh", "git"} and not url.startswith("git@"):
            raise ValueError(f"Service {name} must use an HTTPS or SSH Git URL")
        if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
            raise ValueError(f"Service {name} must have a valid TCP port")
        if port in ports:
            raise ValueError(f"Duplicate service port: {port}")
        if kind not in {"mcp", "web"}:
            raise ValueError(f"Service {name} type must be 'mcp' or 'web'")
        if not isinstance(command, list) or any(not isinstance(part, str) or not part for part in command):
            raise ValueError(f"Service {name} command must be an array of non-empty strings")
        if kind == "web" and not command:
            raise ValueError(f"Web service {name} must define a command")
        if kind == "mcp" and command:
            raise ValueError(f"MCP service {name} uses the standard 'mcp-server' command; omit command")
        if health_path is not None:
            if kind != "web":
                raise ValueError(f"Health paths are only supported for web services ({name})")
            if not isinstance(health_path, str) or not health_path.startswith("/") or health_path.startswith("//"):
                raise ValueError(f"Service {name} health_path must be an absolute URL path")

        names.add(name)
        ports.add(port)
        services.append(
            ManagedService(
                name=name,
                url=url,
                port=port,
                kind=kind,
                command=tuple(command),
                health_path=health_path,
            )
        )

    return services