"""Tests for the geocode() function."""

import httpx
import pytest
import respx

from weather_mcp.geocoding import geocode

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"


@pytest.mark.asyncio
async def test_successful_geocode():
    """geocode() returns correct (lat, lon, display_name) on a successful response."""
    payload = {
        "results": [
            {
                "latitude": 35.6895,
                "longitude": 139.6917,
                "name": "Tokyo",
                "admin1": "Tokyo",
                "country": "Japan",
            }
        ]
    }
    with respx.mock:
        respx.get(GEOCODING_URL).mock(return_value=httpx.Response(200, json=payload))
        async with httpx.AsyncClient() as client:
            lat, lon, display_name = await geocode("Tokyo", client)

    assert lat == pytest.approx(35.6895)
    assert lon == pytest.approx(139.6917)
    assert display_name == "Tokyo, Tokyo, Japan"


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
