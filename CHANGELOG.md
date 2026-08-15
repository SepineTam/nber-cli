# Changelog

All notable changes to this project will be documented in this file.

This file is the canonical release history. The English mirror at `docs/en/changelog.md` and the Chinese mirror at `docs/zh/changelog.md` are generated from the same source content and must stay in lock-step. Any release commit updates all three together.

## [0.11.0] - 2026-08-15

### Added

- Added a Docker Compose setup for the local HTTP MCP service, including loopback-only port publishing, persistent metadata storage, and a container health check.
- Added multi-platform GHCR publishing when a GitHub Release is published.

### Changed

- HTTP MCP transports now expose only paper search and paper info; the download tool remains available through the default stdio transport.
- Added `--host` to `nber-cli mcp-server`, defaulting to `127.0.0.1`; the Docker image binds to `0.0.0.0` for Compose port forwarding.

### Documentation

- Reframed the project documentation around Desktop as the primary researcher interface, with CLI and MCP positioned as AI-agent and automation interfaces.
- Added bilingual user manuals and software specifications covering supported workflows, capability boundaries, persistence, source traceability, verification, and future registration-evidence preparation.
- Updated Desktop, architecture, configuration, persistence, development, and testing references to match the 0.10.0 code layout and behavior.

## [0.10.0] - 2026-07-21

### Added
- Added a draggable, keyboard-accessible divider for resizing the Desktop paper preview from 360px to 640px. The selected width is remembered across restarts, and double-clicking restores the 420px default.
- Added 14px, 16px, and 18px paper-preview font size options in Desktop settings, with 16px as the new default.
- Added `DESIGN.md` and `DESKTOP_UX.md` as the visual and interaction standards for the Desktop research workspace.

### Changed
- Redesigned Desktop as a denser academic research desk with clearer navigation, feed hierarchy, selected and unread states, paper typography, settings, and keyboard focus treatment.
- Increased the default paper-preview reading size while keeping navigation and feed density stable.

### Fixed
- Desktop now normalizes older feed and paper records that omit tag or metadata arrays, preventing undefined-property errors when existing local data is opened in the redesigned interface.

## [0.9.2] - 2026-07-19

### Added
- Added editable Desktop paper tags seeded from NBER Topics and Programs, with separate raw metadata, user tags, and local hiding preferences.
- Added tag chips, tag search, and tag filtering to the Desktop feed, plus add, rename, and remove controls in paper details.

### Changed
- Desktop Feed refresh now prefetches paper details into SQLite, while startup and paper opening read directly from the local database without invoking Python.
- The bundled one-shot Python worker remains the single implementation for NBER network requests and parsing; Desktop users still do not need Python or uv.

### Fixed
- Fixed NBER paper parsing so `info` now captures Topics and Programs from the Related section.
- Fixed slow paper opening and timeout-prone on-demand detail requests by preparing metadata during Feed refresh.
- Legacy cached papers without Topics or Programs are refreshed automatically, and Desktop-only tag tables are created without changing the shared CLI schema.

## [0.9.1] - 2026-07-18

### Changed
- Replaced Desktop's duplicated Rust RSS and paper-page implementation with a bundled one-shot worker built from the existing Python CLI code.
- Desktop users still do not need to install Python or uv; the required runtime is included in each installer and exits after each operation.
- Kept direct Rust/SQLite feed reads and read/unread updates while restoring Python as the single implementation for NBER network, parsing, and metadata-cache behavior.

### Fixed
- Fixed the 0.9.0 architecture that would have required feed and paper parsing rules to be maintained separately in Python and Rust.
- Release validation and package smoke tests now require the bundled worker and continue to reject the legacy long-running HTTP sidecar.

## [0.9.0] - 2026-07-17

### Added
- Added a native Rust data layer for Desktop feed listing, RSS refresh, paper metadata caching, settings, and read/unread state.
- Added Rust tests for CLI-compatible SQLite schema handling, custom database paths, RSS repair/parsing, paper-page parsing, and read status.

