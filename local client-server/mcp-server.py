from mcp.server.fastmcp import FastMCP
from mcp import types

server = FastMCP('adder')

@server.tool()
async def add_numbers(a: int, b: int) -> int:
    """Add two numbers."""
    ''' Do something useful here '''
    return a + b

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """List all tools."""
    return server.tools

if __name__ == "__main__":
    
    server.run()