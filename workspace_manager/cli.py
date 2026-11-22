import argparse
import subprocess
import sys
import venv
from pathlib import Path

from workspace_manager.registry import ManagedService, load_registry
from workspace_manager.repositories import (
    checkout_status,
    run_all_servers,
    run_server,
    start_servers,
    stop_servers,
    sync_repositories,
    write_mcp_config,
)


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_services(root: Path) -> list[ManagedService]:
    return load_registry(root / "repositories.toml")


def _server_python(environment: Path) -> Path:
    if sys.platform == "win32":
        return environment / "Scripts" / "python.exe"
    return environment / "bin" / "python"


def _setup_services(root: Path, services: list[ManagedService]) -> None:
    for service in services:
        checkout = root / "src" / service.name
        project_file = checkout / "pyproject.toml"
        if not project_file.is_file():
            raise RuntimeError(f"{service.name} does not contain a pyproject.toml")

        environment = checkout / ".venv"
        python = _server_python(environment)
        if not python.is_file():
            venv.EnvBuilder(with_pip=True).create(environment)

        subprocess.run(
            [str(python), "-m", "pip", "install", "--editable", str(checkout)],
            check=True,
        )


def _resolve_named_services(services: list[ManagedService], names: list[str]) -> list[ManagedService]:
    by_name = {service.name: service for service in services}
    selected: list[ManagedService] = []
    seen: set[str] = set()
    for name in names:
        service = by_name.get(name)
        if service is None:
            raise ValueError(f"Service {name!r} is not registered")
        if name not in seen:
            selected.append(service)
            seen.add(name)
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(prog="mcp-workspace")
    parser.add_argument(
        "command",
        choices=("sync", "setup", "status", "run", "run-all", "start", "start-all", "stop", "stop-all"),
    )
    parser.add_argument("names", nargs="*", help="registered service name(s) for run, start, stop, or status")
    arguments = parser.parse_args()
    root = _workspace_root()

    try:
        services = _load_services(root)
        if arguments.command == "status":
            if not services:
                print("No services registered. Add [[services]] entries to repositories.toml.")
            else:
                target_services = (
                    _resolve_named_services(services, arguments.names) if arguments.names else services
                )
                for line in checkout_status(root, target_services):
                    print(line)
            return
        if arguments.command == "run":
            if len(arguments.names) != 1:
                parser.error("the run command requires exactly one server name")
            service = _resolve_named_services(services, arguments.names)[0]
            run_server(root, service)
            return
        if arguments.command == "run-all":
            if arguments.names:
                parser.error("the run-all command does not accept service names")
            if not services:
                print("No services registered. Add [[services]] entries to repositories.toml.")
                return
            run_all_servers(root, services)
            return
        if arguments.command == "start":
            if not arguments.names:
                parser.error("the start command requires at least one service name (or use start-all)")
            selected = _resolve_named_services(services, arguments.names)
            for message in start_servers(root, selected):
                print(message)
            return
        if arguments.command == "start-all":
            if arguments.names:
                parser.error("the start-all command does not accept service names")
            if not services:
                print("No services registered. Add [[services]] entries to repositories.toml.")
                return
            for message in start_servers(root, services):
                print(message)
            return
        if arguments.command == "stop":
            if not arguments.names:
                parser.error("the stop command requires at least one service name (or use stop-all)")
            _resolve_named_services(services, arguments.names)
            for message in stop_servers(root, arguments.names):
                print(message)
            return
        if arguments.command == "stop-all":
            if arguments.names:
                parser.error("the stop-all command does not accept service names")
            messages = stop_servers(root, None)
            if not messages:
                print("No tracked background services are running.")
            else:
                for message in messages:
                    print(message)
            return

        if arguments.names:
            parser.error(f"the {arguments.command} command does not accept service names")
        sync_repositories(root, services)
        write_mcp_config(root / ".vscode" / "mcp.json", services)
        if arguments.command == "setup":
            _setup_services(root, services)
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"mcp-workspace: {error}\n")

    if not services:
        print("No services registered. Add [[services]] entries to repositories.toml.")
    elif arguments.command == "sync":
        print(f"Synchronized {len(services)} service repository/repositories.")
    else:
        print(f"Set up {len(services)} service environment(s).")