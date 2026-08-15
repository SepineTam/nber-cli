# NBER-CLI

A desktop-first, local research workspace for following National Bureau of Economic Research (NBER) working papers. NBER-CLI also provides command-line and MCP interfaces designed for AI agents and automation.

[![Pytest](https://github.com/sepinetam/nber-cli/actions/workflows/pytest.yml/badge.svg)](https://github.com/sepinetam/nber-cli/actions/workflows/pytest.yml)
[![Lint](https://github.com/sepinetam/nber-cli/actions/workflows/lint.yml/badge.svg)](https://github.com/sepinetam/nber-cli/actions/workflows/lint.yml)
[![Docs](https://github.com/sepinetam/nber-cli/actions/workflows/docs.yml/badge.svg)](https://github.com/sepinetam/nber-cli/actions/workflows/docs.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![PyPI version](https://img.shields.io/pypi/v/nber-cli.svg)](https://pypi.org/project/nber-cli/)
[![PyPI Downloads](https://static.pepy.tech/badge/nber-cli)](https://pepy.tech/projects/nber-cli)

[简体中文](README.zh-CN.md) | [Documentation](docs/en/index.md)

> **NBER** is a registered trademark of the [National Bureau of Economic Research](https://www.nber.org). This project is an independent open-source tool and is **not affiliated with, endorsed by, or sponsored by** the National Bureau of Economic Research. Before using the project, read the [Usage Policy](docs/en/policy.md).


## Quickly Start
Connect to your agent client with http-mcp: `https://nber-mcp.aidea-labs.com/mcp`

- Codex: `codex mcp add nber-mcp --url https://nber-mcp.aidea-labs.com/mcp`
- Claude Code: `claude mcp add nber-mcp -s user -t http https://nber-mcp.aidea-labs.com/mcp`
- OpenClaw: `openclaw mcp add nber-mcp --url https://nber-mcp.aidea-labs.com/mcp`


## Start with Desktop

For researchers, the recommended entry point is **NBER-CLI Desktop**. Download the installer for macOS, Windows, or Linux from [GitHub Releases](https://github.com/sepinetam/nber-cli/releases/latest). The app includes its own runtime: you do not need Python, uv, a terminal, or a locally running web service.

Desktop provides a focused research desk for:

- Synchronizing and browsing the latest NBER working-paper feed.
- Searching the local feed by title, author, paper ID, or tag, and filtering unread papers.
- Reading abstracts and metadata in a resizable preview pane.
- Marking papers read or unread.
- Organizing papers with NBER Topics, NBER Programs, and private local tags.
- Copying BibTeX, APA, MLA, Harvard, Chicago, or GB/T 7714 citations.
- Adjusting the preview font size and automatic refresh interval.
- Keeping the feed, metadata, read state, tags, and settings on the local device.

Current installers are unsigned. Confirm that the installer came from the official GitHub Release before following any macOS Gatekeeper or Windows SmartScreen override. Platform-specific installation and recovery steps are in the [Desktop guide](docs/en/desktop.md).

## Choose an Interface

| Interface | Intended user | Recommended when |
| --- | --- | --- |
| **Desktop** | Researchers | You want a visual, local workspace and do not want to install developer tools. |
| **MCP server** | AI agents | Your agent supports MCP and should search, inspect, or download papers through structured tools. |
| **CLI** | AI agents and automation | The agent can run shell commands, or you need script-friendly text/JSON output. |
| **Python API** | Developers | You are integrating the core async functions into Python code. |
| **Local HTTP API** | Local integrations | A separate local application needs a loopback JSON API. |

The Desktop app, CLI, MCP server, and optional HTTP API can share the same SQLite database. Their capabilities are intentionally different; see the [software specification](docs/en/software-specification.md) for the supported surface matrix.

## Use with an AI Agent

MCP is the preferred structured interface. Start the stdio server with:

```bash
uvx nber-cli mcp-server
```

Example MCP client configuration:

```json
{
  "mcpServers": {
    "nber-cli-mcp": {
      "command": "uvx",
      "args": ["nber-cli", "mcp-server"]
    }
  }
}
```

The MCP server exposes tools for paper lookup, search, and PDF download. Agent-specific installation guides are available for [Claude Code](docs/en/agents/claude-code.md), [Codex](docs/en/agents/codex.md), [OpenClaw](docs/en/agents/openclaw.md), and [other MCP clients](docs/en/agents/others.md).

Agents that can run shell commands may use the CLI directly:

```bash
uvx nber-cli search "Labor Economics" --format json
uvx nber-cli info w25000 --format json
uvx nber-cli download w34567
```

For the complete command model, output contracts, filesystem restrictions, and exit codes, see the [CLI reference](docs/en/cli.md) and [MCP reference](docs/en/mcp.md).

## Local Data and Network Access

By default, NBER-CLI stores its configuration, SQLite database, and diagnostic log under `~/.nber-cli/`. It does not require an account or API key and does not upload the local database to project infrastructure.

- Desktop contacts NBER only during a manual or scheduled Feed refresh; CLI, MCP, Python, and HTTP operations contact NBER when their requested workflow needs remote data.
- Desktop contacts the GitHub Releases API only when the user selects **检查更新 (Check for Updates)**.
- Desktop does not open a listening port.
- The optional HTTP API and non-stdio MCP transports are separate, explicit integrations with their own security considerations.

See [Persistence](docs/en/persistence.md), [Configuration](docs/en/configuration.md), and [Usage Policy](docs/en/policy.md) before changing paths, deleting data, or exposing a network transport.

## Documentation

- [User Manual](docs/en/user-manual.md): task-oriented operation guide, expected results, local side effects, backup, and removal.
- [Desktop Guide](docs/en/desktop.md): installers, daily workflows, settings, keyboard controls, data, and troubleshooting.
- [Agent Guides](docs/en/agents/index.md): plugin, MCP, and skill setup for supported agents.
- [Software Specification](docs/en/software-specification.md): scope, module map, capability matrix, data model, constraints, and source traceability.
- [System Architecture](docs/en/architecture.md): runtime components and trust boundaries.
- [Full Documentation](docs/en/index.md): all user, API, operations, development, and release references.

## Development

```bash
uv sync --dev --group docs
uv run pytest
uv run ruff check .
uv run --group docs mkdocs build --strict
```

Desktop development and release commands are documented in [desktop/README.md](desktop/README.md) and the [development guide](docs/en/development.md).

## License

NBER-CLI is released under the [Apache-2.0 License](LICENSE).
