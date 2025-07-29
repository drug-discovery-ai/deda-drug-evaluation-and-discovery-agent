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
WORKDIR /app/train-a-model/

# Create and activate virtual environment + install requirements
RUN python -m venv venv && \
    . venv/bin/activate && \
    pip install --upgrade pip && \
    pip install -r requirements.txt


# Set Environment Varible
ENV MCP_SSE_URL=http://localhost:8080/sse
ENV OPENAI_API_KEY=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

# Copy the entrypoint script, 
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/entrypoint.sh"]