### Changed
- Desktop now talks directly to the configured SQLite database and NBER endpoints; it no longer starts, bundles, or requires a Python sidecar.
- Desktop refresh now performs the same RSS upsert and `feed_fetches` accounting as `nber-cli feed fetch`.
- Desktop now honors the CLI's configured `feed.db-path` and refuses to overwrite malformed configuration files.
- Release checks and installer smoke tests now require Python sidecar binaries to be absent.

### Removed
- Removed the Desktop service-port setting and the sidecar build/runtime lifecycle from the Tauri application and release workflow.

## [0.8.1] - 2026-07-16

### Added
- Added Linux x64 build support to the Desktop release workflow, producing AppImage and Debian packages alongside macOS and Windows artifacts.
- Added macOS keyboard shortcuts for Desktop: `Command-1` navigates to the feed, `Command-R` refreshes papers, and `Command-F` focuses paper search.
- Added a manual "Check for Updates" control in the Desktop app.

### Fixed
- Ensured the Desktop sidecar process is stopped and its process group is cleaned up when the application exits.

## [0.8.0] - 2026-07-13

### Added
- Added `nber-cli doctor` to show installed and PyPI versions, executable/package locations, config contents, database path, schema version, size, and last recorded activity. Added `nber-cli doctor --fix-version` to refresh `uvx` caches or upgrade installations detected as `uv tool`, `pipx`, or `pip`.
- Added the optional `server` extra plus the `nber-server` and `nber-sidecar` entry points for a loopback FastAPI service.
- Added a Tauri 2 Desktop app for macOS and Windows with a React research workspace, local feed sync, unread filtering, paper details, settings, and BibTeX/APA/MLA/Harvard/Chicago/GB/T citation copying.
- Added Alembic-managed database migrations and schema v3 with the `read_status` table. Existing v1 and v2 databases upgrade automatically without removing existing records.
- Added cross-platform Desktop build, artifact normalization, package validation, smoke-test, signing-validation, and notarization workflows.

### Changed
- Split the HTTP service into the independent `nber_server` package while continuing to reuse the existing `nber_cli` core and SQLite database.
- Kept FastAPI, Uvicorn, and Alembic out of the default CLI installation; local HTTP users install them through `nber-cli[server]`.
- Expanded the English and Chinese architecture, persistence, configuration, getting-started, testing, and Desktop documentation.

### Fixed
- Stabilized Desktop smoke tests on alternate local ports and added checks for bundled sidecars, installer signatures, and macOS notarization.
- Replaced the default Tauri branding and application icons with NBER-CLI Desktop assets.

## [0.7.0] - 2026-07-08

### Added
- Added a `--verbose` global flag and a rotating debug log at `~/.nber-cli/debug.log`. By default only warnings and errors are logged; `--verbose` or `NBER_CLI_DEBUG=1` enables debug-level output.
- Added `-c/--config <path>` global flag to use a custom config file for a single invocation without changing the default `~/.nber-cli/config.json`.

### Fixed
- Added a full set of browser-like request headers (User-Agent, Accept, Accept-Language, Sec-Fetch, etc.) to all NBER requests, replacing the minimal User-Agent-only headers. This restores access after NBER's CDN began rejecting minimal requests.

## [0.6.0] - 2026-07-05

### Changed
- Migrated the database layer from raw `sqlite3` to SQLModel/SQLAlchemy. All tables are now declared as SQLModel models with explicit indexes.
- `db init --db-path` and `db migrate <new_db_path>` now accept `sqlite:///path/to/nber.db` URLs in addition to file paths.
- Feed fetching, cache cleanup, query logging, download logging, info logging, and info-cache writes now use explicit SQLAlchemy sessions and commits.
- `config.schema.json` now describes the database path as a "Path or sqlite:/// URL".

### Added
- Added `sqlmodel>=0.0.24` and SQLAlchemy to project dependencies.
- Added CLI tests for `sqlite:///` database path handling.
- Added release notes for v0.6.0.

### Fixed
- Updated the version fallback in `cli.py` from `0.4.0` to `0.6.0`.

### Security
- RSS feed parsing now uses `defusedxml` to block XML external entity (XXE) and entity expansion attacks.
- CLI downloads are restricted to the current working directory and its subdirectories by default. Use `nber-cli download --restrict false` to override per invocation. The `download.restrict_dir` config key is stored and validated, but the current CLI default remains `true`.
- Database `init` and `migrate` paths on macOS and Linux must reside within the user's home directory.
- Synchronous HTTP requests enforce TLS 1.2 as the minimum version.
- Selected info/download failure paths now avoid raw exception text; download-log messages and soft database warnings use sanitized summaries or exception class names.

