"""Geocoding module for converting location strings to coordinates."""

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

# Common country codes/abbreviations mapped to the full name returned by Open-Meteo.
_COUNTRY_ALIASES: dict[str, str] = {
    "US": "United States",
    "USA": "United States",
    "UK": "United Kingdom",
    "GB": "United Kingdom",
}


@dataclass
class ParsedLocation:
    """A location string parsed into its component parts.

    Attributes:
        city: The city name.
        country: Optional country name or code.
        state: Optional state or province name.
    """

    city: str
    country: str | None
    state: str | None

    @classmethod
    def from_string(cls, location: str) -> "ParsedLocation":
        """Parse a comma-separated location string into components.

        Accepts the following formats:
            - ``"Dublin"``
            - ``"Dublin, Ireland"``
            - ``"Dublin, US, California"``

        Args:
            location: A comma-separated location string with city, optional
                country, and optional state/province.

        Returns:
            A ParsedLocation with city, country, and state fields.
        """
        parts = [p.strip() for p in location.split(",")]
        raw_country = parts[1] if len(parts) > 1 else None
        country = (
            _COUNTRY_ALIASES.get(raw_country.upper(), raw_country)
            if raw_country
            else None
        )
        return cls(
            city=parts[0],
            country=country,
            state=parts[2] if len(parts) > 2 else None,
        )


async def geocode(location: str, client: httpx.AsyncClient) -> tuple[float, float, str]:
    """Convert a location string to latitude, longitude, and display name.

    Accepts location in the format ``"City"`, ``"City, Country"``, or
    ``"City, Country, State/Province"``. Queries the Open-Meteo geocoding API
    using the city name, then filters the results by country and state if
    provided.

    Args:
        location: A comma-separated location string, e.g. ``"Dublin"``,
            ``"Dublin, Ireland"``, or ``"Dublin, US, California"``.
        client: An active httpx async client to use for the request.

    Returns:
        A tuple of (latitude, longitude, display_name) where display_name is
        formatted as "City, Region, Country".

    Raises:
        ValueError: If no results are found, or if no results match the
            provided country/state filters.
        httpx.TimeoutException: If the geocoding request times out.
        httpx.HTTPError: If a transport-level HTTP error occurs.
        RuntimeError: If the geocoding API returns a non-2xx status code.
    """
    parsed = ParsedLocation.from_string(location)

    logger.info(
        "Geocoding %r — filtering for city=%r country=%r state=%r",
        location,
        parsed.city,
        parsed.country,
        parsed.state,
    )

    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": parsed.city, "count": 10, "language": "en", "format": "json"}

    try:
        response = await client.get(url, params=params)
    except httpx.TimeoutException as exc:
        logger.error("Geocoding request timed out for location %r: %s", location, exc)
        raise
    except httpx.HTTPError as exc:
        logger.error("Geocoding HTTP error for location %r: %s", location, exc)
        raise

    if response.status_code != 200:
        logger.error(
            "Geocoding API returned HTTP %d for location %r",
            response.status_code,
            location,
        )
        raise RuntimeError(
            f"Geocoding API error: HTTP {response.status_code} for location '{location}'"
        )

    data = response.json()
    results = data.get("results", [])
    if not results:
        raise ValueError(f"Location not found: '{location}'")

    result = _filter_results(results, parsed)

    logger.info(
        "Returning result: name=%r admin1=%r country=%r",
        result.get("name"),
        result.get("admin1"),
        result.get("country"),
    )

    lat: float = result["latitude"]
    lon: float = result["longitude"]
    parts = [result.get("name"), result.get("admin1"), result.get("country")]
    display_name = ", ".join(p for p in parts if p)

    return lat, lon, display_name


def _filter_results(results: list[dict], parsed: ParsedLocation) -> dict:
    """Select the best matching result from the geocoding API response.

    Args:
        results: List of result dicts from the Open-Meteo geocoding API.
        parsed: The parsed location components to filter by.

    Returns:
        The first result that matches the given filters.

    Raises:
        ValueError: If no result matches the provided country/state filters.
    """
    if not parsed.country and not parsed.state:
        return results[0]

    for result in results:
        country_match = (
            parsed.country is None
            or (result.get("country") or "").casefold() == parsed.country.casefold()
        )
        state_match = (
            parsed.state is None
            or (result.get("admin1") or "").casefold() == parsed.state.casefold()
        )
        if country_match and state_match:
            return result

    raise ValueError(
        f"No geocoding results match the given filters — "
        f"city={parsed.city!r}, country={parsed.country!r}, state={parsed.state!r}"
    )
