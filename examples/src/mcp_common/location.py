import json
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def resolve_current_location() -> dict[str, Any]:
    request = Request(
        "https://ipapi.co/json/",
        headers={"User-Agent": "multi-mcp-examples/0.1"},
    )

    try:
        with urlopen(request, timeout=8) as response:
            data = json.load(response)
    except (TimeoutError, URLError, json.JSONDecodeError) as error:
        raise RuntimeError("Unable to resolve the server's public-IP location") from error

    if data.get("error"):
        raise RuntimeError("The public-IP location provider returned an error")

    city = data.get("city")
    region = data.get("region")
    country = data.get("country_name")
    location = ", ".join(part for part in (city, region, country) if part)
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    timezone = data.get("timezone")

    if not location or latitude is None or longitude is None or not timezone:
        raise RuntimeError("The public-IP location provider returned incomplete location data")

    return {
        "location": location,
        "latitude": float(latitude),
        "longitude": float(longitude),
        "timezone": timezone,
        "source": "ipapi.co public-IP geolocation",
    }


def resolve_named_location(location: str) -> dict[str, Any]:
    query = urlencode({"name": location, "count": 1, "language": "en", "format": "json"})
    request = Request(
        f"https://geocoding-api.open-meteo.com/v1/search?{query}",
        headers={"User-Agent": "multi-mcp-examples/0.1"},
    )

    try:
        with urlopen(request, timeout=8) as response:
            data = json.load(response)
    except (TimeoutError, URLError, json.JSONDecodeError) as error:
        raise RuntimeError("Unable to resolve the requested place") from error

    results = data.get("results") or []
    if not results:
        raise ValueError(f"Could not find a timezone for location: {location}")

    result = results[0]
    timezone = result.get("timezone")
    if not timezone:
        raise ValueError(f"Could not determine a timezone for location: {location}")

    parts = (result.get("name"), result.get("admin1"), result.get("country"))
    return {
        "location": ", ".join(part for part in parts if part),
        "latitude": float(result["latitude"]),
        "longitude": float(result["longitude"]),
        "timezone": timezone,
        "source": "Open-Meteo Geocoding API",
    }