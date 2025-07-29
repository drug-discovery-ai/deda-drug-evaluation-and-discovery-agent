FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /var/cache/apt/archives/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .
RUN chmod +x /app/entrypoint.sh

# Set Environment Variables
ENV PYTHONPATH=/app
ENV MCP_SSE_URL=http://localhost:8080/sse
# Provide a valid OpenAI API key
ENV OPENAI_API_KEY="sk-proj-XXXX"

# Set the entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
