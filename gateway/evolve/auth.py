from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

from api.gateway.handlers.encryption.storage import (
    check_api_key, 
    get_user_from_api_key
)

auth_key_header = APIKeyHeader(name="X-Community-API-Key")


def get_user(api_key_header: str = Security(auth_key_header)):
    if check_api_key(api_key_header):
        user = get_user_from_api_key(api_key_header)
        return user
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key"
    )


