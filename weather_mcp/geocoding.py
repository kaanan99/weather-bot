"""Geocoding module for converting location strings to coordinates."""

import httpx


async def geocode(location: str, client: httpx.AsyncClient) -> tuple[float, float, str]:
    """Convert a location name to latitude, longitude, and display name.

    Args:
        location: Human-readable location string (e.g. "Tokyo", "Paris, France").
        client: An active httpx async client to use for the request.

    Returns:
        A tuple of (latitude, longitude, display_name) where display_name is
        formatted as "City, Region, Country".

    Raises:
        ValueError: If no results are found for the given location.
        RuntimeError: If the geocoding API returns a non-2xx status code.
    """
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": location, "count": 1, "language": "en", "format": "json"}

    response = await client.get(url, params=params)
    if response.status_code != 200:
        raise RuntimeError(
            f"Geocoding API error: HTTP {response.status_code} for location '{location}'"
        )

    data = response.json()
    results = data.get("results", [])
    if not results:
        raise ValueError(f"Location not found: '{location}'")

    result = results[0]
    lat: float = result["latitude"]
    lon: float = result["longitude"]

    parts = [result.get("name"), result.get("admin1"), result.get("country")]
    display_name = ", ".join(p for p in parts if p)

    return lat, lon, display_name
