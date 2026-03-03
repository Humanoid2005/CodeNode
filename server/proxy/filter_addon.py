"""
mitmproxy addon for filtering network requests based on allowlist.
This addon intercepts HTTP/HTTPS requests and blocks those not in the allowlist.
Allowlist is passed via X-Network-Config header (no external storage needed).
"""
import json
from mitmproxy import http

# Internal/private IP prefixes to always block
BLOCKED_INTERNAL_PREFIXES = [
    '127.',
    '10.',
    '172.16.', '172.17.', '172.18.', '172.19.',
    '172.20.', '172.21.', '172.22.', '172.23.',
    '172.24.', '172.25.', '172.26.', '172.27.',
    '172.28.', '172.29.', '172.30.', '172.31.',
    '192.168.',
    '169.254.',  # Link-local
    '0.',        # Invalid
]

BLOCKED_INTERNAL_HOSTS = [
    'localhost',
    'host.docker.internal',
]


def is_internal_address(host: str) -> bool:
    """Check if the host is an internal/private address"""
    host_lower = host.lower()
    
    # Check exact matches
    if host_lower in BLOCKED_INTERNAL_HOSTS:
        return True
    
    # Check IP prefixes
    for prefix in BLOCKED_INTERNAL_PREFIXES:
        if host.startswith(prefix):
            return True
    
    return False


class NetworkFilter:
    """mitmproxy addon that filters requests based on allowlist in headers"""
    
    def _make_blocked_response(self, message: str, details: dict = None) -> http.Response:
        """Create a blocked response with JSON body"""
        body = {
            "error": "NETWORK_BLOCKED",
            "message": message,
        }
        if details:
            body.update(details)
        
        return http.Response.make(
            403,
            json.dumps(body, indent=2),
            {"Content-Type": "application/json"}
        )
    
    def request(self, flow: http.HTTPFlow) -> None:
        """Intercept and filter requests"""
        host = flow.request.host
        
        # Always block internal addresses (security measure)
        if is_internal_address(host):
            flow.response = self._make_blocked_response(
                f"Access to internal address '{host}' is blocked for security reasons",
                {"blocked_host": host, "reason": "internal_address"}
            )
            return
        
        # Get network config from custom header
        # Format: {"enabled": true, "restricted": true, "allowed_hosts": ["example.com"]}
        config_header = flow.request.headers.get('X-Network-Config', '')
        
        # Remove the custom header before forwarding (don't leak it)
        if 'X-Network-Config' in flow.request.headers:
            del flow.request.headers['X-Network-Config']
        
        # If no config header, BLOCK the request (secure by default)
        # User code running in sandbox won't have config header, so block it
        if not config_header:
            flow.response = self._make_blocked_response(
                f"Network request to '{host}' was blocked. No network access allowed.",
                {"blocked_host": host, "reason": "no_config"}
            )
            return
        
        # Parse config from header
        try:
            config = json.loads(config_header)
        except json.JSONDecodeError:
            # Invalid JSON, allow request (fail-open)
            return
        
        # Check if network is disabled entirely
        if not config.get('enabled', True):
            flow.response = self._make_blocked_response(
                "Network access is disabled for this execution",
                {"blocked_host": host, "reason": "network_disabled"}
            )
            return
        
        # Check if network is restricted
        if not config.get('restricted', False):
            # Not restricted, allow all external requests
            return
        
        # Network is restricted - check allowlist
        allowed_hosts = config.get('allowed_hosts', [])
        
        if host not in allowed_hosts:
            flow.response = self._make_blocked_response(
                f"Network request to '{host}' was blocked. Host not in allowlist.",
                {
                    "blocked_host": host,
                    "allowed_hosts": allowed_hosts,
                    "reason": "not_in_allowlist"
                }
            )
            return
        
        # Host is in allowlist, allow the request
        return


# Register the addon
addons = [NetworkFilter()]
