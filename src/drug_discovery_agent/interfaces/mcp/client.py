"""
NOTE: This `client.py` is a simplified Docker client implementation
intended primarily for local development and testing.

It demonstrates how to interact with the MCP/Starlette backend
within a containerized setup — suitable for debugging, demos,
or minimal client-side validation.

CAUTION: Do not use this file directly in production.

For production environments:
    - Implement your own robust `client.py` with proper error handling,
      logging, retries, authentication, and secure connection management.
    - Ensure it aligns with your deployment’s Docker, network,
      and security policies.

In short → treat this as a reference or starting point, not as a ready-to-deploy client.
"""

import asyncio
import json
import os
from contextlib import AsyncExitStack
from typing import Any

from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.sse import sse_client
from openai import OpenAI
from openai.types.chat import ChatCompletion

load_dotenv()  # Load environment variables from .env file


class MCPClient:
    """A typed MCP client that connects to an SSE-based MCP server and integrates with OpenAI."""

    def __init__(self) -> None:
        """Initialize the MCP client with session management and OpenAI setup."""
        self.session: ClientSession | None = None
        self.exit_stack: AsyncExitStack = AsyncExitStack()
        self.openai: OpenAI = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.available_tools: list[dict[str, Any]] = []
        self.messages: list[dict[str, Any]] = []

    async def connect_to_sse_server(self, server_url: str) -> None:
        """
        Connect to the MCP SSE server and initialize the client session.

        Args:
            server_url (str): URL of the MCP SSE server (e.g., http://localhost:8080/sse).
        """
        print("Connecting to MCP SSE server...")
        self._streams_context = sse_client(url=server_url)
        streams = await self._streams_context.__aenter__()
        print("Streams:", streams)

        self._session_context = ClientSession(*streams)
        self.session = await self._session_context.__aenter__()

        print("Initializing SSE client...")
        await self.session.initialize()
        print("Initialized SSE client")

        await self.get_available_tools()
        await self.get_initial_prompts()

    async def cleanup(self) -> None:
        """Properly clean up the session and streams."""
        if hasattr(self, "_session_context") and self._session_context:
            await self._session_context.__aexit__(None, None, None)
        if hasattr(self, "_streams_context") and self._streams_context:
            await self._streams_context.__aexit__(None, None, None)

    async def get_initial_prompts(self) -> None:
        """Fetch and cache the initial prompts defined on the MCP server."""
        if not self.session:
            raise RuntimeError("Session not initialized.")
        prompt = await self.session.get_prompt("get_initial_prompts")

        messages: list[dict[str, str]] = []
        for message in prompt.messages:
            messages.append({"role": message.role, "content": message.content.text})
        self.messages = messages

    async def get_available_tools(self) -> None:
        """Retrieve and format available tools from the MCP server."""
        if not self.session:
            raise RuntimeError("Session not initialized.")

        print("Fetching available server tools...")
        response = await self.session.list_tools()
        print(
            "Connected to MCP server with tools:",
            [tool.name for tool in response.tools],
        )

        self.available_tools = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                },
                "strict": True,
            }
            for tool in response.tools
        ]

    async def call_openai(self) -> ChatCompletion:
        """
        Call OpenAI with the current conversation and tool metadata.

        Returns:
            ChatCompletion: The OpenAI response object.
        """
        return self.openai.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=1000,
            messages=self.messages,
            tools=self.available_tools,
        )

    async def process_openai_response(self, response: ChatCompletion) -> str:
        """
        Handle the OpenAI response, including any tool invocations.

        Args:
            response (ChatCompletion): The response returned by the OpenAI API.

        Returns:
            str: The assistant’s final textual response.
        """
        for choice in response.choices:
            if choice.finish_reason == "tool_calls":
                # Save assistant message before tool invocation
                self.messages.append(choice.message)

                for tool_call in choice.message.tool_calls or []:
                    tool_name: str = tool_call.function.name
                    tool_args: dict[str, Any] = json.loads(tool_call.function.arguments)
                    assert self.session is not None, (
                        "Client session is not initialized."
                    )
                    print(f" Calling tool '{tool_name}' with args: {tool_args}")
                    result = await self.session.call_tool(tool_name, tool_args)

                    self.messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result.content,
                        }
                    )

                # Recursively process next step
                next_response = await self.call_openai()
                return await self.process_openai_response(next_response)

            elif choice.finish_reason == "stop":
                content = choice.message.content or ""
                print(f"\nAssistant: {content}")
                return content

        return ""

    async def process_query(self, query: str) -> str:
        """
        Send a query to OpenAI and handle possible MCP tool calls.

        Args:
            query (str): The user’s input.

        Returns:
            str: The final assistant output after any tool interactions.
        """
        self.messages.append({"role": "user", "content": query})

        response = await self.call_openai()
        return await self.process_openai_response(response)

    async def chat_loop(self) -> None:
        """Run an interactive command-line chat loop."""
        print("\n\n MCP Client started! Type your queries or 'quit' to exit.\n\n")

        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() == "quit":
                    break
                if query:
                    await self.process_query(query)
            except Exception as e:
                print(f"Error: {e}")


async def main() -> None:
    """Entry point for running the MCP chat client."""
    client = MCPClient()
    try:
        server_url = os.getenv("MCP_SSE_URL")
        if not server_url:
            raise RuntimeError("MCP_SSE_URL not set in .env file.")

        await client.connect_to_sse_server(server_url=server_url)
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
