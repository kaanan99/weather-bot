"""FastMCP server exposing a single get_weather tool backed by Open-Meteo."""

import logging
import sys

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import ValidationError

from pathlib import Path

from weather_mcp import geocoding
from weather_mcp.mcp_data_models import WeatherRequest
from weather_mcp.weather_api import WeatherAPI

logger = logging.getLogger(__name__)

weather_api = WeatherAPI(Path(__file__).parent / "codes.json")

mcp = FastMCP(
    name="weather",
    instructions=(
        "Use get_weather to retrieve current conditions, forecasts, or historical "
        "weather for any location. "
        "The tool accepts a WeatherRequest with the following fields:\n"
        "- location (required): a place name string, e.g. 'Tokyo' or 'Paris, France'.\n"
        "- start_date (optional): a date string in YYYY-MM-DD format. "
        "Omit for current conditions; use today or a future date for a forecast; "
        "use a past date for historical data.\n"
        "- end_date (optional): a date string in YYYY-MM-DD format. "
        "Must be >= start_date. Defaults to start_date when omitted."
    ),
)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_weather(request: WeatherRequest) -> dict:
    """Get weather for any location.

    Omit dates for current conditions. Use a future start_date for forecasts.
    Use a past start_date for historical data. end_date is optional (defaults
    to start_date).

    Args:
        request: Validated weather request containing location and optional dates.

    Returns:
        For current conditions: a flat dict with temperature_c, humidity_percent,
        wind_speed_kmh, precipitation_mm, conditions, and observed_at.

        For forecast/historical: a dict with a "days" list where each entry has
        date, temp_high_c, temp_low_c, precipitation_mm, wind_speed_max_kmh,
        and conditions.

    Raises:
        ToolError: If the location is not found, the API is unreachable, or
            input validation fails.
    """
    try:
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


def main() -> None:
    """Run the weather MCP server over stdio transport."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    logger.info("Weather MCP server starting")
    try:
        mcp.run()
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("Weather MCP server stopped")
