#!/bin/bash
set -e

# Set the API key here
export OPENAI_API_KEY="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"

echo "Starting MCP server..."
python -m drug_discovery_agent.interfaces.mcp.server
