from fastapi import Security, HTTPException, WebSocket, status
from fastapi.security import APIKeyHeader

from common.users import key_db
from common.encryption.storage import check_api_key, get_user_from_api_key


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


async def validate_socket(websocket: WebSocket, collection: str = "example"):
    headers = websocket.headers
    api_key = headers.get(API_KEY_HEADER)
    if api_key is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not find the given key. Invalid API Key")
    
    is_valid = key_db.check_key(api_key, collection)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")
    return api_key


