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
        "--config", "-c",
        default=None,
        help="Path to YAML config file",
    )
    @click.option(
        "--platform-path", "-p",
        required=False,
        default=None,
        help="Path to 1C platform installation directory (overrides config/env)",
    )
    @click.option(
        "--platform-version",
        default=None,
        help="Preferred platform version, e.g. '8.3.20'. Picks closest available. (overrides config/env)",
    )
    @click.option(
        "--mode", "-m",
        type=click.Choice(["stdio", "sse", "streamable-http"]),
        default=None,
        help="Transport mode: stdio, sse, or streamable-http (overrides config/env)",
    )
    @click.option(
        "--port",
        type=int,
        default=None,
        help="Port for HTTP server (overrides config/env)",
    )
    @click.option(
        "--data-source",
        type=click.Choice(["hbk", "json"]),
        default=None,
        help="Data source: 'hbk' or 'json' (overrides config/env)",
    )
    @click.option(
        "--json-path",
        default=None,
        help="Path to directory with pre-exported JSON files (overrides config/env)",
    )
    @click.option(
        "--verbose", "-v",
        is_flag=True,
        default=None,
        help="Enable debug logging (overrides config/env)",
    )
    def cli(
        config: str | None,
        platform_path: str | None,
        platform_version: str | None,
        mode: str | None,
        port: int | None,
        data_source: str | None,
        json_path: str | None,
        verbose: bool | None,
    ) -> None:
        """MCP server for 1C:Enterprise BSL platform context.

        Provides AI assistants with search and navigation across
        1C platform API documentation (methods, properties, types).

        Configuration priority: YAML config < env vars (MCP_BSL_*) < CLI arguments.
        """
        from mcp_bsl_context.config import load_config

        # Build CLI overrides dict (None values are skipped by load_config)
        cli_overrides = {
            "platform.path": platform_path,
            "platform.version": platform_version,
            "platform.data_source": data_source,
            "platform.json_path": json_path,
            "server.mode": mode,
            "server.port": port,
            "server.verbose": verbose,
        }

        app_config = load_config(config_path=config, cli_overrides=cli_overrides)

        log_level = logging.DEBUG if app_config.server.verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            stream=sys.stderr,
        )

        if app_config.platform.data_source == "hbk" and not app_config.platform.path:
            click.echo(
                "Error: platform.path is required for HBK data source. "
                "Set via --platform-path, MCP_BSL_PLATFORM_PATH, or config file.",
                err=True,
            )
            sys.exit(1)

        if app_config.platform.data_source == "json" and not app_config.platform.json_path:
            click.echo(
                "Error: platform.json_path is required for JSON data source. "
                "Set via --json-path, MCP_BSL_JSON_PATH, or config file.",
                err=True,
            )
            sys.exit(1)

        from mcp_bsl_context.server import create_server

        server = create_server(app_config)

        if app_config.server.mode == "stdio":
            server.run(transport="stdio")
        else:
            server.run(transport=app_config.server.mode, port=app_config.server.port)

    cli()


if __name__ == "__main__":
    main()
