from fastapi.testclient import TestClient
from app.main import _app

client = TestClient(_app)

def test_read_main():
    response = client.get("/test")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}
