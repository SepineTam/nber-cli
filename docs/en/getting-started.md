# Getting Started

This guide helps you choose the right NBER-CLI interface and complete a first task. Researchers should start with Desktop. CLI and MCP are primarily intended for AI agents, scripts, and integrations.

## Recommended Desktop Path

1. Download the package for your operating system and CPU from the [official GitHub Release](https://github.com/sepinetam/nber-cli/releases/latest).
2. Verify that the file came from `SepineTam/NBER-CLI`. Current installers may be unsigned; read the [Desktop installation warning](desktop.md#unsigned-release-notice) before overriding an operating-system prompt.
3. Install and open **NBER-CLI Desktop**. No Python or uv installation is required.
4. Select **同步最新论文 (Refresh)** to synchronize the working-paper Feed and prepare local paper details.
5. Select a paper to read its abstract, manage tags or read state, copy a citation, or open the source page.

For the complete task-by-task workflow, see the [User Manual](user-manual.md). The remaining sections describe the AI-facing CLI and optional integration server.

## CLI and Integration Requirements

- Python 3.11 or newer.
- Network access to `https://www.nber.org`.
- `uv`, `pipx`, or `pip` for installation.

These requirements do not apply to Desktop. For an AI agent or integration, the fastest path is `uvx`, which runs the package in an isolated environment without a permanent install.

## Run with uvx

```bash
uvx nber-cli --version
uvx nber-cli search "Labor Economic"
uvx nber-cli info w25000
uvx nber-cli cite w1234
uvx nber-cli download w34567
```

If the command is not found or fails, run `uvx nber-cli -v` to check the current version. If it is not the latest version, update the cache with:

```bash
uvx --refresh nber-cli -v
```

## Install as a Tool

Use `uv tool install` when you want the `nber-cli` command available on your shell path:

```bash
uv tool install nber-cli
nber-cli --version
```

You can also install with `pipx`:

```bash
pipx install nber-cli
nber-cli --version
```

## Run the Optional Local HTTP Server

FastAPI, Uvicorn, and Alembic are kept out of the normal CLI dependency set. Use the `server` extra only when another local integration needs the optional API; Desktop does not use it:

```bash
uvx --from "nber-cli[server]" nber-server --host 127.0.0.1 --port 31527
```

The server binds to loopback by default, upgrades the local database to schema v3, and serves endpoints under `/api/v1`.

## Run as a Python Module

The package also exposes a module entry point. This is useful when the `nber-cli` console script is not on your `PATH` (for example, when running from a checked-out working tree or inside a virtual environment where the wrapper was not generated):

```bash
python -m nber_cli --version
python -m nber_cli search "labor economics"
python -m nber_cli info w25000
```

`python -m nber_cli` is functionally identical to the `nber-cli` command — same arguments, same exit codes, same stdout/stderr contracts. From a working tree you can also run it through `uv`:

```bash
uv run python -m nber_cli --version
```

## First Search

```bash
nber-cli search "labor economics"
```

Search accepts title text, author names, abstracts, keywords, and paper numbers. The default result page contains 20 papers.

Add a date range and result size:

```bash
nber-cli search "minimum wage" --start-date 2024-01-01 --end-date 2024-12-31 --per-page 50
```

Return JSON for scripts:

```bash
nber-cli search "inflation" --format json
```

## Read Paper Details

```bash
nber-cli info w25000
```

Paper IDs can be passed with or without the `w` prefix:

```bash
nber-cli info 25000
```

Use `--all` to include related fields and published-version information when NBER exposes them:

```bash
nber-cli info w25000 --all
```

## Cite a Paper

Copy a bibliography entry to the clipboard:

```bash
nber-cli cite w25000
nber-cli cite w25000 -f apa
```

The default format is BibTeX. `-f` also accepts `mla`, `harvard`, `chicago`, and `gb`. The aliases `bibtex` and `gbt7714` are supported.

Print the citation without using the clipboard, for example to build a bibliography file:

```bash
nber-cli cite w25000 --stdout > references.bib
```

Clipboard mode writes a confirmation to stderr only. If no clipboard backend is available, the citation is printed to stdout and the command exits with code 1.

## Follow New Papers with the Feed Cache

Initialize the local database:

```bash
nber-cli db init
```

The database is a local SQLite file, managed through SQLModel/SQLAlchemy. By default it is stored at `~/.nber-cli/nber.db`; advanced users can choose another path or a `sqlite:///...` URL with `nber-cli db init --db-path ...`.

Fetch the NBER new working papers RSS feed:

```bash
nber-cli feed fetch
```

The first fetch stores the current RSS items in the cache and displays them as new. Later fetches show only items that were not already cached.

Limit output while showing the latest fetched items:

```bash
nber-cli feed fetch --max-items 5
```

Clean old cache records:

```bash
nber-cli feed clean --days 30
```

`feed clean` asks for confirmation before deleting cached records.

## Download a PDF

Download into the current directory:

```bash
nber-cli download w34567
```

Save into a directory:

```bash
nber-cli download w34567 --save-base papers/nber
```

Save to an explicit file path:

```bash
nber-cli download w34567 --file papers/nber/w34567.pdf
```

## Batch Download

```bash
nber-cli download --batch w34567 w25000 w32000 --save-base papers/nber
```

Batch mode supports `--save-base`; it does not support `--file`.

## Next Steps

- Follow the [User Manual](user-manual.md) or review the detailed [Desktop App](desktop.md) guide.
- Configure an AI agent with the [Agent Guides](agents/index.md).
- Integrate with the [Local HTTP API](http-api.md).
- Read the [CLI Reference](cli.md) for all commands and options.
- Configure the [MCP Server](mcp.md) for agent workflows.
- Use the [Python API](python-api.md) in your own async code.
