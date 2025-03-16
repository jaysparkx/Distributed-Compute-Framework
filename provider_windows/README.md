# Windows Provider Client Setup

## Prerequisites
- Docker installed (Docker Desktop on Windows)
- Optional: NVIDIA Container Toolkit for GPU support

## Steps to Run
1. **Install Docker**:
   - Download and install Docker Desktop from docker.com
   - Enable WSL2 if needed

2. **Install NVIDIA Container Toolkit (if using GPU)**:
   - Follow: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html

3. **Build Docker Image**:
   ```bash
   docker build -t provider_client_windows:latest .
   ```

4. **Run via Docker Compose**:
   See `docker-compose.yml` in the root directory. 