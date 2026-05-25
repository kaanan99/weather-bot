# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## User Interactions
Give suggestions to the user. If the user says something contradictory, clarify with the user. If not enough information is given to the ask the user for additional context.

## Commands

```bash
uv sync --all-groups          # install deps + dev deps
uv run pytest                 # run all tests
uv run pytest tests/test_weather.py::test_name  # run a single test
uv run weather-mcp            # start the MCP server (blocks on stdio)
```

## Architecture

This is a Python MCP server (`FastMCP`) that exposes a single `get_weather` tool to AI agents. It uses Open-Meteo APIs — no API key required.

### Request flow

```
agent call → server.py (WeatherRequest validation) → geocoding.py (location → lat/lon) → weather.py (Open-Meteo fetch) → dict response
```

### Key files

- **`weather_mcp/server.py`** — FastMCP app; defines the single `get_weather` tool; catches `ValueError`/`RuntimeError`/`ValidationError` and re-raises as `ToolError`
- **`weather_mcp/mcp_data_models.py`** — Pydantic `WeatherRequest` model; validates `location` (non-empty), `start_date`/`end_date` (YYYY-MM-DD format), and that `start_date <= end_date`
- **`weather_mcp/geocoding.py`** — `async def geocode(location, client)` → `(lat, lon, display_name)` via Open-Meteo geocoding API
- **`weather_mcp/weather.py`** — `async def get_weather(lat, lon, client, start_date, end_date)` with routing logic; also owns `_describe()` and loads `codes.json` at import time
- **`weather_mcp/codes.json`** — WMO weather code → plain-English description map (string keys)

### Routing logic in `weather.py`

| `start_date` | Endpoint |
|---|---|
| `None` | `api.open-meteo.com/v1/forecast` with `current=` params |
| today or future | `api.open-meteo.com/v1/forecast` with `daily=` params |
| past | `archive-api.open-meteo.com/v1/archive` with `daily=` params |

Note: historical data uses a **different subdomain** (`archive-api`, not `api`).

### Testing

Tests use `respx` to mock `httpx` — no real API calls are made. Each test file covers one module: `test_mcp_data_models.py` (Pydantic validators), `test_geocoding.py` (geocode function), `test_weather.py` (routing + response shaping).

### MCP registration

The server is registered in `.claude/settings.json` so Claude Code can invoke it directly in this project. It runs via `uv run weather-mcp` over stdio transport.

## Python conventions

- Add type hints to all function signatures (parameters and return types).
  Use modern syntax (e.g. `list[str]`, `X | None` instead of `Optional[X]`).
- Write a docstring for every function, method, class, and module.
- Use **Google-style** docstrings, matching the format below.

Docstring format example:

    def fetch_user(user_id: int, include_inactive: bool = False) -> dict:
        """Retrieve a user record by ID.

        Args:
            user_id: The unique identifier of the user.
            include_inactive: Whether to include deactivated accounts.
                Defaults to False.

        Returns:
            A dictionary containing the user's profile data.

        Raises:
            ValueError: If no user matches the given ID.
        """