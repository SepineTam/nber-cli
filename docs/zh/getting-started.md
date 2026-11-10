# 快速开始

本指南帮助你选择合适的 NBER-CLI 入口并完成第一个任务。研究者应优先使用 Desktop；CLI 与 MCP 主要面向 AI Agent、脚本和集成程序。

## 推荐的 Desktop 路径

1. 从[官方 GitHub Release](https://github.com/sepinetam/nber-cli/releases/latest) 下载与操作系统和 CPU 一致的安装包。
2. 确认文件来自 `SepineTam/NBER-CLI`。当前安装包可能没有签名；绕过系统提示前先阅读 [Desktop 安装警告](desktop.md#_2)。
3. 安装并打开 **NBER-CLI Desktop**；不需要安装 Python 或 uv。
4. 点击“同步最新论文”，同步工作论文 Feed 并准备本地论文详情。
5. 选择论文后阅读摘要、管理标签和已读状态、复制引用，或打开来源页面。

完整的按任务操作流程见[用户操作手册](user-manual.md)。下面各节说明面向 AI 的 CLI 和可选集成 Server。

## CLI 与集成环境要求

- Python 3.11 或更高版本。
- 能访问 `https://www.nber.org`。
- 使用 `uv`、`pipx` 或 `pip` 安装。

这些要求不适用于 Desktop。AI Agent 或集成程序最快可以使用 `uvx`，它会在隔离环境中运行包，不需要永久安装。

## 使用 uvx 运行

```bash
uvx nber-cli --version
uvx nber-cli search "Labor Economic"
uvx nber-cli info w25000
uvx nber-cli cite w1234
uvx nber-cli download w34567
```

如果提示命令不存在或报错，请先通过 `uvx nber-cli -v` 检查当前运行的版本。如果不是最新版本，可以通过如下命令将缓存更新至最新版本：

```bash
uvx --refresh nber-cli -v
```

## 安装为命令

如果希望 shell 中一直可用 `nber-cli` 命令，可以使用：

```bash
uv tool install nber-cli
nber-cli --version
```

也可以使用 `pipx`：

```bash
pipx install nber-cli
nber-cli --version
```

## 运行可选的本地 HTTP Server

FastAPI、Uvicorn 和 Alembic 不会进入普通 CLI 依赖集合。只有其他本地集成需要可选 API 时才使用 `server` extra；Desktop 不使用它：

```bash
uvx --from "nber-cli[server]" nber-server --host 127.0.0.1 --port 31527
```

Server 默认只绑定 loopback 地址，启动时把本地数据库升级到 schema v3，并在 `/api/v1` 下提供接口。

## 以 Python 模块方式运行

包还提供了模块入口。当 `nber-cli` console script 不在你的 `PATH` 上时（例如从 checkout 的工作区直接运行，或者在没生成 wrapper 脚本的虚拟环境里）这个入口会很有用：

```bash
python -m nber_cli --version
python -m nber_cli search "labor economics"
python -m nber_cli info w25000
```

`python -m nber_cli` 与 `nber-cli` 命令在功能上完全一致——同样的参数、同样的退出码、同样的 stdout/stderr 合同。在工作区中你也可以通过 `uv` 跑它：

```bash
uv run python -m nber_cli --version
```

## 第一次搜索

```bash
nber-cli search "labor economics"
```

搜索可以接受标题、作者、摘要、关键词或论文编号。默认每页返回 20 条结果。

添加日期范围和结果数量：

```bash
nber-cli search "minimum wage" --start-date 2024-01-01 --end-date 2024-12-31 --per-page 50
```

为脚本返回 JSON：

```bash
nber-cli search "inflation" --format json
```

## 查看论文详情

```bash
nber-cli info w25000
```

论文编号可以带 `w` 前缀，也可以不带：

```bash
nber-cli info 25000
```

使用 `--all` 可以包含 NBER 暴露的相关字段和 published version 信息：

```bash
nber-cli info w25000 --all
```

## 生成论文引用

把参考文献条目复制到剪贴板：

```bash
nber-cli cite w25000
nber-cli cite w25000 -f apa
```

默认格式是 BibTeX。`-f` 还支持 `mla`、`harvard`、`chicago` 和 `gb`，也可以使用别名 `bibtex` 与 `gbt7714`。

如果要把引用打印出来并写入参考文献文件，可以运行下面这条命令。

```bash
nber-cli cite w25000 --stdout > references.bib
```

复制成功时，命令只在 stderr 输出确认信息。如果没有可用的剪贴板后端，引用会输出到 stdout，命令以退出码 1 结束。

## 用 Feed 缓存跟踪新论文

初始化本地数据库：

```bash
nber-cli db init
```

数据库是由 SQLModel/SQLAlchemy 管理的本地 SQLite 文件，默认位于 `~/.nber-cli/nber.db`；高级用户可以用 `nber-cli db init --db-path ...` 指定其他路径或 `sqlite:///...` URL。

获取 NBER 最新工作论文 RSS feed：

```bash
nber-cli feed fetch
```

第一次获取会把当前 RSS 条目写入缓存，并显示为新条目。后续获取默认只显示缓存中还没有出现过的条目。

限制输出数量，同时显示最新获取到的条目：

```bash
nber-cli feed fetch --max-items 5
```

清理旧缓存记录：

```bash
nber-cli feed clean --days 30
```

`feed clean` 删除缓存记录前会要求确认。

## 下载 PDF

下载到当前目录：

```bash
nber-cli download w34567
```

保存到指定目录：

```bash
nber-cli download w34567 --save-base papers/nber
```

保存到指定文件路径：

```bash
nber-cli download w34567 --file papers/nber/w34567.pdf
```

## 批量下载

```bash
nber-cli download --batch w34567 w25000 w32000 --save-base papers/nber
```

批量模式支持 `--save-base`，不支持 `--file`。

## 下一步

- 按[用户操作手册](user-manual.md)操作，或查看详细的 [Desktop 应用](desktop.md)指南。
- 通过 [Agent 指南](agents/index.md)配置 AI Agent。
- 通过[本地 HTTP API](http-api.md)进行集成。
- 阅读 [CLI 参考](cli.md) 了解全部命令和选项。
- 配置 [MCP Server](mcp.md) 用于 Agent 工作流。
- 在自己的异步代码中使用 [Python API](python-api.md)。
