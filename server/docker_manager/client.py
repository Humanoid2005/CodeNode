"""Docker client management"""
import os
import docker
from typing import Optional


class DockerClientManager:
    """Manages Docker client connections with fallback support"""
    
    _instance: Optional[docker.DockerClient] = None
    
    @classmethod
    def get_client(cls) -> Optional[docker.DockerClient]:
        """Get Docker client with fallback to Docker Desktop socket"""
        if cls._instance is not None:
            return cls._instance
        
        # Try multiple socket paths
        socket_paths = [f"{os.path.expanduser('~')}/.docker/desktop/docker.sock"]
        
        for socket_path in socket_paths:
            try:
                if socket_path is None:
                    client = docker.from_env()
                else:
                    # Use unix:// scheme for DockerClient
                    client = docker.DockerClient(base_url=f"unix://{socket_path}")
                
                # Test connection
                client.ping()
                print(f"✅ Docker connected via: {socket_path or 'default environment'}")
                cls._instance = client
                return client
            except Exception as e:
                print(f"❌ Failed to connect via {socket_path or 'default'}: {str(e)}")
                continue
        
        print("❌ All Docker connection attempts failed")
        return None
    
    @classmethod
    def close(cls):
        """Close the Docker client connection"""
        if cls._instance:
            cls._instance.close()
            cls._instance = None
