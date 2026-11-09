# CLI 参考

可执行命令是 `nber-cli`。

```bash
nber-cli [--version] <command> [options]
```

## 全局选项

| 选项 | 说明 |
| --- | --- |
| `-v`, `--version` | 打印已安装的 NBER-CLI 版本。 |
| `-h`, `--help` | 显示命令帮助。 |
| `--verbose` | 启用调试日志输出到 stderr 和日志文件。 |
| `-c`, `--config <path>` | 仅在本次运行中使用指定的配置文件。 |

不带子命令运行 `nber-cli` 会打印顶层帮助并成功退出。

## 命令

| 命令 | 用途 |
| --- | --- |
| `download` | 下载一篇或多篇论文 PDF。 |
| `info` | 显示单篇论文的元数据和摘要。 |
| `cite` | 复制论文引用，或输出到 stdout。 |
| `search` | 搜索 NBER 工作论文。 |
| `db` | 管理本地 SQLite 数据库。 |
| `feed` | 管理 NBER 最新工作论文 RSS feed 的本地缓存。 |
| `config` | 查看和编辑 `~/.nber-cli/config.json`。 |
| `doctor` | 检查本地安装、配置、数据库和包版本状态。 |
| `mcp-server` | 启动给 Agent 使用的 MCP server。 |

## cite

复制一篇 NBER 工作论文的完整参考文献条目：

```bash
uvx nber-cli cite w1234
uvx nber-cli cite w1234 -f apa
uvx nber-cli cite w1234 --format gb
uvx nber-cli cite w1234 --stdout > references.bib
uvx nber-cli cite w1234 --refresh
```

| 参数 | 说明 |
| --- | --- |
| `paper_id` | 正数论文编号，如 `w1234` 或 `1234`，不区分大小写。 |
| `--format`, `-f` | `bib`（默认，别名 `bibtex`）、`apa`、`mla`、`harvard`、`chicago`、`gb`（别名 `gbt7714`）。 |
| `--stdout` | 仅将引用写入标准输出，不访问剪贴板。 |
| `--refresh` | 重新获取元数据，复用 `info` 的缓存设置。 |

格式分别面向 APA 第 7 版、MLA 第 9 版、Chicago 第 18 版参考文献表和 GB/T 7714—2025 顺序编码制条目（不分配列表序号）。Harvard 没有统一规范，本项目固定使用作者—年份工作论文格式。输出均为纯文本，不含斜体或 Markdown；正式使用时需核对期刊要求及有歧义的作者姓名。

引用始终指向 NBER 工作论文，不自动替换为期刊发表版本。BibTeX 使用 `@techreport` 和稳定引用键 `nberw1234`，转义 TeX 特殊字符，缺失作者或年份时省略对应字段；其他格式以 `Unknown author` / `n.d.` 表示缺失信息。现有元数据模型不含 DOI，使用论文 URL。国标条目包含本机访问日期，不推断出版地。

复制成功仅向 stderr 输出提示。复制失败时仍向 stdout 输出引用，向 stderr 说明原因，并以退出码 1 结束。参数错误在获取前返回退出码 2；获取或格式化失败返回 1，不修改剪贴板。

macOS 使用 `pbcopy`，Windows 使用 PowerShell `Set-Clipboard`，Linux 使用 `wl-copy`（Wayland）或 `xclip` / `xsel`（X11），需要桌面会话及对应工具。服务器或 SSH 环境建议使用 `--stdout`；远程运行操作的是远程主机的剪贴板。

## download

下载单篇论文：

```bash
nber-cli download w34567
```

下载到明确文件：

```bash
nber-cli download w34567 --file papers/w34567.pdf
nber-cli download w34567 -f papers/w34567.pdf
```

下载到目标目录：

```bash
nber-cli download w34567 --save-base papers/nber
nber-cli download w34567 -s papers/nber
```

批量下载：

