"""Weather data fetching and routing module using Open-Meteo APIs."""

import json
from datetime import date
from pathlib import Path

import httpx

class WeatherAPI:
    """Client for fetching weather data from Open-Meteo APIs.

    Loads WMO weather code descriptions from codes.json on initialization
    and routes requests to the correct endpoint based on the dates provided.
    """

    _FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
    _ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
    _CURRENT_PARAMS = "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation,weather_code"
    _DAILY_PARAMS = "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,weather_code"

    def __init__(self, codes_path: Path) -> None:
        """Initialize WeatherAPI and load WMO weather code descriptions.

        Args:
            codes_path: Path to the JSON file mapping WMO weather codes to descriptions.
        """
        self._codes: dict[str, str] = json.loads(codes_path.read_text())

    def _describe(self, code: int) -> str:
        """Return a plain-English description for a WMO weather code.

        Args:
            code: Integer WMO weather code.

        Returns:
            Human-readable description, or "Unknown (code {code})" if unrecognized.
        """
        return self._codes.get(str(code), f"Unknown (code {code})")

    async def get_weather(
        self,
        lat: float,
        lon: float,
        client: httpx.AsyncClient,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict:
        """Fetch weather data for a geographic coordinate using Open-Meteo.

        Routes to the current-conditions, forecast, or historical archive endpoint
        based on whether start_date is None, today/future, or in the past.

        Args:
            lat: Latitude of the location.
            lon: Longitude of the location.
            client: An active httpx async client.
            start_date: Optional start date string (YYYY-MM-DD). If None, fetches
                current conditions.
            end_date: Optional end date string (YYYY-MM-DD). Defaults to start_date
                when start_date is provided but end_date is not.

        Returns:
            For current conditions: a flat dict with keys temperature_c,
            humidity_percent, wind_speed_kmh, precipitation_mm, conditions,
            observed_at.

            For forecast/historical: a dict with a "days" list, where each item
            has date, temp_high_c, temp_low_c, precipitation_mm,
            wind_speed_max_kmh, conditions.

        Raises:
            RuntimeError: If the Open-Meteo API returns a non-2xx status code.
        """
        if start_date is None:
            return await self._fetch_current(lat, lon, client)

        effective_end = end_date if end_date is not None else start_date
        today = date.today().isoformat()

        if start_date < today:
            return await self._fetch_historical(lat, lon, client, start_date, effective_end)
        return await self._fetch_forecast(lat, lon, client, start_date, effective_end)

    async def _fetch_current(self, lat: float, lon: float, client: httpx.AsyncClient) -> dict:
        """Fetch current weather conditions from the forecast endpoint.

        Args:
            lat: Latitude.
            lon: Longitude.
            client: An active httpx async client.

        Returns:
            Flat dict with current weather data.

        Raises:
            RuntimeError: If the API returns a non-2xx status code.
        """
        url = self._FORECAST_URL
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": self._CURRENT_PARAMS,
        }
        response = await client.get(url, params=params)
        if response.status_code != 200:
            raise RuntimeError(f"Open-Meteo API error: HTTP {response.status_code}")

        data = response.json()
        current = data["current"]
        return {
            "temperature_c": current["temperature_2m"],
            "humidity_percent": current["relative_humidity_2m"],
            "wind_speed_kmh": current["wind_speed_10m"],
            "precipitation_mm": current["precipitation"],
            "conditions": self._describe(current["weather_code"]),
            "observed_at": current["time"],
        }

    async def _fetch_forecast(
        self,
        lat: float,
        lon: float,
        client: httpx.AsyncClient,
        start_date: str,
        end_date: str,
    ) -> dict:
        """Fetch daily forecast data from the forecast endpoint.

        Args:
            lat: Latitude.
            lon: Longitude.
            client: An active httpx async client.
            start_date: Start date string (YYYY-MM-DD).
            end_date: End date string (YYYY-MM-DD).

        Returns:
            Dict with a "days" list of daily weather records.

        Raises:
            RuntimeError: If the API returns a non-2xx status code.
        """
        url = self._FORECAST_URL
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": self._DAILY_PARAMS,
            "start_date": start_date,
            "end_date": end_date,
        }
        return await self._fetch_daily(client, url, params)

    async def _fetch_historical(
        self,
        lat: float,
        lon: float,
        client: httpx.AsyncClient,
        start_date: str,
        end_date: str,
    ) -> dict:
        """Fetch historical daily weather data from the archive endpoint.

        Args:
            lat: Latitude.
            lon: Longitude.
            client: An active httpx async client.
            start_date: Start date string (YYYY-MM-DD).
            end_date: End date string (YYYY-MM-DD).

        Returns:
            Dict with a "days" list of daily weather records.

        Raises:
            RuntimeError: If the API returns a non-2xx status code.
        """
        url = self._ARCHIVE_URL
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": self._DAILY_PARAMS,
            "start_date": start_date,
            "end_date": end_date,
        }
        return await self._fetch_daily(client, url, params)

    async def _fetch_daily(self, client: httpx.AsyncClient, url: str, params: dict) -> dict:
        """Execute a daily-params Open-Meteo request and shape the response.

        Args:
            client: An active httpx async client.
            url: The Open-Meteo endpoint URL.
            params: Query parameters for the request.

        Returns:
            Dict with a "days" list of daily weather records.

        Raises:
            RuntimeError: If the API returns a non-2xx status code.
        """
        response = await client.get(url, params=params)
        if response.status_code != 200:
            raise RuntimeError(f"Open-Meteo API error: HTTP {response.status_code}")

        data = response.json()
        daily = data["daily"]
        days = []
        for i, day_date in enumerate(daily["time"]):
            days.append({
                "date": day_date,
                "temp_high_c": daily["temperature_2m_max"][i],
                "temp_low_c": daily["temperature_2m_min"][i],
                "precipitation_mm": daily["precipitation_sum"][i],
                "wind_speed_max_kmh": daily["wind_speed_10m_max"][i],
                "conditions": self._describe(daily["weather_code"][i]),
            })
        return {"days": days}
