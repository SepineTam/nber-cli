# 更新日志

这里记录项目的重要变更。

本页是仓库根 `CHANGELOG.md` 的中文镜像，英文镜像在 `docs/en/changelog.md`。每次发布提交都会同步更新三份内容。

## 0.11.0 - 2026-08-15

### Added

- 新增本机 HTTP MCP 服务的 Docker Compose 配置，包括仅 loopback 的端口发布、持久化元数据存储和容器健康检查。
- 新增在 GitHub Release 发布后运行的多架构 GHCR 发布工作流。

### Changed

- HTTP MCP transport 现在只提供论文搜索和论文信息；下载工具仍保留在默认 stdio transport 中。
- 为 `nber-cli mcp-server` 新增 `--host`，默认值为 `127.0.0.1`；Docker 镜像使用 `0.0.0.0` 以支持 Compose 端口转发。

### Documentation

- 将项目文档调整为以 Desktop 作为研究者主要入口，并把 CLI 与 MCP 定位为 AI Agent 和自动化入口。
- 新增中英文用户操作手册与软件规格说明，覆盖受支持流程、能力边界、持久化、源码追溯、验证和未来软件登记证据准备。
- 按 0.10.0 的代码布局与实际行为更新 Desktop、架构、配置、持久化、开发和测试参考。

## 0.10.0 - 2026-07-21

### Added
- Desktop 新增可拖动且支持键盘操作的分隔条，论文预览宽度可在 360px 至 640px 之间调整。宽度会在重启后保留，双击分隔条可恢复 420px 默认值。
- Desktop 设置新增 14px、16px 和 18px 三档论文预览字号，并将 16px 设为新默认值。
- 新增 `DESIGN.md` 与 `DESKTOP_UX.md`，作为 Desktop 研究工作台的视觉与交互规范。

### Changed
- 将 Desktop 重构为信息密度更合适的学术研究工作台，改进导航、Feed 层级、选中与未读状态、论文排版、设置页面和键盘焦点表现。
- 提高论文预览的默认阅读字号，同时保持导航与 Feed 的信息密度稳定。

### Fixed
- Desktop 现在会补齐旧版 Feed 和论文记录中缺失的标签或元数据数组，避免重新设计后的界面读取现有本地数据时出现 undefined-property 错误。

## 0.9.2 - 2026-07-19

### Added
- Desktop 新增可编辑的论文标签：默认来自 NBER Topics 与 Programs，官方原始标签、用户标签和本机隐藏记录分别保存。
- Desktop 论文列表新增标签胶囊、标签搜索和标签筛选，论文详情支持新增、改名和删除标签。

### Changed
- Desktop 刷新 Feed 时会把论文详情预取到 SQLite；启动和打开论文直接读取本地数据库，不再调用 Python。
- NBER 网络请求和页面解析仍统一使用内置的一次性 Python 工作器；Desktop 用户无需安装 Python 或 uv。

### Fixed
- 修复 NBER 论文页面解析，`info` 现在可以从 Related 区域获取 Topics 和 Programs。
- 通过刷新时提前准备详情，修复打开论文缓慢和容易超时的问题。
- 旧缓存缺少 Topics 或 Programs 时会自动重新获取；Desktop 专用标签表自动建立，不改变 CLI 共用数据库版本。

## 0.9.1 - 2026-07-18

### Changed
- 将 Desktop 中重复实现的 Rust RSS 与论文页面解析替换为由现有 Python CLI 代码打包的单次工作程序。
- Desktop 用户仍无需安装 Python 或 uv；每个平台的安装包都内置所需运行环境，并在每次操作完成后退出。
- Rust 继续直接读取 Feed 和更新已读/未读状态；NBER 网络请求、解析和论文缓存规则恢复为只有一套 Python 实现。

### Fixed
- 修正 0.9.0 中需要分别维护 Python 与 Rust 两套 Feed 和论文解析规则的架构问题。
- 发布检查和安装包 smoke test 现在要求内置工作程序存在，同时继续拒绝旧的长期运行 HTTP sidecar。

## 0.9.0 - 2026-07-17

### Added
- 为 Desktop 的 Feed 列表、RSS 刷新、论文元数据缓存、设置和已读/未读状态增加 Rust 原生数据层。
- 增加 Rust 测试，覆盖与 CLI 兼容的 SQLite schema、自定义数据库路径、RSS 修复与解析、论文页面解析和阅读状态。

