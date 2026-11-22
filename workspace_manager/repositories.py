import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
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


def _runtime_dir(root: Path) -> Path:
    return root / ".workspace_runtime"


def _process_state_path(root: Path) -> Path:
    return _runtime_dir(root) / "processes.json"


def _load_process_records(root: Path) -> dict[str, dict[str, Any]]:
    state_path = _process_state_path(root)
    if not state_path.is_file():
        return {}
    try:
        raw = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    records: dict[str, dict[str, Any]] = {}
    for name, entry in raw.items():
        if isinstance(name, str) and isinstance(entry, dict) and isinstance(entry.get("pid"), int):
            records[name] = entry
    return records


def _save_process_records(root: Path, records: dict[str, dict[str, Any]]) -> None:
    state_path = _process_state_path(root)
    if not records:
        if state_path.exists():
            state_path.unlink()
        return
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(records, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _is_pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            check=False,
            capture_output=True,
            text=True,
        )
        return result.returncode == 0 and str(pid) in result.stdout
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _pid_command_matches(pid: int, expected_executable: str) -> bool:
    if sys.platform == "win32":
        return True
    result = subprocess.run(
        ["ps", "-p", str(pid), "-o", "command="],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False
    command_line = result.stdout.strip()
    if not command_line:
        return True
    executable_name = Path(expected_executable).name
    return expected_executable in command_line or executable_name in command_line


def _active_process_records(root: Path) -> dict[str, dict[str, Any]]:
    records = _load_process_records(root)
    active: dict[str, dict[str, Any]] = {}
    changed = False
    for name, entry in records.items():
        pid = entry.get("pid")
        command = entry.get("command")
        expected_executable = command[0] if isinstance(command, list) and command and isinstance(command[0], str) else ""
        if isinstance(pid, int) and _is_pid_running(pid) and (
            not expected_executable or _pid_command_matches(pid, expected_executable)
        ):
            active[name] = entry
        else:
            changed = True
    if changed:
        _save_process_records(root, active)
    return active


def _terminate_pid(pid: int, timeout: float = 5.0) -> None:
    if not _is_pid_running(pid):
        return
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            check=False,
            capture_output=True,
            text=True,
        )
        return

    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _is_pid_running(pid):
            return
        time.sleep(0.1)

    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        return


def _port_is_online(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def checkout_status(root: Path, services: list[ManagedService]) -> list[str]:
    active_records = _active_process_records(root)
    lines = []
    for service in services:
        checkout = root / "src" / service.name
        record = active_records.get(service.name)
        process_info = f" process=running(pid={record['pid']})" if record else ""
        if not checkout.exists():
            lines.append(f"{service.name}: not cloned{process_info}")
            continue
        branch = _git(checkout, "branch", "--show-current")
        dirty = bool(_git(checkout, "status", "--porcelain"))
        state = "modified" if dirty else "clean"
        availability = "online" if _port_is_online(service.port) else "offline"
        health = (
            f" health={_web_health_status(service)}"
            if service.kind == "web" and availability == "online"
            else ""
        )
        lines.append(
            f"{service.name} ({service.kind}): branch={branch or '(detached)'} "
            f"worktree={state} endpoint={availability}{health}{process_info}"
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


def _spawn_background_process(command: list[str], log_handle: Any, **popen_kwargs: Any) -> subprocess.Popen:
    return subprocess.Popen(
        command,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        **popen_kwargs,
    )


def start_servers(root: Path, services: list[ManagedService]) -> list[str]:
    if not services:
        return []

    records = _active_process_records(root)
    messages: list[str] = []
    logs_dir = _runtime_dir(root) / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    for service in services:
        existing = records.get(service.name)
        if existing is not None:
            messages.append(
                f"{service.name} ({service.kind}) is already running (pid={existing['pid']}) on 127.0.0.1:{service.port}"
            )
            continue

        if _port_is_online(service.port):
            raise RuntimeError(
                f"Cannot start {service.name}: 127.0.0.1:{service.port} is already accepting connections "
                "(possibly an untracked foreground process)"
            )

        command, checkout, process_environment = _launch_spec(root, service)
        log_path = logs_dir / f"{service.name}.log"
        popen_kwargs: dict[str, Any] = {
            "cwd": checkout,
            "env": process_environment,
            "stdin": subprocess.DEVNULL,
        }
        if sys.platform == "win32":
            popen_kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        else:
            popen_kwargs["start_new_session"] = True

        with log_path.open("ab") as log_handle:
            process = _spawn_background_process(command, log_handle, **popen_kwargs)

        time.sleep(0.15)
        returncode = process.poll()
        if returncode is not None:
            raise RuntimeError(
                f"{service.name} exited immediately with status {returncode}; inspect {log_path}"
            )

        records[service.name] = {
            "pid": process.pid,
            "kind": service.kind,
            "port": service.port,
            "command": command,
            "log": str(log_path),
            "started_at": time.time(),
        }
        _save_process_records(root, records)
        messages.append(
            f"Started {service.name} ({service.kind}) in background (pid={process.pid}) on 127.0.0.1:{service.port}"
        )

    return messages


def stop_servers(root: Path, service_names: list[str] | None = None) -> list[str]:
    records = _active_process_records(root)
    targets = list(records.keys()) if service_names is None else service_names
    messages: list[str] = []

    for name in targets:
        record = records.pop(name, None)
        if record is None:
            messages.append(f"{name}: not running (no tracked background process)")
            continue
        pid = int(record["pid"])
        _terminate_pid(pid)
        messages.append(f"Stopped {name} (pid={pid})")

    _save_process_records(root, records)
    return messages


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