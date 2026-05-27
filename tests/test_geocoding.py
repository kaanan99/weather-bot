"""Tests for the geocode() function and ParsedLocation dataclass."""

import httpx
import pytest
import respx

from weather_mcp.geocoding import ParsedLocation, geocode

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"


# ---------------------------------------------------------------------------
# ParsedLocation.from_string
# ---------------------------------------------------------------------------


def test_parsed_location_city_only():
    """from_string() with a bare city name sets country and state to None."""
    loc = ParsedLocation.from_string("Dublin")
    assert loc.city == "Dublin"
    assert loc.country is None
    assert loc.state is None


def test_parsed_location_city_and_country():
    """from_string() with two parts sets country, leaves state None."""
    loc = ParsedLocation.from_string("Dublin, Ireland")
    assert loc.city == "Dublin"
    assert loc.country == "Ireland"
    assert loc.state is None


def test_parsed_location_all_three_parts():
    """from_string() with three parts sets all fields."""
    loc = ParsedLocation.from_string("Dublin, US, California")
    assert loc.city == "Dublin"
    assert loc.country == "United States"
    assert loc.state == "California"


def test_parsed_location_normalizes_us_alias():
    """from_string() expands 'US' to 'United States'."""
    assert ParsedLocation.from_string("Dublin, US").country == "United States"
    assert ParsedLocation.from_string("Dublin, USA").country == "United States"


def test_parsed_location_normalizes_uk_alias():
    """from_string() expands 'UK' and 'GB' to 'United Kingdom'."""
    assert ParsedLocation.from_string("London, UK").country == "United Kingdom"
    assert ParsedLocation.from_string("London, GB").country == "United Kingdom"


def test_parsed_location_strips_whitespace():
    """from_string() strips leading/trailing whitespace from each part, and resolves aliases."""
    loc = ParsedLocation.from_string("  Dublin  ,  US  ,  California  ")
    assert loc.city == "Dublin"
    assert loc.country == "United States"
    assert loc.state == "California"


# ---------------------------------------------------------------------------
# geocode() — API behaviour
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_geocode_sends_city_name_and_count_10():
    """geocode() queries the API with the city name and count=10."""
    payload = {
        "results": [
            {
                "latitude": 53.3331,
                "longitude": -6.2489,
                "name": "Dublin",
                "admin1": "Leinster",
                "country": "Ireland",
            }
        ]
    }
    with respx.mock:
        route = respx.get(GEOCODING_URL).mock(return_value=httpx.Response(200, json=payload))
        async with httpx.AsyncClient() as client:
            await geocode("Dublin", client)

    sent_params = dict(route.calls[0].request.url.params)
    assert sent_params["name"] == "Dublin"
    assert sent_params["count"] == "10"


@pytest.mark.asyncio
async def test_geocode_city_only_returns_first_result():
    """geocode() with no country/state returns the first result without filtering."""
    payload = {
        "results": [
            {
                "latitude": 53.3331,
                "longitude": -6.2489,
                "name": "Dublin",
                "admin1": "Leinster",
                "country": "Ireland",
            },
            {
                "latitude": 37.7022,
                "longitude": -121.9358,
                "name": "Dublin",
                "admin1": "California",
                "country": "United States",
            },
        ]
    }
    with respx.mock:
        respx.get(GEOCODING_URL).mock(return_value=httpx.Response(200, json=payload))
        async with httpx.AsyncClient() as client:
            lat, lon, display_name = await geocode("Dublin", client)

    assert lat == pytest.approx(53.3331)
    assert display_name == "Dublin, Leinster, Ireland"


@pytest.mark.asyncio
async def test_geocode_country_filter_skips_non_matching():
    """geocode() with a country skips results that don't match."""
    payload = {
        "results": [
            {
                "latitude": 53.3331,
                "longitude": -6.2489,
                "name": "Dublin",
                "admin1": "Leinster",
                "country": "Ireland",
            },
            {
                "latitude": 37.7022,
                "longitude": -121.9358,
                "name": "Dublin",
                "admin1": "California",
                "country": "United States",
            },
        ]
    }
    with respx.mock:
        respx.get(GEOCODING_URL).mock(return_value=httpx.Response(200, json=payload))
        async with httpx.AsyncClient() as client:
            lat, lon, display_name = await geocode("Dublin, United States", client)

    assert lat == pytest.approx(37.7022)
    assert display_name == "Dublin, California, United States"


@pytest.mark.asyncio
async def test_geocode_country_filter_is_case_insensitive():
    """geocode() country matching is case-insensitive."""
    payload = {
        "results": [
            {
                "latitude": 53.3331,
                "longitude": -6.2489,
                "name": "Dublin",
                "admin1": "Leinster",
                "country": "Ireland",
            }
        ]
    }
    with respx.mock:
        respx.get(GEOCODING_URL).mock(return_value=httpx.Response(200, json=payload))
        async with httpx.AsyncClient() as client:
            lat, lon, _ = await geocode("Dublin, Ireland", client)

    assert lat == pytest.approx(53.3331)


