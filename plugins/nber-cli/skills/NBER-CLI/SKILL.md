---
name: NBER-CLI
description: "Use this skill when the user needs to search NBER working papers, inspect NBER paper metadata, download NBER paper PDFs, run NBER-CLI commands, or configure NBER-CLI as an MCP server."
---

# NBER-CLI

## When to Use

Use this skill when the user wants to use NBER-CLI for NBER working papers, including:

- Searching NBER working papers by keyword, paper ID, author, abstract, or date range.
- Inspecting metadata or abstracts for a known NBER paper ID.
- Downloading one or more NBER PDF files to a chosen filesystem path.
- Getting machine-readable JSON output for agent workflows.
- Configuring NBER-CLI as an MCP server.
- Understanding common access errors such as 403, 404, timeout, access denied, or download limits.

## Assumptions

- The user may not have this repository checked out.
- Do not assume `nber-cli` is already installed.
- Prefer `uvx nber-cli ...` for one-off usage because it can run the published package without requiring a checked-out project or preinstalled command.
- If the user already installed the command, `nber-cli ...` is also fine.
- NBER-CLI does not grant access rights beyond what NBER allows for the user's current IP, institution, account, or session.

## CLI Usage

Check the command:

```bash
uvx nber-cli --help
uvx nber-cli --version
```

Search working papers:

```bash
uvx nber-cli search "labor economics"
uvx nber-cli search "minimum wage" --start-date 2024-01-01 --end-date 2024-12-31
uvx nber-cli search "ChatGPT" --format json
```

Show paper metadata:

```bash
uvx nber-cli info w25000
uvx nber-cli info w25000 --all
uvx nber-cli info w25000 --format json
```

Download papers:

```bash
uvx nber-cli download w34567
uvx nber-cli download w34567 --save-base ~/papers/nber
uvx nber-cli download w34567 --file ~/papers/nber/w34567.pdf
uvx nber-cli download --batch w34567 w25000 w32000 --save-base ~/papers/nber
```

Run the MCP server:

```bash
uvx nber-cli mcp-server
uv run nber-cli mcp-server --transport streamable-http --port 8000 --yes
```

The first command uses the published package's default stdio server and includes the download tool. The second uses the current source tree's Unreleased transport spelling and exposes only search and paper-info tools; `--port` already exists in published `0.4.0`, while the source tree newly requires `--yes` for a custom value. The HTTP transport has no built-in authentication; do not expose it to an untrusted network.

## Examples Index

The `examples/` directory contains focused guides for advanced workflows:

- [`examples/use-of-feed.md`](examples/use-of-feed.md): incremental RSS feed monitoring, JSON filtering, cron automation, systemd timers, and batch downloads.
- [`examples/use-of-search.md`](examples/use-of-search.md): historical catalog queries, date ranges, pagination, and search-to-download chains.
- [`examples/use-of-info.md`](examples/use-of-info.md): metadata lookup, full records, batch inspection, and ID validation.
- [`examples/use-of-download.md`](examples/use-of-download.md): single and batch downloads, save paths, restricted access handling, and feed-to-download integration.
- [`examples/use-of-mcp-server.md`](examples/use-of-mcp-server.md): stdio and HTTP MCP server setup, client configuration, and security notes.
- [`examples/use-of-json-pipeline.md`](examples/use-of-json-pipeline.md): stable JSON shapes, jq recipes, citation extraction, and append-only JSON Lines logs.
- [`examples/use-of-db.md`](examples/use-of-db.md): database initialization, custom paths or `sqlite:///...` URLs, migration, direct SQLite queries, and backup.
- [`examples/use-of-automation.md`](examples/use-of-automation.md): weekly digest scripts, cron recipes, systemd timers, and topic alerts.
- [`examples/use-of-error-handling.md`](examples/use-of-error-handling.md): interpreting 403, 404, and timeouts, plus robust shell patterns.

## Advanced Feed Workflows

The feed subsystem tracks NBER's new working papers RSS feed (`https://www.nber.org/rss/new.xml`) in the local database. It is designed for incremental monitoring, not exhaustive search. Use it to answer questions like "what papers appeared this week?" or "has any new paper on topic X shown up?"

For more complete examples, including JSON filtering, cron automation, systemd timers, and batch-download scripts, see [`examples/use-of-feed.md`](examples/use-of-feed.md).

### Initial setup

The database and tables are created automatically on the first `feed fetch`, but you can also initialize explicitly:

```bash
uvx nber-cli db init
```

This writes the default path `~/.nber-cli/nber.db` to `~/.nber-cli/config.json`. To keep feed data in a custom location:

```bash
uvx nber-cli db init --db-path ~/research/nber.db
uvx nber-cli db init --db-path sqlite:////Users/name/research/nber.db
uvx nber-cli db migrate ~/Dropbox/research/nber.db
```

`db migrate` moves the database file and its SQLite sidecar files to the new path and updates config. The database stays on the user's machine and is accessed through SQLModel/SQLAlchemy.

### First fetch vs incremental fetch

`feed fetch` always downloads the current RSS feed and updates `last_seen_at` for every item. By default it only prints items that were not already in the cache:

```bash
uvx nber-cli feed fetch
```

