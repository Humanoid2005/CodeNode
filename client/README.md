# CodeNode Client (React + TypeScript + Vite)

A modern online code editor frontend built with React, TypeScript, and Vite. Features React-Ace editor for a powerful editing experience with real-time execution feedback via Server-Sent Events.

## Features

- 🎨 React-Ace Editor integration with Python syntax highlighting
- 🎯 TypeScript for type safety
- ⚡ Vite for fast development and building
- 🎨 Clean, modern UI with dark theme inspired by VS Code
- 📱 Responsive design
- ⚡ Real-time code execution with SSE streaming
- � Secure secrets/environment variables management
- 📦 Dependency management interface
- 🔍 Live execution logs with color-coded output

## Prerequisites

- Node.js (v18 or higher)
- npm or yarn
- Backend server running on `http://localhost:8000`

## Setup

1. Install dependencies:
```bash
npm install
```

## Development

Start the development server:
```bash
npm run dev
```

The application will be available at `http://localhost:5173`

## Building for Production

Build the application:
```bash
npm run build
```

Preview the production build:
```bash
npm run preview
```

## Project Structure

```
src/
├── components/          # React components
│   ├── CodeNodePopup.tsx   # Main code editor popup component
│   └── CodeNodePopup.css   # Component styles
├── services/            # API services
│   └── api.ts           # SSE client and backend API integration
├── utils/               # Utility functions
│   └── encryption.ts    # Secrets encryption utilities
├── App.tsx              # Root component
├── App.css              # App styles
├── index.css            # Global styles
└── main.tsx             # Application entry point
```

## Key Components

### CodeNodePopup
The main interactive popup interface that includes:
- **Code Editor**: React-Ace editor with Python syntax highlighting
- **Dependencies Input**: Comma-separated package specification
- **Secrets Management**: Add/edit/remove environment variables with show/hide toggle
- **Console Output**: Real-time execution logs with color-coded messages

### API Service
Handles Server-Sent Events (SSE) communication with the backend:
- Fetches encryption key for secrets
- Executes code with streaming responses
- Processes real-time log events

### Encryption Utilities
Client-side encryption for secrets before transmission to backend

## Configuration

The frontend is configured to proxy API requests to the backend server running on `http://localhost:8000`. This is configured in `vite.config.ts`.

## Technologies Used

- **React 18**: UI library with hooks
- **TypeScript**: Type-safe JavaScript
- **Vite**: Build tool and dev server
- **React-Ace**: Code editor component (based on Ace Editor)
- **@microsoft/fetch-event-source**: SSE client for real-time streaming
- **crypto-js**: Client-side encryption library

## Features in Detail

### Code Editor
- Python syntax highlighting
- Line numbers
- Auto-completion
- Monokai dark theme
- Tab size: 4 spaces

### Execution Flow
1. User enters code and optionally adds dependencies/secrets
2. Secrets are encrypted before transmission
3. Click "Execute" to trigger code execution
4. Real-time logs stream via SSE:
   - Installation logs (blue/orange)
   - Execution logs (white)
   - Success messages (green)
   - Error messages (red)
5. Results displayed in console output panel

### Secrets Management
- Add multiple environment variables as key-value pairs
- Toggle visibility of secret values
- Encrypted before sending to backend
- Accessible in Python code via `os.environ.get("KEY")`

## Available Scripts

- `npm run dev` - Start development server with HMR
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## Environment Variables

Create a `.env` file (optional):
```
VITE_API_URL=http://localhost:8000
```

## Notes

- Make sure the backend server is running on port 8000 before starting the frontend
- Docker must be available on the backend for code execution
- All code executes in isolated Docker containers for security