### Added
- `nber-cli config show` / `get <key>` / `set <key> <value>` / `verify` for inspecting and editing `~/.nber-cli/config.json`.
- `download.concurrency` configuration option (default `3`) and the `--concurrency` / `-c` CLI flag to cap concurrent downloads.
- `--restrict true|false` flag on `nber-cli download` to control directory restriction per invocation.
- `--yes` flag for `nber-cli mcp-server`; the existing `--port` option now requires explicit confirmation when set to a non-default value.
- `sse` transport for `nber-cli mcp-server`.
- JSON Schema (`config.schema.json`) for validating `~/.nber-cli/config.json`.
- Strict raw-configuration validation that reports malformed JSON, invalid section/value types, and schema-minimum violations without silently injecting defaults.
- Plugin manifests and marketplace metadata now share the package version, and the Claude plugin skill path uses the case-sensitive tracked `./skills/NBER-CLI` directory.
- Domain invariant validation in all core dataclasses (`NBER`, `NBERSearchResults`, `NBERFeedItem`, `NBERFeedFetchResult`, clean results, and download results).
- `get_config_value`, `set_config_value`, `read_config`, `write_config`, and `validate_config` exported from the package top level.
- Paper ID format validation (`w?\d+`) across CLI, download, and MCP entry points.
- Validation of fetched paper titles, positive citation IDs, and response/request paper-ID agreement before metadata is accepted.

### Changed
- Replaced legacy `typing.Dict`, `List`, and `Optional` aliases with modern Python 3.11 syntax.
- Added `mypy` configuration and strengthened type annotations across `cli.py`, `config_store.py`, and `fetcher.py`.
- `mcp-server` transport name corrected to `streamable-http`; the existing `--port` option now uses `--yes` confirmation for non-default values.
- Retry loops in `fetcher.py` now use exponential backoff capped at 30 seconds.
- `feed fetch` skips malformed individual RSS items instead of failing the entire feed.
- Invalid configured or per-call download concurrency values are rejected or fall back to the documented safe default instead of creating an invalid semaphore.
- Database schema-changing and data-writing operations reject databases with a future `PRAGMA user_version`; the diagnostic schema-version reader remains read-only.
- Feed fetching establishes/validates the local schema before the network request, then writes feed items plus fetch history transactionally after the response is parsed; cleanup operations pair schema validation/upgrade and deletion in one SQLite transaction.
- `download.py` enables `raise_for_status=True` on `ClientSession`.
- Error handling narrowed to specific network/timeout exception types with preserved exception chains.
- Removed the info cache hit hint that was printed to stderr on cached `info` lookups.

### Fixed
- `feed fetch` now tolerates unescaped `<` characters followed by whitespace or a digit in RSS title and description text while keeping strict XML parsing for all other malformed input.
- RSS parse failures now report their line and column when available, and `feed fetch` reports runtime parse errors with exit code `1` without printing command usage.

## [0.4.0] - 2026-06-04

### Added
- `nber-cli info --refresh` skips the local `info_cache` and re-fetches the paper from NBER. The new data is written back to the cache when the cache is enabled.
- `nber-cli info cache --turn-on` / `--turn-off` toggle the `info_cache` lookup globally and persist the state to `~/.nber-cli/config.json`.
- `nber-cli info cache --set-refresh <N>` sets the cache refresh interval in days. The value is persisted to `~/.nber-cli/config.json` and used as the TTL for every subsequent `info` call. Defaults to `30` days.
- `nber-cli info cache clear` with `--days`, `--all`, `--start-date`, or `--end-date` mirrors the `feed clean` parameter set, using `last_fetched_at` from the `info_cache` table. `nber-cli info cache clean` is a convenience alias for `clear --all`.
- `nber-cli info cache` (no sub-action) prints the current cache state, TTL, and cached row count.
- New `nber_cli.config_store` module: centralised read and write of `~/.nber-cli/config.json` plus the `InfoCacheSettings` dataclass and helpers (`get_info_cache_settings`, `set_info_cache_enabled`, `set_info_cache_ttl_days`).
- New `nber_cli.info_cache.get_paper_with_info_cache_result` async helper (in the `nber_cli.info_cache` module) that returns an `InfoCacheLookupResult` carrying the `NBER` paper and a `from_cache` flag, so callers (CLI and MCP) can surface a "loaded from cache" hint.
- Public Python API exports from the package top level: `InfoCacheSettings`, `clear_info_cache`, `count_info_cache`, `get_info_cache_settings`, `get_info_cache_ttl_days`, `is_info_cache_enabled`, `is_info_cache_expired`, `set_info_cache_enabled`, `set_info_cache_ttl_days`, `NBERInfoCacheClearResult`. `InfoCacheLookupResult` and `get_paper_with_info_cache_result` are exposed from the `nber_cli.info_cache` module rather than the package top level; import them as `from nber_cli.info_cache import ...`.