### Changed
- Desktop 现在直接访问配置中的 SQLite 数据库和 NBER endpoint，不再启动、打包或依赖 Python sidecar。
- Desktop 刷新现在执行与 `nber-cli feed fetch` 相同的 RSS upsert 和 `feed_fetches` 计数。
- Desktop 现在读取 CLI 配置的 `feed.db-path`，并在配置文件损坏时拒绝覆盖原文件。
- 发布检查和安装包 smoke test 现在要求安装包中不存在 Python sidecar。

### Removed
- 从 Tauri 应用和发布工作流中移除 Desktop 服务端口设置及 sidecar 构建/生命周期。

## 0.8.1 - 2026-07-16

### Added
- 为 Desktop 发布工作流增加 Linux x64 构建支持，与 macOS 和 Windows 产物一起生成 AppImage 和 Debian 安装包。
- 为 Desktop 增加 macOS 快捷键：`Command-1` 切换到 Feed，`Command-R` 刷新论文，`Command-F` 聚焦论文搜索。
- 在 Desktop 应用里增加手动"检查更新"入口。

### Fixed
- 修复 Desktop 退出时 sidecar 进程未停止、进程组未清理的问题。

## 0.8.0 - 2026-07-13

### Added
- 新增 `nber-cli doctor`，用于显示已安装版本、PyPI 最新版本、可执行文件和包位置、配置内容、数据库路径、schema 版本、占用空间与最后记录的活动时间。新增 `nber-cli doctor --fix-version`，可刷新 `uvx` 缓存，或按检测到的 `uv tool`、`pipx`、`pip` 安装方式升级。
- 新增可选的 `server` extra，以及用于启动 loopback FastAPI 服务的 `nber-server` 和 `nber-sidecar` 入口。
- 新增面向 macOS 和 Windows 的 Tauri 2 Desktop 应用，包含 React 研究工作台、本地 feed 同步、未读筛选、论文详情、设置，以及 BibTeX、APA、MLA、Harvard、Chicago、GB/T 引用复制。
- 新增由 Alembic 管理的数据库迁移和带 `read_status` 表的 schema v3。已有 v1、v2 数据库会自动升级且不会删除原有记录。
- 新增跨平台 Desktop 构建、产物重命名、安装包校验、smoke test、签名校验和 macOS notarization 工作流。

### Changed
- 将 HTTP 服务拆分为独立的 `nber_server` 包，同时继续复用现有 `nber_cli` 核心和 SQLite 数据库。
- FastAPI、Uvicorn 和 Alembic 不进入默认 CLI 安装；需要本地 HTTP 服务时通过 `nber-cli[server]` 安装。
- 扩充中英文架构、持久化、配置、快速开始、测试和 Desktop 文档。

### Fixed
- 稳定 Desktop 在备用本地端口上的 smoke test，并增加内置 sidecar、安装包签名和 macOS notarization 检查。
- 用 NBER-CLI Desktop 品牌资源替换默认 Tauri 品牌和应用图标。

## 0.7.0 - 2026-07-08

### Added
- 新增全局参数 `--verbose` 与轮转调试日志文件 `~/.nber-cli/debug.log`。默认仅写入警告和错误；`--verbose` 或 `NBER_CLI_DEBUG=1` 可开启调试级别输出。
- 新增全局参数 `-c/--config <path>`，可在单次运行中指定自定义配置文件，不影响默认的 `~/.nber-cli/config.json`。

### Fixed
- 为所有 NBER 请求补全类浏览器请求头（User-Agent、Accept、Accept-Language、Sec-Fetch 等），替代原先仅含 User-Agent 的极简头，以恢复 NBER CDN 访问。

## 0.6.0 - 2026-07-05

### Changed

- 数据库层从原生 `sqlite3` 迁移到 SQLModel/SQLAlchemy。所有表均声明为带显式索引的 SQLModel 模型。
- `db init --db-path` 和 `db migrate <new_db_path>` 除文件路径外，现在也接受 `sqlite:///path/to/nber.db` URL。
- Feed 拉取、缓存清理、查询日志、下载日志、info 日志和 info 缓存写入现在使用显式的 SQLAlchemy Session 并提交。
- `config.schema.json` 将数据库路径描述为 "Path or sqlite:/// URL"。

### Added

- 项目依赖中新增 `sqlmodel>=0.0.24` 及其 SQLAlchemy 传递依赖。
- 新增针对 `sqlite:///` 数据库路径处理的 CLI 测试。
- 新增 v0.6.0 release notes。

### Fixed

- 将 `cli.py` 中的版本 fallback 从 `0.4.0` 更新为 `0.6.0`。

### Security

