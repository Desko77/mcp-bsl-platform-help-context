"""CLI entry point for the MCP BSL platform context server."""

from __future__ import annotations

import logging
import sys


def main() -> None:
    try:
        import click
    except ImportError:
        print("Error: 'click' package is required. Install with: pip install click", file=sys.stderr)
        sys.exit(1)

    @click.command()
    @click.option(
        "--platform-path", "-p",
        required=False,
        default=None,
        envvar="MCP_BSL_PLATFORM_PATH",
        help="Path to 1C platform installation directory (env: MCP_BSL_PLATFORM_PATH)",
    )
    @click.option(
        "--mode", "-m",
        type=click.Choice(["stdio", "sse"]),
        default="stdio",
        envvar="MCP_BSL_MODE",
        help="Transport mode: stdio or sse (env: MCP_BSL_MODE)",
    )
    @click.option(
        "--port",
        type=int,
        default=8080,
        envvar="MCP_BSL_PORT",
        help="Port for SSE server (env: MCP_BSL_PORT)",
    )
    @click.option(
        "--data-source",
        type=click.Choice(["hbk", "json"]),
        default="hbk",
        envvar="MCP_BSL_DATA_SOURCE",
        help="Data source: 'hbk' or 'json' (env: MCP_BSL_DATA_SOURCE)",
    )
    @click.option(
        "--json-path",
        default=None,
        envvar="MCP_BSL_JSON_PATH",
        help="Path to directory with pre-exported JSON files (env: MCP_BSL_JSON_PATH)",
    )
    @click.option(
        "--verbose", "-v",
        is_flag=True,
        envvar="MCP_BSL_VERBOSE",
        help="Enable debug logging (env: MCP_BSL_VERBOSE)",
    )
    def cli(platform_path: str | None, mode: str, port: int, data_source: str, json_path: str | None, verbose: bool) -> None:
        """MCP server for 1C:Enterprise BSL platform context.

        Provides AI assistants with search and navigation across
        1C platform API documentation (methods, properties, types).
        """
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            stream=sys.stderr,
        )

        if data_source == "hbk" and not platform_path:
            click.echo(
                "Error: --platform-path or MCP_BSL_PLATFORM_PATH is required for HBK data source",
                err=True,
            )
            sys.exit(1)

        if data_source == "json" and not json_path:
            click.echo(
                "Error: --json-path or MCP_BSL_JSON_PATH is required when --data-source=json",
                err=True,
            )
            sys.exit(1)

        from mcp_bsl_context.server import create_server

        server = create_server(
            platform_path=platform_path or "",
            data_source=data_source,
            json_path=json_path,
        )

        if mode == "stdio":
            server.run(transport="stdio")
        elif mode == "sse":
            server.run(transport="sse", port=port)

    cli()


if __name__ == "__main__":
    main()
