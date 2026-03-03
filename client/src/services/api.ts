const API_BASE_URL = 'http://localhost:8000';

import { encryptSecrets, isEncryptionSupported, EncryptionKeyInfo } from '../utils/encryption';

// Cache the encryption key to avoid fetching it on every request
let cachedKeyInfo: EncryptionKeyInfo | null = null;

export interface NetworkConfig {
  enabled: boolean;  // Enable/disable network access entirely
  restricted: boolean;  // If true, only allow hosts in allowed_hosts
  allowed_hosts: string[];  // List of allowed domains/IPs
}

export interface CodeExecutionRequest {
  code: string;
  dependencies: string[];
  secrets: Record<string, string>;
  encrypted_secrets?: string;
  language: string;
  enable_network?: boolean;  // Deprecated, use network_config
  network_config?: NetworkConfig;  // Network filtering configuration
}

export interface LogMessage {
  type: 'info' | 'error' | 'success' | 'stdout' | 'install';
  message: string;
}

export interface ExecutionCallbacks {
  onLog: (log: LogMessage) => void;
  onComplete: () => void;
  onError: (error: string) => void;
}

export interface ExecutionResult {
  stdout: string;
  stderr: string;
  compile_output: string;
  message: string;
  time: string;
  memory: number;
  status: {
    id: number;
    description: string;
  };
  exit_code: number | null;
  token: string;
}

export const getEncryptionKey = async (): Promise<EncryptionKeyInfo> => {
  // Return cached key if available
  if (cachedKeyInfo) {
    return cachedKeyInfo;
  }
  
  try {
    const response = await fetch(`${API_BASE_URL}/api/encryption-key`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    cachedKeyInfo = data as EncryptionKeyInfo;
    return cachedKeyInfo;
  } catch (error) {
    throw new Error('Failed to get encryption key');
  }
};

/**
 * Clear the cached encryption key (useful if the server restarts)
 */
export const clearEncryptionKeyCache = (): void => {
  cachedKeyInfo = null;
};

export const executeCodeWithSSE = async (
  request: CodeExecutionRequest,
  callbacks: ExecutionCallbacks
): Promise<void> => {
  try {
    callbacks.onLog({ type: 'info', message: 'Submitting code to execution engine...' });
    
    // Prepare the request payload
    let payload: Record<string, unknown> = {
      code: request.code,
      dependencies: request.dependencies,
      language: request.language,
      enable_network: request.enable_network,
    };
    
    // Add network_config if provided
    if (request.network_config) {
      payload.network_config = request.network_config;
    }
    
    // Encrypt secrets if there are any
    const hasSecrets = request.secrets && Object.keys(request.secrets).some(k => request.secrets[k]);
    
    if (hasSecrets && isEncryptionSupported()) {
      try {
        const keyInfo = await getEncryptionKey();
        const encryptedSecrets = await encryptSecrets(request.secrets, keyInfo);
        payload.encrypted_secrets = encryptedSecrets;
        // Don't send unencrypted secrets
        payload.secrets = {};
      } catch (encryptError) {
        console.warn('Failed to encrypt secrets, falling back to unencrypted:', encryptError);
        // Fallback to unencrypted if encryption fails
        payload.secrets = request.secrets;
      }
    } else {
      // No encryption support or no secrets
      payload.secrets = request.secrets || {};
    }
    
    const response = await fetch(`${API_BASE_URL}/api/run`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(errorData.detail || `HTTP error ${response.status}`);
    }

    const result: ExecutionResult = await response.json();
    
    // Log stdout if present
    if (result.stdout) {
      callbacks.onLog({ type: 'stdout', message: result.stdout });
    }
    
    // Log stderr if present
    if (result.stderr) {
      callbacks.onLog({ type: 'error', message: result.stderr });
    }
    
    // Log compile output if present
    if (result.compile_output) {
      callbacks.onLog({ type: 'info', message: `Compile output: ${result.compile_output}` });
    }
    
    // Log execution info
    if (result.time) {
      callbacks.onLog({ type: 'info', message: `Execution time: ${result.time}s` });
    }
    
    // Check status
    if (result.status.id === 3) {
      // Accepted - successful execution
      callbacks.onComplete();
    } else if (result.status.id >= 4 && result.status.id <= 12) {
      // Error statuses (Wrong Answer, Time Limit Exceeded, etc.)
      callbacks.onError(`Execution status: ${result.status.description}`);
    } else if (result.status.id === 13) {
      // Internal Error
      callbacks.onError(result.message || 'Internal execution error');
    } else {
      callbacks.onComplete();
    }
    
  } catch (error) {
    callbacks.onError(error instanceof Error ? error.message : 'Connection error');
  }
};
