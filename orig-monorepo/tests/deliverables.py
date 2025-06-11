import requests

USE_LOCAL = True
LOCAL_URL = "http://localhost:8080/"
PROD_URL = ""  # TODO: eventually get this
ROOT = LOCAL_URL if USE_LOCAL else PROD_URL


def test_root():
    resp = requests.get(ROOT).json()
    assert resp
    print(resp)


def test_auth():
    api_key = "test"
    url = f"{ROOT}/api/v1/test-authentication"

    headers = {"X-Community-API-Key": api_key}
    response = requests.get(url, headers=headers)
    assert response.status_code == 200
    print(response.json())
