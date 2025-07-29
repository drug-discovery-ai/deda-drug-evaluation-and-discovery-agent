#!/bin/bash
set -e
ls
# Start the server in background
echo "Starting MCP server..."
python mcp/boltz/server.py &

# Wait for the server to start
echo "Waiting for MCP server to start..."
sleep 3

# Run the MCP client
echo "Starting MCP client..."
python mcp/boltz/client.py