- RSS feed 解析改用 `defusedxml`，阻止 XML 外部实体（XXE）和实体展开攻击。
- CLI 下载默认限制在当前工作目录及其子目录。可使用 `nber-cli download --restrict false` 单次覆盖。`download.restrict_dir` 配置键会被存储和校验，但当前 CLI 默认值仍固定为 `true`。
- macOS 和 Linux 上数据库 `init` 与 `migrate` 路径必须位于用户主目录内。
- 同步 HTTP 请求强制最低 TLS 1.2 版本。
- 部分 info/download 失败路径不再输出原始异常文本；下载日志消息和容错数据库 warning 使用脱敏摘要或异常类名。

### Added

- 新增 `nber-cli config show` / `get <key>` / `set <key> <value>` / `verify`，用于查看和编辑 `~/.nber-cli/config.json`。
- 新增 `download.concurrency` 配置项（默认 `3`）以及 CLI 参数 `--concurrency` / `-c`，用于限制并发下载数。
- 新增 `nber-cli download --restrict true|false`，用于单次控制下载目录限制。
- 新增 `nber-cli mcp-server --yes`；原有 `--port` 设为非默认值时现在需要显式确认。
- 为 `nber-cli mcp-server` 新增 `sse` 传输。
- 新增 JSON Schema（`config.schema.json`）用于校验 `~/.nber-cli/config.json`。
- 新增严格原始配置校验：报告损坏 JSON、非法配置段/值类型及低于 schema 最小值的数值，不静默注入默认值。
- 同步 plugin manifest 与 marketplace metadata 的版本，并把 Claude plugin skill 路径修正为大小写敏感且已跟踪的 `./skills/NBER-CLI` 目录。
- 为核心数据类（`NBER`、`NBERSearchResults`、`NBERFeedItem`、`NBERFeedFetchResult`、清理结果和下载结果）增加领域不变量校验。
- 包顶层新增导出 `get_config_value`、`set_config_value`、`read_config`、`write_config`、`validate_config`。
- 在 CLI、下载和 MCP 入口统一增加论文编号格式校验（`w?\d+`）。
- 在接受元数据前校验拉取到的论文标题、正数 citation ID，以及响应 ID 与请求 ID 是否一致。

### Changed

- 将旧版 `typing.Dict`、`List`、`Optional` 类型别名替换为 Python 3.11 原生语法。
- 新增 `mypy` 配置，并加强 `cli.py`、`config_store.py`、`fetcher.py` 的类型注解。
- 修正 `mcp-server` 传输名称为 `streamable-http`；原有 `--port` 选项对非默认值改用 `--yes` 确认。
- `fetcher.py` 的重试等待改为指数退避，上限 30 秒。
- `feed fetch` 遇到单个损坏的 RSS 条目时跳过，不再导致整个 feed 失败。
- 非法的配置或单次调用下载并发值会被拒绝或回退到文档规定的安全默认值，不再创建非法 semaphore。
- 修改 schema 或写入数据的数据库操作会拒绝未来版本的 `PRAGMA user_version`；诊断用 schema 版本读取器保持只读。
- Feed 拉取会在网络请求前建立并校验本地 schema，并在响应解析后以事务方式写入 feed 条目和抓取历史；清理操作会把 schema 校验/升级和删除放在同一个 SQLite 事务中。
- `download.py` 在 `ClientSession` 上启用 `raise_for_status=True`。
- 错误处理收窄为具体的网络/超时异常类型，并保留异常链。
- 移除 `info` 命中缓存时向 stderr 打印的提示行。

### Fixed

- `feed fetch` 现在可以容忍 RSS 标题和摘要文本中后接空白或数字的未转义 `<`，其他格式错误仍使用严格 XML 解析。
- RSS 解析失败时会在可用情况下报告行号和列号；`feed fetch` 的运行时解析错误会以退出码 `1` 返回，不再打印命令 usage。

## 0.4.0 - 2026-06-04

### Added

