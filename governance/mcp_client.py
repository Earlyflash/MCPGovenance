"""Talk to a domain's MCP server. The PoC launches each server as a local stdio subprocess inside the
reviewer job; production would point at a remote streamable-HTTP endpoint instead (same tool contract)."""

from __future__ import annotations

import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPCallError(RuntimeError):
    pass


class DomainClient:
    def __init__(self, session: ClientSession):
        self._session = session

    async def call(self, tool: str, **arguments: Any) -> Any:
        result = await self._session.call_tool(tool, arguments)
        text = "".join(c.text for c in result.content if getattr(c, "type", "") == "text")
        if result.isError:
            raise MCPCallError(f"{tool} failed: {text}")
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise MCPCallError(f"{tool} returned non-JSON: {text[:200]}") from exc

    async def tool_names(self) -> list[str]:
        return [t.name for t in (await self._session.list_tools()).tools]


@asynccontextmanager
async def open_domain(domain_id: str, root: Path) -> AsyncIterator[DomainClient]:
    server = Path(root) / "domains" / domain_id / "mcp_server.py"
    if not server.is_file():
        raise FileNotFoundError(f"no MCP server for domain '{domain_id}' at {server}")
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(server)],
        env={"PYTHONPATH": str(Path(root))},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield DomainClient(session)
