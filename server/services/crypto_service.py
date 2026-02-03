"""
Cryptography Service for secure secret handling
Uses AES-256-GCM for encryption/decryption
"""
import os
import base64
import json
import secrets
from typing import Dict, Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class CryptoService:
    """Service for encrypting and decrypting secrets"""
    
    # Key length for AES-256
    KEY_LENGTH = 32  # 256 bits
    NONCE_LENGTH = 12  # 96 bits for GCM
    
    def __init__(self):
        """Initialize crypto service with a secret key"""
        # Try to load key from environment, or generate a new one
        key_b64 = os.getenv("ENCRYPTION_KEY")
        
        if key_b64:
            self._key = base64.b64decode(key_b64)
        else:
            # Generate a new random key for this session
            self._key = secrets.token_bytes(self.KEY_LENGTH)
            # Log warning in development
            print("WARNING: Using session-generated encryption key. "
                  "Set ENCRYPTION_KEY env var for persistence.")
        
        self._aesgcm = AESGCM(self._key)
    
    def get_public_key_info(self) -> Dict[str, str]:
        """
        Get the encryption key info for the frontend.
        Returns the key encoded in base64.
        
        Note: In production with untrusted networks, use asymmetric encryption
        or a proper key exchange protocol.
        """
        return {
            "key": base64.b64encode(self._key).decode('utf-8'),
            "algorithm": "AES-256-GCM",
            "nonce_length": self.NONCE_LENGTH
        }
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a string using AES-256-GCM.
        
        Args:
            plaintext: The string to encrypt
            
        Returns:
            Base64 encoded string containing nonce + ciphertext + tag
        """
        # Generate a random nonce
        nonce = secrets.token_bytes(self.NONCE_LENGTH)
        
        # Encrypt the plaintext
        plaintext_bytes = plaintext.encode('utf-8')
        ciphertext = self._aesgcm.encrypt(nonce, plaintext_bytes, None)
        
        # Combine nonce + ciphertext (tag is appended by AESGCM)
        combined = nonce + ciphertext
        
        return base64.b64encode(combined).decode('utf-8')
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt a string that was encrypted with AES-256-GCM.
        
        Args:
            encrypted_data: Base64 encoded string containing nonce + ciphertext + tag
            
        Returns:
            Decrypted plaintext string
            
        Raises:
            ValueError: If decryption fails (invalid data or tampered)
        """
        try:
            # Decode the base64 data
            combined = base64.b64decode(encrypted_data)
            
            # Extract nonce and ciphertext
            nonce = combined[:self.NONCE_LENGTH]
            ciphertext = combined[self.NONCE_LENGTH:]
            
            # Decrypt
            plaintext_bytes = self._aesgcm.decrypt(nonce, ciphertext, None)
            
            return plaintext_bytes.decode('utf-8')
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")
    
    def encrypt_secrets(self, secrets: Dict[str, str]) -> str:
        """
        Encrypt a dictionary of secrets.
        
        Args:
            secrets: Dictionary of key-value pairs to encrypt
            
        Returns:
            Base64 encoded encrypted JSON string
        """
        json_str = json.dumps(secrets)
        return self.encrypt(json_str)
    
    def decrypt_secrets(self, encrypted_secrets: str) -> Dict[str, str]:
        """
        Decrypt an encrypted secrets string back to a dictionary.
        
        Args:
            encrypted_secrets: Base64 encoded encrypted JSON string
            
        Returns:
            Dictionary of decrypted secrets
            
        Raises:
            ValueError: If decryption fails or JSON is invalid
        """
        try:
            json_str = self.decrypt(encrypted_secrets)
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid secrets format after decryption: {str(e)}")


# Singleton instance
_crypto_service: Optional[CryptoService] = None


def get_crypto_service() -> CryptoService:
    """Get the singleton crypto service instance"""
    global _crypto_service
    if _crypto_service is None:
        _crypto_service = CryptoService()
    return _crypto_service
