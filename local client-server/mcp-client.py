import asyncio
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import sys


class MinecraftMCPClient:
    def __init__(self):
        self.session : Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
    
    async def connect(self, server_script_path):
        """Connect to the MCP server."""
        command = 'python'
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )

        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession.create(self.stdio, self.write)
        )

        await self.session.initialize()

        response = await self.session.list_tools()
        tools = response.tools
        print("Available tools:")
        for tool in tools:
            print(f" - {tool.name}: {tool.description}")

async def main():
    client = MinecraftMCPClient()
    try:
        await client.connect('mcp-server.py')
    except Exception as e:
        print(f"Error connecting to MCP server: {e}")
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())