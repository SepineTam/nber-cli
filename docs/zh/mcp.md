# MCP Server

NBER-CLI 内置 MCP server，让 Agent 无需解析命令行文本即可使用结构化论文工具。默认 stdio transport 提供搜索、论文信息和 PDF 下载；HTTP transport 有意只提供搜索和论文信息。

MCP server 如何与 CLI 共用核心模块，见 [系统架构](architecture.md)。

## 启动服务

默认传输方式是 stdio：

```bash
uvx nber-cli mcp-server
```

已安装的命令也一样：

```bash
nber-cli mcp-server
```

## MCP 客户端配置

适用于启动 stdio server 的 MCP 客户端：

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

如果机器上已经安装了 `nber-cli`，也可以直接调用：

```json
{
  "mcpServers": {
    "nber-cli-mcp": {
      "command": "nber-cli",
      "args": ["mcp-server"]
    }
  }
}
```

## HTTP Transport

如果客户端支持 streamable HTTP：

```bash
uvx nber-cli mcp-server --transport streamable-http --port 8000
```

默认 host 是 `127.0.0.1`。如需通过容器端口映射访问，容器内进程必须监听全部容器网络接口：

```bash
nber-cli mcp-server --transport streamable-http --host 0.0.0.0 --port 5090 --yes
```

项目提供的 Docker 镜像已使用该容器内部 host 设置。受支持的本机 HTTP 启动方式是：

```bash
docker compose pull
docker compose up -d --wait
```

`--port` 只对 HTTP transport 生效。当端口设为非默认值时，需要加 `--yes` 确认：

```bash
uvx nber-cli mcp-server --transport streamable-http --port 9000 --yes
```

Compose 文件把容器的 5090 端口映射到宿主机 `127.0.0.1:5090`，因此服务仍只对宿主机本地开放。server 不内置身份认证：任何能访问 HTTP endpoint 的位置都可以调用搜索和论文信息工具。未经可信的反向代理认证，不要把宿主机绑定地址改成公网接口。

Compose 的 streamable HTTP endpoint 是：

```text
http://127.0.0.1:5090/mcp
```

手动启动 server 时，请使用其实际配置的端口（默认是 8000）。旧版 SSE transport 使用：

```text
http://127.0.0.1:8000/sse
```

端点路径取决于所选 transport：streamable HTTP 使用 `/mcp`，SSE 使用 `/sse`。实际主机和路径请按所接入的反向代理进行调整。

## 可用工具

默认 stdio server 提供下面三个工具。Streamable HTTP 和 SSE 只提供 `get_paper_info` 与 `search_papers`。

### get_paper_info

获取单篇 NBER 工作论文的元数据和摘要。

参数：

| 名称 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `paper_id` | `string` | 必填 | 论文编号，例如 `w25000` 或 `25000`。 |
| `include_all` | `boolean` | `true` | 如果可用，包含相关字段和 published-version 数据。 |

返回包含 `id`、`title`、`authors`、`date`、`abstract`、`url` 等字段的字典。

### search_papers

搜索 NBER 工作论文。

参数：

| 名称 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `query` | `string` | 必填 | 标题、编号、作者、摘要片段或关键词。 |
| `start_date` | `string` 或 `null` | `null` | 最早论文日期，格式为 `YYYY-MM-DD`。 |
| `end_date` | `string` 或 `null` | `null` | 最晚论文日期，格式为 `YYYY-MM-DD`。 |
| `page` | `integer` | `1` | 要获取的结果页。 |
| `per_page` | `integer` | `20` | 每页结果数量，支持 `20`、`50` 和 `100`。 |

返回搜索元数据和论文列表。

### download_paper（仅 stdio）

下载单篇论文 PDF。

参数：

