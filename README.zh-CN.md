# NBER-CLI

一个以 Desktop 为主要入口、在本机运行的 NBER 工作论文研究工作台；同时提供面向 AI Agent 和自动化任务的 CLI 与 MCP 接口。

[![Pytest](https://github.com/sepinetam/nber-cli/actions/workflows/pytest.yml/badge.svg)](https://github.com/sepinetam/nber-cli/actions/workflows/pytest.yml)
[![Lint](https://github.com/sepinetam/nber-cli/actions/workflows/lint.yml/badge.svg)](https://github.com/sepinetam/nber-cli/actions/workflows/lint.yml)
[![Docs](https://github.com/sepinetam/nber-cli/actions/workflows/docs.yml/badge.svg)](https://github.com/sepinetam/nber-cli/actions/workflows/docs.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![PyPI version](https://img.shields.io/pypi/v/nber-cli.svg)](https://pypi.org/project/nber-cli/)
[![PyPI Downloads](https://static.pepy.tech/badge/nber-cli)](https://pepy.tech/projects/nber-cli)

[English](README.md) | [中文文档](docs/zh/index.md)

> **NBER** 是 [美国国家经济研究局](https://www.nber.org)（National Bureau of Economic Research）的注册商标。本项目是独立的开源工具，与美国国家经济研究局**不存在任何附属、认可或赞助关系**。使用前请阅读[使用政策](docs/zh/policy.md)。


## 快速开始
通过 HTTP MCP 将 NBER MCP 接入你的 Agent 客户端：`https://nber-mcp.aidea-labs.com/mcp`

- Codex：`codex mcp add nber-mcp --url https://nber-mcp.aidea-labs.com/mcp`
- Claude Code：`claude mcp add nber-mcp -s user -t http https://nber-mcp.aidea-labs.com/mcp`
- OpenClaw：`openclaw mcp add nber-mcp --url https://nber-mcp.aidea-labs.com/mcp`


## 从 Desktop 开始

如果你是研究者，推荐直接使用 **NBER-CLI Desktop**。请从 [GitHub Releases](https://github.com/sepinetam/nber-cli/releases/latest) 下载 macOS、Windows 或 Linux 安装包。安装包已经包含运行环境，不需要另外安装 Python、uv，也不需要使用终端或启动本地 Web 服务。

Desktop 提供一套面向论文跟踪与阅读的本地工作台：

- 同步并浏览最新的 NBER 工作论文 Feed。
- 按标题、作者、论文编号或标签搜索本地 Feed，并筛选未读论文。
- 在宽度可调的预览区阅读摘要和论文元数据。
- 标记已读或未读。
- 使用 NBER Topics、NBER Programs 和仅保存在本机的自定义标签整理论文。
- 复制 BibTeX、APA、MLA、Harvard、Chicago 或 GB/T 7714 引用。
- 调整预览字号和自动同步间隔。
- 将 Feed、论文元数据、阅读状态、标签和设置保存在本机。

当前安装包尚未签名。在处理 macOS Gatekeeper 或 Windows SmartScreen 提示前，请先确认安装包来自项目官方 GitHub Release。各平台的安装与恢复方法见 [Desktop 指南](docs/zh/desktop.md)。

## 选择使用入口

| 入口 | 主要使用者 | 适用情况 |
| --- | --- | --- |
| **Desktop** | 研究者 | 希望使用可视化、本地化工作台，不想安装开发工具。 |
| **MCP Server** | AI Agent | Agent 支持 MCP，需要通过结构化工具搜索、查看或下载论文。 |
| **CLI** | AI Agent 与自动化任务 | Agent 可以执行终端命令，或任务需要稳定的文本/JSON 输出。 |
| **Python API** | 开发者 | 需要在 Python 代码中直接调用异步核心函数。 |
| **本地 HTTP API** | 本地集成程序 | 另一个本地应用需要 loopback JSON API。 |

Desktop、CLI、MCP Server 和可选 HTTP API 可以共用同一个 SQLite 数据库，但各入口支持的能力并不完全相同。完整对照见[软件规格说明](docs/zh/software-specification.md)。

## 给 AI Agent 使用

优先使用结构化的 MCP 接口。启动 stdio MCP Server：

```bash
uvx nber-cli mcp-server
```

MCP 客户端配置示例：

```json
{
  "mcpServers": {
    "nber-cli-mcp": {
      "command": "uvx",
      "args": ["nber-cli", "mcp-server"]
    }
  }
}
```

MCP Server 提供论文查询、搜索和 PDF 下载工具。不同 Agent 的安装方法见 [Claude Code](docs/zh/agents/claude-code.md)、[Codex](docs/zh/agents/codex.md)、[OpenClaw](docs/zh/agents/openclaw.md) 和[其他 MCP 客户端](docs/zh/agents/others.md)。

能够执行终端命令的 Agent 也可以直接使用 CLI：

```bash
uvx nber-cli search "Labor Economics" --format json
uvx nber-cli info w25000 --format json
uvx nber-cli download w34567
```

完整命令、输出格式、文件写入限制和退出码见 [CLI 参考](docs/zh/cli.md)与 [MCP 参考](docs/zh/mcp.md)。

## 本地数据与网络访问

默认情况下，配置、SQLite 数据库和诊断日志保存在 `~/.nber-cli/`。项目不要求账号或 API Key，也不会把本地数据库上传到项目方的基础设施。

- Desktop 只在手动或定时刷新 Feed 时访问 NBER；CLI、MCP、Python 与 HTTP 操作会在所请求流程需要远程数据时访问 NBER。
- 只有用户点击“检查更新”时，Desktop 才会访问 GitHub Releases API。
- Desktop 不会监听本地端口。
- 可选 HTTP API 和非 stdio MCP 传输需要用户主动启动，并有各自的安全注意事项。

修改路径、删除数据或开放网络传输前，请阅读[持久化层](docs/zh/persistence.md)、[配置](docs/zh/configuration.md)和[使用政策](docs/zh/policy.md)。

## 文档

- [用户操作手册](docs/zh/user-manual.md)：按任务说明操作步骤、预期结果、本地副作用、备份与卸载。
- [Desktop 指南](docs/zh/desktop.md)：安装包、日常操作、设置、快捷键、本地数据和故障排查。
- [Agent 指南](docs/zh/agents/index.md)：各类 Agent 的 plugin、MCP 和 skill 配置。
- [软件规格说明](docs/zh/software-specification.md)：范围、模块、能力矩阵、数据模型、限制和源码追溯关系。
- [系统架构](docs/zh/architecture.md)：运行组件与信任边界。
- [完整文档](docs/zh/index.md)：全部用户、API、运维、开发与发布文档。

## 开发

```bash
uv sync --dev --group docs
uv run pytest
uv run ruff check .
uv run --group docs mkdocs build --strict
```

Desktop 的开发与发布命令见 [desktop/README.md](desktop/README.md) 和[开发指南](docs/zh/development.md)。

## 许可证

NBER-CLI 使用 [Apache-2.0 License](LICENSE) 发布。
