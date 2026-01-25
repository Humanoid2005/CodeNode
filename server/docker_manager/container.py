"""Docker container configuration and management"""
import tarfile
import io
from typing import Dict, Optional
import docker
from docker.models.containers import Container
from docker.errors import ImageNotFound


class ContainerManager:
    """Manages Docker containers for code execution"""
    
    PYTHON_IMAGE = "python:3.11-slim"
    LIBRARY_VOLUME = "codenode_library"
    
    def __init__(self, docker_client: docker.DockerClient):
        self.client = docker_client
    
    def ensure_image_exists(self) -> bool:
        """Ensure Python image is available, pull if needed"""
        try:
            self.client.images.get(self.PYTHON_IMAGE)
            print(f"✓ Image {self.PYTHON_IMAGE} already exists")
            return True
        except ImageNotFound:
            print(f"⬇ Pulling {self.PYTHON_IMAGE}... (this may take a minute)")
            try:
                self.client.images.pull(self.PYTHON_IMAGE)
                print(f"✓ Successfully pulled {self.PYTHON_IMAGE}")
                return True
            except Exception as e:
                print(f"✗ Failed to pull image: {e}")
                return False
        except Exception as e:
            print(f"Error checking image: {e}")
            return False
    
    def ensure_volume_exists(self) -> bool:
        """Ensure library volume exists, create if needed"""
        try:
            self.client.volumes.get(self.LIBRARY_VOLUME)
            return True
        except:
            try:
                self.client.volumes.create(self.LIBRARY_VOLUME)
                print(f"✅ Created volume: {self.LIBRARY_VOLUME}")
                return True
            except Exception as e:
                print(f"Error creating volume: {e}")
                return False
    
    def create_install_container(self, dependencies: list) -> Optional[Container]:
        """Create container for installing dependencies"""
        try:
            deps_str = " ".join(dependencies)
            install_cmd = f"pip install --target=/library {deps_str}"
            
            container = self.client.containers.run(
                self.PYTHON_IMAGE,
                command=["sh", "-c", install_cmd],
                volumes={self.LIBRARY_VOLUME: {'bind': '/library', 'mode': 'rw'}},
                user="0",  # Root for installation
                remove=False,
                detach=True
            )
            return container
        except Exception as e:
            print(f"Error creating install container: {e}")
            return None
    
    def create_execution_container(
        self, 
        code: str,
        environment: Dict[str, str],
        network_disabled: bool = True
    ) -> Optional[Container]:
        """Create container for code execution with code copied inside"""
        try:
            # Debug logging
            network_mode = 'none' if network_disabled else 'bridge'
            print(f"🔍 DEBUG: network_disabled={network_disabled}, network_mode={network_mode}")
            
            # Create container
            container = self.client.containers.create(
                self.PYTHON_IMAGE,
                command=["python", "/tmp/script.py"],
                volumes={self.LIBRARY_VOLUME: {'bind': '/library', 'mode': 'ro'}},
                environment={
                    **environment,
                    'PYTHONPATH': '/library'
                },
                user="1000:1000",  # Non-root user for security
                network_mode=network_mode,
                mem_limit='512m',
                cpu_period=100000,
                cpu_quota=50000  # 50% CPU
            )
            
            # Copy code into container using tar archive
            self._copy_code_to_container(container, code)
            
            return container
            
        except Exception as e:
            print(f"Error creating execution container: {e}")
            return None
    
    def _copy_code_to_container(self, container: Container, code: str):
        """Copy code into container using tar archive"""
        # Create tar archive with the code
        tar_stream = io.BytesIO()
        tar = tarfile.TarFile(fileobj=tar_stream, mode='w')
        
        # Add code file to tar
        code_data = code.encode('utf-8')
        tarinfo = tarfile.TarInfo(name='script.py')
        tarinfo.size = len(code_data)
        tarinfo.mode = 0o644
        tar.addfile(tarinfo, io.BytesIO(code_data))
        tar.close()
        
        # Put archive into container at /tmp
        tar_stream.seek(0)
        container.put_archive('/tmp', tar_stream.read())
    
    def stream_container_logs(self, container: Container, follow: bool = True):
        """Stream logs from container"""
        try:
            for log_line in container.logs(stream=True, follow=follow):
                yield log_line.decode('utf-8').strip()
        except Exception as e:
            print(f"Error streaming logs: {e}")
            yield f"Error: {str(e)}"
    
    def wait_for_container(self, container: Container, timeout: int = 30) -> int:
        """Wait for container to finish and return exit code"""
        try:
            result = container.wait(timeout=timeout)
            return result['StatusCode']
        except Exception as e:
            print(f"Container timeout or error: {e}")
            try:
                container.kill()
            except:
                pass
            return -1
    
    def cleanup_container(self, container: Container):
        """Remove container"""
        try:
            container.remove(force=True)
        except Exception as e:
            print(f"Error removing container: {e}")
