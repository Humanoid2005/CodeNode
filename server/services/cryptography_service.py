"""Cryptography service for encrypting/decrypting secrets"""
import json
import base64
from cryptography.fernet import Fernet
from typing import Dict


class CryptographyService:
    """Handles encryption and decryption of secrets"""
    
    def __init__(self):
        # In production, load this from environment variable
        self.encryption_key = Fernet.generate_key()
        self.cipher_suite = Fernet(self.encryption_key)
    
    def get_encryption_key_base64(self) -> str:
        """Get encryption key encoded as base64 for client"""
        return base64.b64encode(self.encryption_key).decode('utf-8')
    
    def decrypt_secrets(self, encrypted_data: str) -> Dict[str, str]:
        """Decrypt secrets sent from client"""
        try:
            decrypted_bytes = self.cipher_suite.decrypt(encrypted_data.encode())
            return json.loads(decrypted_bytes.decode())
        except Exception as e:
            raise ValueError(f"Failed to decrypt secrets: {str(e)}")
    
    def encrypt_secrets(self, secrets: Dict[str, str]) -> str:
        """Encrypt secrets (for testing purposes)"""
        try:
            json_str = json.dumps(secrets)
            encrypted_bytes = self.cipher_suite.encrypt(json_str.encode())
            return encrypted_bytes.decode()
        except Exception as e:
            raise ValueError(f"Failed to encrypt secrets: {str(e)}")