After the first run, the same command becomes an incremental "what's new" check. To see everything that NBER is currently advertising, regardless of cache state:

```bash
uvx nber-cli feed fetch --display-all
```

To preview a fixed number of the most recent items (and automatically enable `--display-all`):

```bash
uvx nber-cli feed fetch --max-items 10
uvx nber-cli feed fetch --max-items 10 --format json
```

### Machine-readable feed processing

Use JSON output when you want to filter, store, or pass feed items to another tool:

```bash
uvx nber-cli feed fetch --format json | jq '.items[] | {paper_id, title, authors}'
```

Save only new papers to a JSON Lines file for downstream processing:

```bash
uvx nber-cli feed fetch --format json | jq -c '.items[]' >> nber_feed_new.jsonl
```

The JSON shape is stable and includes:

- `source_url`: the RSS URL
- `database_path`: resolved path to the local SQLite cache
- `total_fetched`: how many items NBER returned
- `new_count`: how many items were not already in the cache
- `display_all`: whether the output includes all items or only new ones
- `max_items`: the display cap, if any
- `items`: list of feed items, each with `paper_id`, `title`, `authors`, `abstract`, `url`, `source_url`, `guid`

### Combining feed with search, info, and download

A typical agent workflow is:

1. Run `feed fetch` to discover new papers.
2. Use `search` if you need a broader or historical set.
3. Use `info` to read abstracts and metadata.
4. Use `download` to retrieve PDFs.

Example: fetch the latest feed, then inspect and download a specific paper:

```bash
uvx nber-cli feed fetch --max-items 5
uvx nber-cli info w32000 --all
uvx nber-cli download w32000 --save-base ./papers/this-week
```

Example: find the newest paper by an author you follow:

```bash
uvx nber-cli feed fetch --display-all --format json \
  | jq '.items[] | select(.authors[] | contains("Daron Acemoglu")) | {paper_id, title}'
```

Then download the matching paper:

```bash
uvx nber-cli download w32000 --save-base ./papers/acemoglu
```

### Feed cache cleanup strategies

`feed clean` removes rows from `feed_items`. It always previews the match count and asks for confirmation unless you pipe `y` to it. The audit table `feed_fetches` is never touched, so you keep a complete history of every fetch.

Remove items not seen in the last 30 days (the default):

```bash
uvx nber-cli feed clean
```

Use a custom retention window:

```bash
uvx nber-cli feed clean --days 7
```

Clean a specific date range:

```bash
uvx nber-cli feed clean --start-date 2026-05-01 --end-date 2026-05-31
```

Wipe the cache entirely (all `feed_items` rows):

```bash
uvx nber-cli feed clean --all
```

This is safe because the next `feed fetch` will repopulate whatever NBER is currently advertising. It is useful when you want to reset the "new" state, for example after changing how you filter papers.

### Automated monitoring

Because `feed fetch` is idempotent and fast, you can run it on a schedule. A minimal cron entry that fetches every weekday morning and appends new items to a JSON Lines log:

```cron
0 9 * * 1-5 cd /home/user/research && uvx nber-cli feed fetch --format json | jq -c '.items[]' >> nber_feed_new.jsonl
```

A slightly richer script that downloads new papers to a weekly folder:

```bash
#!/usr/bin/env bash
# save_new_papers.sh
WEEK_DIR="./papers/$(date +%Y-%W)"
mkdir -p "$WEEK_DIR"
uvx nber-cli feed fetch --format json > /tmp/feed_new.json
if [ "$(jq '.new_count' /tmp/feed_new.json)" -gt 0 ]; then
  jq -r '.items[].paper_id' /tmp/feed_new.json | while read -r paper_id; do
    uv run nber-cli download "$paper_id" --save-base "$WEEK_DIR" --restrict true
  done
fi
```

### What feed does not do

- It does not search the historical NBER catalog. Use `nber-cli search ...` for that.
- It does not guarantee that every NBER paper ever published appears. It only reflects the current `new.xml` RSS feed.
- It does not download PDFs automatically. Combine it with `nber-cli download` for that.
- It does not deduplicate by title or DOI; deduplication is by NBER paper ID extracted from the item link.
- It does not expire cache entries automatically. Use `feed clean` to manage size.

## Output Formats

Use default text output for humans. Use JSON when the result should be consumed by another program or agent:

```bash
uvx nber-cli search "inflation" --format json
uvx nber-cli info w25000 --format json
```

## Common Failures

Interpret download errors conservatively:

- `403` means NBER denied access for the current IP, institution, account, session, download limit, or paper access policy.
- `404` means the paper or PDF endpoint was not found.
- Timeout or network errors usually mean the user should retry later or check connectivity.
- A paper's publication date alone does not prove the current user can download the PDF.

## Access Policy

NBER-CLI must not bypass NBER controls. Do not suggest proxy rotation, credential sharing, CAPTCHA bypass, account automation, request-signature tampering, or other access-circumvention behavior. If NBER returns denial, limits, redirects, or access pages, surface the response clearly and stop.

## Report Issues

If the user finds a bug or unexpected behavior in NBER-CLI, direct them to report it at `https://github.com/sepinetam/nber-cli/issues`.
