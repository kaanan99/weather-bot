#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

uv sync --directory "$SCRIPT_DIR"
exec uv run --directory "$SCRIPT_DIR" weather-mcp
