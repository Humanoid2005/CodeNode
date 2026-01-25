#!/bin/bash

# CodeNode Setup Script
# This script sets up both the backend and frontend for the CodeNode project

set -e  # Exit on error

echo "🚀 CodeNode Setup Script"
echo "========================"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Docker is installed and running
echo -e "${BLUE}Checking Docker...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! docker ps &> /dev/null; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker is available${NC}"

# Check Python
echo -e "${BLUE}Checking Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed. Please install Python 3.8+${NC}"
    exit 1
fi
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1-2)
echo -e "${GREEN}✓ Python $PYTHON_VERSION is available${NC}"

# Check Node.js
echo -e "${BLUE}Checking Node.js...${NC}"
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js is not installed. Please install Node.js 18+${NC}"
    exit 1
fi
NODE_VERSION=$(node --version)
echo -e "${GREEN}✓ Node.js $NODE_VERSION is available${NC}"

echo ""
echo -e "${YELLOW}Setting up Backend...${NC}"
echo "====================="

# Setup backend
cd server

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi

# Activate virtual environment and install dependencies
echo "Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt
echo -e "${GREEN}✓ Python dependencies installed${NC}"

# Pull Docker image
echo "Pulling Python Docker image (this may take a while on first run)..."
docker pull python:3.11-slim
echo -e "${GREEN}✓ Docker image ready${NC}"

# Create library directory
echo "Creating shared library directory..."
mkdir -p /tmp/codenode_library
chmod 755 /tmp/codenode_library
echo -e "${GREEN}✓ Library directory created${NC}"

deactivate
cd ..

echo ""
echo -e "${YELLOW}Setting up Frontend...${NC}"
echo "====================="

# Setup frontend
cd client

# Install npm dependencies
echo "Installing Node.js dependencies..."
npm install
echo -e "${GREEN}✓ Node.js dependencies installed${NC}"

cd ..

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✨ Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "To start the application:"
echo ""
echo -e "${BLUE}1. Start the backend:${NC}"
echo "   cd server"
echo "   source venv/bin/activate"
echo "   uvicorn main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo -e "${BLUE}2. In a new terminal, start the frontend:${NC}"
echo "   cd client"
echo "   npm run dev"
echo ""
echo -e "${BLUE}3. Open your browser:${NC}"
echo "   http://localhost:5173"
echo ""
echo -e "${GREEN}Happy coding! 🎉${NC}"
