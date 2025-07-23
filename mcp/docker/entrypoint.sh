#!/bin/bash
set -e

# Activate virtual environment
source /app/train-a-model/mcp/mcp/bin/activate

# Start the server in background
echo "Starting MCP server..."
python /app/train-a-model/mcp/boltz/server.py &

# Wait few moments MCP server to get started.
sleep 2

# Run the MCP client
echo "Starting MCP client..."
python /app/train-a-model/mcp/boltz/client.py

