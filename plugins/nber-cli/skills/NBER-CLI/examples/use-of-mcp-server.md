# Use of MCP Server

NBER-CLI can expose its search, paper-info, and download capabilities through the Model Context Protocol (MCP). The available tools depend on the transport.

## Run the stdio server

```bash
uvx nber-cli mcp-server
```

This is the default transport. Most MCP clients expect stdio and read the server's tools from this command. The stdio server exposes search, paper-info, and download tools.

## Run the HTTP server

```bash
uv run nber-cli mcp-server --transport streamable-http --port 8000 --yes
```

The HTTP transports expose only `search_papers` and `get_paper_info`; they do not expose `download_paper`. They have no built-in authentication, so do not expose them to an untrusted network. `--port` exists in published `0.4.0`; the source tree additionally requires `--yes` for a custom port.

## Example MCP client configuration

For clients that read a `mcpServers` block:

```json
{
  "mcpServers": {
    "nber-cli": {
      "command": "uvx",
      "args": ["nber-cli", "mcp-server"]
    }
  }
}
```

## Using the exposed tools

The stdio server exposes:

- `search_papers`: keyword search with an optional date range.
- `get_paper_info`: metadata lookup by paper ID.
- `download_paper`: PDF download within the current directory.

The HTTP servers expose only the first two tools.

## Security notes

- The stdio download tool writes files within the current working directory. Run the client in an appropriate working directory.
- The HTTP transport should bind to `localhost` only unless you have placed it behind authenticated reverse proxy.
- Do not configure the server to bypass NBER access controls.
