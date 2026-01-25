# CodeNode - Secure Containerized Python Code Editor

A full-stack online code editor that allows users to execute Python code in secure, isolated Docker containers with dependency management, environment variables, and real-time execution feedback. Built with FastAPI backend and React + TypeScript frontend.

## Features

### Security & Isolation
- **Docker Containerization**: Each code execution runs in an isolated Docker container
- **Non-root Execution**: Containers execute as non-root user (UID 1000)
- **Network Isolation**: No network access during code execution
- **Resource Limits**: 512MB memory and 50% CPU quota per container
- **Encrypted Secrets**: Secrets encrypted during transmission using Fernet encryption

### Execution Features
- **Real-time Streaming**: Server-Sent Events (SSE) for live execution feedback
- **Dependency Management**: Shared `/library` folder for persistent dependencies
- **Environment Variables**: Secure secrets management accessible via `os.environ`
- **Two-Phase Execution**:
  1. Installation Phase: Install dependencies with real-time logs
  2. Execution Phase: Run code with environment variables

### User Interface
- **Code Editor**: React-Ace editor with Python syntax highlighting
- **Interactive Popup**: Clean interface for code input and execution management
- **Real-time Logs**: Live streaming of installation and execution logs
- **Secrets Management**: Add/remove environment variables with encryption
- **Dependency Input**: Comma-separated package specification

## Prerequisites

### Backend
- Python 3.8 or higher
- Docker installed and running
- pip (Python package manager)

### Frontend
- Node.js 18 or higher
- npm or yarn

## Installation & Setup

### 1. Clone the Repository

```bash
cd OnlineCodeEditor
```

### 2. Backend Setup

```bash
cd server

# Create a virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify Docker is running
docker ps
```

### 3. Frontend Setup

```bash
cd ../client

# Install dependencies
npm install
```

##  Running the Application

### Start the Backend Server

```bash
cd server
source venv/bin/activate  # If not already activated
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The backend API will be available at `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`
- Alternative Docs: `http://localhost:8000/redoc`

### Start the Frontend Development Server

In a new terminal:

```bash
cd client
npm run dev
```

The frontend will be available at `http://localhost:5173`

## Usage Guide

### Basic Code Execution

1. **Write Code**: Enter your Python code in the editor
2. **Add Dependencies** (optional): Enter comma-separated packages (e.g., `requests, pandas, numpy`)
3. **Add Secrets** (optional): Add environment variables for your code
4. **Execute**: Click the "Execute" button to run your code
5. **View Output**: See real-time logs in the console output panel

### Using Environment Variables

In your Python code, access environment variables using:

```python
import os

api_key = os.environ.get("API_KEY")
database_url = os.environ.get("DATABASE_URL")
```

### Example with Dependencies

Add `requests` to the dependencies field, then:

```python
import requests

response = requests.get('https://api.github.com')
print(f"Status: {response.status_code}")
print(f"Data: {response.json()}")
```

## Project Structure

```
OnlineCodeEditor/
├── server/                 # FastAPI Backend
│   ├── main.py            # Main application with Docker integration
│   ├── requirements.txt   # Python dependencies
│   └── README.md          # Backend documentation
│
├── client/                # React Frontend
│   ├── src/
│   │   ├── components/    # React components
│   │   │   ├── CodeNodePopup.tsx    # Main code editor component
│   │   │   └── CodeNodePopup.css    # Component styles
│   │   ├── services/      # API services
│   │   │   └── api.ts     # SSE client implementation
│   │   ├── utils/         # Utility functions
│   │   │   └── encryption.ts  # Secrets encryption
│   │   ├── App.tsx        # Root component
│   │   └── main.tsx       # Entry point
│   ├── package.json       # Node dependencies
│   └── README.md          # Frontend documentation
│
└── README.md              # This file
```

## 🔒 Security Architecture

### Backend Security

1. **Container Isolation**: Each execution in separate Docker container
2. **Non-root User**: Containers run as UID 1000 (non-root)
3. **Network Disabled**: No network access during execution
4. **Resource Limits**:
   - Memory: 512MB per container
   - CPU: 50% of one core
5. **Timeout**: 30-second execution limit
6. **Encrypted Secrets**: Fernet encryption for sensitive data
7. **Read-only Code**: Code files mounted as read-only

### Frontend Security

1. **Secrets Encryption**: All secrets encrypted before transmission
2. **Server-Sent Events**: One-way communication for output
3. **No Credentials Storage**: Secrets not persisted locally

## Technologies Used

### Backend
- **FastAPI**: Modern, fast web framework for Python
- **Uvicorn**: ASGI server
- **Docker SDK**: Container management
- **SSE-Starlette**: Server-Sent Events
- **Cryptography**: Fernet encryption for secrets
- **Pydantic**: Data validation

### Frontend
- **React 18**: UI library
- **TypeScript**: Type-safe JavaScript
- **Vite**: Fast build tool
- **React-Ace**: Code editor component
- **@microsoft/fetch-event-source**: SSE client
- **crypto-js**: Client-side encryption

## API Endpoints

### GET /
Returns API information

### GET /health
Health check endpoint

### GET /api/encryption-key
Returns encryption key for client

### POST /api/run
Execute Python code with SSE streaming

**Request:**
```json
{
  "code": "print('Hello, World!')",
  "dependencies": ["requests"],
  "secrets": {"API_KEY": "value"},
  "encrypted_secrets": "base64_encrypted_data",
  "language": "python"
}
```

**SSE Events:**
- `log`: Execution logs (info, error, success, stdout, install)
- `done`: Execution completion status

## 🔧 Development

### Backend Development

The backend uses FastAPI's auto-reload feature:
```bash
uvicorn main:app --reload
```

Watch Docker containers:
```bash
docker ps -a
```

### Frontend Development

The frontend uses Vite's hot module replacement:
```bash
npm run dev
```

## Troubleshooting

### Docker Issues

**Docker not running:**
```bash
# Start Docker daemon
sudo systemctl start docker  # Linux
# or use Docker Desktop on Windows/Mac
```

**Permission denied:**
```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER
newgrp docker
```

**Container cleanup:**
```bash
# Remove all stopped containers
docker container prune -f

# Remove unused images
docker image prune -a -f
```

### GET /health
Health check endpoint

### POST /api/execute
Execute Python code

**Request:**
```json
{
  "code": "print('Hello, World!')",
  "language": "python"
}
```

**Response:**
```json
{
  "output": "Hello, World!\n",
  "error": null,
  "execution_time": 0.045
}
```

## Development

### Backend Development

The backend uses FastAPI's auto-reload feature:
```bash
uvicorn main:app --reload
```

### Frontend Development

The frontend uses Vite's hot module replacement:
```bash
npm run dev
```

