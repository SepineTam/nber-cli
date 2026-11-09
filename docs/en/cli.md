# CLI Reference

The executable command is `nber-cli`.

```bash
nber-cli [--version] <command> [options]
```

## Global Options

| Option | Description |
| --- | --- |
| `-v`, `--version` | Print the installed NBER-CLI version. |
| `-h`, `--help` | Show command help. |
| `--verbose` | Enable debug logging to stderr and the log file. |
| `-c`, `--config <path>` | Use a custom config file for this run only. |

Running `nber-cli` without a subcommand prints the top-level help and exits successfully.

## Commands

| Command | Purpose |
| --- | --- |
| `download` | Download one or more paper PDFs. |
| `info` | Show metadata and abstract for one paper. |
| `cite` | Copy or print a paper citation. |
| `search` | Search NBER working papers. |
| `db` | Manage the local SQLite database. |
| `feed` | Manage the NBER new working papers RSS feed cache. |
| `config` | Inspect and edit `~/.nber-cli/config.json`. |
| `doctor` | Inspect the local installation, config, database, and package version status. |
| `mcp-server` | Start the MCP server for agents. |

## cite

Copy a single NBER working-paper bibliography entry (not an in-text citation):

```bash
uvx nber-cli cite w1234
uvx nber-cli cite w1234 -f apa
uvx nber-cli cite w1234 --format gb
uvx nber-cli cite w1234 --stdout > references.bib
uvx nber-cli cite w1234 --refresh
```

| Option | Description |
| --- | --- |
| `paper_id` | Positive paper ID such as `w1234` or `1234`; case insensitive. |
| `--format`, `-f` | `bib` (default; alias `bibtex`), `apa`, `mla`, `harvard`, `chicago`, `gb` (alias `gbt7714`). |
| `--stdout` | Print only the citation, without accessing the clipboard. |
| `--refresh` | Fetch fresh metadata, using the same cache settings as `info`. |

Styles target APA 7th, MLA 9th, Chicago 18th bibliography, and GB/T 7714—2025 sequential-reference entries (without an assigned list number). Harvard uses this project's fixed author–date working-paper profile; Harvard has no single universal specification. Formatted references are plain text, without italics or Markdown. Verify journal-specific requirements and ambiguous author names before publication.

References always describe the NBER working paper, even when a published version exists. BibTeX uses `@techreport` and the stable key `nberw1234`, escapes TeX special characters, and omits missing author/year fields. Other styles use `Unknown author` / `n.d.` for missing metadata. The current metadata model has no DOI field; entries use the paper URL. GB entries include the local access date. No publication location is inferred.

On success, clipboard mode writes only a confirmation to stderr. On clipboard failure, the generated citation is printed to stdout, an explanation goes to stderr, and the command exits with code 1. Invalid arguments exit with code 2 before fetching; fetch/format errors exit with code 1 without changing the clipboard.

Clipboard support uses `pbcopy` on macOS, PowerShell `Set-Clipboard` on Windows, and `wl-copy` (Wayland) or `xclip` / `xsel` (X11) on Linux. Linux requires a desktop session and an installed clipboard utility. Use `--stdout` on servers or over SSH; remote execution targets the remote host's clipboard.

## download

Download one paper:

```bash
nber-cli download w34567
```

Download to an explicit file:

```bash
nber-cli download w34567 --file papers/w34567.pdf
nber-cli download w34567 -f papers/w34567.pdf
```

Download to a target directory:

```bash
nber-cli download w34567 --save-base papers/nber
nber-cli download w34567 -s papers/nber
```

Batch download:

```bash
nber-cli download --batch w34567 w25000 w32000 --save-base papers/nber
nber-cli download -b w34567 w25000 w32000 -s papers/nber
```

### download Options

| Option | Description |
| --- | --- |
| `paper_id` | Optional positional paper ID for single downloads, for example `w34567`. |
| `--file`, `-f` | Explicit target PDF path for a single download. |
| `--save-base`, `-s` | Target directory for generated `<paper_id>.pdf` files. Defaults to the current working directory. |
| `--batch`, `-b` | One or more paper IDs to download concurrently. |
| `--restrict` | Enable the current lexical working-directory check. Defaults to `true`; use `--restrict false` to disable it per invocation. |
| `--concurrency`, `-c` | Maximum concurrent downloads. Overrides the `download.concurrency` config value. |

