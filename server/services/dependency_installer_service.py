"""Dependency installer service"""
import json
import sys
from pathlib import Path
from typing import List, AsyncGenerator, Dict
import asyncio

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from docker.models.containers import Container
from docker_manager.container import ContainerManager


class DependencyInstallerService:
    """Handles installation of Python dependencies in Docker containers"""
    
    def __init__(self, container_manager: ContainerManager):
        self.container_manager = container_manager
    
    async def install_dependencies(
        self, 
        dependencies: List[str]
    ) -> AsyncGenerator[Dict, None]:
        """Install dependencies and stream progress"""
        
        if not dependencies:
            yield {
                "event": "status",
                "data": json.dumps({"phase": "install", "success": True})
            }
            return
        
        try:
            # Ensure image and volume exist
            if not self.container_manager.ensure_image_exists():
                yield {
                    "event": "log",
                    "data": json.dumps({
                        "type": "error",
                        "message": "Failed to ensure Python image exists"
                    })
                }
                await asyncio.sleep(0)  # Yield control for SSE streaming
                yield {
                    "event": "status",
                    "data": json.dumps({"phase": "install", "success": False})
                }
                return
            
            yield {
                "event": "log",
                "data": json.dumps({
                    "type": "info",
                    "message": "Pulling Python Docker image (first time only)..."
                })
            }
            await asyncio.sleep(0)  # Yield control for SSE streaming
            
            if not self.container_manager.ensure_volume_exists():
                yield {
                    "event": "log",
                    "data": json.dumps({
                        "type": "error",
                        "message": "Failed to create library volume"
                    })
                }
                await asyncio.sleep(0)
                yield {
                    "event": "status",
                    "data": json.dumps({"phase": "install", "success": False})
                }
                return
            
            yield {
                "event": "log",
                "data": json.dumps({
                    "type": "info",
                    "message": f"Installing dependencies: {', '.join(dependencies)}"
                })
            }
            await asyncio.sleep(0)  # Yield control for SSE streaming
            
            # Create and run installation container
            container = self.container_manager.create_install_container(dependencies)
            
            if not container:
                yield {
                    "event": "log",
                    "data": json.dumps({
                        "type": "error",
                        "message": "Failed to create installation container"
                    })
                }
                yield {
                    "event": "status",
                    "data": json.dumps({"phase": "install", "success": False})
                }
                return
            
            # Stream installation logs
            for log_line in self.container_manager.stream_container_logs(container):
                if log_line:
                    yield {
                        "event": "log",
                        "data": json.dumps({"type": "install", "message": log_line})
                    }
                    await asyncio.sleep(0)  # Yield control for SSE streaming
            
            # Wait for container to finish
            exit_code = self.container_manager.wait_for_container(container, timeout=300)
            
            # Cleanup
            self.container_manager.cleanup_container(container)
            
            if exit_code != 0:
                yield {
                    "event": "log",
                    "data": json.dumps({
                        "type": "error",
                        "message": "Dependency installation failed"
                    })
                }
                yield {
                    "event": "status",
                    "data": json.dumps({"phase": "install", "success": False})
                }
            else:
                yield {
                    "event": "log",
                    "data": json.dumps({
                        "type": "success",
                        "message": "Dependencies installed successfully"
                    })
                }
                yield {
                    "event": "status",
                    "data": json.dumps({"phase": "install", "success": True})
                }
            
        except Exception as e:
            yield {
                "event": "log",
                "data": json.dumps({
                    "type": "error",
                    "message": f"Installation error: {str(e)}"
                })
            }
            yield {
                "event": "status",
                "data": json.dumps({"phase": "install", "success": False})
            }
