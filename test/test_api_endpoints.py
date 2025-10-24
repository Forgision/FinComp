from fastapi.testclient import TestClient
from app.main import _app as app_instance # Import _app directly

client = TestClient(app_instance)

def test_read_test_endpoint():
    """Test the /test endpoint."""
    response = client.get("/test")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}