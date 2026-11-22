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


def main() -> None:
    parser = argparse.ArgumentParser(prog="mcp-workspace")
    parser.add_argument("command", choices=("sync", "setup", "status", "run", "run-all"))
    parser.add_argument("name", nargs="?", help="registered service name for the run command")
    arguments = parser.parse_args()
    root = _workspace_root()

    try:
        services = _load_services(root)
        if arguments.command == "status":
            if not services:
                print("No services registered. Add [[services]] entries to repositories.toml.")
            else:
                for line in checkout_status(root, services):
                    print(line)
            return
        if arguments.command == "run":
            if not arguments.name:
                parser.error("the run command requires a server name")
            service = next((item for item in services if item.name == arguments.name), None)
            if service is None:
                raise ValueError(f"Service {arguments.name!r} is not registered")
            run_server(root, service)
            return
        if arguments.command == "run-all":
            if not services:
                print("No services registered. Add [[services]] entries to repositories.toml.")
                return
            run_all_servers(root, services)
            return

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