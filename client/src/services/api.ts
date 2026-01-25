import { fetchEventSource } from '@microsoft/fetch-event-source';

const API_BASE_URL = 'http://localhost:8000';

export interface CodeExecutionRequest {
  code: string;
  dependencies: string[];
  secrets: Record<string, string>;
  encrypted_secrets?: string;
  language: string;
  enable_network?: boolean;  // Optional: enable network access in container
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

export const getEncryptionKey = async (): Promise<string> => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/encryption-key`);
    const data = await response.json();
    return data.key;
  } catch (error) {
    throw new Error('Failed to get encryption key');
  }
};

export const executeCodeWithSSE = async (
  request: CodeExecutionRequest,
  callbacks: ExecutionCallbacks
): Promise<void> => {
  const abortController = new AbortController();

  try {
    await fetchEventSource(`${API_BASE_URL}/api/run`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
      signal: abortController.signal,
      
      async onopen(response) {
        if (response.ok) {
          return; // Success
        } else if (response.status >= 400 && response.status < 500 && response.status !== 429) {
          throw new Error(`HTTP error ${response.status}`);
        }
      },
      
      onmessage(event) {
        try {
          if (event.event === 'log') {
            const log: LogMessage = JSON.parse(event.data);
            callbacks.onLog(log);
          } else if (event.event === 'done') {
            const data = JSON.parse(event.data);
            if (data.status === 'complete') {
              callbacks.onComplete();
            } else if (data.status === 'error') {
              callbacks.onError('Execution failed');
            }
            abortController.abort();
          }
        } catch (error) {
          console.error('Error parsing SSE message:', error);
        }
      },
      
      onerror(error) {
        callbacks.onError(error instanceof Error ? error.message : 'Connection error');
        abortController.abort();
        throw error; // Stop retrying
      },
      
      openWhenHidden: true,
    });
  } catch (error) {
    if (error instanceof Error && error.name !== 'AbortError') {
      callbacks.onError(error.message);
    }
  }
  
  return Promise.resolve();
};
