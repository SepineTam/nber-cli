# Desktop App

NBER-CLI Desktop is the recommended interface for researchers. It is a local Tauri 2 and React workspace for following, reading, and organizing NBER working papers without installing Python, uv, or a browser extension.

The current repository version is **0.11.0**. Desktop and the Python package use the same version number and release tag. Desktop installers are published on GitHub Releases; the Python package is published on PyPI.

## Install

Download packages only from the project's [official GitHub Releases](https://github.com/sepinetam/nber-cli/releases/latest) page.

| Platform | Package label | Device |
| --- | --- | --- |
| macOS Apple silicon | `macOS-arm64.dmg` | Mac with an M-series processor |
| macOS Intel | `macOS-x64.dmg` | Intel-based Mac |
| Windows | `Windows-x64.exe` | 64-bit Windows |
| Linux | `Linux-x64.AppImage` or `Linux-x64.deb` | 64-bit Linux desktop |

The installer includes a one-shot worker built from the same Python implementation as the CLI. The worker starts only for initialization or Feed refresh, then exits. Desktop does not start the optional `nber-server`, does not open a listening port, and does not require a system Python installation.

## Unsigned Release Notice

Current installers are not code-signed or notarized because the project does not have paid Apple and Windows certificates. macOS Gatekeeper or Windows SmartScreen may warn on first launch.

Before overriding a warning:

1. Confirm that the file came from the official `SepineTam/NBER-CLI` GitHub Release.
2. Confirm that its version, operating system, and CPU architecture match your computer.
3. Do not continue with an installer received through a mirror, email, or chat attachment.

On macOS, use **System Settings → Privacy & Security → Open Anyway** only after those checks. If macOS reports that the app is damaged, move it to `/Applications`, then run:

```bash
xattr -cr /Applications/NBER-CLI\ Desktop.app
```

On Windows, select **More info → Run anyway** only for the official file you verified.

## First Launch

Desktop validates and opens the configured SQLite database when it already exists. On a new installation the database and Feed are created by the first successful refresh:

1. Open Desktop.
2. Select **同步最新论文 (Refresh)** in the Feed toolbar.
3. Wait for the synchronization notice. The worker stores the Feed and, when `info.cache_enabled` is true, prepares paper details in the local database.
4. Select a paper to open its local detail record. Opening it also marks it read.

A failed refresh does not delete existing local data. If some paper details cannot be prepared, the notice reports the failure count and the next refresh retries records that still lack required metadata. When the shared info cache is disabled, Desktop deliberately skips metadata prefetch, so full details and NBER-derived Topics/Programs may remain unavailable.

## Research Workflow

### Browse and filter

- **全部 / 未读 (All / Unread)** filters the currently loaded local Feed items.
- The search box matches title, author, paper ID, and visible tag text.
- The tag selector filters papers by one visible tag.
- **加载更多 (Load more)** reads the next local page; it does not make a network request.
- The Feed header shows the number of papers indexed locally and the last successful refresh time.

Search and filters operate on items already loaded into the Desktop list. They are not a replacement for the CLI's remote NBER search command.

### Read a paper record

Selecting a Feed row opens the cached title, authors, date, abstract, NBER URL, publication information, Topics, and Programs when available. The right preview is 420 px wide by default:

- Drag the divider to resize it between 360 px and 640 px.
- Use the divider's arrow keys to change the width by 16 px, or hold Shift for 48 px steps.
- Use Home or End on the divider to select the minimum or maximum width.
- Double-click the divider to return to 420 px.
- The chosen width is stored in the webview's local storage and restored on the same device.

Desktop shows metadata and opens the public NBER page. It does not currently provide an in-app PDF download button; use an AI agent, the CLI, or the NBER page when a PDF download is required.

### Manage reading state

Opening a paper marks it read. Use the eye control in the detail pane to mark it unread or read again. This state is stored in the shared `read_status` table and is also visible to the optional local HTTP API.

### Organize with tags

After a refresh prepares paper metadata, Desktop seeds visible tags from NBER **Topics** and **Programs**. You can:

- Add a private local tag.
- Rename a local tag.
- Edit an NBER-derived tag; Desktop hides the original locally and creates a user tag with the new text.
- Remove a local tag, or hide an NBER-derived tag on this device.
- Search and filter the loaded Feed by visible tags.

Tag edits never change NBER data. Raw NBER tags, user tags, and local hiding choices are stored separately so a later refresh can synchronize source metadata without overwriting local organization.

