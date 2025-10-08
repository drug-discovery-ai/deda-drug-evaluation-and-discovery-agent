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

# point PYTHONPATH to src
ENV PYTHONPATH=/app/src

ENTRYPOINT ["/app/entrypoint.sh"]
