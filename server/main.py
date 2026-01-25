"""
CodeNode API - Modular Backend
A secure containerized Python code execution platform
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from routes import code_execution_router

# Initialize FastAPI app
app = FastAPI(
    title="CodeNode API",
    version="2.0.0",
    description="Secure containerized Python code execution platform"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(code_execution_router, prefix="/api", tags=["Code Execution"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "CodeNode API is running",
        "version": "2.0.0",
        "status": "healthy"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
