# Weather MCP Server

A Model Context Protocol (MCP) server that gives AI agents access to real-time, forecast, and historical weather data via [Open-Meteo](https://open-meteo.com/) — no API key required.

## What it does

Exposes a single `get_weather` tool that accepts a location name and optional date range, then routes to the correct Open-Meteo endpoint automatically:

| Dates provided | Data returned |
|---|---|
| None | Current conditions |
| Today or future | Daily forecast |
| Past | Historical daily data |

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

## Installation

```bash
git clone <repo-url>
cd weather-bot
uv sync
```

## Running tests

```bash
uv run pytest
```

## Integrating with Claude Desktop

Claude Desktop loads MCP servers from a config file on startup.

**1. Open the config file:**

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

**2. Add the weather server entry:**

```json
{
  "mcpServers": {
    "weather": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/weather-bot", "weather-mcp"]
    }
  }
}
```

Replace `/absolute/path/to/weather-bot` with the actual path where you cloned this repo.

**3. Restart Claude Desktop.**

The `get_weather` tool will now appear in Claude Desktop. You can ask things like:

- "What's the weather in Tokyo right now?"
- "Give me a 7-day forecast for Paris starting June 1st."
- "What was the weather in New York from January 1–7, 2024?"

## Project structure

```
weather_mcp/
├── server.py          # FastMCP app and tool definition
├── mcp_data_models.py # Pydantic request validation
├── geocoding.py       # Location string → lat/lon via Open-Meteo geocoding
├── weather.py         # Open-Meteo fetch + routing logic
└── codes.json         # WMO weather code descriptions
tests/
├── test_mcp_data_models.py
├── test_geocoding.py
└── test_weather.py
```