### Copy citations

The detail pane can copy BibTeX, APA, MLA, Harvard, Chicago, or GB/T 7714 text to the clipboard. Review the result before publication: citation output is generated from the metadata currently stored locally, which may be incomplete or may differ from a journal's house style.

## Settings

| Setting or control | Valid value | Behavior |
| --- | --- | --- |
| Automatic Feed refresh | Positive integer minutes, default `60` | Refresh runs only while the app is open, initialized, visible, and not already refreshing. |
| Preview font size | `14`, `16`, or `18` px; default `16` | Changes abstract and paper-detail reading text. |
| Database path | Display only | Shows the active SQLite file. Change it with the shared CLI configuration, not from Desktop. |
| Config path | Display only | Shows the active `config.json`. |
| Open log directory | Button | Opens `~/.nber-cli/logs/`. |
| **检查更新 (Check for Updates)** | Manual button | Contacts GitHub's latest-release API only when clicked; it never installs an update. |

Desktop has no server-port setting because it does not run a local HTTP process. The legacy `desktop.server_port` field is used only by the optional HTTP API compatibility layer.

## Keyboard and Pointer Controls

| Control | Action |
| --- | --- |
| `Command/Ctrl+1` | Open the Feed view. |
| `Command/Ctrl+F` or `Command/Ctrl+K` | Open the Feed and focus paper search. |
| `Command/Ctrl+R` | Refresh the Feed. |
| `Command+,` on macOS | Open Settings through the native app menu. |
| `Escape` | Close the open citation-style menu. |
| Divider drag / keyboard controls | Resize the paper preview as described above. |

## Local Data and Network Access

| Path or store | Purpose |
| --- | --- |
| `~/.nber-cli/config.json` | Database path, cache settings, refresh interval, and preview font size. |
| `~/.nber-cli/nber.db` | Feed, metadata cache, behavior history, read state, and Desktop tag data. |
| `~/.nber-cli/logs/` | Desktop diagnostic directory. No long-running sidecar log is created. |
| Webview local storage | Preview-pane width on the current device. |

Desktop contacts NBER during Feed refresh. It contacts `api.github.com` only after **检查更新 (Check for Updates)** is selected and opens an NBER or GitHub page only after the related user action. It does not upload the SQLite database to project infrastructure.

Desktop honors `feed.db-path` from the shared config, including a path set by `nber-cli db migrate`. On macOS and Linux, the normalized database path must stay inside the user's home directory. An in-memory database is not supported.

If `config.json` is malformed, Desktop stops with an error instead of replacing the file. Restore or repair the JSON, then reopen the app.

## Backup, Update, and Removal

Before a file-level backup, close Desktop and stop any CLI, MCP, or HTTP process using the same database. Copy `nber.db` together with `nber.db-wal` and `nber.db-shm` when present, or use SQLite's online backup command. See [Persistence](persistence.md#backup).

Desktop does not install updates automatically. Use **检查更新 (Check for Updates)**, download the matching installer from the official Release, close Desktop, and install the new version over the existing application.

Removing the application does not intentionally delete `~/.nber-cli/`. Delete that directory separately only if you also want to remove the shared config, database, tags, caches, and logs. Back it up first if the data may be needed later.

## Troubleshooting

| Symptom | Check and consequence |
| --- | --- |
| Feed refresh fails | Confirm access to `nber.org`, then retry. Existing local rows remain available. |
| Some details were not prepared | Refresh again later. The Feed summary remains usable, but full metadata or source tags may be missing. |
| Paper search finds fewer items than expected | Select **加载更多 (Load more)**; Desktop filters loaded local rows, while CLI `search` queries NBER remotely. |
| Paper details fail to open | The cached detail may not exist yet. Refresh the Feed; removed or restricted source pages can still fail. |
| Custom database is missing | Check `feed.db-path`; on macOS/Linux it must resolve inside the home directory. |
| Database is reported as newer or incompatible | Upgrade Desktop. It refuses to write a database whose schema version does not equal its supported version. |
| Config file is invalid | Repair or restore the JSON. Desktop deliberately does not overwrite malformed configuration. |
| Update check fails | Check access to `api.github.com`; this does not affect local reading or NBER Feed data. |

For exact table behavior and recovery precautions, see [Persistence](persistence.md). For a task-by-task walkthrough, see the [User Manual](user-manual.md).
