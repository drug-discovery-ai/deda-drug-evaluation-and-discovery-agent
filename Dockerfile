FROM python:3.12-slim

WORKDIR /app

# System deps
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libffi-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the full app
COPY . .

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# ✅ Fix: point PYTHONPATH to src
ENV PYTHONPATH=/app/src

# Other envs
ENV MCP_SSE_URL=http://localhost:8080/sse

ENTRYPOINT ["/app/entrypoint.sh"]
