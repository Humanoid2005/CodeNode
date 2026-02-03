"""Code execution API routes using Judge0 Python SDK"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Union
import json
import logging

from services.judge0_service import Judge0Service
from services.crypto_service import get_crypto_service

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize Judge0 service
judge0_service = Judge0Service()


class CodeExecutionRequest(BaseModel):
    code: str
    language: str = "python"
    dependencies: List[str] = Field(default_factory=list)  # List of package names
    secrets: dict = Field(default_factory=dict)  # Environment variables/secrets
    encrypted_secrets: Optional[str] = None  # Encrypted secrets (for future use)
    enable_network: bool = False  # Enable network access in container
    stdin: Optional[str] = None  # Standard input for the program


class TestCase(BaseModel):
    input: str
    expected_output: Optional[str] = None


class CodeExecutionWithTestsRequest(BaseModel):
    code: str
    language: str = "python"
    test_cases: List[Union[TestCase, tuple, list]]
    dependencies: List[str] = Field(default_factory=list)  # List of package names
    secrets: dict = Field(default_factory=dict)  # Environment variables/secrets
    enable_network: bool = False  # Enable network access


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


@router.post("/run", response_model=CodeExecutionResponse)
async def run_code(request: CodeExecutionRequest):
    """Execute code using Judge0 API"""
    try:
        logger.info(f"Received request: code length={len(request.code)}, language={request.language}, "
                   f"dependencies={request.dependencies}, secrets keys={list(request.secrets.keys())}")
        
        # Validate language
        supported_langs = judge0_service.get_supported_languages()
        if request.language.lower() not in supported_langs:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported language: {request.language}. "
                       f"Supported: {', '.join(supported_langs)}"
            )
        
        # Validate code is not empty
        if not request.code or not request.code.strip():
            raise HTTPException(
                status_code=400,
                detail="Code cannot be empty"
            )
        
        # Ensure stdin is a string
        stdin = request.stdin or ""
        if not isinstance(stdin, str):
            stdin = str(stdin)
        
        # Convert dependencies list to requirements.txt format (note: not fully supported in Judge0 CE)
        requirements = None
        if request.dependencies and len(request.dependencies) > 0:
            requirements = "\n".join(request.dependencies)
            logger.warning("Dependencies specified but may not be fully supported in Judge0 CE")
        
        # Handle encrypted secrets if provided
        env_vars = None
        if request.encrypted_secrets:
            try:
                crypto_service = get_crypto_service()
                decrypted_secrets = crypto_service.decrypt_secrets(request.encrypted_secrets)
                env_vars = {k: v for k, v in decrypted_secrets.items() if v}
                logger.info(f"Decrypted {len(env_vars)} environment variables")
            except ValueError as e:
                logger.error(f"Failed to decrypt secrets: {e}")
                raise HTTPException(status_code=400, detail="Failed to decrypt secrets. Invalid encryption.")
        elif request.secrets:
            # Fallback to unencrypted secrets (for backward compatibility)
            env_vars = {k: v for k, v in request.secrets.items() if v}
            if env_vars:
                logger.warning("Using unencrypted secrets - consider using encrypted_secrets instead")
        
        if env_vars:
            logger.info(f"Environment variables set: {list(env_vars.keys())}")
        
        # Execute code
        logger.debug(f"Executing code for language: {request.language}")
        result = judge0_service.execute_code(
            source_code=request.code,
            language=request.language,
            stdin=stdin,
            requirements=requirements,
            env_vars=env_vars,
        )
        
        # Log the execution result status
        status_desc = result.get("status", {}).get("description", "Unknown")
        logger.info(f"Execution completed with status: {status_desc}")
        
        return CodeExecutionResponse(**result)
        
    except ValueError as e:
        logger.error(f"ValueError: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except TimeoutError as e:
        logger.error(f"TimeoutError: {str(e)}")
        raise HTTPException(status_code=408, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Exception: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Execution error: {str(e)}")


@router.post("/run/tests")
async def run_code_with_tests(request: CodeExecutionWithTestsRequest):
    """Execute code with multiple test cases"""
    try:
        # Validate language
        if request.language.lower() not in judge0_service.get_supported_languages():
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported language: {request.language}"
            )
        
        # Convert test cases to tuples
        test_cases = []
        for tc in request.test_cases:
            if isinstance(tc, dict):
                test_cases.append((tc.get("input", ""), tc.get("expected_output")))
            elif isinstance(tc, (list, tuple)):
                test_cases.append(tuple(tc))
            else:
                test_cases.append((tc.input, tc.expected_output))
        
        # Convert dependencies list to requirements.txt format
        requirements = None
        if request.dependencies:
            requirements = "\n".join(request.dependencies)
        
        # Execute with test cases
        results = judge0_service.execute_with_test_cases(
            source_code=request.code,
            language=request.language,
            test_cases=test_cases,
            requirements=requirements,
            env_vars=request.secrets,  # Use secrets as environment variables
        )
        
        return {"results": results, "total": len(results)}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
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
    return {
        "languages": judge0_service.get_supported_languages(),
        "count": len(judge0_service.get_supported_languages())
    }


@router.get("/languages/info")
async def get_languages_info():
    """Get detailed information about all supported languages from Judge0"""
    try:
        return judge0_service.get_languages_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch languages: {str(e)}")


