"""Code execution API routes"""
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
from sse_starlette.sse import EventSourceResponse

from docker_manager.client import DockerClientManager
from docker_manager.container import ContainerManager
from services import (
    CodeExecutionService,
    DependencyInstallerService,
    CryptographyService
)

router = APIRouter()

# Initialize services
crypto_service = CryptographyService()


class CodeExecutionRequest(BaseModel):
    code: str
    dependencies: List[str] = []
    secrets: Dict[str, str] = {}
    encrypted_secrets: Optional[str] = None
    language: str = "python"
    enable_network: bool = False  # Allow network access if needed


@router.get("/encryption-key")
async def get_encryption_key():
    """Return the encryption key for the client to encrypt secrets"""
    return {"key": crypto_service.get_encryption_key_base64()}


@router.post("/run")
async def run_code(request: CodeExecutionRequest):
    """Execute Python code in a containerized environment with SSE streaming"""
    
    async def event_generator():
        try:
            # Get Docker client
            docker_client = DockerClientManager.get_client()
            
            if docker_client is None:
                yield {
                    "event": "log",
                    "data": json.dumps({
                        "type": "error",
                        "message": "Docker is not available. Please ensure Docker or Docker Desktop is running."
                    })
                }
                yield {
                    "event": "done",
                    "data": json.dumps({"status": "error"})
                }
                return
            
            # Initialize managers and services
            container_manager = ContainerManager(docker_client)
            dependency_service = DependencyInstallerService(container_manager)
            execution_service = CodeExecutionService(container_manager)
            
            # Decrypt secrets if encrypted
            secrets = request.secrets
            if request.encrypted_secrets:
                try:
                    secrets = crypto_service.decrypt_secrets(request.encrypted_secrets)
                except Exception as e:
                    yield {
                        "event": "log",
                        "data": json.dumps({"type": "error", "message": str(e)})
                    }
                    yield {
                        "event": "done",
                        "data": json.dumps({"status": "error"})
                    }
                    return
            
            # Phase 1: Install dependencies
            if request.dependencies:
                install_success = False
                async for event in dependency_service.install_dependencies(request.dependencies):
                    yield event
                    # Check for status event to determine success
                    if event.get("event") == "status":
                        data = json.loads(event["data"])
                        if data.get("phase") == "install":
                            install_success = data.get("success", False)
                
                if not install_success:
                    yield {
                        "event": "done",
                        "data": json.dumps({"status": "error"})
                    }
                    return
            
            # Phase 2: Execute code
            async for event in execution_service.execute_code(
                request.code, 
                secrets, 
                network_enabled=request.enable_network
            ):
                yield event
            
            # Send completion event
            yield {
                "event": "done",
                "data": json.dumps({"status": "complete"})
            }
            
        except Exception as e:
            yield {
                "event": "log",
                "data": json.dumps({"type": "error", "message": f"Unexpected error: {str(e)}"})
            }
            yield {
                "event": "done",
                "data": json.dumps({"status": "error"})
            }
    
    return EventSourceResponse(event_generator())
