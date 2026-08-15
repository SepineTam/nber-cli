# NBER-CLI

NBER-CLI 是一个以 Desktop 为主要入口、在本机运行的 NBER 工作论文研究工作台。研究者使用 Desktop；AI Agent 和自动化任务使用 MCP Server 或 CLI；定制集成还可以使用 Python API 和可选的 loopback HTTP API。

## 推荐入口：Desktop

请从 [GitHub Releases](https://github.com/sepinetam/nber-cli/releases/latest) 下载 macOS、Windows 或 Linux 安装包。Desktop 自带运行环境，普通用户不需要安装 Python 或 uv。

Desktop 可以同步 NBER 工作论文 Feed、搜索和筛选本地论文、显示缓存详情、维护已读状态和本地标签、复制六种引用格式，并将研究数据保存在用户自己的设备上。

第一次使用请按[用户操作手册](user-manual.md)完成完整流程；平台、设置、数据、快捷键和排错细节见 [Desktop 指南](desktop.md)。

!!! warning "安装包尚未签名"
    当前 Desktop 安装包没有代码签名或 macOS notarization。只从官方 GitHub Release 下载；确认系统和 CPU 架构正确后，再决定是否绕过操作系统警告。

## 使用入口

| 入口 | 主要使用者 | 用途 |
| --- | --- | --- |
| Desktop | 研究者 | 可视化论文 Feed、阅读、引用、已读状态和本地标签工作流。 |
| MCP Server | AI Agent | 结构化搜索、论文查询和受目录约束的 PDF 下载工具。 |
| CLI | AI Agent 与自动化任务 | 提供适合脚本的命令、可读文本和 JSON 输出。 |
| Python API | 开发者 | 直接调用异步获取、下载、Feed、缓存和数据库函数。 |
| 本地 HTTP API | 本地集成程序 | 可选的 loopback 服务，提供 Feed、论文、已读状态和设置接口。 |

各入口会在合适的地方共用核心代码和本地数据，但支持的能力并不完全相同。准确的功能矩阵与源码追溯表见[软件规格说明](software-specification.md)。

## 配置 AI Agent

对于支持 MCP 的 Agent，先启动 stdio Server：

```bash
uvx nber-cli mcp-server
```

再把下面的配置加入 MCP 客户端：

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

不同客户端的安装与验证方法见 [Agent 指南](agents/index.md)。通过终端工作的 Agent 也可以直接使用 [CLI 参考](cli.md)。

## 文档导航

### 使用软件

- [用户操作手册](user-manual.md)：安装、首次同步、Desktop 日常任务、Agent 工作流、备份、更新和卸载。
- [Desktop 应用](desktop.md)：安装包、本地数据、设置、快捷键、限制和故障排查。
- [快速开始](getting-started.md)：选择 Desktop、MCP 或 CLI 并完成第一个任务。
- [Agent 指南](agents/index.md)：Claude Code、Codex、OpenClaw 和其他 Agent 的配置。
- [CLI 参考](cli.md)与 [MCP Server](mcp.md)：准确的 AI 使用接口。

### 理解数据和行为

- [软件规格说明](software-specification.md)：软件标识、功能范围、模块边界、约束和代码追溯。
- [配置](configuration.md)：运行默认值和支持的本地设置。
- [持久化层](persistence.md)：文件、SQLite 数据表、缓存、迁移、清理和备份。
- [使用政策](policy.md)：项目边界、访问、版权与用户责任。
- [术语表](glossary.md)：项目专用名词。

### 集成与开发

- [本地 HTTP API](http-api.md)与 [Python API](python-api.md)：集成接口契约。
- [系统架构](architecture.md)：运行组件、核心流程和信任边界。
- [开发](development.md)、[测试](testing.md)和[贡献指南](contributing.md)：仓库工作流与质量门禁。
- [更新日志](changelog.md)：版本历史。当前仓库版本为 **0.11.0**。

## 范围与状态

NBER-CLI 是处于 Beta 阶段的独立 Apache-2.0 开源项目。它使用 NBER 的公开页面和端点，不需要项目账号或 API Key，也不隶属于 NBER 或获得 NBER 认可。具体论文能否访问仍取决于 NBER 的服务状态与政策。
