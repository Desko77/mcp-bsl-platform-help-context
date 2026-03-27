#!/bin/bash
# Fix ownership of bind-mounted data directories.
# Docker Desktop on Windows mounts them as root:root,
# but the app runs as mcpuser and needs write access.

chown -R mcpuser:mcpuser /home/mcpuser/data 2>/dev/null || true
exec runuser -u mcpuser -- "$@"
