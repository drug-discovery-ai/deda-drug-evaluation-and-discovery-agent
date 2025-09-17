# Bio-informatics AI agent for Drug discovery Research

<p align="center">
  <img src="assets/logo.png" alt="Drug Discovery AI Agent Logo" width="333"/>
</p>

Follow our [wiki pages](https://github.com/drug-discovery-ai/deda-drug-evaluation-and-discovery-agent/wiki) for more insight.

## Overview

Agentic AI allows people to control system components using plain language. It is flexible enough that experts from different fields can connect it to their own tools—reducing hallucinations by ensuring the AI interacts with real systems rather than guessing.

We built this project on that foundation, focusing on bioinformatics researchers who want to explore drug discovery, analyze protein structures, prototype ideas quickly, and more—all through natural language commands. For example, instead of writing code to fetch a protein or run a molecule generation tool, you can simply ask:

```bash
Show known binding pockets for the SARS-CoV-2 virus.
```

<p align="center">
  <img src="electron-app/demo.gif" style="width:100%; max-width:100%;"/>
</p>


Behind the scenes, the AI can connect to trusted data sources such as **UniProt**, **AlphaFold**, and **OpenTargets**, grounding its responses in real biological and chemical knowledge and reducing the risk of _hallucination_. This approach makes complex bioinformatics workflows more accessible, accurate, and reproducible—empowering researchers to focus on discovery rather than tooling.


## Quick Start

### Installation

Create a virtual environment using `python` version `3.12` or later.

```bash
python3 -m venv venv
```

Then activate the environment:

```bash
source venv/bin/activate
```

Then install the required packages:

```bash
pip install -r requirements.txt
```

```bash
pip install -e .
```

#### Setting Up Environment Variables

Before running any component, configure the required environment variables.
Copy the example environment file:

```bash
cp .env.example .env
```

Edit the `.env` file and add your OpenAI API key:

```
OPENAI_API_KEY=your_openai_api_key_here
```

---

## Running the Application

This project provides multiple ways to interact with the bioinformatics AI agent:

### 1. Running MCP Server

The Model Control Protocol (MCP) server provides the core AI agent functionality that can be integrated with compatible
clients like Claude Desktop.

Start the MCP server:

```bash
# Basic server
python -m drug_discovery_agent.interfaces.mcp.server

# With custom port
python -m drug_discovery_agent.interfaces.mcp.server --port 8081
```

The server will start on `localhost:8080` by default and can be connected to by MCP-compatible clients.

### 2. Running Chat on CLI

For quick terminal-based interactions with the AI agent:

```bash
python -m drug_discovery_agent.chat
# or simply
chat
```

#### Debug and Verbose Mode

To see detailed tool selection and execution activity (useful for debugging or understanding how the AI agent works):

```bash
python -m drug_discovery_agent.chat --verbose
# or
python -m drug_discovery_agent.chat --debug
```

This will show:

- Tool selection decisions made by the LLM
- Tool execution steps and reasoning
- Input/output details for each tool call
- Agent's internal reasoning process

Try queries like: `Show me details for UniProt ID P0DTC2`, followed
by `What are the structural properties of this protein?`

### 3. Running Chat on UI (Desktop App)

For a modern, user-friendly desktop experience, use the Electron-based chat interface:

**📱 [See the full Desktop App documentation →](electron-app/README.md)**

Quick setup:

```bash
cd electron-app
npm install
npm run dev
```

The desktop app provides:

- Modern chat interface with message history
- Real-time AI responses with progress indicators
- Session management and conversation persistence
- Cross-platform support (Windows, macOS, Linux)
- Integrated backend server management

#### Creating Distribution Installers

To create installable packages for distribution:

**📦 [See detailed installer creation guide →](electron-app/README.md#-creating-distribution-installers)**

Quick installer build:

```bash
# Navigate to electron-app directory
cd electron-app

# Build Python backend first
npm run build:python

# Then build Electron installer
npm run build:mac    # or build:win, build:linux
```

Supports creating native installers for Windows (.exe), macOS (.dmg), and Linux (.AppImage) with automatic environment
configuration and backend bundling.

# Development

## Code Quality

This project uses `ruff` for linting and formatting, and `mypy` for type checking.

### Development Setup

Install development dependencies:

```bash
pip install -e ".[dev]"
pre-commit install
```

The `pre-commit install` sets up Git hooks to automatically run `ruff`, `mypy`, and `pytest` before each commit,
preventing broken code from reaching the repository.

Run linting:

```bash
ruff check .          # Check for linting issues
ruff check . --fix    # Auto-fix linting issues
ruff format .         # Auto-format code
```

Run type checking:

```bash
mypy .                # Run type checking on all files
```

## Testing

The project includes a unified snapshot testing system for reliable, fast API testing:

### Run Tests

```bash
# Run all tests (uses snapshots by default - fast, no network calls)
pytest

# Run only unit tests (uses mocks)
pytest -k "unit"

# Run only integration tests (uses snapshots)  
pytest -k "integration"

# Update snapshots from live APIs (when APIs change)
pytest --update-snapshots

# Validate existing snapshots against live APIs
pytest --validate-snapshots
```

### Test Architecture

- **Unit tests**: Use `@patch` decorators for fast, isolated testing
- **Integration tests**: Use `@pytest.mark.integration` with automatic snapshot/recording
- **Snapshots**: Real API responses captured for realistic testing without network calls
- **HTTP Interception**: Transparent to application code - no changes needed to API clients

See `snapshots/README.md` for detailed information about the snapshot testing system.

# Run the AI assistant using Docker

**Pre-requisite** Make sure your `docker` runs in `rootless` mode. If you can run

```
docker run hello-world
```

without `sudo`, you are good to go.

### Change API Key Before Proceeding

Inside `Dockerfile`, replace the `OPENAI_API_KEY`, with your openAI api key.

```
ENV OPENAI_API_KEY=sk-proj-XXXX
```

Run the following command to build the docker image

```
docker build --no-cache -t mcp_app .
```

To test

```
docker run -it mcp_app
```

Enjoy chatting!