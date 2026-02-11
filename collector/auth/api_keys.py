"""API key authentication middleware."""

import hashlib
import logging
import os

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

security = HTTPBearer()

# In-memory set of valid API key hashes (loaded from config on startup)
_valid_key_hashes: set = set()


def configure_api_keys(api_keys: list) -> None:
    """Load plaintext API keys, store their SHA-256 hashes."""
    global _valid_key_hashes
    _valid_key_hashes = {_hash_key(k) for k in api_keys if k}
    logger.info(f"Configured {len(_valid_key_hashes)} API key(s)")


def _hash_key(key: str) -> str:
    """SHA-256 hash a key."""
    return hashlib.sha256(key.encode()).hexdigest()


def _is_auth_disabled() -> bool:
    """Check if authentication is explicitly disabled via environment variable."""
    return os.environ.get("AUTH_DISABLED", "").lower() == "true"


def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> str:
    """FastAPI dependency that validates Bearer token against known API keys.

    Returns the (hashed) key identifier on success.
    Raises HTTPException 401 on failure.
    """
    # Explicit opt-out: AUTH_DISABLED=true must be set to skip auth
    if _is_auth_disabled():
        return "auth-disabled"

    if not _valid_key_hashes:
        # No keys configured and auth not explicitly disabled — reject
        logger.warning("No API keys configured and AUTH_DISABLED is not set; rejecting request")
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Configure API keys or set AUTH_DISABLED=true.",
        )

    token = credentials.credentials
    token_hash = _hash_key(token)

    if token_hash not in _valid_key_hashes:
        logger.warning("Invalid API key attempt")
        raise HTTPException(status_code=401, detail="Invalid API key")

    return token_hash
