# CodeNode Backend (FastAPI)

A FastAPI backend server for executing Python code in secure, containerized Docker environments with dependency management and real-time execution feedback.

## Features

- **Docker Containerization**: Each code execution runs in an isolated Docker container
- **Dependency Management**: Shared `/library` folder for persistent dependencies
- **Real-time Streaming**: Server-Sent Events (SSE) for live execution feedback
- **Security**: 
  - Non-root user execution in containers
  - Network isolation
  - Resource limits (CPU, memory)
  - Encrypted secrets transmission
- **Two-Phase Execution**:
  - Phase 1: Dependency installation
  - Phase 2: Code execution with environment variables

## Prerequisites

- Python 3.8+
- Docker installed and running
- Docker daemon accessible

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Ensure Docker is running:
```bash
docker ps  # Should not error
```

## Running the Server

### Development Mode
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode
```bash
python main.py
```

The server will be available at `http://localhost:8000`

## API Endpoints

### GET /
Returns API information and version

### GET /health
Health check endpoint

### GET /api/encryption-key
Returns encryption key for client to encrypt secrets

**Response:**
```json
{
  "key": "base64_encoded_key"
}
```

### POST /api/run
Execute Python code with SSE streaming

**Request Body:**
```json
{
  "code": "print('Hello, World!')",
  "dependencies": ["requests", "pandas"],
  "secrets": {
    "API_KEY": "secret_value"
  },
  "encrypted_secrets": "encrypted_base64_string",
  "language": "python"
}
```

**SSE Events:**

The endpoint returns Server-Sent Events with the following event types:

1. **log** - Execution logs
```json
{
  "type": "info|error|success|stdout|install",
  "message": "log message"
}
```

2. **done** - Execution completed
```json
{
  "status": "complete|error"
}
```

## Execution Flow

### Phase 1: Installation Phase
1. Pull Python Docker image (first time only)
2. Send SSE: "Installing dependencies"
3. Start container with `/library` mounted as read-write
4. Execute: `pip install --target=/library <dependencies>`
5. Stream installation logs via SSE
6. Stop and remove container

### Phase 2: Execution Phase
1. Decrypt secrets (if encrypted)
2. Create temporary file with user code
3. Send SSE: "Executing code"
4. Start container with:
   - Code file mounted as read-only
   - `/library` in PYTHONPATH
   - Secrets as environment variables
   - Non-root user (UID 1000)
   - Network disabled
   - Resource limits (512MB RAM, 50% CPU)
5. Stream STDOUT in real-time via SSE
6. Send completion status
7. Clean up temporary files and container

## Security Features

- **Container Isolation**: Each execution in separate container
- **Non-root Execution**: Containers run as UID 1000
- **Network Disabled**: No network access during execution
- **Resource Limits**: 512MB memory, 50% CPU quota
- **Timeout Protection**: 30-second execution timeout
- **Encrypted Secrets**: Fernet encryption for sensitive data
- **Read-only Code**: Code files mounted as read-only

## Docker Configuration

The backend requires:
- Docker image: `python:3.11-slim`
- Shared library path: `/tmp/codenode_library`
- Container resources:
  - Memory limit: 512MB
  - CPU quota: 50% of one core
  - Network: disabled
  - User: 1000:1000 (non-root)

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Troubleshooting

### Docker Not Available
```bash
# Check if Docker is running
docker ps

# On Linux, add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### Permission Issues
```bash
# Ensure library directory is writable
chmod 755 /tmp/codenode_library
```

### Container Cleanup
```bash
# Remove stopped containers
docker container prune -f

# Remove unused images
docker image prune -a -f
```