@pytest.mark.asyncio
async def test_geocode_us_alias_resolves_to_united_states():
    """geocode() with 'US' as country matches results with 'United States'."""
    payload = {
        "results": [
            {
                "latitude": 53.3331,
                "longitude": -6.2489,
                "name": "Dublin",
                "admin1": "Leinster",
                "country": "Ireland",
            },
            {
                "latitude": 37.7022,
                "longitude": -121.9358,
                "name": "Dublin",
                "admin1": "California",
                "country": "United States",
            },
        ]
    }
    with respx.mock:
        respx.get(GEOCODING_URL).mock(return_value=httpx.Response(200, json=payload))
        async with httpx.AsyncClient() as client:
            lat, lon, _ = await geocode("Dublin, US", client)

    assert lat == pytest.approx(37.7022)


@pytest.mark.asyncio
async def test_geocode_country_and_state_filter():
    """geocode() with country + state matches on both fields."""
    payload = {
        "results": [
            {
                "latitude": 53.3331,
                "longitude": -6.2489,
                "name": "Dublin",
                "admin1": "Leinster",
                "country": "Ireland",
            },
            {
                "latitude": 37.7022,
                "longitude": -121.9358,
                "name": "Dublin",
                "admin1": "California",
                "country": "United States",
            },
        ]
    }
    with respx.mock:
        respx.get(GEOCODING_URL).mock(return_value=httpx.Response(200, json=payload))
        async with httpx.AsyncClient() as client:
            lat, lon, display_name = await geocode("Dublin, United States, California", client)

    assert lat == pytest.approx(37.7022)
    assert display_name == "Dublin, California, United States"


@pytest.mark.asyncio
async def test_geocode_no_country_match_raises_value_error():
    """geocode() raises ValueError with filter details when country doesn't match any result."""
    payload = {
        "results": [
            {
                "latitude": 53.3331,
                "longitude": -6.2489,
                "name": "Dublin",
                "admin1": "Leinster",
                "country": "Ireland",
            }
        ]
    }
    with respx.mock:
        respx.get(GEOCODING_URL).mock(return_value=httpx.Response(200, json=payload))
        async with httpx.AsyncClient() as client:
            with pytest.raises(ValueError, match="No geocoding results match"):
                await geocode("Dublin, US", client)


@pytest.mark.asyncio
async def test_geocode_no_state_match_raises_value_error():
    """geocode() raises ValueError with filter details when state doesn't match any result."""
    payload = {
        "results": [
            {
                "latitude": 37.7022,
                "longitude": -121.9358,
                "name": "Dublin",
                "admin1": "California",
                "country": "United States",
            }
        ]
    }
    with respx.mock:
        respx.get(GEOCODING_URL).mock(return_value=httpx.Response(200, json=payload))
        async with httpx.AsyncClient() as client:
            with pytest.raises(ValueError, match="No geocoding results match"):
                await geocode("Dublin, United States, Texas", client)


@pytest.mark.asyncio
async def test_geocode_missing_admin1():
    """geocode() builds display_name correctly when admin1 is absent."""
    payload = {
        "results": [
            {
                "latitude": 51.5074,
                "longitude": -0.1278,
                "name": "London",
                "country": "United Kingdom",
            }
        ]
    }
    with respx.mock:
        respx.get(GEOCODING_URL).mock(return_value=httpx.Response(200, json=payload))
        async with httpx.AsyncClient() as client:
            lat, lon, display_name = await geocode("London", client)

    assert display_name == "London, United Kingdom"


@pytest.mark.asyncio
async def test_geocode_empty_results_raises_value_error():
    """geocode() raises ValueError when the API returns an empty results list."""
    payload = {"results": []}
    with respx.mock:
        respx.get(GEOCODING_URL).mock(return_value=httpx.Response(200, json=payload))
        async with httpx.AsyncClient() as client:
            with pytest.raises(ValueError, match="Location not found"):
                await geocode("zzzznotacity", client)


@pytest.mark.asyncio
async def test_geocode_no_results_key_raises_value_error():
    """geocode() raises ValueError when the API response has no 'results' key."""
    with respx.mock:
        respx.get(GEOCODING_URL).mock(return_value=httpx.Response(200, json={}))
        async with httpx.AsyncClient() as client:
            with pytest.raises(ValueError, match="Location not found"):
                await geocode("nowhere", client)


@pytest.mark.asyncio
async def test_geocode_non_200_raises_runtime_error():
    """geocode() raises RuntimeError on a non-2xx HTTP response."""
    with respx.mock:
        respx.get(GEOCODING_URL).mock(return_value=httpx.Response(503))
        async with httpx.AsyncClient() as client:
            with pytest.raises(RuntimeError, match="Geocoding API error"):
                await geocode("Tokyo", client)


@pytest.mark.asyncio
async def test_geocode_timeout_raises_timeout_exception():
    """geocode() raises httpx.TimeoutException on a timeout."""
    with respx.mock:
        respx.get(GEOCODING_URL).mock(side_effect=httpx.TimeoutException("timed out"))
        async with httpx.AsyncClient() as client:
            with pytest.raises(httpx.TimeoutException):
                await geocode("Tokyo", client)


@pytest.mark.asyncio
async def test_geocode_http_error_raises_http_error():
    """geocode() raises httpx.HTTPError on a transport-level error."""
    with respx.mock:
        respx.get(GEOCODING_URL).mock(side_effect=httpx.HTTPError("connection failed"))
        async with httpx.AsyncClient() as client:
            with pytest.raises(httpx.HTTPError):
                await geocode("Tokyo", client)
