FROM python:3.12-slim

WORKDIR /app

# Install only essential system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
# RUN pip install -r requirements.txt
# for first build use --no-cache-dir to avoid cache issues
RUN pip install --no-cache-dir -r requirements.txt

# Copy code & data
COPY src/ ./src
COPY data/ ./data

# Start server (with auto-reload in dev)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
