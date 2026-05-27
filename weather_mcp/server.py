"""FastMCP server exposing a single get_weather tool backed by Open-Meteo."""

import logging
import sys

import httpx
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import ValidationError

from pathlib import Path

from weather_mcp import geocoding
from weather_mcp.mcp_data_models import WeatherRequest
from weather_mcp.weather_api import WeatherAPI

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)

weather_api = WeatherAPI(Path(__file__).parent / "codes.json")

mcp = FastMCP(
    name="weather",
    instructions=(
        "Use get_weather to retrieve current conditions, forecasts, or historical "
        "weather for any location. "
        "Parameters:\n"
        "- location (required): location in the format 'City Name, Country, State/Province'. "
        "Country and State/Province are optional. "
        "Examples: 'Dublin', 'Dublin, Ireland', 'Dublin, US, California'.\n"
        "- start_date (optional): a date string in YYYY-MM-DD format. "
        "Omit for current conditions; use today or a future date for a forecast; "
        "use a past date for historical data.\n"
        "- end_date (optional): a date string in YYYY-MM-DD format. "
        "Must be >= start_date. Defaults to start_date when omitted."
    ),
)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_weather(
    location: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Get weather for any location.

    Omit dates for current conditions. Use a future start_date for forecasts.
    Use a past start_date for historical data. end_date is optional (defaults
    to start_date).

    Args:
        location: Location in the format "City Name, Country, State/Province".
            Country and State/Province are optional. E.g. "Dublin",
            "Dublin, Ireland", "Dublin, US, California".
        start_date: Optional date in YYYY-MM-DD format. Omit for current
            conditions; use today or a future date for a forecast; use a past
            date for historical data.
        end_date: Optional date in YYYY-MM-DD format. Must be >= start_date.
            Defaults to start_date when omitted.

    Returns:
        For current conditions (no start_date), a dict with keys:
            temperature_c (float), humidity_percent (float),
            wind_speed_kmh (float), precipitation_mm (float),
            conditions (str), observed_at (str, ISO datetime),
            location (str, resolved display name).

        For forecast/historical (with start_date), a dict with keys:
            days (list of dicts, each with: date (str, YYYY-MM-DD),
            temp_high_c (float), temp_low_c (float),
            precipitation_mm (float), wind_speed_max_kmh (float),
            conditions (str)),
            location (str, resolved display name).

    Raises:
        ToolError: If the location is not found, the API is unreachable, or
            input validation fails.

    Example:
        # Current conditions
        await get_weather(location="Tokyo")

        # 3-day forecast
        await get_weather(
            location="Paris",
            start_date="2026-06-01",
            end_date="2026-06-03",
        )

        # Historical data
        await get_weather(
            location="New York",
            start_date="2025-01-01",
            end_date="2025-01-07",
        )
    """
    try:
        request = WeatherRequest(
            location=location, start_date=start_date, end_date=end_date
        )
        async with httpx.AsyncClient(timeout=10.0) as client:
            lat, lon, display_name = await geocoding.geocode(request.location, client)
            result = await weather_api.get_weather(
                lat,
                lon,
                client,
                start_date=request.start_date,
                end_date=request.end_date,
            )
        result["location"] = display_name
        return result
    except (ValueError, RuntimeError) as exc:
        raise ToolError(str(exc)) from exc
    except ValidationError as exc:
        logger.error("Validation error for request: %s", exc)
        raise ToolError(str(exc)) from exc