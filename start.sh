#!/bin/bash

# CodeNode Start Script
# Starts both backend and frontend in separate terminal windows

echo "🚀 Starting CodeNode..."

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if setup has been run
if [ ! -d "$SCRIPT_DIR/server/venv" ]; then
    echo "❌ Setup not complete. Please run ./setup.sh first"
    exit 1
fi

if [ ! -d "$SCRIPT_DIR/client/node_modules" ]; then
    echo "❌ Setup not complete. Please run ./setup.sh first"
    exit 1
fi

# Function to start backend
start_backend() {
    cd "$SCRIPT_DIR/server"
    echo "Starting backend on http://localhost:8000"
    source venv/bin/activate
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
}

# Function to start frontend
start_frontend() {
    cd "$SCRIPT_DIR/client"
    echo "Starting frontend on http://localhost:5173"
    npm run dev
}

# Detect terminal emulator and open new windows
if command -v gnome-terminal &> /dev/null; then
    # GNOME Terminal
    gnome-terminal -- bash -c "cd '$SCRIPT_DIR' && $(declare -f start_backend) && start_backend; exec bash"
    sleep 2
    gnome-terminal -- bash -c "cd '$SCRIPT_DIR' && $(declare -f start_frontend) && start_frontend; exec bash"
elif command -v xterm &> /dev/null; then
    # xterm
    xterm -e "cd '$SCRIPT_DIR' && $(declare -f start_backend) && start_backend; bash" &
    sleep 2
    xterm -e "cd '$SCRIPT_DIR' && $(declare -f start_frontend) && start_frontend; bash" &
else
    # Fallback: run in background with logs
    echo "Starting services in background..."
    echo "Backend logs: $SCRIPT_DIR/backend.log"
    echo "Frontend logs: $SCRIPT_DIR/frontend.log"
    
    cd "$SCRIPT_DIR/server"
    source venv/bin/activate
    uvicorn main:app --reload --host 0.0.0.0 --port 8000 > ../backend.log 2>&1 &
    BACKEND_PID=$!
    
    cd "$SCRIPT_DIR/client"
    npm run dev > ../frontend.log 2>&1 &
    FRONTEND_PID=$!
    
    echo "Backend PID: $BACKEND_PID"
    echo "Frontend PID: $FRONTEND_PID"
    echo ""
    echo "To stop services:"
    echo "  kill $BACKEND_PID $FRONTEND_PID"
    echo ""
    echo "To view logs:"
    echo "  tail -f backend.log"
    echo "  tail -f frontend.log"
fi

echo ""
echo "✨ CodeNode is starting!"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo "API Docs: http://localhost:8000/docs"
