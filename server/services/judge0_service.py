"""
Judge0 Service using REST API
Handles code execution using self-hosted Judge0 REST API
"""
import os
import base64
import time
import json
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class NetworkConfig:
    """Network configuration for code execution"""
    enabled: bool = True
    restricted: bool = False
    allowed_hosts: List[str] = None
    
    def __post_init__(self):
        if self.allowed_hosts is None:
            self.allowed_hosts = []
    
    def to_dict(self) -> Dict:
        return {
            "enabled": self.enabled,
            "restricted": self.restricted,
            "allowed_hosts": self.allowed_hosts,
        }

class Judge0Service:
    """Service for interacting with self-hosted Judge0 using REST API"""
    
    # Language ID mapping for Judge0 API (using active/non-archived IDs)
    LANGUAGE_IDS = {
        "c": 50,           # GCC 9.2.0
        "cpp": 54,         # GCC 9.2.0
        "csharp": 51,      # Mono 6.6.0.161
        "javascript": 63,  # Node.js 12.14.0
        "java": 62,        # OpenJDK 13.0.1
        "python": 71,      # Python 3.8.1
        "python_ml": 71,   # Python 3.8.1
        "ruby": 72,        # Ruby 2.7.0
        "go": 60,          # Go 1.13.5
        "rust": 73,        # Rust 1.40.0
        "php": 68,         # PHP 7.4.1
        "typescript": 74,  # TypeScript 3.7.4
        "bash": 46,        # Bash 5.0.0
    }
    
    def __init__(self):
        """Initialize Judge0 client with self-hosted instance"""
        self.judge0_url = os.getenv("JUDGE0_URL", "http://localhost:2358")
        
        # Language mapping for easier access (using active/non-archived IDs)
        self.language_map = {
            "python": 71,      # Python 3.8.1
            "javascript": 63,  # Node.js 12.14.0
            "cpp": 54,         # GCC 9.2.0
            "c": 50,           # GCC 9.2.0
            "java": 62,        # OpenJDK 13.0.1
            "csharp": 51,      # Mono 6.6.0.161
            "ruby": 72,        # Ruby 2.7.0
            "go": 60,          # Go 1.13.5
            "rust": 73,        # Rust 1.40.0
            "php": 68,         # PHP 7.4.1
            "typescript": 74,  # TypeScript 3.7.4
            "bash": 46,        # Bash 5.0.0
            "python_ml": 71,   # Python 3.8.1
        }
    
    def _get_language_id(self, language_name: str) -> Optional[int]:
        """Get Judge0 language ID from language name"""
        return self.language_map.get(language_name.lower())
    
    def _inject_network_config(self, source_code: str, language: str, network_config: 'NetworkConfig') -> str:
        """
        Inject code that blocks network requests not in allowlist.
        Uses monkey-patching to intercept requests before they're made.
        
        Args:
            source_code: Original user code
            language: Programming language
            network_config: Network configuration object
            
        Returns:
            Modified source code with network filtering
        """
        if not network_config:
            return source_code
        
        # If network is disabled entirely, don't inject anything
        # Judge0's enable_network=false will handle blocking
        if not network_config.enabled:
            return source_code
        
        # If not restricted, allow all - no injection needed
        if not network_config.restricted:
            return source_code
        
        # Network is enabled but restricted - inject allowlist checking
        allowed_hosts = network_config.allowed_hosts or []
        allowed_hosts_str = json.dumps(allowed_hosts)
        
        language = language.lower()
        
        if language in ['python', 'python_ml']:
            # Inject Python code to filter requests
            network_patch = f'''# === Network Filter (auto-generated) ===
_ALLOWED_HOSTS = {allowed_hosts_str}

def _check_url_allowed(url):
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        host = parsed.netloc.split(':')[0]  # Remove port
        if host in _ALLOWED_HOSTS:
            return True
        # Check if it's a subdomain of an allowed host
        for allowed in _ALLOWED_HOSTS:
            if host.endswith('.' + allowed):
                return True
        raise ConnectionError(f"Network request to '{{host}}' blocked. Allowed hosts: {{_ALLOWED_HOSTS}}")
    except ConnectionError:
        raise
    except:
        raise ConnectionError(f"Invalid URL: {{url}}")

# Patch requests library
try:
    import requests as _req
    _orig_request = _req.Session.request
    def _filtered_request(self, method, url, **kwargs):
        _check_url_allowed(url)
        return _orig_request(self, method, url, **kwargs)
    _req.Session.request = _filtered_request
except ImportError:
    pass

# Patch urllib
try:
    import urllib.request as _urllib
    _orig_urlopen = _urllib.urlopen
    def _filtered_urlopen(url, *args, **kwargs):
        url_str = url.full_url if hasattr(url, 'full_url') else str(url)
        _check_url_allowed(url_str)
        return _orig_urlopen(url, *args, **kwargs)
    _urllib.urlopen = _filtered_urlopen
except:
    pass
# === End Network Filter ===

'''
            return network_patch + source_code
            
        elif language == 'javascript':
            allowed_hosts_js = json.dumps(allowed_hosts)
            network_patch = f'''// === Network Filter (auto-generated) ===
const _ALLOWED_HOSTS = {allowed_hosts_js};
function _checkUrlAllowed(url) {{
    try {{
        const parsed = new URL(url);
        const host = parsed.hostname;
        if (_ALLOWED_HOSTS.includes(host)) return true;
        for (const allowed of _ALLOWED_HOSTS) {{
            if (host.endsWith('.' + allowed)) return true;
        }}
        throw new Error(`Network request to '${{host}}' blocked. Allowed: ${{_ALLOWED_HOSTS}}`);
    }} catch (e) {{
        if (e.message.includes('blocked')) throw e;
        throw new Error(`Invalid URL: ${{url}}`);
    }}
}}

// Patch fetch
if (typeof fetch !== 'undefined') {{
    const _origFetch = fetch;
    global.fetch = (url, opts) => {{ _checkUrlAllowed(url.toString()); return _origFetch(url, opts); }};
}}

// Patch http/https
['http', 'https'].forEach(p => {{
    try {{
        const m = require(p);
        const _orig = m.request;
        m.request = (opts, cb) => {{
            const url = typeof opts === 'string' ? opts : `${{p}}://${{opts.hostname || opts.host}}`;
            _checkUrlAllowed(url);
            return _orig(opts, cb);
        }};
    }} catch(e) {{}}
}});
// === End Network Filter ===

'''
            return network_patch + source_code
        
        # For other languages, return as-is (no filtering)
        return source_code

    def _inject_env_vars(self, source_code: str, language: str, env_vars: Optional[Dict[str, str]]) -> str:
        """
        Inject environment variables into source code based on language
        
        Args:
            source_code: Original user code
            language: Programming language
            env_vars: Dictionary of environment variables
            
        Returns:
            Modified source code with environment variables set
        """
        if not env_vars:
            return source_code
            
        language = language.lower()
        
        if language in ['python', 'python_ml']:
            # Inject os.environ setup for Python
            # Always add import os and env setup at the very beginning
            # This ensures env vars are set before any user code runs
            
            # Build the env setup lines
            env_setup_lines = []
            for key, value in env_vars.items():
                # Escape quotes and backslashes in the value
                escaped_value = value.replace("\\", "\\\\").replace('"', '\\"')
                env_setup_lines.append(f'os.environ["{key}"] = "{escaped_value}"')
            
            if not env_setup_lines:
                return source_code
            
            # Always prepend import os and env vars at the top
            # This works even if user's code also imports os (duplicate import is harmless)
            import_stmt = "import os"
            env_setup = '\n'.join(env_setup_lines)
            return import_stmt + '\n' + env_setup + '\n' + source_code
            
        elif language == 'javascript':
            # Inject process.env setup for Node.js
            env_setup = ""
            for key, value in env_vars.items():
                # Escape quotes in the value
                escaped_value = value.replace("\\", "\\\\").replace('"', '\\"')
                env_setup += f'process.env.{key} = "{escaped_value}";\n'
            
            return env_setup + "\n" + source_code
            
        elif language == 'bash':
            # Inject export statements for Bash
            env_setup = ""
            for key, value in env_vars.items():
                # Escape special characters in the value
                escaped_value = value.replace("\\", "\\\\").replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
                env_setup += f'export {key}="{escaped_value}"\n'
            
            return env_setup + source_code
            
        elif language == 'ruby':
            # Inject ENV setup for Ruby
            env_setup = ""
            for key, value in env_vars.items():
                # Escape quotes in the value
                escaped_value = value.replace("\\", "\\\\").replace('"', '\\"')
                env_setup += f'ENV["{key}"] = "{escaped_value}"\n'
            
            return env_setup + "\n" + source_code
            
        elif language == 'go':
            # Inject os.Setenv setup for Go
            import_stmt = 'package main\n\nimport (\n\t"os"\n)\n\nfunc init() {\n'
            env_setup = ""
            for key, value in env_vars.items():
                # Escape quotes in the value
                escaped_value = value.replace("\\", "\\\\").replace('"', '\\"')
                env_setup += f'\tos.Setenv("{key}", "{escaped_value}")\n'
            env_setup += "}\n"
            
            # Only add import if code doesn't already have it
            if 'package main' not in source_code:
                return import_stmt + env_setup + "\n" + source_code
            return source_code.replace('package main', import_stmt) + env_setup
            
        elif language in ['c', 'cpp']:
            # For C/C++, environment variables can be read via getenv but not set easily
            # Return code as-is with a note
            return source_code
            
        elif language in ['java']:
            # Inject System.setenv equivalent for Java (setenv not available, use workaround)
            env_setup = ""
            # Java doesn't have a direct setenv, so we use reflection
            for key, value in env_vars.items():
                escaped_value = value.replace("\\", "\\\\").replace('"', '\\"')
                # Note: This requires special permissions in sandbox
                env_setup += f'System.setProperty("{key}", "{escaped_value}");  // Note: env var may not propagate to child processes\n'
            
            return env_setup + "\n" + source_code
            
        else:
            # For unsupported languages, return as-is
            return source_code
    
    
    def execute_code(
        self,
        source_code: str,
        language: str,
        stdin: str = "",
        requirements: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None,
        network_config: Optional[NetworkConfig] = None,
    ) -> Dict:
        """Execute code using self-hosted Judge0 API"""
        # Get language ID
        lang_id = self._get_language_id(language)
        if lang_id is None:
            raise ValueError(f"Unsupported language: {language}")
        
        code_to_execute = source_code
        
        # Handle network configuration - inject config directly into headers
        if network_config and network_config.enabled:
            code_to_execute = self._inject_network_config(code_to_execute, language, network_config)
        
        # Inject environment variables into the code
        code_to_execute = self._inject_env_vars(code_to_execute, language, env_vars)
        
        # Prepare request payload
        payload = {
            "source_code": code_to_execute,
            "language_id": lang_id,
            # Control network access via Judge0's enable_network flag
            # Default is false (set in judge0.conf), only enable if explicitly requested
            "enable_network": network_config.enabled if network_config else False,
        }
        if stdin:
            payload["stdin"] = stdin
        
        # Submit code to Judge0
        try:
            submit_url = f"{self.judge0_url}/submissions"
            
            response = requests.post(submit_url, json=payload)
            
            if response.status_code != 201:
                error_detail = response.text
                raise RuntimeError(f"Judge0 submission failed (status {response.status_code}): {error_detail}")
            
            result = response.json()
            token = result.get("token")
            if not token:
                raise ValueError(f"No token received from Judge0. Response: {result}")
            
            # Poll for result with longer timeout
            max_attempts = 600  # 60 seconds timeout (0.1s per attempt)
            attempt = 0
            
            while attempt < max_attempts:
                result_url = f"{self.judge0_url}/submissions/{token}"
                result_response = requests.get(result_url)
                
                if result_response.status_code != 200:
                    raise RuntimeError(f"Failed to fetch submission result (status {result_response.status_code})")
                
                result = result_response.json()
                status_id = result.get("status", {}).get("id")
                
                # Status 1 = In Queue, 2 = Processing
                if status_id not in [1, 2]:
                    break
                
                time.sleep(0.1)
                attempt += 1
            
            if not result:
                raise RuntimeError("Failed to get submission result")
            
            stdout = result.get("stdout") or ""
            stderr = result.get("stderr") or ""
            compile_output = result.get("compile_output") or ""
            
            return {
                "stdout": stdout,
                "stderr": stderr,
                "compile_output": compile_output,
                "message": result.get("message") or "",
                "time": result.get("time"),
                "memory": result.get("memory"),
                "status": result.get("status", {"id": 0, "description": "Unknown"}),
                "exit_code": result.get("exit_code"),
                "token": token,
            }
            
        except requests.RequestException as e:
            raise RuntimeError(f"Judge0 API connection error: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Judge0 execution error: {str(e)}")
    
    def execute_with_test_cases(
        self,
        source_code: str,
        language: str,
        test_cases: List[tuple],
        requirements: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None,
        network_config: Optional[NetworkConfig] = None,
    ) -> List[Dict]:
        """
        Execute code with multiple test cases
        
        Args:
            source_code: The source code to execute
            language: Programming language
            test_cases: List of (input, expected_output) tuples
            requirements: Dependencies (not supported in Judge0 CE)
            env_vars: Environment variables to set
            network_config: Network configuration for filtering
        
        Returns:
            List of execution results for each test case
        """
        lang_id = self._get_language_id(language)
        if lang_id is None:
            raise ValueError(f"Unsupported language: {language}")
        
        results = []
        
        # Execute each test case separately
        for test_input, expected_output in test_cases:
            result = self.execute_code(
                source_code=source_code,
                language=language,
                stdin=test_input or "",
                requirements=None,  # Not supported
                env_vars=env_vars,
                network_config=network_config,
            )
            results.append(result)
        
        return results
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported language names"""
        return list(self.language_map.keys())
    
    def get_languages_info(self) -> List[Dict]:
        """Get detailed information about all supported languages from Judge0"""
        try:
            languages_url = f"{self.judge0_url}/languages"
            response = requests.get(languages_url)
            
            if response.status_code == 200:
                return response.json()
            else:
                # Fallback to basic language info if API call fails
                return [
                    {"name": name, "id": lang_id, "supported": True}
                    for name, lang_id in self.language_map.items()
                ]
        except Exception as e:
            # Fallback to basic language info if API call fails
            return [
                {"name": name, "id": lang_id, "supported": True}
                for name, lang_id in self.language_map.items()
            ]