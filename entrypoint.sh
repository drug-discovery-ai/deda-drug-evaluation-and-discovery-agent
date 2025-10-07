#!/bin/bash
set -e

# Set the API key here
export OPENAI_API_KEY="demo-proj-XXXX"

# Set the MCP SSE Communication Endpint
export MCP_SSE_URL=http://localhost:8080/sse

# RUN MCP Server
echo "Starting MCP server..."
python -m drug_discovery_agent.interfaces.mcp.server
