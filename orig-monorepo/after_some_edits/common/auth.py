from fastapi import HTTPException, Security, WebSocket, status
from fastapi.security import APIKeyHeader

from sms_api.common.log import get_logger
from sms_api.common.users import UserMetadata, check_api_key, get_user_from_api_key, key_db

logger = get_logger(__file__)

SESSION_COOKIE = "session_user"
API_KEY_HEADER = "X-Community-API-Key"
auth_key_header = APIKeyHeader(name=API_KEY_HEADER)


def get_user(api_key_header: str = Security(auth_key_header)):
    """
    FastAPI app dependency.
    """
    if check_api_key(api_key_header):
        user = get_user_from_api_key(api_key_header)
        return user
    e = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    logger.error(str(e))
    raise e


def validate_user(username: str, pwd: str, collection: str = "main") -> UserMetadata:
    """
    Used at login

    :param username:
    :param pwd:
    :param collection: (str) defaults to "main".

    :return: UserMetadata
    :raises: fastapi.HTTPException if either username and/or pwd is not valid.
    """
    valid_key = key_db.check_key(pwd, collection)
    user = key_db.find_user(username)
    if valid_key and user is not None:
        return user.metadata
    else:
        e = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
        logger.error(str(e))
        raise e


async def validate_socket(websocket: WebSocket, collection: str = "example"):
    headers = websocket.headers
    api_key = headers.get(API_KEY_HEADER)
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not find the given key. Invalid API Key"
        )

    is_valid = validate_user(api_key, collection)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")
    return api_key
