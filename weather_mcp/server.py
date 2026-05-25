"""FastMCP server exposing a single get_weather tool backed by Open-Meteo."""

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.utilities.types import ToolAnnotations
from mcp.types import ToolError
from pydantic import ValidationError

from weather_mcp import geocoding, weather
from weather_mcp.mcp_data_models import WeatherRequest

mcp = FastMCP(
    name="weather",
    instructions=(
        "Use get_weather to retrieve current conditions, forecasts, or historical "
        "weather for any location. Omit dates for current conditions; provide a "
        "future start_date for a forecast; provide a past start_date for historical data."
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
            result = await weather.get_weather(
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
        raise ToolError(str(exc)) from exc


def main() -> None:
    """Run the weather MCP server over stdio transport."""
    mcp.run()
