# NBER-CLI

NBER-CLI is a desktop-first, local research workspace for following NBER working papers. Researchers use the Desktop app; AI agents and automation use the MCP server or CLI. A Python API and optional loopback HTTP API are available for custom integrations.

## Recommended: Desktop

Download the installer for macOS, Windows, or Linux from [GitHub Releases](https://github.com/sepinetam/nber-cli/releases/latest). Desktop includes its own runtime, so end users do not install Python or uv.

The app can synchronize the NBER working-paper feed, search and filter local papers, show cached details, maintain read state and local tags, copy six citation formats, and keep research data on the user's device.

Start with the [User Manual](user-manual.md) for an end-to-end walkthrough or the [Desktop Guide](desktop.md) for platform, settings, data, keyboard, and troubleshooting details.

!!! warning "Unsigned installers"
    Current Desktop installers are not code-signed or notarized. Download only from the official GitHub Release and verify the platform and CPU architecture before overriding an operating-system warning.

## Interfaces

| Interface | Primary audience | Purpose |
| --- | --- | --- |
| Desktop | Researchers | Visual paper feed, reading, citation, read-state, and local-tag workflow. |
| MCP server | AI agents | Structured search, paper lookup, and constrained PDF download tools. |
| CLI | AI agents and automation | Scriptable commands with human-readable and JSON output. |
| Python API | Developers | Direct async access to fetch, download, feed, cache, and database helpers. |
| Local HTTP API | Local integrations | Optional loopback service for feed, paper, read-state, and settings operations. |

The interfaces share core code and local storage where practical, but they do not expose identical capabilities. See the [Software Specification](software-specification.md) for the exact capability and source traceability matrices.

## AI Agent Setup

For an MCP-capable agent, start the stdio server:

```bash
uvx nber-cli mcp-server
```

Then add this configuration to the client:

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

Use the [Agent Guides](agents/index.md) for client-specific installation and verification. Agents that work through a shell can instead follow the [CLI Reference](cli.md).

## Documentation Map

### Use the software

- [User Manual](user-manual.md): installation, first synchronization, daily Desktop tasks, agent workflows, backup, update, and removal.
- [Desktop App](desktop.md): supported packages, data behavior, settings, shortcuts, limitations, and troubleshooting.
- [Getting Started](getting-started.md): choose Desktop, MCP, or CLI and complete the first task.
- [Agent Guides](agents/index.md): setup for Claude Code, Codex, OpenClaw, and other agents.
- [CLI Reference](cli.md) and [MCP Server](mcp.md): exact AI-facing interfaces.

### Understand data and behavior

- [Software Specification](software-specification.md): software identity, functional scope, module boundaries, constraints, and code traceability.
- [Configuration](configuration.md): runtime defaults and supported local settings.
- [Persistence Layer](persistence.md): files, SQLite tables, cache rules, migrations, cleanup, and backup.
- [Usage Policy](policy.md): project boundaries, access, copyright, and user responsibility.
- [Glossary](glossary.md): project-specific terms.

### Integrate and develop

- [Local HTTP API](http-api.md) and [Python API](python-api.md): integration contracts.
- [System Architecture](architecture.md): runtime components, workflows, and trust boundaries.
- [Development](development.md), [Testing](testing.md), and [Contributing](contributing.md): repository workflow and quality gates.
- [Changelog](changelog.md): release history. The current repository version is **0.11.0**.

## Scope and Status

NBER-CLI is an independent Apache-2.0 open-source project in beta. It works with public NBER pages and endpoints, requires no project account or API key, and is not affiliated with or endorsed by NBER. Availability and access to individual papers remain subject to NBER's service and policies.
