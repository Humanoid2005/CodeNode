# CodeNode - Online Code Editor

A full-stack online code editor with secure sandboxed execution for 12+ programming languages. Built with React + TypeScript frontend, FastAPI backend, and Judge0 for code execution.

## Features

- **Multi-language Support**: Python, JavaScript, C++, C, Java, C#, Ruby, Go, Rust, PHP, TypeScript, Bash
- **Sandboxed Execution**: Code runs in isolated containers via Judge0
- **Encrypted Secrets**: AES-256-GCM encryption for environment variables
- **Modern Editor**: React-Ace with syntax highlighting and dark theme

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client (React)                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  Code Editor │  │  Secrets    │  │  Console Output (SSE)   │  │
│  │  (React-Ace) │  │  Manager    │  │                         │  │
│  └──────┬───────┘  └──────┬──────┘  └────────────▲────────────┘  │
│         │                 │                      │               │
│         │    ┌────────────▼────────────┐         │               │
│         │    │  AES-256-GCM Encryption │         │               │
│         │    └────────────┬────────────┘         │               │
│         └────────────────┬┘                      │               │
└──────────────────────────┼───────────────────────┼───────────────┘
                           │ HTTPS                 │ SSE
┌──────────────────────────▼───────────────────────┼───────────────┐
│                      Server (FastAPI)            │               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────┴─────┐         │
│  │  Code Execution │  │  Crypto Service │  │  SSE      │         │
│  │  Routes         │  │  (Decrypt)      │  │  Stream   │         │
│  └────────┬────────┘  └─────────────────┘  └───────────┘         │
│           │                                                       │
│           │ REST API                                              │
│  ┌────────▼────────┐                                             │
│  │  Judge0 Service │                                             │
│  └────────┬────────┘                                             │
└───────────┼──────────────────────────────────────────────────────┘
            │
┌───────────▼──────────────────────────────────────────────────────┐
│                    Judge0 (Docker Compose)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐   │
│  │  API Server │  │  Workers    │  │  Redis + PostgreSQL     │   │
│  │  (Rails)    │  │  (Isolate)  │  │                         │   │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
OnlineCodeEditor/
├── client/                     # React + TypeScript + Vite
│   ├── src/
│   │   ├── components/         # UI components (CodeNodePopup)
│   │   ├── services/           # API client
│   │   └── utils/              # AES-256-GCM encryption
│   └── package.json
│
├── server/                     # FastAPI backend
│   ├── main.py                 # App entry point
│   ├── routes/                 # API endpoints
│   │   └── code_execution.py   # /api/run, /api/run/tests
│   ├── services/
│   │   ├── judge0_service.py   # Judge0 REST API client
│   │   └── crypto_service.py   # AES-256-GCM decryption
│   ├── proxy/                  # Network filter proxy
│   │   └── filter_addon.py     # mitmproxy addon
│   └── requirements.txt
│
├── docker-compose.yml          # Judge0 + proxy stack
├── Dockerfile.judge0-cg2       # Custom Judge0 image (cgroup v2)
├── judge0.conf                 # Judge0 configuration
└── README.md
```

## Implementation Details

| Component | Technology | Purpose |
|-----------|------------|---------|
| Frontend | React 18, TypeScript, Vite | Code editor UI with React-Ace |
| Backend | FastAPI, Python 3.10+ | REST API |
| Execution | Judge0 (self-hosted) | Sandboxed code execution |
| Encryption | AES-256-GCM | Client-side secret encryption |
| Communication | SSE | Real-time execution output |

## Running Locally

### Prerequisites

- **Docker** with Docker Compose v2
- **Python 3.10+**
- **Node.js 18+**
- **Linux with cgroup v2** (required for Judge0 sandboxing)

> **Note**: The custom Judge0 image uses isolate v2.0 which requires cgroup v2. Most modern Linux distros (Ubuntu 22.04+, Fedora 31+) use cgroup v2 by default.

### 1. Clone & Setup

```bash
git clone https://github.com/YOUR_USERNAME/OnlineCodeEditor.git
cd OnlineCodeEditor
```

### 2. Start Judge0 (Docker)

```bash
# Build custom Judge0 image and start all services
docker-compose up -d --build

# Wait for services to be ready (~60 seconds for first build)
# Check if Judge0 is running:
curl http://localhost:2358/about
```

This starts:
- **judge0-server** - API server on port 2358
- **judge0-workers** - Code execution workers
- **judge0-db** - PostgreSQL database
- **judge0-redis** - Redis for job queue
- **filter-proxy** - Network filter (mitmproxy)

### 3. Start Backend

```bash
cd server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

Backend runs at `http://localhost:8000` (API docs: `http://localhost:8000/docs`)

### 4. Start Frontend

```bash
cd client
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`

## Network Filtering

By default, code runs with **network disabled** for security. To enable network access:

1. Set `enable_network: true` in the submission
2. Optionally provide an `allowed_urls` list to restrict which domains can be accessed

Example API call with network enabled:
```json
{
  "source_code": "import requests; print(requests.get('https://httpbin.org/get').status_code)",
  "language": "python",
  "enable_network": true,
  "allowed_urls": ["httpbin.org", "api.example.com"]
}
```

## Stopping Services

```bash
# Stop all Docker services
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v
```

## Troubleshooting

### "cgroup v1 is not supported" error

Your system needs cgroup v2. Check with:
```bash
mount | grep cgroup
# Should show "cgroup2" not "cgroup"
```

On Ubuntu/Debian, cgroup v2 is default on 22.04+. For older versions, add to `/etc/default/grub`:
```
GRUB_CMDLINE_LINUX="systemd.unified_cgroup_hierarchy=1"
```
Then run `sudo update-grub && sudo reboot`.

### Judge0 workers not starting

Check logs:
```bash
docker-compose logs judge0-workers
```

Common fixes:
- Ensure Docker is running in privileged mode (already configured in docker-compose.yml)
- Make sure `/sys/fs/cgroup` is mounted correctly

### Port conflicts

- Judge0 API: 2358
- Backend: 8000
- Frontend: 5173

If ports are in use, either stop conflicting services or modify the ports in `docker-compose.yml` and the respective config files.

