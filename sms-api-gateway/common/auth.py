from fastapi import Security, HTTPException, WebSocket, status
from fastapi.security import APIKeyHeader

from common.encryption.storage import check_api_key, get_user_from_api_key

API_KEY_HEADER = "X-Community-API-Key"
EXPECTED_KEY = "test"
auth_key_header = APIKeyHeader(name=API_KEY_HEADER)


def get_user(api_key_header: str = Security(auth_key_header)):
    if check_api_key(api_key_header):
        user = get_user_from_api_key(api_key_header)
        return user
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key"
    )

def extract_api_key(headers):
    api_key = headers.get(API_KEY_HEADER)
    if api_key != EXPECTED_KEY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API Key")
    return api_key


async def get_user_ws(websocket: WebSocket):
    return extract_api_key(websocket.headers)