- 新增 `nber-cli info --refresh`，跳过本地 `info_cache` 并直接从 NBER 重新拉取论文元数据。缓存开启时，新数据会写回缓存。
- 新增 `nber-cli info cache --turn-on` 和 `--turn-off`，全局开关 `info_cache` 读取行为，状态会持久化到 `~/.nber-cli/config.json`。
- 新增 `nber-cli info cache --set-refresh <N>`，设置缓存刷新间隔（天）。该值会持久化到 `~/.nber-cli/config.json`，并在后续每次 `info` 调用中作为 TTL 生效，默认 `30` 天。
- 新增 `nber-cli info cache clear`，参数集与 `feed clean` 一致：`--days`、`--all`、`--start-date`、`--end-date`，使用 `info_cache` 表的 `last_fetched_at` 字段过滤。`nber-cli info cache clean` 是 `clear --all` 的便利别名。
- 新增 `nber-cli info cache`（不带子动作），用于打印当前缓存状态、TTL 和已缓存行数。
- 新增 `nber_cli.config_store` 模块，集中处理 `~/.nber-cli/config.json` 的读写，包含 `InfoCacheSettings` 数据类及 `get_info_cache_settings`、`set_info_cache_enabled`、`set_info_cache_ttl_days` 等辅助函数。
- 新增 `nber_cli.info_cache.get_paper_with_info_cache_result` 异步辅助函数（位于 `nber_cli.info_cache` 模块），返回包含 `NBER` 论文对象和 `from_cache` 标志的 `InfoCacheLookupResult`。
- 新增包顶层的 Python API 导出：`InfoCacheSettings`、`clear_info_cache`、`count_info_cache`、`get_info_cache_settings`、`get_info_cache_ttl_days`、`is_info_cache_enabled`、`is_info_cache_expired`、`set_info_cache_enabled`、`set_info_cache_ttl_days`、`NBERInfoCacheClearResult`。`InfoCacheLookupResult` 和 `get_paper_with_info_cache_result` 由 `nber_cli.info_cache` 模块导出，而不是从包顶层；导入路径是 `from nber_cli.info_cache import ...`。

### Changed

- `~/.nber-cli/config.json` 现在携带 `info` 段：`info.cache_enabled`（默认 `true`）和 `info.cache_ttl_days`（默认 `30`）。字段缺失或类型错误时回退到默认值。
- `info` 命令在从本地缓存命中时，会通过 stderr 打印一行提示，并指向 `nber-cli info <id> --refresh` 用于强制刷新。

## 0.3.1 - 2026-06-03

### Added

- 添加 `nber-cli db init` 和 `nber-cli db migrate`，用于初始化和迁移本地数据库，替代原先的 `feed init` 和 `feed migrate`。
- 添加 `info_cache` 表，重复执行 `nber-cli info` 或 MCP `get_paper_info` 时直接从缓存返回。
- 添加 `query_log`、`download_log`、`info_log` 表，记录搜索关键词、下载结果和 info 查询。
- 在 `~/.nber-cli/config.json` 中写入 `schema_version` 字段，便于后续的 schema 升级。

### Changed

- 默认数据库文件从 `feed.db` 改名为 `nber.db`。已经安装了 `~/.nber-cli/feed.db` 的用户无需手动迁移。
- 数据库 schema 从版本 1 升级到版本 2，下次启动时自动完成升级。
- 公共数据库代码迁移到 `nber_cli.db`,原先的 `init_feed_database` 和 `migrate_feed_database` 作为薄薄的兼容层保留。

## 0.3.0 - 2026-06-03

### Added

- 添加 `nber-cli feed init`，用于创建本地 SQLite feed 缓存。
- 添加 `nber-cli feed fetch`，用于获取 NBER 最新工作论文 RSS feed 并显示新缓存的条目。
- 添加 `nber-cli feed fetch --max-items`，用于限制 feed 输出数量。
- 添加 `nber-cli feed migrate`，用于移动 feed 缓存数据库并更新用户配置。
- 添加 `nber-cli feed clean`，用于在确认后清理 feed 缓存数据库记录。
- 补充 feed 缓存辅助函数和 feed 数据模型的 Python API 文档。

### Changed

- 添加 `~/.nber-cli/config.json` 和 `feed.db-path` 的用户配置文档。
- 扩展中英文 CLI、快速开始、配置和 Python API 页面中的 feed 缓存文档。

## 0.2.0 - 2026-05-31

### Changed

- 将 CLI 重构为 `nber-cli download ...` 子命令语法。
- 添加 `--file/-f` 和 `--save-base/-s` 路径处理行为。
- 添加 `--batch/-b` 多编号下载模式。
- 移除基于数据库的下载状态跟踪。
- 将下载器简化为直接异步 HTTP PDF 获取。
- 更新 v0.2 命令模型文档。
- 移除旧 web UI 模块和脚本入口。

## 0.1.4 - 2025-08-09

### Added

- 添加 `--version` / `-v` 参数用于显示当前版本。
- 添加更完整的帮助信息和示例。
- 添加 `__main__.py` 以支持 `python -m nber_cli`。
- 添加参数分组以改善 CLI 结构。
- 不带参数运行时自动显示帮助信息。
