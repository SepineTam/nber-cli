# Desktop 应用

NBER-CLI Desktop 是面向研究者的推荐入口。它是一个基于 Tauri 2 与 React、在本机运行的 NBER 工作论文跟踪、阅读和整理工作台，不需要安装 Python、uv 或浏览器扩展。

当前仓库版本为 **0.11.0**。Desktop 与 Python 包使用相同版本号和 Release tag；Desktop 安装包发布在 GitHub Releases，Python 包发布在 PyPI。

## 安装

只从项目官方 [GitHub Releases](https://github.com/sepinetam/nber-cli/releases/latest) 页面下载安装包。

| 平台 | 文件标识 | 适用设备 |
| --- | --- | --- |
| macOS Apple silicon | `macOS-arm64.dmg` | M 系列芯片 Mac |
| macOS Intel | `macOS-x64.dmg` | Intel 芯片 Mac |
| Windows | `Windows-x64.exe` | 64 位 Windows |
| Linux | `Linux-x64.AppImage` 或 `Linux-x64.deb` | 64 位 Linux 桌面系统 |

安装包内置一个由 CLI 同一套 Python 实现打包而成的单次工作程序。它只在初始化或刷新 Feed 时启动，操作完成后退出。Desktop 不会启动可选的 `nber-server`，不会监听端口，也不依赖系统 Python。

## 未签名提示

项目目前没有付费的 Apple 和 Windows 证书，因此安装包没有代码签名或 macOS notarization。macOS Gatekeeper 或 Windows SmartScreen 可能在首次启动时警告。

放行前依次确认：

1. 文件来自官方 `SepineTam/NBER-CLI` GitHub Release。
2. 版本、操作系统和 CPU 架构与电脑一致。
3. 文件不是来自镜像、邮件或聊天附件。

macOS 用户只应在确认后使用**系统设置 → 隐私与安全性 → 仍要打开**。如果系统提示应用“已损坏”，先把应用移到 `/Applications`，再运行：

```bash
xattr -cr /Applications/NBER-CLI\ Desktop.app
```

Windows 用户只应对已经确认的官方文件选择**更多信息 → 仍要运行**。

## 首次启动

如果配置中的 SQLite 数据库已经存在，Desktop 启动时会校验并打开它。全新安装的数据库和 Feed 会在第一次成功刷新时创建：

1. 打开 Desktop。
2. 点击 Feed 工具栏中的“同步最新论文”。
3. 等待同步提示；内置工作程序会保存 Feed；`info.cache_enabled` 为 true 时，还会把论文详情预先写入本地数据库。
4. 选择一篇论文打开本地详情；打开时也会标记为已读。

刷新失败不会删除已有本地数据。如果部分论文详情没有准备成功，提示会显示失败数量；下次刷新会重试仍缺少必要元数据的记录。共用 info cache 关闭时，Desktop 会有意跳过元数据预取，因此完整详情和 NBER 来源的 Topics/Programs 可能不可用。

## 研究工作流

### 浏览与筛选

- **全部 / 未读**：筛选当前已加载的本地 Feed。
- 搜索框：匹配标题、作者、论文编号和可见标签文字。
- 标签选择器：按一个可见标签筛选论文。
- **加载更多**：读取下一页本地数据，不会发起网络请求。
- Feed 标题区：显示本地索引数量和最近一次成功刷新时间。

搜索和筛选只针对已经加载到 Desktop 列表中的记录，不等同于 CLI 对 NBER 执行的远程搜索。

### 阅读论文记录

选择 Feed 记录后，如果本地缓存中存在相应数据，右侧会显示标题、作者、日期、摘要、NBER URL、发表信息、Topics 和 Programs。预览区默认宽度为 420 px：

- 拖动分隔条可在 360 px 至 640 px 之间调整宽度。
- 分隔条获得焦点后，方向键每次调整 16 px，按住 Shift 时每次调整 48 px。
- Home 或 End 切换到最小或最大宽度。
- 双击分隔条恢复 420 px。
- 选择的宽度保存在当前设备的 WebView local storage 中，重启后继续使用。

Desktop 负责显示元数据并打开 NBER 公开页面，目前没有应用内 PDF 下载按钮。需要下载 PDF 时，请使用 AI Agent、CLI 或 NBER 页面。

### 管理已读状态

打开论文会自动标记已读。使用详情区的眼睛按钮可以重新标记为未读或已读。状态保存在共用的 `read_status` 表中，可选本地 HTTP API 也能读取和修改它。

### 使用标签整理

Feed 刷新并准备论文详情后，Desktop 会根据 NBER **Topics** 和 **Programs** 生成可见标签。你可以：

- 添加仅保存在本机的自定义标签。
- 重命名自定义标签。
- 编辑 NBER 来源标签；Desktop 会在本机隐藏原标签，并创建新文字的用户标签。
- 删除自定义标签，或在本机隐藏 NBER 来源标签。
- 按可见标签搜索和筛选已加载的 Feed。

标签操作不会修改 NBER 数据。原始 NBER 标签、用户标签和本机隐藏选择分别保存，因此后续刷新可以同步来源数据，同时保留用户自己的整理结果。

### 复制引用

详情区可以复制 BibTeX、APA、MLA、Harvard、Chicago 或 GB/T 7714 引用。正式使用前请自行核对：引用由当前本地元数据生成，可能缺少字段，也可能与期刊的具体格式要求不同。

## 设置

| 设置或控制 | 有效值 | 行为 |
| --- | --- | --- |
| 自动刷新 Feed | 正整数分钟，默认 `60` | 只有应用已打开、初始化完成、窗口可见且当前没有刷新时才会执行。 |
| 预览字号 | `14`、`16` 或 `18` px，默认 `16` | 调整摘要和论文详情的阅读字号。 |
| 数据库路径 | 只读显示 | 显示当前 SQLite 文件；需要通过共用 CLI 配置修改，不能在 Desktop 中修改。 |
| 配置文件路径 | 只读显示 | 显示当前 `config.json`。 |
| 打开日志目录 | 按钮 | 打开 `~/.nber-cli/logs/`。 |
| 检查更新 | 手动按钮 | 只有点击后才访问 GitHub 最新 Release API，不会自动安装。 |

Desktop 不运行本地 HTTP 进程，因此没有服务端口设置。旧的 `desktop.server_port` 只由可选 HTTP API 的兼容层使用。

## 键盘与指针操作

| 操作 | 结果 |
| --- | --- |
| `Command/Ctrl+1` | 打开 Feed 页面。 |
| `Command/Ctrl+F` 或 `Command/Ctrl+K` | 打开 Feed 并聚焦论文搜索。 |
| `Command/Ctrl+R` | 刷新 Feed。 |
| macOS 上的 `Command+,` | 通过原生应用菜单打开设置。 |
| `Escape` | 关闭已经打开的引用格式菜单。 |
| 拖动分隔条或使用其键盘控制 | 按前述规则调整论文预览宽度。 |

## 本地数据与网络访问

| 路径或存储 | 用途 |
| --- | --- |
| `~/.nber-cli/config.json` | 数据库路径、缓存设置、刷新间隔和预览字号。 |
| `~/.nber-cli/nber.db` | Feed、元数据缓存、行为历史、已读状态和 Desktop 标签数据。 |
| `~/.nber-cli/logs/` | Desktop 诊断目录；不会生成长期运行的 sidecar 日志。 |
| WebView local storage | 当前设备上的预览区宽度。 |

Desktop 在刷新 Feed 时访问 NBER；只有点击“检查更新”后才访问 `api.github.com`；只有执行相应操作后才会打开 NBER 或 GitHub 页面。它不会把 SQLite 数据库上传到项目方的基础设施。

Desktop 会读取共用配置中的 `feed.db-path`，包括由 `nber-cli db migrate` 设置的路径。在 macOS 和 Linux 上，规范化后的数据库路径必须位于用户 home 目录内；不支持内存数据库。

如果 `config.json` 无法解析，Desktop 会报错并停止，不会替换原文件。请恢复或修复 JSON 后重新打开应用。

## 备份、更新与卸载

做文件级备份前，关闭 Desktop，并停止所有使用同一数据库的 CLI、MCP 或 HTTP 进程。如果存在 `nber.db-wal` 和 `nber.db-shm`，应与 `nber.db` 一起复制；也可以使用 SQLite 在线备份命令。详见[持久化层](persistence.md)。

Desktop 不会自动安装更新。使用“检查更新”，从官方 Release 下载匹配的安装包，关闭 Desktop 后覆盖安装。

删除应用程序本身不会主动删除 `~/.nber-cli/`。只有确定还要删除共用配置、数据库、标签、缓存和日志时，才单独删除该目录；如果数据将来可能有用，请先备份。

## 故障排查

| 情况 | 检查方法与后果 |
| --- | --- |
| Feed 刷新失败 | 确认能访问 `nber.org` 后重试；已有本地记录仍可使用。 |
| 部分详情没有准备成功 | 稍后再次刷新；Feed 摘要仍可用，但完整元数据或来源标签可能缺失。 |
| 搜索结果比预期少 | 先点“加载更多”；Desktop 筛选已加载的本地记录，CLI `search` 才会远程查询 NBER。 |
| 无法打开论文详情 | 本地详情可能尚未生成；先刷新 Feed。来源页面已移除或受限时仍可能失败。 |
| 找不到自定义数据库 | 检查 `feed.db-path`；macOS/Linux 下必须解析到 home 目录内。 |
| 提示数据库更新或不兼容 | 升级 Desktop；它会拒绝写入 schema 版本不等于当前支持版本的数据库。 |
| 配置文件无效 | 修复或恢复 JSON；Desktop 有意不覆盖损坏的配置。 |
| 检查更新失败 | 检查能否访问 `api.github.com`；不会影响本地阅读或 NBER Feed 数据。 |

准确的数据表行为与恢复注意事项见[持久化层](persistence.md)，按任务操作的完整流程见[用户操作手册](user-manual.md)。
