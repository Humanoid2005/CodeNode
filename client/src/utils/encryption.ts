/**
 * Encryption utilities for secure secret handling
 * Uses AES-256-GCM for encryption (compatible with backend Python implementation)
 */

export interface EncryptionKeyInfo {
  key: string;  // Base64 encoded AES-256 key
  algorithm: string;
  nonce_length: number;
}

/**
 * Encrypt secrets using AES-256-GCM
 * 
 * @param secrets - Dictionary of secret key-value pairs
 * @param keyInfo - Encryption key info from the backend
 * @returns Base64 encoded encrypted data (nonce + ciphertext + tag)
 */
export const encryptSecrets = async (
  secrets: Record<string, string>,
  keyInfo: EncryptionKeyInfo
): Promise<string> => {
  // Convert secrets to JSON string
  const jsonStr = JSON.stringify(secrets);
  const encoder = new TextEncoder();
  const plaintext = encoder.encode(jsonStr);
  
  // Decode the base64 key
  const keyBytes = Uint8Array.from(atob(keyInfo.key), c => c.charCodeAt(0));
  
  // Import the key for Web Crypto API
  const cryptoKey = await crypto.subtle.importKey(
    'raw',
    keyBytes,
    { name: 'AES-GCM' },
    false,
    ['encrypt']
  );
  
  // Generate a random nonce (12 bytes for GCM)
  const nonce = crypto.getRandomValues(new Uint8Array(keyInfo.nonce_length));
  
  // Encrypt the plaintext
  const ciphertext = await crypto.subtle.encrypt(
    {
      name: 'AES-GCM',
      iv: nonce,
    },
    cryptoKey,
    plaintext
  );
  
  // Combine nonce + ciphertext (ciphertext includes the auth tag)
  const combined = new Uint8Array(nonce.length + ciphertext.byteLength);
  combined.set(nonce, 0);
  combined.set(new Uint8Array(ciphertext), nonce.length);
  
  // Encode as base64
  return btoa(String.fromCharCode(...combined));
};

/**
 * Check if Web Crypto API is available
 */
export const isEncryptionSupported = (): boolean => {
  return typeof crypto !== 'undefined' && 
         typeof crypto.subtle !== 'undefined' &&
         typeof crypto.subtle.encrypt === 'function';
};
