import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app import app

client = TestClient(app)

class TestEndpoints:
    def test_health_endpoint(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_resolve_endpoint_invalid_url(self):
        response = client.get("/resolve?url=invalid-url")
        assert response.status_code == 400
    
    def test_resolve_endpoint_valid_url(self):
        with patch('utils.resolve_single') as mock_resolve:
            mock_resolve.return_value = AsyncMock(
                status="success",
                url="https://example.com",
                data={"test": "data"}
            )
            response = client.get("/resolve?url=https://example.com")
            assert response.status_code == 200
    
    def test_batch_endpoint_empty_urls(self):
        response = client.post("/resolve-batch", json={"urls": []})
        assert response.status_code == 400
    
    def test_batch_endpoint_too_many_urls(self):
        urls = ["https://example.com"] * 100  # Exceeds MAX_BATCH_SIZE
        response = client.post("/resolve-batch", json={"urls": urls})
        assert response.status_code == 400

@pytest.mark.asyncio
async def test_async_operations():
    """Test async operations don't block event loop"""
    from utils import resolve_single
    
    start_time = asyncio.get_event_loop().time()
    tasks = [resolve_single("https://example.com") for _ in range(5)]
    await asyncio.gather(*tasks, return_exceptions=True)
    end_time = asyncio.get_event_loop().time()
    
    # Should complete concurrently, not sequentially
    assert end_time - start_time < 10  # Reasonable concurrent execution time