### download Rules

- A single positional paper ID and `--batch` cannot be used together.
- `--file` is only supported for a single paper.
- Batch mode supports `--save-base` only.
- If neither `--file` nor `--save-base` is passed, PDFs are saved in the current working directory.
- If a paper is unavailable, NBER-CLI exits with code `1` and prints a readable error message.

### download Filesystem Behavior

!!! warning "The restriction is not a sandbox"
    In 0.10.0, restricted mode compares absolute path components without resolving `..` segments or symbolic links. A crafted path can therefore pass the check and still write outside the working directory. Use simple relative filenames, run the process in an isolated working directory when input is untrusted, and do not treat `--restrict` as an operating-system security boundary.

- **Existing files are overwritten.** When the target PDF path already exists, NBER-CLI writes the new bytes in place and overwrites the previous file. There is no "skip if newer" or "preserve on error" mode.
- **No atomic rename.** The download is read fully into memory and then written to the target path in a single `write_bytes` call. If the process is killed, the host loses power, or the disk fills up mid-write, the file at the target path can be left empty, truncated, or partially written. The previous file (when it existed) is not preserved on the failure path.
- **Parent directories are auto-created.** The parent of the resolved output path is created with `mkdir(parents=True, exist_ok=True)`. Missing intermediate directories do not cause a failure, but the process needs write permission on the deepest existing ancestor.
- **Path resolution is literal.** The string passed to `--file` (or `<paper_id>.pdf` derived from `--save-base`) is used verbatim. Relative paths resolve against the current working directory. Tilde expansion (`~`) is **not** performed; if you want `~`-relative paths, your shell needs to expand them.
- **Single download is fully in-memory.** The full PDF body is buffered before any disk write, so a single download holds the entire PDF in memory for the duration of the transfer. Very large PDFs may briefly use several hundred MB of RAM.
- **Python API callers own sessions they provide.** `download_paper` and `download_paper_to_file` accept a custom `aiohttp.ClientSession`; the caller owns its lifecycle, timeout, and connector limits. NBER-CLI still applies its fixed-attempt retry helper. `download_multiple_papers` does not currently accept a session argument.

