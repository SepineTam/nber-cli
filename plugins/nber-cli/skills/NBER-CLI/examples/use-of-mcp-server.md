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

The HTTP transports expose only `search_papers` and `get_paper_info`; they do not expose `download_paper`. The `--host` option defaults to `127.0.0.1`. The Docker image uses `--host 0.0.0.0` internally so a Compose `ports` mapping can reach the service. HTTP has no built-in authentication, so bind the host-side Compose port to `127.0.0.1` unless an authenticated proxy protects it. `--port` exists in published `0.4.0`; the source tree additionally requires `--yes` for a custom port.

The supported Docker setup is:

```bash
docker compose pull
docker compose up -d --wait
```

Connect to `http://127.0.0.1:5090/mcp`, inspect logs with `docker compose logs nber-mcp`, and stop it with `docker compose down`. The named volume preserves the metadata cache and configuration.

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
