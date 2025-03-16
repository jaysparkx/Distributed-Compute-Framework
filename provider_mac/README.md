# Mac Provider Client Setup

## Prerequisites
- Docker installed (Docker Desktop on Mac)

## Steps to Run
1. **Install Docker**:
   - Download and install Docker Desktop from docker.com
   - Start Docker Desktop

2. **Build Docker Image**:
   ```bash
   docker build -t provider_client_mac:latest .
   ```

3. **Run via Docker Compose**:
   See `docker-compose.yml` in the root directory. 