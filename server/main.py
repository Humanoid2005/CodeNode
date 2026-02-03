"""
CodeNode API - Judge0 Backend
A code execution platform using Judge0 API
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv

from routes.code_execution import router as code_execution_router

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="CodeNode API",
    version="3.0.0",
    description="Code execution platform powered by Judge0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
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
        "version": "3.0.0",
        "status": "healthy",
        "powered_by": "Judge0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

