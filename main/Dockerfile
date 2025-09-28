# Base
FROM python:3.11-slim

# Working directory
WORKDIR /app

# Install system deps if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt requirements.txt

# Install Python deps
RUN pip install --no-cache-dir -r requirements.txt

# Also install LangGraph CLI + extra if needed
RUN pip install --no-cache-dir "langgraph-cli[all]"

# Copy everything (including Mcp_client_word from parent directory)
COPY . .
COPY ../Mcp_client_word ./Mcp_client_word

# Expose the port LangGraph Studio / Server will use
EXPOSE 8080

# Default command
CMD ["langgraph", "dev", "--host", "0.0.0.0", "--port", "8080"]

