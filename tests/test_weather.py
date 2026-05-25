"""Tests for WeatherAPI routing and _describe()."""

from datetime import date
from pathlib import Path

import httpx
import pytest
import respx

from weather_mcp.weather_api import WeatherAPI

CODES_PATH = Path(__file__).parent.parent / "weather_mcp" / "codes.json"

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

CURRENT_PAYLOAD = {
    "current": {
        "time": "2026-05-24T12:00",
        "temperature_2m": 22.5,
        "relative_humidity_2m": 60,
        "wind_speed_10m": 15.0,
        "precipitation": 0.0,
        "weather_code": 1,
    }
}

DAILY_PAYLOAD = {
    "daily": {
        "time": ["2026-06-01", "2026-06-02"],
        "temperature_2m_max": [25.0, 27.0],
        "temperature_2m_min": [15.0, 16.0],
        "precipitation_sum": [0.0, 2.5],
        "wind_speed_10m_max": [20.0, 18.0],
        "weather_code": [0, 61],
    }
}


@pytest.fixture
def api() -> WeatherAPI:
    """Return a WeatherAPI instance for testing."""
    return WeatherAPI(CODES_PATH)


# --- _describe() tests ---

def test_describe_known_code(api: WeatherAPI):
    """_describe() returns correct description for a known WMO code."""
    assert api._describe(0) == "Clear sky"


def test_describe_thunderstorm_code(api: WeatherAPI):
    """_describe() returns correct description for code 95."""
    assert api._describe(95) == "Thunderstorm"


def test_describe_unknown_code(api: WeatherAPI):
    """_describe() returns fallback string for unrecognized codes."""
    assert api._describe(999) == "Unknown (code 999)"


# --- get_weather() routing tests ---

@pytest.mark.asyncio
async def test_no_dates_calls_current_endpoint(api: WeatherAPI):
    """get_weather() without dates hits the forecast endpoint with current= params."""
    with respx.mock:
        route = respx.get(FORECAST_URL).mock(
            return_value=httpx.Response(200, json=CURRENT_PAYLOAD)
        )
        async with httpx.AsyncClient() as client:
            result = await api.get_weather(35.69, 139.69, client)

    assert route.called
    assert "temperature_c" in result
    assert result["temperature_c"] == 22.5
    assert result["humidity_percent"] == 60
    assert result["conditions"] == "Mainly clear"
    assert result["observed_at"] == "2026-05-24T12:00"
    request_url = str(route.calls[0].request.url)
    assert "current=" in request_url


@pytest.mark.asyncio
async def test_future_start_date_calls_forecast_endpoint(api: WeatherAPI):
    """get_weather() with a future start_date hits the forecast endpoint with daily= params."""
    with respx.mock:
        route = respx.get(FORECAST_URL).mock(
            return_value=httpx.Response(200, json=DAILY_PAYLOAD)
        )
        async with httpx.AsyncClient() as client:
            result = await api.get_weather(48.85, 2.35, client, start_date="2026-06-01", end_date="2026-06-02")

    assert route.called
    assert "days" in result
    assert len(result["days"]) == 2
    assert result["days"][0]["date"] == "2026-06-01"
    assert result["days"][0]["temp_high_c"] == 25.0
    assert result["days"][0]["conditions"] == "Clear sky"
    request_url = str(route.calls[0].request.url)
    assert "daily=" in request_url


@pytest.mark.asyncio
async def test_past_start_date_calls_archive_endpoint(api: WeatherAPI):
    """get_weather() with a past start_date hits the archive endpoint."""
    archive_payload = {
        "daily": {
            "time": ["2024-01-01"],
            "temperature_2m_max": [5.0],
            "temperature_2m_min": [-2.0],
            "precipitation_sum": [1.0],
            "wind_speed_10m_max": [30.0],
            "weather_code": [3],
        }
    }
    with respx.mock:
        route = respx.get(ARCHIVE_URL).mock(
            return_value=httpx.Response(200, json=archive_payload)
        )
        async with httpx.AsyncClient() as client:
            result = await api.get_weather(40.71, -74.01, client, start_date="2024-01-01", end_date="2024-01-01")

    assert route.called
    assert "days" in result
    assert result["days"][0]["conditions"] == "Overcast"


@pytest.mark.asyncio
async def test_end_date_defaults_to_start_date(api: WeatherAPI):
    """get_weather() uses start_date as end_date when end_date is omitted."""
    with respx.mock:
        route = respx.get(FORECAST_URL).mock(
            return_value=httpx.Response(200, json=DAILY_PAYLOAD)
        )
        async with httpx.AsyncClient() as client:
            await api.get_weather(48.85, 2.35, client, start_date="2026-06-01")

    request_url = str(route.calls[0].request.url)
    assert "start_date=2026-06-01" in request_url
    assert "end_date=2026-06-01" in request_url


@pytest.mark.asyncio
async def test_today_start_date_calls_forecast_endpoint(api: WeatherAPI):
    """get_weather() with today as start_date hits the forecast endpoint, not the archive."""
    today = date.today().isoformat()
    with respx.mock:
        route = respx.get(FORECAST_URL).mock(
            return_value=httpx.Response(200, json=DAILY_PAYLOAD)
        )
        async with httpx.AsyncClient() as client:
            await api.get_weather(35.69, 139.69, client, start_date=today)

    assert route.called


@pytest.mark.asyncio
async def test_api_error_raises_runtime_error(api: WeatherAPI):
    """get_weather() raises RuntimeError on a non-2xx API response."""
    with respx.mock:
        respx.get(FORECAST_URL).mock(return_value=httpx.Response(500))
        async with httpx.AsyncClient() as client:
            with pytest.raises(RuntimeError, match="Open-Meteo API error"):
                await api.get_weather(35.69, 139.69, client)


def test_init_missing_codes_file_raises():
    """WeatherAPI raises FileNotFoundError when codes_path does not exist."""
    with pytest.raises(FileNotFoundError):
        WeatherAPI(Path("/nonexistent/codes.json"))


@pytest.mark.asyncio
async def test_current_response_missing_key_raises(api: WeatherAPI):
    """get_weather() raises KeyError when the current response is malformed."""
    with respx.mock:
        respx.get(FORECAST_URL).mock(return_value=httpx.Response(200, json={}))
        async with httpx.AsyncClient() as client:
            with pytest.raises(KeyError):
                await api.get_weather(35.69, 139.69, client)


@pytest.mark.asyncio
async def test_daily_mismatched_list_lengths_raises(api: WeatherAPI):
    """get_weather() raises IndexError when daily lists have mismatched lengths."""
    bad_payload = {
        "daily": {
            "time": ["2026-06-01", "2026-06-02"],
            "temperature_2m_max": [25.0, 27.0],
            "temperature_2m_min": [15.0, 16.0],
            "precipitation_sum": [0.0, 2.5],
            "wind_speed_10m_max": [20.0, 18.0],
            "weather_code": [0],  # one entry short
        }
    }
    with respx.mock:
        respx.get(FORECAST_URL).mock(return_value=httpx.Response(200, json=bad_payload))
        async with httpx.AsyncClient() as client:
            with pytest.raises(IndexError):
                await api.get_weather(35.69, 139.69, client, start_date="2026-06-01", end_date="2026-06-02")
