from fastapi.testclient import TestClient

from sms_api.api.main import app

client = TestClient(app)


# create dir service
# create get data service
# use fastapi testclient
# marimo embedded services


def test_read_main():
    response = client.get("/test-get-results")
    assert response.status_code == 200
