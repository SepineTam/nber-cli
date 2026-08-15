# NBER-CLI Desktop

NBER-CLI Desktop is the researcher-facing Tauri v2 and React workspace. Feed refresh and metadata prefetch run through a bundled one-shot worker built from the same Python code as the CLI. Startup, paper opening, read state, and tags use the local SQLite database. Users do not install Python or uv, and no local web server or long-running sidecar is started.

Desktop and the Python CLI share the configured database, including `feed_items`, `info_cache`, and `read_status`. A custom `feed.db-path` created by `nber-cli db migrate` is honored when it points inside the user's home directory.

## Development

From the repository root:

```bash
cd desktop
npm install
npm run tauri dev
```

The React frontend calls these native Tauri commands:

- `get_config`
- `get_feed`
- `refresh_feed`
- `get_paper`
- `set_paper_read_status`
- `add_paper_tag`
- `rename_paper_tag`
- `remove_paper_tag`
- `get_settings`
- `save_settings`

The optional Python HTTP API remains available for other local integrations, but Desktop does not use it. Rust reads local Feed and paper data, writes read/unread state, and manages Desktop-only tag tables. NBER network, parsing, and metadata-cache rules stay in the shared Python implementation.

## Build App

```bash
uv sync --dev --group desktop-build
uv run python scripts/build-desktop-worker.py --clean
cd desktop
npm run build
npm run tauri build
```

The resulting installer contains its own Python runtime, so end users do not need Python or uv. Code signing remains optional because the project currently ships unsigned packages.

## Verification

Run the repository gates before preparing a Desktop build:

```bash
uv run ruff check .
uv run pytest
cd desktop
npm run lint
npm run test
npm run build
cd src-tauri
cargo test --locked
```

After building a package, verify its contents and startup flow:

```bash
uv run python scripts/check-desktop-release.py --platform macos --max-mb 150
uv run python scripts/smoke-desktop-app.py --install-from-package
```

On Windows or Linux, replace only the first command's `--platform` value with `windows` or `linux`; the smoke script detects its platform automatically. The package check fails if the bundled one-shot worker is missing or a legacy HTTP sidecar is present. The `150` MB threshold matches the normal release gate; signed-package workflows may apply an additional stricter check.

## Release

GitHub Actions builds macOS arm64/x64, Windows x64, and Linux x64 artifacts from a `v*` tag. The same tag is used for the Python package and Desktop app. Pushing `v0.11.0` creates or updates a draft GitHub Release titled `NBER-CLI v0.11.0`; publish it after all platform artifacts have uploaded successfully.

Before tagging, keep these versions aligned:

- `pyproject.toml`
- `desktop/package.json` and `desktop/package-lock.json`
- `desktop/src-tauri/tauri.conf.json`, `Cargo.toml`, and `Cargo.lock`
- Claude and Codex plugin manifests

Signing is not required. If paid certificates are added later, set `DESKTOP_REQUIRE_SIGNING=true` and configure the signing secrets documented in the release workflow.
