from zoneinfo import ZoneInfo

from gambling_server.server import roll_a_dice
from time_server.server import get_current_time


def test_roll_a_dice_returns_a_six_sided_value() -> None:
    assert roll_a_dice() in range(1, 7)


def test_get_current_time_accepts_an_iana_timezone() -> None:
    result = get_current_time("Asia/Tokyo")

    assert result["timezone"] == "Asia/Tokyo"
    assert result["location"] == "Asia/Tokyo"
    assert ZoneInfo("Asia/Tokyo")


def test_get_current_time_resolves_a_place_name(monkeypatch) -> None:
    from time_server import server

    monkeypatch.setattr(
        server,
        "resolve_named_location",
        lambda location: {"timezone": "Europe/Paris"},
    )

    result = server.get_current_time("Paris")

    assert result["timezone"] == "Europe/Paris"
    assert result["location"] == "Paris"