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
        required=True,
        help="Path to 1C platform installation directory",
    )
    @click.option(
        "--mode", "-m",
        type=click.Choice(["stdio", "sse"]),
        default="stdio",
        help="Transport mode (default: stdio)",
    )
    @click.option(
        "--port",
        type=int,
        default=8080,
        help="Port for SSE server (default: 8080)",
    )
    @click.option(
        "--data-source",
        type=click.Choice(["hbk", "json"]),
        default="hbk",
        help="Data source: 'hbk' for direct reading, 'json' for pre-exported JSON",
    )
    @click.option(
        "--json-path",
        default=None,
        help="Path to directory with pre-exported JSON files (required for --data-source=json)",
    )
    @click.option(
        "--verbose", "-v",
        is_flag=True,
        help="Enable debug logging",
    )
    def cli(platform_path: str, mode: str, port: int, data_source: str, json_path: str | None, verbose: bool) -> None:
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

        if data_source == "json" and not json_path:
            click.echo("Error: --json-path is required when --data-source=json", err=True)
            sys.exit(1)

        from mcp_bsl_context.server import create_server

        server = create_server(
            platform_path=platform_path,
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
