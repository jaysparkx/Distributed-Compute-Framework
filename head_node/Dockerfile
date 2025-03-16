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
RUN pip install --no-cache-dir numpy==1.21.0 && \
    pip install --no-cache-dir torch==1.12.1 && \
    pip install --no-cache-dir -r requirements.txt

COPY head_node.py .

EXPOSE 5000 5555 5556 5557 5558

CMD ["python", "head_node.py"] 