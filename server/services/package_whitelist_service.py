"""
Package whitelist service.
Loads allowed packages from JSON and validates dependency requests safely.
"""
import json
import os
import re
from typing import Dict, List, Tuple


_SAFE_PACKAGE_PATTERN = re.compile(
    r"^[a-zA-Z0-9_.-]+(\[[a-zA-Z0-9_,.-]+\])?(==[a-zA-Z0-9_.+-]+)?$"
)


class PackageWhitelistService:
    """Validates package installation requests against a JSON whitelist."""

    def __init__(self, whitelist_path: str = None):
        base_dir = os.path.dirname(os.path.dirname(__file__))  # server/
        default_path = os.path.join(base_dir, "config", "whitelisted_packages.json")
        self.whitelist_path = whitelist_path or os.getenv("PACKAGE_WHITELIST_PATH", default_path)
        self._data = self._load_whitelist()

    def _load_whitelist(self) -> Dict:
        if not os.path.exists(self.whitelist_path):
            raise FileNotFoundError(f"Whitelist file not found: {self.whitelist_path}")

        with open(self.whitelist_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            raise ValueError("Whitelist JSON must be an object")
        return data

    def reload(self) -> None:
        self._data = self._load_whitelist()

    def get_whitelist(self, language: str) -> Dict:
        return self._data.get(language.lower(), {})

    def get_allowed_packages(self, language: str) -> Dict:
        config = self.get_whitelist(language)
        return {
            "exact": sorted(config.get("exact", [])),
            "versioned": config.get("versioned", {})
        }

    def validate_dependencies(self, language: str, dependencies: List[str]) -> Tuple[List[str], List[str]]:
        """
        Returns (validated_dependencies, rejected_dependencies).
        For Python:
        - allows exact package names if present in exact[]
        - allows pkg==version only if version is explicitly allowed in versioned[pkg]
        """
        language = language.lower()
        if not dependencies:
            return [], []

        if language not in self._data:
            # Non-configured languages: reject dependency installation completely
            return [], list(dependencies)

        config = self.get_whitelist(language)
        exact_allowed = set(config.get("exact", []))
        versioned_allowed = config.get("versioned", {})

        valid = []
        rejected = []

        for raw_dep in dependencies:
            dep = str(raw_dep).strip()

            if not dep or not _SAFE_PACKAGE_PATTERN.fullmatch(dep):
                rejected.append(dep)
                continue

            if dep.startswith("-"):
                rejected.append(dep)
                continue

            if "==" in dep:
                pkg, version = dep.split("==", 1)
                allowed_versions = versioned_allowed.get(pkg, [])
                if version in allowed_versions:
                    valid.append(dep)
                else:
                    rejected.append(dep)
            else:
                if dep in exact_allowed:
                    valid.append(dep)
                else:
                    rejected.append(dep)

        return valid, rejected


_package_whitelist_service = None


def get_package_whitelist_service() -> PackageWhitelistService:
    global _package_whitelist_service
    if _package_whitelist_service is None:
        _package_whitelist_service = PackageWhitelistService()
    return _package_whitelist_service