```bash
nber-cli download --batch w34567 w25000 w32000 --save-base papers/nber
nber-cli download -b w34567 w25000 w32000 -s papers/nber
```

### download 选项

| 选项 | 说明 |
| --- | --- |
| `paper_id` | 单篇下载时可选的位置参数，例如 `w34567`。 |
| `--file`, `-f` | 单篇下载的明确 PDF 输出路径。 |
| `--save-base`, `-s` | 生成 `<paper_id>.pdf` 文件的目标目录，默认是当前工作目录。 |
| `--batch`, `-b` | 要并发下载的一组论文编号。 |
| `--restrict` | 启用当前的工作目录字面检查。默认 `true`；单次调用可用 `--restrict false` 关闭。 |
| `--concurrency`, `-c` | 最大并发下载数。会覆盖 `download.concurrency` 配置值。 |

### download 规则

- 单篇位置参数不能和 `--batch` 同时使用。
- `--file` 只支持单篇论文。
- 批量模式只支持 `--save-base`。
- 如果没有传入 `--file` 或 `--save-base`，PDF 会保存到当前工作目录。
- 如果论文不可下载，NBER-CLI 会以退出码 `1` 退出，并打印可读错误信息。

### download 文件系统行为

!!! warning "该限制不是安全沙箱"
    0.10.0 的受限模式会比较绝对路径片段，但不会解析 `..` 或符号链接。因此，构造后的路径可能通过检查，却仍写到工作目录之外。请使用简单相对文件名；输入不可信时，把进程运行在隔离工作目录中；不要把 `--restrict` 当作操作系统级安全边界。

- **已有文件会被覆盖。** 目标 PDF 路径已经存在时，NBER-CLI 会把新字节直接写入并覆盖原文件。没有“较新则跳过”或“失败时保留旧文件”的模式。
- **不会做原子 rename。** 下载会先把整段响应体读入内存，再通过一次 `write_bytes` 调用写入目标路径。进程被杀掉、宿主机断电或磁盘在写入过程中写满，目标路径上都可能留下空文件、被截断的文件或只有部分字节的文件。失败路径上不会保留原来的旧文件。
- **父目录会自动创建。** 解析后的输出路径的父目录会用 `mkdir(parents=True, exist_ok=True)` 创建。中间目录缺失不会导致失败，但进程需要对最深的已存在祖先目录有写权限。
- **路径按字面值解析。** 传给 `--file` 的字符串（或者由 `--save-base` 推导出的 `<paper_id>.pdf`）会按字面值使用。相对路径相对于当前工作目录解析。`~` **不会** 被展开；如果需要 `~` 相对路径，请让 shell 先做展开。
- **单篇下载是全内存的。** 在任何磁盘写入发生之前，PDF 的完整内容会先被缓冲进内存，因此单篇下载在传输过程中始终把整篇 PDF 放在内存里。非常大的 PDF 可能短暂占用数百 MB 内存。
- **Python API 调用方负责自己传入的 session。** `download_paper` 和 `download_paper_to_file` 接受自定义 `aiohttp.ClientSession`；其生命周期、超时和连接器限制由调用方负责，NBER-CLI 仍执行固定尝试次数的重试辅助逻辑。`download_multiple_papers` 目前不接受 session 参数。

