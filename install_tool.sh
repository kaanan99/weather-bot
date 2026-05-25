#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Locate the Claude Desktop config file
if [[ "$OSTYPE" == "darwin"* ]]; then
    CONFIG_FILE="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
elif [[ "$OSTYPE" == "msys"* || "$OSTYPE" == "cygwin"* || "$OSTYPE" == "win32"* ]]; then
    CONFIG_FILE="$APPDATA/Claude/claude_desktop_config.json"
else
    echo "Unsupported OS: $OSTYPE" >&2
    exit 1
fi

# Require jq for safe JSON manipulation
if ! command -v jq &>/dev/null; then
    echo "Error: jq is required but not installed." >&2
    echo "Install it with: brew install jq" >&2
    exit 1
fi

# Create the config file if it doesn't exist yet
mkdir -p "$(dirname "$CONFIG_FILE")"
if [[ ! -f "$CONFIG_FILE" ]]; then
    echo '{}' > "$CONFIG_FILE"
fi

# Merge the weather server entry into mcpServers, preserving all other config
UPDATED=$(jq \
    --arg cmd "$SCRIPT_DIR/server_start.sh" \
    '.mcpServers.weather = {"command": $cmd}' \
    "$CONFIG_FILE")

echo "$UPDATED" > "$CONFIG_FILE"

echo "Weather MCP server added to Claude Desktop config."
echo "Config: $CONFIG_FILE"
echo "Restart Claude Desktop to apply the change."
