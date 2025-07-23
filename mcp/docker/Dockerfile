FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    wget \
    unzip \
    bash \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Clone the repository
RUN git clone https://github.com/masudias/train-a-model.git

# Change to project directory
WORKDIR /app/train-a-model/mcp/

# Create and activate virtual environment + install requirements
RUN python -m venv mcp && \
    . mcp/bin/activate && \
    pip install --upgrade pip && \
    pip install -r requirements.txt


# Set Environment Varible
ENV MCP_SSE_URL=http://localhost:8080/sse
ENV OPENAI_API_KEY=sk-proj-XXXX

# Copy the entrypoint script, 
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/entrypoint.sh"]
