"""
Judge0 Service using REST API
Handles code execution using self-hosted Judge0 REST API
"""
import os
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

    LANGUAGE_IDS = {
        "c": 50,
        "cpp": 54,
        "csharp": 51,
        "javascript": 63,
        "java": 62,
        "python": 71,
        "python_ml": 71,
        "ruby": 72,
        "go": 60,
        "rust": 73,
        "php": 68,
        "typescript": 74,
        "bash": 46,
    }

    def __init__(self):
        self.judge0_url = os.getenv("JUDGE0_URL", "http://localhost:2358")

        self.language_map = {
            "python": 71,
            "javascript": 63,
            "cpp": 54,
            "c": 50,
            "java": 62,
            "csharp": 51,
            "ruby": 72,
            "go": 60,
            "rust": 73,
            "php": 68,
            "typescript": 74,
            "bash": 46,
            "python_ml": 71,
        }

    def _get_language_id(self, language_name: str) -> Optional[int]:
        return self.language_map.get(language_name.lower())

    def _normalize_requirements(self, requirements: Optional[object]) -> List[str]:
        if not requirements:
            return []

        if isinstance(requirements, list):
            return [str(item).strip() for item in requirements if str(item).strip()]

        if isinstance(requirements, str):
            text = requirements.replace(",", "\n")
            return [line.strip() for line in text.splitlines() if line.strip()]

        return []

    def _inject_python_requirements(self, source_code: str, requirements: List[str]) -> str:
        """
        Prepend Python code that installs approved packages at runtime.
        The whitelist validation is performed before this function is called.
        """
        if not requirements:
            return source_code

        req_json = json.dumps(requirements)

        wrapper = f'''# === Dependency Installer (auto-generated) ===
import subprocess
import sys

_REQUIRED_PACKAGES = {req_json}

if _REQUIRED_PACKAGES:
    print("Installing approved dependencies:", ", ".join(_REQUIRED_PACKAGES), file=sys.stderr)
    subprocess.check_call([
        sys.executable, "-m", "pip", "install",
        "--user",
        "--no-input",
        "--disable-pip-version-check",
        * _REQUIRED_PACKAGES
    ])
# === End Dependency Installer ===

'''
        return wrapper + source_code

    def _inject_network_config(self, source_code: str, language: str, network_config: 'NetworkConfig') -> str:
        if not network_config:
            return source_code
        if not network_config.enabled:
            return source_code
        if not network_config.restricted:
            return source_code

        allowed_hosts = network_config.allowed_hosts or []
        allowed_hosts_str = json.dumps(allowed_hosts)
        language = language.lower()

        if language in ['python', 'python_ml']:
            network_patch = f'''# === Network Filter (auto-generated) ===
_ALLOWED_HOSTS = {allowed_hosts_str}

def _check_url_allowed(url):
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        host = parsed.netloc.split(':')[0]
        if host in _ALLOWED_HOSTS:
            return True
        for allowed in _ALLOWED_HOSTS:
            if host.endswith('.' + allowed):
                return True
        raise ConnectionError(f"Network request to '{{host}}' blocked. Allowed hosts: {{_ALLOWED_HOSTS}}")
    except ConnectionError:
        raise
    except Exception:
        raise ConnectionError(f"Invalid URL: {{url}}")

try:
    import requests as _req
    _orig_request = _req.Session.request
    def _filtered_request(self, method, url, **kwargs):
        _check_url_allowed(url)
        return _orig_request(self, method, url, **kwargs)
    _req.Session.request = _filtered_request
except ImportError:
    pass

try:
    import urllib.request as _urllib
    _orig_urlopen = _urllib.urlopen
    def _filtered_urlopen(url, *args, **kwargs):
        url_str = url.full_url if hasattr(url, 'full_url') else str(url)
        _check_url_allowed(url_str)
        return _orig_urlopen(url, *args, **kwargs)
    _urllib.urlopen = _filtered_urlopen
except Exception:
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

if (typeof fetch !== 'undefined') {{
    const _origFetch = fetch;
    global.fetch = (url, opts) => {{ _checkUrlAllowed(url.toString()); return _origFetch(url, opts); }};
}}

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

        return source_code

    def _inject_env_vars(self, source_code: str, language: str, env_vars: Optional[Dict[str, str]]) -> str:
        if not env_vars:
            return source_code

        language = language.lower()

        if language in ['python', 'python_ml']:
            env_setup_lines = []
            for key, value in env_vars.items():
                escaped_value = value.replace("\\", "\\\\").replace('"', '\\"')
                env_setup_lines.append(f'os.environ["{key}"] = "{escaped_value}"')

            if not env_setup_lines:
                return source_code

            import_stmt = "import os"
            env_setup = '\n'.join(env_setup_lines)
            return import_stmt + '\n' + env_setup + '\n' + source_code

        elif language == 'javascript':
            env_setup = ""
            for key, value in env_vars.items():
                escaped_value = value.replace("\\", "\\\\").replace('"', '\\"')
                env_setup += f'process.env.{key} = "{escaped_value}";\n'
            return env_setup + "\n" + source_code

        elif language == 'bash':
            env_setup = ""
            for key, value in env_vars.items():
                escaped_value = (
                    value.replace("\\", "\\\\")
                    .replace('"', '\\"')
                    .replace('$', '\\$')
                    .replace('`', '\\`')
                )
                env_setup += f'export {key}="{escaped_value}"\n'
            return env_setup + source_code

        elif language == 'ruby':
            env_setup = ""
            for key, value in env_vars.items():
                escaped_value = value.replace("\\", "\\\\").replace('"', '\\"')
                env_setup += f'ENV["{key}"] = "{escaped_value}"\n'
            return env_setup + "\n" + source_code

        elif language == 'go':
            import_stmt = 'package main\n\nimport (\n\t"os"\n)\n\nfunc init() {\n'
            env_setup = ""
            for key, value in env_vars.items():
                escaped_value = value.replace("\\", "\\\\").replace('"', '\\"')
                env_setup += f'\tos.Setenv("{key}", "{escaped_value}")\n'
            env_setup += "}\n"

            if 'package main' not in source_code:
                return import_stmt + env_setup + "\n" + source_code
            return source_code.replace('package main', import_stmt) + env_setup

        elif language in ['java']:
            env_setup = ""
            for key, value in env_vars.items():
                escaped_value = value.replace("\\", "\\\\").replace('"', '\\"')
                env_setup += f'System.setProperty("{key}", "{escaped_value}");\n'
            return env_setup + "\n" + source_code

        return source_code

    def execute_code(
        self,
        source_code: str,
        language: str,
        stdin: str = "",
        requirements: Optional[object] = None,
        env_vars: Optional[Dict[str, str]] = None,
        network_config: Optional[NetworkConfig] = None,
    ) -> Dict:
        lang_id = self._get_language_id(language)
        if lang_id is None:
            raise ValueError(f"Unsupported language: {language}")

        code_to_execute = source_code
        normalized_requirements = self._normalize_requirements(requirements)

        if language.lower() in ["python", "python_ml"] and normalized_requirements:
            code_to_execute = self._inject_python_requirements(code_to_execute, normalized_requirements)

        if network_config and network_config.enabled:
            code_to_execute = self._inject_network_config(code_to_execute, language, network_config)

        code_to_execute = self._inject_env_vars(code_to_execute, language, env_vars)

        payload = {
            "source_code": code_to_execute,
            "language_id": lang_id,
            "enable_network": network_config.enabled if network_config else False,
        }

        if stdin:
            payload["stdin"] = stdin

        try:
            submit_url = f"{self.judge0_url}/submissions"
            response = requests.post(submit_url, json=payload, timeout=30)

            if response.status_code != 201:
                error_detail = response.text
                raise RuntimeError(f"Judge0 submission failed (status {response.status_code}): {error_detail}")

            result = response.json()
            token = result.get("token")
            if not token:
                raise ValueError(f"No token received from Judge0. Response: {result}")

            max_attempts = 600
            attempt = 0

            while attempt < max_attempts:
                result_url = f"{self.judge0_url}/submissions/{token}"
                result_response = requests.get(result_url, timeout=30)

                if result_response.status_code != 200:
                    raise RuntimeError(
                        f"Failed to fetch submission result (status {result_response.status_code})"
                    )

                result = result_response.json()
                status_id = result.get("status", {}).get("id")

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
        requirements: Optional[object] = None,
        env_vars: Optional[Dict[str, str]] = None,
        network_config: Optional[NetworkConfig] = None,
    ) -> List[Dict]:
        lang_id = self._get_language_id(language)
        if lang_id is None:
            raise ValueError(f"Unsupported language: {language}")

        results = []

        for test_input, expected_output in test_cases:
            result = self.execute_code(
                source_code=source_code,
                language=language,
                stdin=test_input or "",
                requirements=requirements,
                env_vars=env_vars,
                network_config=network_config,
            )

            if expected_output is not None:
                actual = (result.get("stdout") or "").strip()
                expected = str(expected_output).strip()
                result["passed"] = (actual == expected)
                result["expected_output"] = expected_output

            results.append(result)

        return results

    def get_supported_languages(self) -> List[str]:
        return list(self.language_map.keys())

    def get_languages_info(self) -> List[Dict]:
        try:
            languages_url = f"{self.judge0_url}/languages"
            response = requests.get(languages_url, timeout=30)

            if response.status_code == 200:
                return response.json()

            return [
                {"name": name, "id": lang_id, "supported": True}
                for name, lang_id in self.language_map.items()
            ]
        except Exception:
            return [
                {"name": name, "id": lang_id, "supported": True}
                for name, lang_id in self.language_map.items()
            ]