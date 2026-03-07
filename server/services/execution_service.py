"""
Execution orchestration layer.
This makes the backend easier to integrate into RASP later.
"""
import logging
import re
from typing import Dict, List, Optional

from fastapi import HTTPException

from services.judge0_service import Judge0Service, NetworkConfig
from services.crypto_service import get_crypto_service
from services.package_whitelist_service import get_package_whitelist_service

logger = logging.getLogger(__name__)

_DOMAIN_PATTERN = re.compile(
    r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$'
)
_IPV4_PATTERN = re.compile(
    r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
)


def _is_valid_host(host: str) -> bool:
    if not host or len(host) > 253:
        return False
    return bool(_DOMAIN_PATTERN.match(host) or _IPV4_PATTERN.match(host))


class ExecutionService:
    """High-level execution service. Suitable for direct reuse by RASP later."""

    def __init__(self):
        self.judge0_service = Judge0Service()
        self.whitelist_service = get_package_whitelist_service()

    def get_supported_languages(self) -> List[str]:
        return self.judge0_service.get_supported_languages()

    def get_languages_info(self):
        return self.judge0_service.get_languages_info()

    def get_package_whitelist(self, language: str) -> Dict:
        return self.whitelist_service.get_allowed_packages(language)

    def execute(
        self,
        code: str,
        language: str,
        dependencies: Optional[List[str]] = None,
        secrets: Optional[Dict[str, str]] = None,
        encrypted_secrets: Optional[str] = None,
        stdin: Optional[str] = None,
        network_config_request=None,
        enable_network: bool = True,
    ) -> Dict:
        language = language.lower().strip()

        supported_langs = self.judge0_service.get_supported_languages()
        if language not in supported_langs:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported language: {language}. Supported: {', '.join(supported_langs)}"
            )

        if not code or not code.strip():
            raise HTTPException(status_code=400, detail="Code cannot be empty")

        stdin = stdin or ""
        if not isinstance(stdin, str):
            stdin = str(stdin)

        env_vars = None
        if encrypted_secrets:
            try:
                crypto_service = get_crypto_service()
                decrypted_secrets = crypto_service.decrypt_secrets(encrypted_secrets)
                env_vars = {k: v for k, v in decrypted_secrets.items() if v}
            except ValueError:
                raise HTTPException(status_code=400, detail="Failed to decrypt secrets. Invalid encryption.")
        elif secrets:
            env_vars = {k: v for k, v in secrets.items() if v}
            if env_vars:
                logger.warning("Using unencrypted secrets - consider using encrypted_secrets instead")

        validated_dependencies, rejected_dependencies = self.whitelist_service.validate_dependencies(
            language=language,
            dependencies=dependencies or [],
        )

        if rejected_dependencies:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Some dependencies are not whitelisted or are invalid",
                    "rejected_dependencies": rejected_dependencies,
                    "allowed_dependencies": self.whitelist_service.get_allowed_packages(language)
                }
            )

        network_config = None
        if network_config_request:
            validated_hosts = []
            for host in network_config_request.allowed_hosts:
                host = host.strip()
                if host and _is_valid_host(host):
                    validated_hosts.append(host)

            network_config = NetworkConfig(
                enabled=network_config_request.enabled,
                restricted=network_config_request.restricted,
                allowed_hosts=validated_hosts,
            )
        elif not enable_network:
            network_config = NetworkConfig(enabled=False)

        result = self.judge0_service.execute_code(
            source_code=code,
            language=language,
            stdin=stdin,
            requirements=validated_dependencies,
            env_vars=env_vars,
            network_config=network_config,
        )

        result["validated_dependencies"] = validated_dependencies
        return result

    def execute_with_test_cases(
        self,
        code: str,
        language: str,
        test_cases: List[tuple],
        dependencies: Optional[List[str]] = None,
        secrets: Optional[Dict[str, str]] = None,
        network_config_request=None,
        enable_network: bool = True,
    ) -> List[Dict]:
        language = language.lower().strip()

        if language not in self.judge0_service.get_supported_languages():
            raise HTTPException(status_code=400, detail=f"Unsupported language: {language}")

        validated_dependencies, rejected_dependencies = self.whitelist_service.validate_dependencies(
            language=language,
            dependencies=dependencies or [],
        )

        if rejected_dependencies:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Some dependencies are not whitelisted or are invalid",
                    "rejected_dependencies": rejected_dependencies,
                    "allowed_dependencies": self.whitelist_service.get_allowed_packages(language)
                }
            )

        network_config = None
        if network_config_request:
            validated_hosts = [
                host.strip() for host in network_config_request.allowed_hosts
                if host.strip() and _is_valid_host(host.strip())
            ]
            network_config = NetworkConfig(
                enabled=network_config_request.enabled,
                restricted=network_config_request.restricted,
                allowed_hosts=validated_hosts,
            )
        elif not enable_network:
            network_config = NetworkConfig(enabled=False)

        return self.judge0_service.execute_with_test_cases(
            source_code=code,
            language=language,
            test_cases=test_cases,
            requirements=validated_dependencies,
            env_vars=secrets,
            network_config=network_config,
        )