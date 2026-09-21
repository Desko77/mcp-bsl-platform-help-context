#!/bin/bash
# Fix ownership of bind-mounted data directories.
# Docker Desktop on Windows mounts them as root:root,
# but the app runs as mcpuser and needs write access.

chown -R mcpuser:mcpuser /home/mcpuser/data 2>/dev/null || true

# A YAML config mounted at /home/mcpuser/config.yml is passed to the server
# unless a config is already given (--config/-c argument or MCP_BSL_CONFIG)
CONFIG_FILE="/home/mcpuser/config.yml"
has_config_arg=false
for arg in "$@"; do
    case "$arg" in
        -c|--config|--config=*) has_config_arg=true ;;
    esac
done
if [ -f "$CONFIG_FILE" ] && [ "$1" = "mcp-bsl-context" ] && [ -z "$MCP_BSL_CONFIG" ] && [ "$has_config_arg" = false ]; then
    set -- "$@" --config "$CONFIG_FILE"
fi

exec runuser -u mcpuser -- "$@"
