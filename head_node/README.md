# Head Node Setup

## Prerequisites
- Docker installed

## Steps to Run
1. **Install Docker**:
   ```bash
   sudo apt update
   sudo apt install docker.io
   sudo systemctl start docker
   sudo systemctl enable docker
   ```

2. **Build Docker Image**:
   ```bash
   docker build -t head_node:latest .
   ```

3. **Run via Docker Compose**:
   See `docker-compose.yml` in the root directory. 