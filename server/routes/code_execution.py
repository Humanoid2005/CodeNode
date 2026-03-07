"""Code execution API routes using Judge0 backend services"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Union
import logging

from services.crypto_service import get_crypto_service
from services.execution_service import ExecutionService

logger = logging.getLogger(__name__)

router = APIRouter()
execution_service = ExecutionService()


class NetworkConfigRequest(BaseModel):
    enabled: bool = True
    restricted: bool = False
    allowed_hosts: List[str] = Field(default_factory=list)


class CodeExecutionRequest(BaseModel):
    code: str
    language: str = "python"
    dependencies: List[str] = Field(default_factory=list)
    secrets: dict = Field(default_factory=dict)
    encrypted_secrets: Optional[str] = None
    enable_network: bool = True
    stdin: Optional[str] = None
    network_config: Optional[NetworkConfigRequest] = None


class TestCase(BaseModel):
    input: str
    expected_output: Optional[str] = None


class CodeExecutionWithTestsRequest(BaseModel):
    code: str
    language: str = "python"
    test_cases: List[Union[TestCase, tuple, list]]
    dependencies: List[str] = Field(default_factory=list)
    secrets: dict = Field(default_factory=dict)
    enable_network: bool = True
    network_config: Optional[NetworkConfigRequest] = None


class CodeExecutionResponse(BaseModel):
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    compile_output: Optional[str] = None
    message: Optional[str] = None
    time: Optional[str] = None
    memory: Optional[int] = None
    status: dict = {}
    exit_code: Optional[int] = None
    token: str
    validated_dependencies: List[str] = Field(default_factory=list)


@router.post("/run", response_model=CodeExecutionResponse)
async def run_code(request: CodeExecutionRequest):
    """Execute code using Judge0 API"""
    try:
        logger.info(
            f"Received request: code length={len(request.code)}, language={request.language}, "
            f"dependencies={request.dependencies}, secrets keys={list(request.secrets.keys())}"
        )

        result = execution_service.execute(
            code=request.code,
            language=request.language,
            dependencies=request.dependencies,
            secrets=request.secrets,
            encrypted_secrets=request.encrypted_secrets,
            stdin=request.stdin,
            network_config_request=request.network_config,
            enable_network=request.enable_network,
        )

        status_desc = result.get("status", {}).get("description", "Unknown")
        logger.info(f"Execution completed with status: {status_desc}")
        return CodeExecutionResponse(**result)

    except HTTPException:
        raise
    except TimeoutError as e:
        logger.error(f"TimeoutError: {str(e)}")
        raise HTTPException(status_code=408, detail=str(e))
    except Exception as e:
        logger.error(f"Exception: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Execution error: {str(e)}")


@router.post("/run/tests")
async def run_code_with_tests(request: CodeExecutionWithTestsRequest):
    """Execute code with multiple test cases"""
    try:
        test_cases = []
        for tc in request.test_cases:
            if isinstance(tc, dict):
                test_cases.append((tc.get("input", ""), tc.get("expected_output")))
            elif isinstance(tc, (list, tuple)):
                test_cases.append(tuple(tc))
            else:
                test_cases.append((tc.input, tc.expected_output))

        results = execution_service.execute_with_test_cases(
            code=request.code,
            language=request.language,
            test_cases=test_cases,
            dependencies=request.dependencies,
            secrets=request.secrets,
            network_config_request=request.network_config,
            enable_network=request.enable_network,
        )

        return {"results": results, "total": len(results)}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution error: {str(e)}")


@router.get("/encryption-key")
async def get_encryption_key():
    """Get the encryption key for encrypting secrets on the frontend"""
    crypto_service = get_crypto_service()
    return crypto_service.get_public_key_info()


@router.get("/languages")
async def get_supported_languages():
    """Get list of supported programming languages"""
    languages = execution_service.get_supported_languages()
    return {
        "languages": languages,
        "count": len(languages)
    }


@router.get("/languages/info")
async def get_languages_info():
    """Get detailed information about all supported languages from Judge0"""
    try:
        return execution_service.get_languages_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch languages: {str(e)}")


@router.get("/packages/whitelist/{language}")
async def get_package_whitelist(language: str):
    """Expose allowed installable packages for a language"""
    try:
        return {
            "language": language.lower(),
            "whitelist": execution_service.get_package_whitelist(language)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load whitelist: {str(e)}")