# CodeNode - Online Code Editor

A full-stack online code editor with secure sandboxed execution for 12+ programming languages. Built with React + TypeScript frontend, FastAPI backend, and Judge0 for code execution.

## Features

- **Multi-language Support**: Python, JavaScript, C++, C, Java, C#, Ruby, Go, Rust, PHP, TypeScript, Bash
- **Sandboxed Execution**: Code runs in isolated containers via Judge0
- **Encrypted Secrets**: AES-256-GCM encryption for environment variables
- **Real-time Output**: Server-Sent Events (SSE) for live execution feedback
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
│   │   ├── services/           # API client with SSE support
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
│   ├── judge0/                 # Self-hosted Judge0 config
│   └── requirements.txt
│
└── README.md
```

## Implementation Details

| Component | Technology | Purpose |
|-----------|------------|---------|
| Frontend | React 18, TypeScript, Vite | Code editor UI with React-Ace |
| Backend | FastAPI, Python 3.10+ | REST API with SSE streaming |
| Execution | Judge0 (self-hosted) | Sandboxed code execution |
| Encryption | AES-256-GCM | Client-side secret encryption |
| Communication | SSE | Real-time execution output |

## Running Locally

### Prerequisites
- Python 3.10+, Node.js 18+, Docker & Docker Compose

### 1. Start Judge0

```bash
cd server/judge0
docker-compose up -d
# Wait for services to be ready (~30 seconds)
curl http://localhost:2358/about
```

### 2. Start Backend

```bash
cd server
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python main.py
```

Backend runs at `http://localhost:8000` (API docs: `/docs`)

### 3. Start Frontend

```bash
cd client
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`

