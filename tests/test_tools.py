import json
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from workspace_manager import cli
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


def _git(repository: Path, *arguments: str) -> None:
    subprocess.run(["git", "-C", str(repository), *arguments], check=True, capture_output=True)


def test_load_registry_rejects_duplicate_ports(tmp_path: Path) -> None:
    registry = tmp_path / "repositories.toml"
    registry.write_text(
        '[[services]]\nname="one"\ntype="mcp"\nurl="https://example.com/one.git"\nport=8001\n'
        '[[services]]\nname="two"\ntype="mcp"\nurl="https://example.com/two.git"\nport=8001\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Duplicate service port"):
        load_registry(registry)


def test_load_registry_treats_legacy_servers_as_mcp(tmp_path: Path) -> None:
    registry = tmp_path / "repositories.toml"
    registry.write_text(
        '[[servers]]\nname="legacy"\nurl="https://example.com/legacy.git"\nport=8001\n',
        encoding="utf-8",
    )

    service = load_registry(registry)[0]

    assert service.kind == "mcp"


def test_sync_clones_main_and_generates_http_config(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    _git(source, "init", "--initial-branch=main")
    _git(source, "config", "user.email", "test@example.com")
    _git(source, "config", "user.name", "Test")
    (source / "pyproject.toml").write_text("[project]\nname='sample'\nversion='0.1.0'\n", encoding="utf-8")
    _git(source, "add", "pyproject.toml")
    _git(source, "commit", "-m", "initial")

    remote = tmp_path / "remote.git"
    subprocess.run(["git", "clone", "--bare", str(source), str(remote)], check=True, capture_output=True)
    _git(source, "remote", "add", "origin", str(remote))
    _git(source, "push", "--set-upstream", "origin", "main")

    root = tmp_path / "workspace"
    service = ManagedService(name="sample", url=str(remote), port=8101)
    sync_repositories(root, [service])
    write_mcp_config(root / ".vscode" / "mcp.json", [service])

    checkout = root / "src" / "sample"
    assert (checkout / "pyproject.toml").is_file()
    config = json.loads((root / ".vscode" / "mcp.json").read_text(encoding="utf-8"))
    assert config["servers"]["sample"]["url"] == "http://127.0.0.1:8101/mcp"

    with socket.socket() as listener:
        listener.bind(("127.0.0.1", service.port))
        listener.listen()
        assert "endpoint=online" in checkout_status(root, [service])[0]


def test_run_server_passes_registry_port(monkeypatch, tmp_path: Path) -> None:
    service = ManagedService(name="sample", url="https://example.com/sample.git", port=8102)
    executable_dir = "Scripts" if sys.platform == "win32" else "bin"
    executable_name = "mcp-server.exe" if sys.platform == "win32" else "mcp-server"
    executable = tmp_path / "src" / service.name / ".venv" / executable_dir / executable_name
    executable.parent.mkdir(parents=True)
    executable.touch()
    captured: dict[str, object] = {}

    def fake_run(command, **options) -> None:
        captured["command"] = command
        captured.update(options)

    monkeypatch.setattr("workspace_manager.repositories.subprocess.run", fake_run)

    run_server(tmp_path, service)

    environment = captured["env"]
    assert environment["MCP_HOST"] == "127.0.0.1"
    assert environment["MCP_PORT"] == "8102"
    assert environment["MCP_TRANSPORT"] == "http"


def test_run_all_starts_and_stops_every_registered_server(monkeypatch, tmp_path: Path) -> None:
    servers = [
        ManagedService(name="one", url="https://example.com/one.git", port=8101),
        ManagedService(name="two", url="https://example.com/two.git", port=8102),
    ]
    for server in servers:
        executable = tmp_path / "src" / server.name / ".venv" / "bin" / "mcp-server"
        executable.parent.mkdir(parents=True)
        executable.touch()

    launches = []

    class FakeProcess:
        returncode = None

        def __init__(self, command, **options) -> None:
            launches.append((command, options))
            self.terminated = False

        def poll(self):
            return self.returncode

        def terminate(self) -> None:
            self.terminated = True
            self.returncode = 0

        def wait(self, timeout=None):
            return self.returncode

        def kill(self) -> None:
            self.returncode = -9

    def interrupt(_interval) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr("workspace_manager.repositories.subprocess.Popen", FakeProcess)
    monkeypatch.setattr("workspace_manager.repositories.time.sleep", interrupt)

    run_all_servers(tmp_path, servers)

    assert len(launches) == 2
    assert [options["env"]["MCP_PORT"] for _, options in launches] == ["8101", "8102"]
    assert all(options["env"]["MCP_TRANSPORT"] == "http" for _, options in launches)


def test_run_all_with_empty_registry_reports_without_error(monkeypatch, tmp_path: Path, capsys) -> None:
    (tmp_path / "repositories.toml").write_text("", encoding="utf-8")
    monkeypatch.setattr(cli, "_workspace_root", lambda: tmp_path)
    monkeypatch.setattr(sys, "argv", ["mcp-workspace", "run-all"])

    cli.main()

    assert "No services registered" in capsys.readouterr().out


def test_web_registry_command_and_health_path(tmp_path: Path) -> None:
    registry = tmp_path / "repositories.toml"
    registry.write_text(
        '[[services]]\nname="api"\ntype="web"\n'
        'url="https://example.com/api.git"\nport=8200\n'
        'command=["python", "-m", "uvicorn", "app.main:app", "--host", "{host}", "--port", "{port}"]\n'
        'health_path="/health"\n',
        encoding="utf-8",
    )
    service = load_registry(registry)[0]

    assert service.kind == "web"
    assert service.command[-1] == "{port}"
    assert service.health_path == "/health"


def test_run_web_service_expands_host_and_port_without_a_shell(monkeypatch, tmp_path: Path) -> None:
    service = ManagedService(
        name="api",
        url="https://example.com/api.git",
        port=8200,
        kind="web",
        command=("python", "-m", "uvicorn", "app.main:app", "--host", "{host}", "--port", "{port}"),
    )
    python = tmp_path / "src" / "api" / ".venv" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.touch()
    captured: dict[str, object] = {}

    def fake_run(command, **options) -> None:
        captured["command"] = command
        captured.update(options)

    monkeypatch.setattr("workspace_manager.repositories.subprocess.run", fake_run)

    run_server(tmp_path, service)

    assert captured["command"] == [
        str(python), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8200"
    ]
    assert captured["env"]["HOST"] == "127.0.0.1"
    assert captured["env"]["PORT"] == "8200"
    assert "MCP_PORT" not in captured["env"]


def test_status_reports_web_http_health(monkeypatch, tmp_path: Path) -> None:
    service = ManagedService(
        name="api",
        url="https://example.com/api.git",
        port=8200,
        kind="web",
        command=("python", "-m", "uvicorn", "app.main:app"),
        health_path="/health",
    )
    checkout = tmp_path / "src" / "api"
    checkout.mkdir(parents=True)
    _git(checkout, "init", "--initial-branch=main")

    class FakeResponse:
        status = 204

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr(
        "workspace_manager.repositories.socket.create_connection",
        lambda *_args, **_kwargs: FakeResponse(),
    )
    monkeypatch.setattr(
        "workspace_manager.repositories.urlopen",
        lambda *_args, **_kwargs: FakeResponse(),
    )

    assert "endpoint=online health=healthy" in checkout_status(tmp_path, [service])[0]


def test_mcp_config_excludes_web_services(tmp_path: Path) -> None:
    services = [
        ManagedService(name="mcp-one", url="https://example.com/mcp.git", port=8101),
        ManagedService(
            name="web-one",
            url="https://example.com/web.git",
            port=8201,
            kind="web",
            command=("python", "-m", "http.server", "{port}"),
        ),
    ]

    config_path = tmp_path / ".vscode" / "mcp.json"
    write_mcp_config(config_path, services)
    config = json.loads(config_path.read_text(encoding="utf-8"))

    assert list(config["servers"]) == ["mcp-one"]


def test_start_and_stop_servers_track_background_processes(monkeypatch, tmp_path: Path) -> None:
    services = [
        ManagedService(name="alpha", url="https://example.com/alpha.git", port=8301),
        ManagedService(name="beta", url="https://example.com/beta.git", port=8302),
    ]
    executable_dir = "Scripts" if sys.platform == "win32" else "bin"
    executable_name = "mcp-server.exe" if sys.platform == "win32" else "mcp-server"
    for service in services:
        checkout = tmp_path / "src" / service.name
        executable = checkout / ".venv" / executable_dir / executable_name
        executable.parent.mkdir(parents=True)
        executable.touch()
        _git(checkout, "init", "--initial-branch=main")

    running_pids: set[int] = set()
    next_pid = 4000

    class FakeBackgroundProcess:
        def __init__(self, _command, _log_handle, **_options) -> None:
            nonlocal next_pid
            next_pid += 1
            self.pid = next_pid
            running_pids.add(self.pid)

        def poll(self):
            return None

    monkeypatch.setattr("workspace_manager.repositories._spawn_background_process", FakeBackgroundProcess)
    monkeypatch.setattr("workspace_manager.repositories._port_is_online", lambda _port: False)
    monkeypatch.setattr("workspace_manager.repositories._is_pid_running", lambda pid: pid in running_pids)
    monkeypatch.setattr("workspace_manager.repositories._pid_command_matches", lambda _pid, _cmd: True)
    monkeypatch.setattr("workspace_manager.repositories._terminate_pid", lambda pid, timeout=5.0: running_pids.discard(pid))
    monkeypatch.setattr("workspace_manager.repositories.time.sleep", lambda _seconds: None)

    started = start_servers(tmp_path, services)
    assert len(started) == 2
    assert "Started alpha (mcp) in background (pid=4001)" in started[0]

    # Starting an already tracked service is idempotent
    repeat = start_servers(tmp_path, [services[0]])
    assert "already running (pid=4001)" in repeat[0]

    status_lines = checkout_status(tmp_path, services)
    assert "process=running(pid=4001)" in status_lines[0]
    assert "process=running(pid=4002)" in status_lines[1]

    stopped_one = stop_servers(tmp_path, ["alpha"])
    assert stopped_one == ["Stopped alpha (pid=4001)"]
    assert 4001 not in running_pids
    assert 4002 in running_pids

    stopped_rest = stop_servers(tmp_path, None)
    assert stopped_rest == ["Stopped beta (pid=4002)"]
    assert not running_pids
    assert not (tmp_path / ".workspace_runtime" / "processes.json").exists()


def test_stale_process_record_is_pruned_automatically(monkeypatch, tmp_path: Path) -> None:
    service = ManagedService(name="stale-svc", url="https://example.com/stale.git", port=8305)
    checkout = tmp_path / "src" / service.name
    checkout.mkdir(parents=True)
    _git(checkout, "init", "--initial-branch=main")

    runtime_dir = tmp_path / ".workspace_runtime"
    runtime_dir.mkdir(parents=True)
    state_file = runtime_dir / "processes.json"
    state_file.write_text(
        json.dumps({"stale-svc": {"pid": 99999, "port": 8305, "command": ["mcp-server"]}}),
        encoding="utf-8",
    )

    monkeypatch.setattr("workspace_manager.repositories._is_pid_running", lambda _pid: False)
    monkeypatch.setattr("workspace_manager.repositories._port_is_online", lambda _port: False)

    lines = checkout_status(tmp_path, [service])
    assert "process=running" not in lines[0]
    assert not state_file.exists()


def test_cli_start_stop_and_filtered_status(monkeypatch, tmp_path: Path, capsys) -> None:
    (tmp_path / "repositories.toml").write_text(
        '[[services]]\nname="svc-a"\ntype="mcp"\nurl="https://example.com/a.git"\nport=8401\n'
        '[[services]]\nname="svc-b"\ntype="mcp"\nurl="https://example.com/b.git"\nport=8402\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "_workspace_root", lambda: tmp_path)
    monkeypatch.setattr(
        cli,
        "start_servers",
        lambda _root, selected: [f"started:{item.name}" for item in selected],
    )
    monkeypatch.setattr(
        cli,
        "stop_servers",
        lambda _root, names: [f"stopped:{name}" for name in (names or ["all"])],
    )

    monkeypatch.setattr(sys, "argv", ["mcp-workspace", "start", "svc-b"])
    cli.main()
    assert capsys.readouterr().out.strip() == "started:svc-b"

    monkeypatch.setattr(sys, "argv", ["mcp-workspace", "status", "svc-b"])
    cli.main()
    assert capsys.readouterr().out.strip() == "svc-b: not cloned"

    monkeypatch.setattr(sys, "argv", ["mcp-workspace", "stop", "svc-a"])
    cli.main()
    assert capsys.readouterr().out.strip() == "stopped:svc-a"

    monkeypatch.setattr(sys, "argv", ["mcp-workspace", "stop-all"])
    cli.main()
    assert capsys.readouterr().out.strip() == "stopped:all"