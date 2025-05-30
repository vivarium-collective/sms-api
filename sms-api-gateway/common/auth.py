from typing import Optional

from fastapi import Security, HTTPException, WebSocket, status, Request
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse

from common.users import key_db
from common.log import get_logger
from common.encryption.storage import UserMetadata, check_api_key, get_user_from_api_key


logger = get_logger(__file__)

SESSION_COOKIE = "session_user"
API_KEY_HEADER = "X-Community-API-Key"
auth_key_header = APIKeyHeader(name=API_KEY_HEADER)


def get_user(api_key_header: str = Security(auth_key_header)):
    if check_api_key(api_key_header):
        user = get_user_from_api_key(api_key_header)
        return user
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key"
    )


def validate_user(username: str, pwd: str, collection: str = "example") -> UserMetadata:
    valid_key = key_db.check_key(pwd, collection)
    user = get_user_from_api_key(pwd)
    if valid_key and user is not None and user.name == username:
        return user
    else: 
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")
        

async def validate_socket(websocket: WebSocket, collection: str = "example"):
    headers = websocket.headers
    api_key = headers.get(API_KEY_HEADER)
    if api_key is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not find the given key. Invalid API Key")
    
    is_valid = validate_user(api_key, collection)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")
    return api_key


