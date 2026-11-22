import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from workspace_manager.registry import ManagedService


def _git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(message or f"git {' '.join(arguments)} failed")
    return result.stdout.strip()


def sync_repositories(root: Path, services: list[ManagedService]) -> None:
    source_directory = root / "src"
    source_directory.mkdir(parents=True, exist_ok=True)

    for service in services:
        checkout = source_directory / service.name
        if not checkout.exists():
            result = subprocess.run(
                [
                    "git",
                    "clone",
                    "--single-branch",
                    "--branch",
                    "main",
                    service.url,
                    str(checkout),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            if result.returncode:
                message = result.stderr.strip() or result.stdout.strip()
                raise RuntimeError(f"Unable to clone {service.name}: {message}")
            continue

        try:
            top_level = Path(_git(checkout, "rev-parse", "--show-toplevel")).resolve()
        except RuntimeError as error:
            raise RuntimeError(f"{checkout} exists but is not a Git checkout") from error
        if top_level != checkout.resolve():
            raise RuntimeError(f"{checkout} is inside another Git checkout")

        origin = _git(checkout, "remote", "get-url", "origin")
        if origin != service.url:
            raise RuntimeError(
                f"Origin mismatch for {service.name}: registry has {service.url}, checkout has {origin}"
            )
        branch = _git(checkout, "branch", "--show-current")
        if branch != "main":
            raise RuntimeError(f"{service.name} is on branch {branch!r}, expected 'main'")
        if _git(checkout, "status", "--porcelain"):
            raise RuntimeError(f"{service.name} has local changes; commit or stash them before syncing")

        _git(checkout, "pull", "--ff-only", "origin", "main")


def write_mcp_config(path: Path, services: list[ManagedService]) -> None:
    data = {
        "servers": {
            service.name: {
                "type": "http",
                "url": f"http://127.0.0.1:{service.port}/mcp",
            }
            for service in services
            if service.kind == "mcp"
        }
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _web_health_status(service: ManagedService) -> str:
    if not service.health_path:
        return "not-configured"
    request = f"http://127.0.0.1:{service.port}{service.health_path}"
    try:
        with urlopen(request, timeout=1) as response:
            return "healthy" if 200 <= response.status < 300 else f"unhealthy({response.status})"
    except HTTPError as error:
        return f"unhealthy({error.code})"
    except (TimeoutError, URLError, OSError):
        return "unhealthy"


def checkout_status(root: Path, services: list[ManagedService]) -> list[str]:
    lines = []
    for service in services:
        checkout = root / "src" / service.name
        if not checkout.exists():
            lines.append(f"{service.name}: not cloned")
            continue
        branch = _git(checkout, "branch", "--show-current")
        dirty = bool(_git(checkout, "status", "--porcelain"))
        state = "modified" if dirty else "clean"
        try:
            with socket.create_connection(("127.0.0.1", service.port), timeout=0.5):
                availability = "online"
        except OSError:
            availability = "offline"
        health = (
            f" health={_web_health_status(service)}"
            if service.kind == "web" and availability == "online"
            else ""
        )
        lines.append(
            f"{service.name} ({service.kind}): branch={branch or '(detached)'} "
            f"worktree={state} endpoint={availability}{health}"
        )
    return lines


def _launch_spec(root: Path, service: ManagedService) -> tuple[list[str], Path, dict[str, str]]:
    checkout = root / "src" / service.name
    environment = checkout / ".venv"
    if sys.platform == "win32":
        scripts = environment / "Scripts"
        python = scripts / "python.exe"
    else:
        scripts = environment / "bin"
        python = scripts / "python"

    command = ["mcp-server"] if service.kind == "mcp" else list(service.command)
    executable_name = command[0]
    if executable_name in {"python", "python3"}:
        executable = python
    else:
        executable = scripts / executable_name
        if sys.platform == "win32" and not executable.suffix:
            executable = executable.with_suffix(".exe")
    if not executable.is_file():
        raise RuntimeError(f"{service.name} is not set up or command {command[0]!r} is missing; run 'mcp-workspace setup' first")

    host = "127.0.0.1"
    port = str(service.port)
    arguments = [part.replace("{host}", host).replace("{port}", port) for part in command[1:]]

    process_environment = os.environ.copy()
    process_environment.update({"HOST": host, "PORT": port})
    if service.kind == "mcp":
        process_environment.update(
            {"MCP_HOST": host, "MCP_PORT": port, "MCP_TRANSPORT": "http"}
        )
    return [str(executable), *arguments], checkout, process_environment


def run_server(root: Path, service: ManagedService) -> None:
    command, checkout, process_environment = _launch_spec(root, service)
    subprocess.run(
        command,
        cwd=checkout,
        env=process_environment,
        check=True,
    )


def run_all_servers(root: Path, services: list[ManagedService]) -> None:
    if not services:
        raise RuntimeError("No services registered. Add [[services]] entries to repositories.toml.")

    launches = []
    for service in services:
        command, checkout, process_environment = _launch_spec(root, service)
        launches.append((service, command, checkout, process_environment))

    processes: list[tuple[ManagedService, subprocess.Popen]] = []
    try:
        for service, command, checkout, process_environment in launches:
            process = subprocess.Popen(
                command,
                cwd=checkout,
                env=process_environment,
            )
            processes.append((service, process))
            print(f"Started {service.name} ({service.kind}) on 127.0.0.1:{service.port}")

        while True:
            for service, process in processes:
                returncode = process.poll()
                if returncode is not None:
                    raise RuntimeError(
                        f"{service.name} exited unexpectedly with status {returncode}; stopping all services"
                    )
            time.sleep(0.25)
    except KeyboardInterrupt:
        print("Stopping all services...")
    finally:
        running = [process for _, process in processes if process.poll() is None]
        for process in running:
            process.terminate()

        deadline = time.monotonic() + 5
        for process in running:
            remaining = max(0, deadline - time.monotonic())
            try:
                process.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()