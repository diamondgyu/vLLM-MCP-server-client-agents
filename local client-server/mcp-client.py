import asyncio
import json
import aiohttp
from typing import Dict, Any, List, Optional
from aiohttp import ClientSession
from contextlib import AsyncExitStack
from mcp.client.stdio import StdioServerParameters, stdio_client, is_python

class VLLMClient:
    """Client for communicating with vLLM server"""
    
    def __init__(self, base_url: str = "http://localhost:8000/v1", api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = None
    
    '''
    Asynchronous context manager for vLLMClient to manage session lifecycle
    Each methods are called by async context manager (async with statement) to ensure proper session management
    '''
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    '''
    Sending chat completion request to vLLM server
    with adding tool information
    '''
    async def chat_completion(self, messages: List[Dict], tools: List[Dict] = None):
        """Send chat completion request to vLLM server"""
        url = f"{self.base_url}/v1/chat/completions"
        
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        payload = {
            "model": "google/gemma-3-27b-it",  # Use your model name
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 8192,
            "stream": True,  # Enable streaming
        }
        
        if tools:
            payload["tools"] = tools
        
        async with self.session.post(url, headers=headers, json=payload) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                raise Exception(f"vLLM request failed: {response.status} - {error_text}")

class MinecraftMCPClient:
    """MCP Client that integrates with vLLM and Minecraft MCP server"""
    
    def __init__(self, vllm_base_url: str, vllm_api_key: Optional[str] = None):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.vllm_client = VLLMClient(base_url=vllm_base_url, api_key=vllm_api_key)

    async def connect_server(self, server_script_path: str):
        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def send_query(self, query: str) -> str:
        """Send a query to the MCP server and return the response."""
        if not self.session:
            raise Exception("Not connected to MCP server")
        messages = [
            {
                "role": "user",
                "content": query
            }
        ]

        tools = self.session.list_tools()
        available_tools = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters
                }
            } for tool in tools
        ]

        response = await self.vllm_client.chat_completion(messages, tools=available_tools)
        if response and "choices" in response:
            # Extract the first choice's message content
            return response["choices"][0]["message"]["content"]

# Usage example
async def main():
    # Initialize MCP client with your vLLM server details
    client = MinecraftMCPClient(
        vllm_base_url="http://your-server-ip:8000",
        vllm_api_key="your_api_key"  # Optional if you set one
    )
    
    try:
        # Connect to your Minecraft MCP server
        await client.connect_to_mcp_server("path/to/your/minecraft_mcp_server.py")
        
        # Process user queries
        while True:
            user_input = input("\nEnter your query (or 'quit' to exit): ")
            if user_input.lower() == 'quit':
                break
                
            response = await client.process_query(user_input)
            print(f"\nResponse: {response}")
            
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())