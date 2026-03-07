"""
CodeNode API - Judge0 Backend
A code execution platform using Judge0 API
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv
import logging

from routes.code_execution import router as code_execution_router

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

app = FastAPI(
    title="CodeNode API",
    version="3.1.0",
    description="Code execution platform powered by Judge0 with whitelisted package installation"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(code_execution_router, prefix="/api", tags=["Code Execution"])


@app.get("/")
async def root():
    return {
        "message": "CodeNode API is running",
        "version": "3.1.0",
        "status": "healthy",
        "powered_by": "Judge0",
        "features": [
            "sandboxed_execution",
            "encrypted_secrets",
            "network_filtering",
            "whitelisted_package_installation",
            "rasp_ready_execution_service"
        ]
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)