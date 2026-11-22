from mcp_server_template.server import hello


def test_hello_returns_a_greeting() -> None:
    assert hello("Ada") == "Hello, Ada!"