For the Python API, see [Python API — Download PDF](python-api.md#download-a-pdf).

## info

Show paper metadata:

```bash
nber-cli info w25000
```

Show all available fields:

```bash
nber-cli info w25000 --all
```

Return JSON:

```bash
nber-cli info w25000 --format json
nber-cli info w25000 -f json
```

### info Options

| Option | Description |
| --- | --- |
| `paper_id` | Required paper ID, with or without the `w` prefix. |
| `--all`, `-a` | Include related fields and published-version information when available. |
| `--format`, `-f` | Output format: `list` or `json`. Defaults to `list`. |
| `--refresh` | Bypass the local `info_cache` and re-fetch from NBER. The new data is written back to the cache when the cache is enabled. |

When the cache is enabled and the cached entry has not yet passed the configured TTL, repeated `info` calls are served from the local database. The first `info` call after a TTL expiry, or any call with `--refresh`, performs a live fetch.

The TTL is **sliding**: every cache hit updates `last_fetched_at` and increments `fetch_count`, so frequently consulted papers keep their cached copy until at least `cache_ttl_days` have passed since the most recent hit. "Last fetched" therefore means "last local hit", not "last network fetch from NBER". `--refresh` always bypasses the cache and writes a fresh row.

The MCP `get_paper_info` tool follows the same cache behavior, but it does not accept a per-call `--refresh` argument. The tool always honors the current `info_cache` toggle and TTL; agents that need a forced refresh must toggle the cache off, call `get_paper_info`, and toggle the cache back on (or rely on the next call after a TTL-driven re-fetch).

## info cache

Manage the `info_cache` lookup behavior and clear cached records.

Show the current cache state, TTL, and row count:

```bash
nber-cli info cache
nber-cli info cache status
```

`info cache` and `info cache status` are equivalent — both print the same status view (cache enabled/disabled, current TTL, and row count). The explicit `status` sub-action is provided for symmetry with `clear`/`clean` and for scripts that prefer an unambiguous form.

Toggle the cache globally:

```bash
nber-cli info cache --turn-on
nber-cli info cache --turn-off
```

Set the cache refresh interval in days:

```bash
nber-cli info cache --set-refresh 7
nber-cli info cache --set-refresh 30
```

`--set-refresh` requires a positive integer. The new value is written to `~/.nber-cli/config.json` and used as the TTL for every subsequent `info` call.

Clean cached records not refreshed in the last 30 days:

```bash
nber-cli info cache clear
nber-cli info cache clear --days 30
```

Clean all cached records:

```bash
nber-cli info cache clear --all
nber-cli info cache clean
```

`info cache clean` is a convenience alias for `info cache clear --all`.

Clean cached records by `last_fetched_at` date:

```bash
nber-cli info cache clear --end-date 2026-06-01
nber-cli info cache clear --start-date 2026-05-01 --end-date 2026-06-01
```

`--end-date` without `--start-date` cleans from the earliest cached record through the end date. `--start-date` and `--end-date` are inclusive. Passing only `--start-date` is invalid.

Before deleting anything, `info cache clear` prints how many cached records match and asks for confirmation:

```text
This operation is irreversible.
Deleted info cache records may be fetched again from NBER.
Continue? [y/N]:
```

Only `y` or `Y` continues. Any other response aborts without deleting records.

### info cache Options

| Subcommand | Option | Description |
| --- | --- | --- |
| (none) | `--turn-on` | Enable the info cache globally. |
| (none) | `--turn-off` | Disable the info cache globally. |
| (none) | `--set-refresh` | Set the info cache refresh interval in days. Must be a positive integer. |
| `status` | — | Print the current cache state, TTL, and row count. Equivalent to running `info cache` with no sub-action. |
| `clear` | `--days` | Clean cached records not refreshed for this many days. Defaults to `30`. |
| `clear` | `--all` | Clean all cached records. |
| `clear` | `--start-date` | Clean cached records refreshed on or after this date, formatted `YYYY-MM-DD`. |
| `clear` | `--end-date` | Clean cached records refreshed on or before this date, formatted `YYYY-MM-DD`. |
| `clean` | — | Alias for `clear --all`. |

## search

Search by query:

```bash
nber-cli search "Labor Economic"
```

Use date filters:

```bash
nber-cli search "minimum wage" --start-date 2024-01-01 --end-date 2024-12-31
```

Change pagination:

```bash
nber-cli search "inflation" --page 2 --per-page 50
```

Return JSON:

```bash
nber-cli search "inflation" --format json
nber-cli search "inflation" -f json
```

### search Options

| Option | Description |
| --- | --- |
| `query` | Required search query. It may be a title, number, author, abstract phrase, or keyword. |
| `--start-date`, `--start` | Include papers on or after this date, formatted `YYYY-MM-DD`. |
| `--end-date`, `--end` | Include papers on or before this date, formatted `YYYY-MM-DD`. |
| `--page` | Result page to fetch. Defaults to `1`. |
| `--per-page` | Results per page. Allowed values: `20`, `50`, `100`. Defaults to `20`. |
| `--format`, `-f` | Output format: `list` or `json`. Defaults to `list`. |

When only `--start-date` is provided, NBER-CLI automatically uses the current date as the end date.

## feed

`feed` works with NBER's new working papers RSS feed and the local database. The database tracks which RSS items have already been seen, so `feed fetch` can show only newly discovered papers by default.

### feed fetch

Fetch the RSS feed, store all fetched items in the cache, and display only new items by default:

```bash
nber-cli feed fetch
```

Display all fetched RSS items, including items already present in the cache:

```bash
nber-cli feed fetch --display-all true
nber-cli feed fetch --display-all
```

`--display-all` accepts a boolean value. The parser recognises (case-insensitive, whitespace tolerated) `true`, `false`, `1`, `0`, `yes`, `no`, `y`, `n`, `on`, `off`. When the flag is passed with no value (`--display-all` on its own) it defaults to `true`. Any other value is rejected with exit code `2`.

Limit displayed output:

```bash
nber-cli feed fetch --max-items 5
```

When `--max-items` is provided and `--display-all` is omitted, `--display-all` defaults to `true`. This makes `nber-cli feed fetch --max-items 5` show the first five fetched RSS items instead of showing nothing when there are no new items.

Return JSON:

```bash
nber-cli feed fetch --format json
nber-cli feed fetch -f json
```

NBER-CLI strictly parses the RSS XML. To tolerate a known upstream formatting issue, it repairs only unescaped `<` characters followed by whitespace or a digit inside RSS `title` and `description` text. Other malformed XML is rejected. Parse errors exit with code `1`, print a concise error with the line and column when available, and do not print command usage.

### feed clean

Clean cached feed database records. This deletes records from the local cache, not from NBER. Deleted cache records may be fetched again as new items if they still appear in the RSS feed.

Clean records not seen for 30 days:

```bash
nber-cli feed clean
nber-cli feed clean --days 30
```

Clean all cached records:

```bash
nber-cli feed clean --all
```

Clean records by last-seen date:

```bash
nber-cli feed clean --end-date 2026-05-31
nber-cli feed clean --start-date 2026-05-01 --end-date 2026-05-31
```

`--end-date` without `--start-date` cleans from the earliest cached record through the end date. `--start-date` and `--end-date` are inclusive. Passing only `--start-date` is invalid.

Before deleting anything, `feed clean` prints how many cached records match and asks for confirmation:

```text
This operation is irreversible.
Deleted cache records may be fetched again as new items if they still appear in the RSS feed.
Continue? [y/N]:
```

Only `y` or `Y` continues. Any other response aborts without deleting records.

### feed Options

| Subcommand | Option | Description |
| --- | --- | --- |
| `fetch` | `--display-all [true\|false]` | Display all fetched RSS items instead of only new items. Accepts `true`/`false`/`1`/`0`/`yes`/`no`/`y`/`n`/`on`/`off` (case-insensitive). When passed without a value, defaults to `true`. |
| `fetch` | `--format`, `-f` | Output format: `list` or `json`. Defaults to `list`. |
| `fetch` | `--max-items` | Maximum number of feed items to display. |
| `clean` | `--days` | Clean cached records not seen for this many days. Defaults to `30`. |
| `clean` | `--all` | Clean all cached feed records. |
| `clean` | `--start-date` | Clean cached records last seen on or after this date, formatted `YYYY-MM-DD`. |
| `clean` | `--end-date` | Clean cached records last seen on or before this date, formatted `YYYY-MM-DD`. |

## db

`db` manages the local SQLite database used by `info`, `search`, `download`, and `feed` for cache and behavior logs. The database is stored on the user's machine and accessed through SQLModel/SQLAlchemy; commands accept either a filesystem path or a `sqlite:///...` URL.

### db init

Initialize the database and write its path to the user config:

```bash
nber-cli db init
nber-cli db init --db-path ~/.nber-cli/nber.db
nber-cli db init --db-path sqlite:////Users/name/data/nber.db
```

If `--db-path` is omitted, the default database path is `~/.nber-cli/nber.db`.

If an existing `~/.nber-cli/feed.db` from 0.3.0 is present and no `nber.db` exists yet, NBER-CLI uses that legacy file in place. On first database-backed use, older schemas are upgraded step by step to the current version 3.

### db migrate

Move the database to a new path and update the user config:

```bash
nber-cli db migrate ~/data/nber.db
nber-cli db migrate sqlite:////Users/name/data/nber.db
```

Migration moves the SQLite database file and any SQLite sidecar files such as `-wal`, `-shm`, and `-journal`. The target path must not already exist.

### db Options

| Subcommand | Option | Description |
| --- | --- | --- |
| `init` | `--db-path` | SQLite database path or `sqlite:///...` URL. Defaults to `~/.nber-cli/nber.db`. |
| `migrate` | `new_db_path` | New SQLite database path or `sqlite:///...` URL. |

## config

Inspect and edit `~/.nber-cli/config.json`:

```bash
nber-cli config show
nber-cli config get info.cache_ttl_days
nber-cli config set download.concurrency 5
nber-cli config verify
```

### config Options

| Subcommand | Arguments | Description |
| --- | --- | --- |
| `show` | — | Print the current configuration. |
| `get` | `<key>` | Print the value for a dot-separated key, such as `info.cache_ttl_days`. |
| `set` | `<key> <value>` | Set a dot-separated key to the inferred value (`true`/`false`/integer/string). |
| `verify` | — | Validate the configuration against `config.schema.json`. |

## doctor

Inspect the current local installation and runtime state:

```bash
nber-cli doctor
```

The report includes the installed version, latest PyPI version, executable path, package path, Python executable, config path and contents, database path, database existence, schema version, database size, and the latest recorded query/download/info/feed activity.

To upgrade when PyPI has a newer version:

```bash
nber-cli doctor --fix-version
```

The command first checks whether the installed version is current. If an upgrade is needed, it refreshes `uvx` executions with `uvx --refresh nber-cli -v`, upgrades `uv tool` installations with `uv tool upgrade nber-cli`, upgrades `pipx` installations with `pipx upgrade nber-cli`, and otherwise falls back to `python -m pip install --upgrade nber-cli` using the current Python executable. It runs a second version check after the upgrade command and writes failures to `~/.nber-cli/debug.log`.

## mcp-server

Start the default stdio MCP server:

```bash
nber-cli mcp-server
```

Start an HTTP transport:

```bash
nber-cli mcp-server --transport streamable-http --port 8000
```

Use `--yes` to confirm a non-default port:

```bash
nber-cli mcp-server --transport streamable-http --port 9000 --yes
```

### mcp-server Options

| Option | Description |
| --- | --- |
| `--transport` | Transport mechanism: `stdio`, `sse`, or `streamable-http`. Defaults to `stdio`. |
| `--port` | Port for HTTP transports. Defaults to `8000`. |
| `--yes` | Confirm use of a non-default port. |

For client configuration and tool details, see [MCP Server](mcp.md).

## Exit Codes

| Code | Meaning |
| --- | --- |
| `0` | Command completed successfully, or help was printed. |
| `1` | Runtime failure such as a failed download, a network error, a parse error, or any other unhandled exception. |
| `2` | Invalid command-line arguments. Argparse raises `SystemExit(2)` and prints a usage message to stderr. |

A few extra rules that are easy to miss:

- A single `download` failure exits `1`. The successful `Successfully downloaded <id> to <path>` line goes to stdout; the `Failed to download <id>: <reason>` line goes to stderr. The download log row in `download_log` is written before the failure is printed.
- A batch `download` runs every requested paper and only exits `1` at the end if at least one paper failed. Successful files are written to stdout (`Successfully downloaded ...`), failures and the per-failure reasons go to stderr. The exit code is `0` only when every paper succeeded.
- A `feed fetch` RSS parse failure exits `1` and writes a concise error to stderr without printing command usage. The error includes the XML line and column when available.
- `db init`, `db migrate`, `info cache clear`, and `feed clean` print a confirmation prompt to stderr. The command aborts with exit code `0` if the user declines (`Abort.` is printed to stderr). The actual deletion (when confirmed) exits `0` on success.
- Database record-keeping failures (`record_query`, `record_download`, `record_info`, `touch_info_cache`, `write_info_cache`) print a one-line `warning: failed to ...` to stderr but do **not** raise. The main command's exit code is unaffected.
- The download module reads the entire PDF body into memory and then writes it in one call. A failure that occurs between the network read and the disk write (process kill, disk full, permission revoked) typically surfaces as a Python exception on the way out; the user sees the traceback on stderr and the process exits `1`. There is no atomic-rename guarantee, so a target file may be left empty or partially written when this happens.

## Output Formats

`info`, `search`, and `feed fetch` default to `list`, a readable text format. Use `--format json` when piping output into scripts or agent workflows.

The rule of thumb for scripting:

- **stdout** carries the human-readable output or the JSON payload (with `--format json`).
- **stderr** carries per-paper error messages, success lines that are incidental to the main payload, `warning: ...` lines for failed background logging, and confirmation prompts for destructive commands. Cache hits do not produce a separate stderr hint.

This means a script that wants the JSON payload can capture stdout with `2>/dev/null` (or simply `2>&-`), and a script that wants only errors can capture stderr with `2>&1 >/dev/null`.