### Changed
- `~/.nber-cli/config.json` now carries an `info` section: `info.cache_enabled` (default `true`) and `info.cache_ttl_days` (default `30`). Missing or malformed fields fall back to defaults.
- `info` now prints a one-line stderr hint when the paper was served from the local cache, pointing to `nber-cli info <id> --refresh` for a fresh fetch.

## [0.3.1] - 2026-06-03

### Added
- `db init` and `db migrate` top-level subcommands replace `feed init` and `feed migrate`. The database is now general-purpose and stores feed cache, behavior logs, and paper metadata cache.
- `info_cache` table caches paper metadata fetched via `info` and the MCP `get_paper_info` tool. Subsequent lookups return immediately from the cache.
- `query_log`, `download_log`, and `info_log` tables record search keywords, download outcomes, and paper info lookups for later auditing.
- `schema_version` field written to `~/.nber-cli/config.json` so future schema migrations can roll forward safely.

### Changed
- Default database renamed from `feed.db` to `nber.db`. Existing `~/.nber-cli/feed.db` installations continue to work without manual steps.
- Database schema upgraded from `user_version = 1` to `user_version = 2`. Existing v1 databases are upgraded automatically on next CLI invocation; original `feed_items` rows are preserved.
- Database code consolidated into `nber_cli.db`. The original `init_feed_database`, `migrate_feed_database`, and `get_feed_database_path` helpers are kept as thin compatibility wrappers.

## [0.3.0] - 2026-06-03

### Added
- `feed init` subcommand: initialize a local SQLite feed cache and write its path to user config.
- `feed fetch` subcommand: fetch NBER's new working papers RSS feed, cache seen items, and show newly discovered papers by default.
- `feed fetch --max-items`: limit displayed feed output. When used without `--display-all`, display-all behavior is enabled automatically.
- `feed migrate` subcommand: move the feed cache database and SQLite sidecar files to a new path, then update user config.
- `feed clean` subcommand: clean cached feed database records by age, date range, or all records after interactive confirmation.
- Python API exports for feed cache helpers and feed result models.

### Changed
- Added user config support at `~/.nber-cli/config.json` for the feed cache database path.
- Expanded English and Chinese documentation for feed commands, configuration, Python API, and release notes.

## [0.2.0] - 2026-05-31

### Added
- `download` subcommand: single paper ID or batch mode (`--batch`), explicit file path (`--file`), target directory (`--save-base`).
- `info` subcommand: paper metadata with `--all` flag for full details and `--format json` option.
- `search` subcommand: full-text search with date filters (`--start-date`, `--end-date`), pagination (`--page`, `--per-page`), `--format json` option.
- `mcp-server` subcommand: MCP server for AI agent integration with stdio and streamable_http transports.

### Changed
- Reworked CLI into subcommand syntax (`nber-cli <subcommand>`).
- Simplified downloader to direct async HTTP PDF fetches (removed database-backed state tracking).
- Removed legacy web UI module and script entrypoint.

## [0.1.4] - 2025-08-09

### Added
- Added `--version` / `-v` flag to display current version.
- Added comprehensive help message with examples.
- Added `__main__.py` file to support `python -m nber_cli` usage.
- Added argument grouping for better CLI organization.
- Added automatic help display when no arguments are provided.
