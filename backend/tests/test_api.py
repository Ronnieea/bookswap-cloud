import os

# 測試環境不使用正式 DynamoDB
os.environ["STORAGE_BACKEND"] = "memory"

from fastapi.testclient import TestClient
from app.main import app
from app.routers import exchanges


class FakeExchangeRepository:
    """只供測試使用，不連接 AWS。"""

    def get_all(self):
        return []


def test_openapi_schema():
    with TestClient(app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "paths" in response.json()


def test_books_endpoint():
    with TestClient(app) as client:
        response = client.get("/books")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_exchange_requests_endpoint(monkeypatch):
    monkeypatch.setattr(
        exchanges,
        "get_exchange_repository",
        lambda: FakeExchangeRepository()
    )

    with TestClient(app) as client:
        response = client.get("/exchange-requests")

    assert response.status_code == 200
    assert response.json() == []