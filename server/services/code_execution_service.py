"""Code execution service"""
import json
import sys
from pathlib import Path
from typing import Dict, AsyncGenerator
import asyncio

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from docker_manager.container import ContainerManager


class CodeExecutionService:
    """Handles code execution in Docker containers"""
    
    def __init__(self, container_manager: ContainerManager):
        self.container_manager = container_manager
    
    async def execute_code(
        self,
        code: str,
        secrets: Dict[str, str],
        network_enabled: bool = False
    ) -> AsyncGenerator[Dict, None]:
        """Execute code in Docker container and stream output"""
        
        try:
            # Debug logging
            print(f"🔍 DEBUG: network_enabled = {network_enabled}")
            
            yield {
                "event": "log",
                "data": json.dumps({"type": "info", "message": f"Executing code (network: {'enabled' if network_enabled else 'disabled'})..."})
            }
            await asyncio.sleep(0)  # Yield control for SSE streaming
            
            # Prepare environment variables from secrets
            environment = {key: value for key, value in secrets.items()}
            
            # Create execution container
            container = self.container_manager.create_execution_container(
                code=code,
                environment=environment,
                network_disabled=not network_enabled  # Invert: if network_enabled=True, then network_disabled=False
            )
            
            if not container:
                yield {
                    "event": "log",
                    "data": json.dumps({
                        "type": "error",
                        "message": "Failed to create execution container"
                    })
                }
                await asyncio.sleep(0)
                return
            
            try:
                # Start container
                container.start()
                
                # Stream execution logs
                for log_line in self.container_manager.stream_container_logs(container):
                    if log_line:
                        yield {
                            "event": "log",
                            "data": json.dumps({"type": "stdout", "message": log_line})
                        }
                        await asyncio.sleep(0)  # Yield control for SSE streaming
                
                # Wait for container to finish
                exit_code = self.container_manager.wait_for_container(container, timeout=30)
                
                if exit_code != 0:
                    yield {
                        "event": "log",
                        "data": json.dumps({
                            "type": "error",
                            "message": f"Code execution failed with exit code {exit_code}"
                        })
                    }
                else:
                    yield {
                        "event": "log",
                        "data": json.dumps({
                            "type": "success",
                            "message": "Code executed successfully"
                        })
                    }
                
            finally:
                # Always cleanup container
                self.container_manager.cleanup_container(container)
                
        except Exception as e:
            yield {
                "event": "log",
                "data": json.dumps({
                    "type": "error",
                    "message": f"Execution error: {str(e)}"
                })
            }
