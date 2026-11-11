"""Accessibility guidance MCP server (stdio). Run: python domains/accessibility/mcp_server.py"""

from pathlib import Path

from governance.domain_mcp import build_server

mcp, _knowledge = build_server(Path(__file__).parent)

if __name__ == "__main__":
    mcp.run()
