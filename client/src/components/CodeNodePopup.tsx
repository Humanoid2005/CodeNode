import React, { useState } from 'react';
import AceEditor from 'react-ace';
import 'ace-builds/src-noconflict/mode-python';
import 'ace-builds/src-noconflict/theme-monokai';
import 'ace-builds/src-noconflict/ext-language_tools';
import { executeCodeWithSSE } from '../services/api';
// import { encryptSecretsForFernet } from '../utils/encryption';
import './CodeNodePopup.css';

interface Secret {
  key: string;
  value: string;
}

interface LogMessage {
  type: string;
  message: string;
}

const DEFAULT_CODE = `# Welcome to CodeNode - Secure Python Executor
# 
# Features:
# - Docker containerized execution
# - Dependency management
# - Environment variables/secrets support
# - Real-time execution feedback
#
# Example: Using environment variables
import os

# Access secrets/environment variables
api_key = os.environ.get("API_KEY", "not_set")
print(f"API Key: {api_key}")

# Example with dependencies
# Add 'requests' to dependencies below, then run:
# import requests
# response = requests.get('https://api.github.com')
# print(f"GitHub API Status: {response.status_code}")

print("Hello from CodeNode!")
print("Your code runs in an isolated Docker container.")
`;

const CodeNodePopup: React.FC = () => {
  const [code, setCode] = useState<string>(DEFAULT_CODE);
  const [dependencies, setDependencies] = useState<string>('');
  const [secrets, setSecrets] = useState<Secret[]>([{ key: 'API_KEY', value: 'my-secret-key-123' }]);
  const [logs, setLogs] = useState<LogMessage[]>([]);
  const [isExecuting, setIsExecuting] = useState<boolean>(false);
  // const [encryptionKey, setEncryptionKey] = useState<string>('');
  const [showSecrets, setShowSecrets] = useState<boolean>(false);
  const [enableNetwork, setEnableNetwork] = useState<boolean>(false);

  // Skip encryption for now - commented out
  // useEffect(() => {
  //   // Fetch encryption key on component mount
  //   const fetchKey = async () => {
  //     try {
  //       const key = await getEncryptionKey();
  //       setEncryptionKey(key);
  //     } catch (error) {
  //       addLog({ type: 'error', message: 'Failed to fetch encryption key' });
  //     }
  //   };
  //   fetchKey();
  // }, []);

  const addLog = (log: LogMessage) => {
    setLogs(prev => [...prev, log]);
  };

  const clearLogs = () => {
    setLogs([]);
  };

  const addSecret = () => {
    setSecrets([...secrets, { key: '', value: '' }]);
  };

  const updateSecret = (index: number, field: 'key' | 'value', value: string) => {
    const newSecrets = [...secrets];
    newSecrets[index][field] = value;
    setSecrets(newSecrets);
  };

  const removeSecret = (index: number) => {
    setSecrets(secrets.filter((_, i) => i !== index));
  };

  const handleExecute = async () => {
    if (!code.trim()) {
      addLog({ type: 'error', message: 'Code cannot be empty' });
      return;
    }

    setIsExecuting(true);
    clearLogs();

    // Parse dependencies
    const depsList = dependencies
      .split(',')
      .map(d => d.trim())
      .filter(d => d.length > 0);

    // Convert secrets array to object and filter out empty keys
    const secretsObj: Record<string, string> = {};
    secrets.forEach(secret => {
      if (secret.key.trim()) {
        secretsObj[secret.key.trim()] = secret.value;
      }
    });

    // Skip encryption for now - send secrets as plaintext
    // In production, use HTTPS to secure the connection
    // let encryptedSecrets = '';
    // if (Object.keys(secretsObj).length > 0 && encryptionKey) {
    //   try {
    //     encryptedSecrets = encryptSecretsForFernet(secretsObj, encryptionKey);
    //   } catch (error) {
    //     addLog({ type: 'error', message: 'Failed to encrypt secrets' });
    //     setIsExecuting(false);
    //     return;
    //   }
    // }

    try {
      await executeCodeWithSSE(
        {
          code,
          dependencies: depsList,
          secrets: secretsObj,
          // encrypted_secrets: encryptedSecrets,
          language: 'python',
          enable_network: enableNetwork,
        },
        {
          onLog: addLog,
          onComplete: () => {
            setIsExecuting(false);
            addLog({ type: 'success', message: '✓ Execution completed' });
          },
          onError: (error) => {
            setIsExecuting(false);
            addLog({ type: 'error', message: `✗ ${error}` });
          },
        }
      );
    } catch (error) {
      setIsExecuting(false);
      addLog({ 
        type: 'error', 
        message: error instanceof Error ? error.message : 'Unknown error' 
      });
    }
  };

  const handleReset = () => {
    setCode(DEFAULT_CODE);
    setDependencies('');
    setSecrets([{ key: 'API_KEY', value: 'my-secret-key-123' }]);
    clearLogs();
  };

  const getLogClassName = (type: string) => {
    switch (type) {
      case 'error':
        return 'log-error';
      case 'success':
        return 'log-success';
      case 'info':
        return 'log-info';
      case 'install':
        return 'log-install';
      case 'stdout':
        return 'log-stdout';
      default:
        return 'log-default';
    }
  };

  return (
    <div className="codenode-container">
      <div className="codenode-header">
        <div className="header-left">
          <h1 className="header-title">👨‍💻 CodeNode</h1>
          <span className="header-subtitle">Secure Containerized Code Execution</span>
        </div>
        <div className="header-actions">
          <button 
            className="btn btn-secondary" 
            onClick={handleReset}
            disabled={isExecuting}
          >
            Reset
          </button>
          <button 
            className="btn btn-primary" 
            onClick={handleExecute}
            disabled={isExecuting}
          >
            {isExecuting ? '⏳ Running...' : '▶ Execute'}
          </button>
        </div>
      </div>

      <div className="codenode-body">
        {/* Left Panel - Code Editor */}
        <div className="editor-section">
          <div className="section-header">
            <span className="section-title">Code Editor</span>
            <span className="language-tag">Python 3.11</span>
          </div>
          <div className="editor-wrapper">
            <AceEditor
              mode="python"
              theme="monokai"
              value={code}
              onChange={setCode}
              name="code-editor"
              width="100%"
              height="100%"
              fontSize={14}
              showPrintMargin={false}
              showGutter={true}
              highlightActiveLine={true}
              setOptions={{
                enableBasicAutocompletion: true,
                enableLiveAutocompletion: true,
                enableSnippets: true,
                showLineNumbers: true,
                tabSize: 4,
                useWorker: false,
              }}
            />
          </div>

          {/* Dependencies Section */}
          <div className="config-section">
            <div className="config-header">
              <span className="config-title">📦 Dependencies</span>
              <span className="config-hint">Comma-separated (e.g., requests, pandas, numpy)</span>
            </div>
            <input
              type="text"
              className="config-input"
              placeholder="requests, pandas, numpy"
              value={dependencies}
              onChange={(e) => setDependencies(e.target.value)}
              disabled={isExecuting}
            />
          </div>

          {/* Network Access Section */}
          <div className="config-section">
            <label className="network-checkbox">
              <input
                type="checkbox"
                checked={enableNetwork}
                onChange={(e) => setEnableNetwork(e.target.checked)}
                disabled={isExecuting}
              />
              <span className="config-title">🌐 Enable Network Access</span>
              <span className="config-hint" style={{ marginLeft: '10px' }}>
                (Required for HTTP requests, API calls, etc.)
              </span>
            </label>
          </div>

          {/* Secrets Section */}
          <div className="config-section">
            <div className="config-header">
              <span className="config-title">🔐 Environment Variables / Secrets</span>
              <button 
                className="btn-toggle-secrets"
                onClick={() => setShowSecrets(!showSecrets)}
              >
                {showSecrets ? '👁️ Hide' : '👁️‍🗨️ Show'} Values
              </button>
            </div>
            <div className="secrets-list">
              {secrets.map((secret, index) => (
                <div key={index} className="secret-item">
                  <input
                    type="text"
                    className="secret-key"
                    placeholder="KEY"
                    value={secret.key}
                    onChange={(e) => updateSecret(index, 'key', e.target.value)}
                    disabled={isExecuting}
                  />
                  <input
                    type={showSecrets ? 'text' : 'password'}
                    className="secret-value"
                    placeholder="value"
                    value={secret.value}
                    onChange={(e) => updateSecret(index, 'value', e.target.value)}
                    disabled={isExecuting}
                  />
                  <button
                    className="btn-remove"
                    onClick={() => removeSecret(index)}
                    disabled={isExecuting}
                    title="Remove"
                  >
                    ✕
                  </button>
                </div>
              ))}
              <button 
                className="btn-add-secret"
                onClick={addSecret}
                disabled={isExecuting}
              >
                + Add Secret
              </button>
            </div>
          </div>
        </div>

        {/* Right Panel - Output Console */}
        <div className="output-section">
          <div className="section-header">
            <span className="section-title">Console Output</span>
            {logs.length > 0 && (
              <button 
                className="btn-clear-logs"
                onClick={clearLogs}
                disabled={isExecuting}
              >
                Clear
              </button>
            )}
          </div>
          <div className="console-wrapper">
            {logs.length === 0 ? (
              <div className="console-empty">
                <p>📋 Ready to execute code</p>
                <p className="console-hint">Click "Execute" to run your Python code</p>
              </div>
            ) : (
              <div className="console-logs">
                {logs.map((log, index) => (
                  <div key={index} className={`log-entry ${getLogClassName(log.type)}`}>
                    <span className="log-icon">
                      {log.type === 'error' && '❌'}
                      {log.type === 'success' && '✅'}
                      {log.type === 'info' && 'ℹ️'}
                      {log.type === 'install' && '📦'}
                      {log.type === 'stdout' && '▶️'}
                    </span>
                    <span className="log-message">{log.message}</span>
                  </div>
                ))}
              </div>
            )}
            {isExecuting && (
              <div className="executing-indicator">
                <div className="spinner"></div>
                <span>Executing...</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default CodeNodePopup;