Python API 部分请参见 [Python API — 下载 PDF](python-api.md#pdf)。

## info

显示论文元数据：

```bash
nber-cli info w25000
```

显示全部可用字段：

```bash
nber-cli info w25000 --all
```

返回 JSON：

```bash
nber-cli info w25000 --format json
nber-cli info w25000 -f json
```

### info 选项

| 选项 | 说明 |
| --- | --- |
| `paper_id` | 必填论文编号，可以带 `w` 前缀，也可以不带。 |
| `--all`, `-a` | 如果可用，包含相关字段和 published-version 信息。 |
| `--format`, `-f` | 输出格式：`list` 或 `json`，默认是 `list`。 |
| `--refresh` | 跳过本地 `info_cache` 并直接从 NBER 重新拉取。缓存开启时，新数据会写回缓存。 |

当缓存开启且缓存条目尚未超过配置的 TTL 时，重复执行 `info` 会从本地数据库返回。TTL 到期后的第一次 `info` 调用，或任何携带 `--refresh` 的调用，都会执行实时网络拉取。

TTL 是**滑动**的：每次缓存命中都会更新 `last_fetched_at` 并把 `fetch_count` 加 1，所以被反复查询的论文，其缓存副本会从“最近一次命中”起继续保留至少 `cache_ttl_days` 天。因此“最近一次拉取时间”指的是“最近一次本地命中”，而不是“最近一次从 NBER 网络拉取”。`--refresh` 会无条件跳过缓存并写入一条新记录。

MCP 的 `get_paper_info` 工具遵循相同的缓存行为，但不接受每次调用的 `--refresh` 参数。该工具始终遵守当前的 `info_cache` 开关和 TTL 设置；需要强制刷新的 Agent 应先关闭缓存、调用 `get_paper_info`，再重新打开缓存（或者依赖 TTL 到期后的下一次调用）。

## info cache

管理 `info_cache` 的读取行为并清理缓存记录。

显示当前缓存状态、TTL 和已缓存行数：

```bash
nber-cli info cache
nber-cli info cache status
```

`info cache` 和 `info cache status` 等价——两者都打印同一份状态视图（缓存启用/禁用、当前 TTL、已缓存行数）。提供显式 `status` 子动作是为了和 `clear`/`clean` 保持对称，也是为了让偏好明确形式的脚本更易读。

全局开关缓存：

```bash
nber-cli info cache --turn-on
nber-cli info cache --turn-off
```

设置缓存刷新间隔（天）：

```bash
nber-cli info cache --set-refresh 7
nber-cli info cache --set-refresh 30
```

`--set-refresh` 必须是正整数。新值会写入 `~/.nber-cli/config.json`，并在后续每次 `info` 调用中作为 TTL 生效。

清理 30 天内没有刷新的缓存记录：

```bash
nber-cli info cache clear
nber-cli info cache clear --days 30
```

清理全部缓存记录：

```bash
nber-cli info cache clear --all
nber-cli info cache clean
```

`info cache clean` 是 `info cache clear --all` 的便利别名。

按 `last_fetched_at` 日期清理缓存记录：

```bash
nber-cli info cache clear --end-date 2026-06-01
nber-cli info cache clear --start-date 2026-05-01 --end-date 2026-06-01
```

只提供 `--end-date` 时，会从最早的缓存记录清理到该结束日期。`--start-date` 和 `--end-date` 都是前后包含的。只提供 `--start-date` 是无效的。

删除前，`info cache clear` 会先打印匹配到的缓存记录数量，并要求确认：

```text
This operation is irreversible.
Deleted info cache records may be fetched again from NBER.
Continue? [y/N]:
```

只有输入 `y` 或 `Y` 才会继续。其他输入都会中止，不删除记录。

### info cache 选项

| 子命令 | 选项 | 说明 |
| --- | --- | --- |
| (无) | `--turn-on` | 全局启用 info cache。 |
| (无) | `--turn-off` | 全局禁用 info cache。 |
| (无) | `--set-refresh` | 设置 info cache 刷新间隔（天），必须是正整数。 |
| `status` | — | 打印当前缓存状态、TTL 和已缓存行数；与不带子动作的 `info cache` 等价。 |
| `clear` | `--days` | 清理这么多天没有刷新的缓存记录，默认是 `30`。 |
| `clear` | `--all` | 清理全部 info cache 记录。 |
| `clear` | `--start-date` | 清理 `last_fetched_at` 在该日期及之后的缓存记录，格式为 `YYYY-MM-DD`。 |
| `clear` | `--end-date` | 清理 `last_fetched_at` 在该日期及之前的缓存记录，格式为 `YYYY-MM-DD`。 |
| `clean` | — | `clear --all` 的别名。 |

## search

按查询词搜索：

```bash
nber-cli search "Labor Economic"
```

使用日期筛选：

```bash
nber-cli search "minimum wage" --start-date 2024-01-01 --end-date 2024-12-31
```

调整分页：

```bash
nber-cli search "inflation" --page 2 --per-page 50
```

返回 JSON：

```bash
nber-cli search "inflation" --format json
nber-cli search "inflation" -f json
```

### search 选项

| 选项 | 说明 |
| --- | --- |
| `query` | 必填搜索词，可以是标题、编号、作者、摘要片段或关键词。 |
| `--start-date`, `--start` | 只包含该日期及之后的论文，格式为 `YYYY-MM-DD`。 |
| `--end-date`, `--end` | 只包含该日期及之前的论文，格式为 `YYYY-MM-DD`。 |
| `--page` | 要获取的结果页，默认是 `1`。 |
| `--per-page` | 每页结果数量，允许值为 `20`、`50`、`100`，默认是 `20`。 |
| `--format`, `-f` | 输出格式：`list` 或 `json`，默认是 `list`。 |

只提供 `--start-date` 时，NBER-CLI 会自动使用当前日期作为结束日期。

## feed

`feed` 用于处理 NBER 最新工作论文 RSS feed 和本地数据库。数据库会记录哪些 RSS 条目已经见过，因此 `feed fetch` 默认只显示新发现的论文。

### feed fetch

获取 RSS feed，把所有获取到的条目写入缓存，并默认只显示新的条目：

```bash
nber-cli feed fetch
```

显示所有获取到的 RSS 条目，包括缓存中已经存在的条目：

```bash
nber-cli feed fetch --display-all true
nber-cli feed fetch --display-all
```

`--display-all` 接受布尔值。解析器会识别（不区分大小写、允许前后空格）`true`、`false`、`1`、`0`、`yes`、`no`、`y`、`n`、`on`、`off`。不传值（只写 `--display-all`）时默认为 `true`。任何其他取值都会被 argparse 拒绝，并以退出码 `2` 退出。

限制输出数量：

```bash
nber-cli feed fetch --max-items 5
```

当提供 `--max-items` 且没有提供 `--display-all` 时，`--display-all` 默认会变成 `true`。因此 `nber-cli feed fetch --max-items 5` 会显示本次获取到的前 5 个 RSS 条目，而不是在没有新条目时显示空结果。

返回 JSON：

```bash
nber-cli feed fetch --format json
nber-cli feed fetch -f json
```

NBER-CLI 会严格解析 RSS XML。为了兼容已知的上游格式问题，程序只会修复 RSS `title` 和 `description` 文本中后接空白或数字的未转义 `<`；其他 XML 格式错误仍会被拒绝。解析错误会以退出码 `1` 退出，在可用时输出包含行号和列号的简洁错误信息，并且不会打印命令 usage。

### feed clean

清理 feed 缓存数据库记录。这个操作删除的是本地缓存记录，不会影响 NBER。被删除的缓存记录如果仍然出现在 RSS feed 中，后续可能会再次作为新条目被获取。

清理 30 天没有再次出现的记录：

```bash
nber-cli feed clean
nber-cli feed clean --days 30
```

清理全部缓存记录：

```bash
nber-cli feed clean --all
```

按 last-seen 日期清理记录：

```bash
nber-cli feed clean --end-date 2026-05-31
nber-cli feed clean --start-date 2026-05-01 --end-date 2026-05-31
```

只提供 `--end-date` 时，会从最早的缓存记录清理到该结束日期。`--start-date` 和 `--end-date` 都是前后包含的。只提供 `--start-date` 是无效的。

删除前，`feed clean` 会先打印匹配到的缓存记录数量，并要求确认：

```text
This operation is irreversible.
Deleted cache records may be fetched again as new items if they still appear in the RSS feed.
Continue? [y/N]:
```

只有输入 `y` 或 `Y` 才会继续。其他输入都会中止，不删除记录。

### feed 选项

| 子命令 | 选项 | 说明 |
| --- | --- | --- |
| `fetch` | `--display-all [true\|false]` | 显示所有获取到的 RSS 条目，而不是只显示新条目。可接受 `true`/`false`/`1`/`0`/`yes`/`no`/`y`/`n`/`on`/`off`（不区分大小写）。不传值时默认为 `true`。 |
| `fetch` | `--format`, `-f` | 输出格式：`list` 或 `json`，默认是 `list`。 |
| `fetch` | `--max-items` | 最多显示多少个 feed 条目。 |
| `clean` | `--days` | 清理这么多天没有再次出现的缓存记录，默认是 `30`。 |
| `clean` | `--all` | 清理全部 feed 缓存记录。 |
| `clean` | `--start-date` | 清理 last-seen 日期在该日期及之后的缓存记录，格式为 `YYYY-MM-DD`。 |
| `clean` | `--end-date` | 清理 last-seen 日期在该日期及之前的缓存记录，格式为 `YYYY-MM-DD`。 |

## db

`db` 用于管理本地 SQLite 数据库，`info`、`search`、`download` 和 `feed` 会用这个数据库存放缓存和行为日志。数据库保存在用户机器上，并通过 SQLModel/SQLAlchemy 访问；命令参数既接受普通文件路径，也接受 `sqlite:///...` URL。

### db init

初始化数据库，并把数据库路径写入用户配置：

```bash
nber-cli db init
nber-cli db init --db-path ~/.nber-cli/nber.db
nber-cli db init --db-path sqlite:////Users/name/data/nber.db
```

如果省略 `--db-path`，默认数据库路径是 `~/.nber-cli/nber.db`。

如果用户原来使用 0.3.0 留下的 `~/.nber-cli/feed.db`，并且还没有 `nber.db`，NBER-CLI 会沿用这个旧文件。第一次执行数据库相关操作时，旧 schema 会逐级升级到当前版本 3。

### db migrate

把数据库移到新路径并更新用户配置：

```bash
nber-cli db migrate ~/data/nber.db
nber-cli db migrate sqlite:////Users/name/data/nber.db
```

迁移会移动 SQLite 数据库文件，以及 `-wal`、`-shm`、`-journal` 等 SQLite sidecar 文件。目标路径不能已经存在。

### db 选项

| 子命令 | 选项 | 说明 |
| --- | --- | --- |
| `init` | `--db-path` | SQLite 数据库路径或 `sqlite:///...` URL，默认是 `~/.nber-cli/nber.db`。 |
| `migrate` | `new_db_path` | 新的 SQLite 数据库路径或 `sqlite:///...` URL。 |

## config

查看和编辑 `~/.nber-cli/config.json`：

```bash
nber-cli config show
nber-cli config get info.cache_ttl_days
nber-cli config set download.concurrency 5
nber-cli config verify
```

### config 选项

| 子命令 | 参数 | 说明 |
| --- | --- | --- |
| `show` | — | 打印当前配置。 |
| `get` | `<key>` | 打印点分 key 的值，例如 `info.cache_ttl_days`。 |
| `set` | `<key> <value>` | 把点分 key 设置为推断后的值（`true`/`false`/整数/字符串）。 |
| `verify` | — | 根据 `config.schema.json` 校验配置。 |

## doctor

检查当前本地安装与运行状态：

```bash
nber-cli doctor
```

报告会包含已安装版本、PyPI 最新版本、可执行文件路径、包路径、Python 可执行文件、配置文件路径与内容、数据库路径、数据库是否存在、schema 版本、数据库大小，以及最近一次有记录的 query/download/info/feed 活动时间。

当 PyPI 上有更新版本时执行升级：

```bash
nber-cli doctor --fix-version
```

该命令会先检查当前版本是否已经最新。如果需要升级，它会用 `uvx --refresh nber-cli -v` 刷新 `uvx` 执行缓存，用 `uv tool upgrade nber-cli` 升级 `uv tool` 安装，用 `pipx upgrade nber-cli` 升级 `pipx` 安装，否则回退到当前 Python 的 `python -m pip install --upgrade nber-cli`。升级命令完成后会再次检查版本；失败详情会写入 `~/.nber-cli/debug.log`。

## mcp-server

启动默认 stdio MCP server：

```bash
nber-cli mcp-server
```

启动 HTTP transport：

```bash
nber-cli mcp-server --transport streamable-http --port 8000
```

非默认端口需要用 `--yes` 确认：

```bash
nber-cli mcp-server --transport streamable-http --port 9000 --yes
```

### mcp-server 选项

| 选项 | 说明 |
| --- | --- |
| `--transport` | 传输机制：`stdio`、`sse` 或 `streamable-http`，默认是 `stdio`。 |
| `--port` | HTTP transport 使用的端口，默认是 `8000`。 |
| `--yes` | 确认使用非默认端口。 |

客户端配置和工具详情见 [MCP Server](mcp.md)。

## 退出码

| 退出码 | 含义 |
| --- | --- |
| `0` | 命令成功完成，或帮助信息已打印。 |
| `1` | 运行时失败，例如下载失败、网络错误、解析错误或其它未处理异常。 |
| `2` | 命令行参数无效。argparse 会抛出 `SystemExit(2)` 并把 usage 打印到 stderr。 |

下面是一些容易漏掉的细节：

- 单篇 `download` 失败会以退出码 `1` 退出。成功时的 `Successfully downloaded <id> to <path>` 行写到 stdout，失败时的 `Failed to download <id>: <reason>` 行写到 stderr。`download_log` 中的日志行在失败信息打印之前写入。
- 批量 `download` 会跑完所有请求的论文，只有在最后存在失败论文时才以退出码 `1` 退出。成功的文件路径写到 stdout（`Successfully downloaded ...`），失败和每条失败原因写到 stderr。**只有全部成功** 时退出码才是 `0`。
- `feed fetch` 遇到 RSS 解析失败时会以退出码 `1` 退出，并向 stderr 写入简洁错误信息，不打印命令 usage；在可用时，错误信息会包含 XML 行号和列号。
- `db init`、`db migrate`、`info cache clear` 和 `feed clean` 会向 stderr 打印确认提示。用户在确认提示中拒绝时（`Abort.` 会被打印到 stderr）命令以退出码 `0` 中止。确认后真正执行删除时，成功完成会以 `0` 退出。
- 数据库记录失败（`record_query`、`record_download`、`record_info`、`touch_info_cache`、`write_info_cache`）会向 stderr 打印一行 `warning: failed to ...`，**不会**抛出异常，主命令的退出码也不受影响。
- 下载模块先把整段 PDF 读入内存，再一次性写入磁盘。发生在网络读取和磁盘写入之间的失败（进程被 kill、磁盘写满、权限被收回）通常以 Python 异常的形式抛出；用户会在 stderr 上看到 traceback，进程以退出码 `1` 退出。这里**没有**原子 rename 保证，目标文件在这种失败下可能留下空文件或只写了一半的内容。

## 输出格式

`info`、`search` 和 `feed fetch` 默认使用 `list`，这是一种适合人阅读的文本格式。需要把输出交给脚本或 Agent 工作流时，请使用 `--format json`。

脚本可参考的简单规则：

- **stdout** 承载人类可读的输出，或 `--format json` 时的 JSON 负载。
- **stderr** 承载每条论文的错误信息、与主负载无关的成功信息、后台日志失败时的 `warning: ...` 行，以及破坏性命令的确认提示。缓存命中不会额外输出 stderr 提示。

也就是说，想要 JSON 负载的脚本可以用 `2>/dev/null`（或 `2>&-`）屏蔽 stderr；只想要错误信息的脚本可以用 `2>&1 >/dev/null` 把 stderr 提取出来。
