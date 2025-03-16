FROM python:3.9-slim

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install packages in a specific order to ensure compatibility
RUN pip install --no-cache-dir numpy==1.24.3 && \
    pip install --no-cache-dir torch==2.0.1 && \
    pip install --no-cache-dir -r requirements.txt

COPY provider_client_mac.py .

CMD ["python", "provider_client_mac.py"] 