| 名称 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `paper_id` | `string` | 必填 | 论文编号，例如 `w34567` 或 `34567`；两种形式都会被规范化为 `w34567`。 |
| `output_path` | `string` 或 `null` | `null` | 明确的 PDF 输出路径，必须通过当前工作目录字面检查。省略时会在 server 进程当前目录使用规范化文件名，例如 `w34567.pdf`。 |

下载成功时返回 `{"success": true}`。参数、路径、网络或文件系统错误会返回 `{"error": "..."}`，不会向 MCP 调用方抛出底层异常；调用方必须检查返回值中出现的是哪个 key。

## Agent 使用建议

- 使用 stdio 时，如果不知道论文编号，先用 `search_papers`。
- 工作流需要确认标题、作者或摘要时，下载前先用 `get_paper_info`。
- MCP 客户端控制隔离工作目录时，优先使用默认文件名或简单的相对 `output_path`。
- NBER 可能会限制新发布论文第一周的访问，这类下载可能返回 HTTP 403。

## 安全说明

所有 MCP transport 都会向 NBER 发起网络请求。只有默认 stdio transport 暴露 `download_paper`，并可能向磁盘写入 PDF。请只在可信客户端中配置 stdio；工具参数可能不可信时，应在隔离工作目录中启动它。Docker HTTP 服务不暴露下载工具。

!!! warning "路径检查不是安全沙箱"
    0.10.0 的检查会比较绝对路径片段，但不会解析 `..` 或符号链接。因此，构造后的 `output_path` 可能通过检查，却仍写到工作目录之外。请使用简单相对文件名；真正的安全边界应依靠操作系统隔离。

### 本地持久化与缓存

`get_paper_info` 遵守与 CLI 相同的 `info_cache` 开关和 TTL。缓存开启时，命中会从 `info_cache` 读取，未命中会写入新行，行为与 CLI 一致。每次调用还会向 `info_log` 追加一行，使本地数据库记录这次查询；这个由 SQLModel/SQLAlchemy 访问的本地数据库与 CLI 共用，由 `~/.nber-cli/config.json` 中配置的路径或 `sqlite:///...` URL 决定。工具的返回值不会标明结果是否来自缓存；调用方需要该信号时，应自己检查调用历史或直接使用 CLI。

### 与 CLI 的差异

- `get_paper_info` 不接受每次调用的 `--refresh` 参数。要强制刷新，可以先关闭缓存、调用 `get_paper_info`，再打开缓存，或等待 TTL 到期后自然刷新。
- `get_paper_info` 和 CLI 都不会向 stderr 输出缓存命中提示。
- 当前版本的 MCP `search_papers` 与仅 stdio 提供的 `download_paper` 工具**不**写 `query_log` 或 `download_log`；只有 CLI 会写入这两个表。
- MCP 工具的返回值就是普通 Python 字典，不会包装为 `DownloadBatchResult`。工具失败通过 `error` key 返回，而不是向 MCP 调用方抛出异常。

### 返回对象结构

工具的 docstring 已经描述了公开的返回值形状。简而言之：

- `get_paper_info` 返回的字典与 CLI `--format json` 路径下的 `info(...)` 一致；当 `include_all=True` 时还会并入 `related(...)` 字段。`published_version` 仅在 `include_all=True` 且非空时出现。
- `search_papers` 返回 `search_results(...)` 字典。
- 仅 stdio 提供的 `download_paper` 成功时返回 `{"success": True}`，失败时返回 `{"error": "..."}`。

### 下载路径规则

省略 `output_path` 时，文件会保存到 `<cwd>/<规范化论文编号>.pdf`，其中 `cwd` 是 **server 进程**的工作目录。server 通常由 MCP 客户端启动，因此该目录可能不同于用户交互式 shell 的当前目录。明确路径会经过上述字面检查：明显没有当前目录前缀的路径会返回 `error` 字典，但当前不能阻止 `..` 或符号链接逃逸。下载模块会一次性把整段响应体写入磁盘，并覆盖目标路径上的已有文件。不保证原子 rename；写入被打断可能在目标路径上留下部分文件。
