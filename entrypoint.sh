#!/bin/bash
set -e

# ---- Environment ----
export OPENAI_API_KEY="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"
export MCP_SSE_URL=http://localhost:8080/sse

# ---- Start MCP Server ----
echo "Starting MCP server..."
python -m drug_discovery_agent.interfaces.mcp.server &

# ---- Give the server a few seconds, need to be replace with "http://localhost:8080/healthz" api later, Retry until http://localhost:8080/healthz returns 200 ----
sleep 5

# ---- Start MCP Client ----
echo "Starting MCP client..."
python -m drug_discovery_agent.interfaces.mcp.client
