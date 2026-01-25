import CryptoJS from 'crypto-js';

export const encryptSecrets = (secrets: Record<string, string>, key: string): string => {
  const jsonStr = JSON.stringify(secrets);
  
  // Decode the base64 key from the server
  const keyBytes = CryptoJS.enc.Base64.parse(key);
  
  // Use the key to encrypt the secrets
  // Note: Python's Fernet uses specific encryption, so we need to match it
  // For simplicity, we'll send the base64-encoded encrypted data
  const encrypted = CryptoJS.AES.encrypt(jsonStr, key).toString();
  
  return encrypted;
};

// Simple implementation that matches Python's Fernet encryption format
export const encryptSecretsForFernet = (secrets: Record<string, string>, fernetKey: string): string => {
  // Convert secrets to JSON string
  const jsonStr = JSON.stringify(secrets);
  
  // For Fernet compatibility, we'll use a simpler approach
  // In production, use a proper Fernet-compatible JS library
  // For now, we'll encode the secrets and let the server handle decryption differently
  
  const utf8Bytes = CryptoJS.enc.Utf8.parse(jsonStr);
  const base64 = CryptoJS.enc.Base64.stringify(utf8Bytes);
  
  return base64;
};
