import os

os.environ["STORAGE_BACKEND"] = "memory"

from datetime import datetime, timezone
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers import exchanges


NOW = datetime.now(timezone.utc).isoformat()


class FakeBookRepository:
    def __init__(self):
        self.books = {
            "book-001": {
                "book_id": "book-001",
                "status": "AVAILABLE"
            },
            "book-002": {
                "book_id": "book-002",
                "status": "RESERVED"
            }
        }

    def get_by_id(self, book_id):
        return self.books.get(book_id)


class FakeExchangeRepository:
    def __init__(self, book_repository):
        self.book_repository = book_repository
        self.requests = {
            "request-001": {
                "request_id": "request-001",
                "requested_book_id": "book-001",
                "requester_name": "Test User",
                "message": "I want this book",
                "status": "PENDING",
                "created_at": NOW
            },
            "request-002": {
                "request_id": "request-002",
                "requested_book_id": "book-002",
                "requester_name": "Test User",
                "message": "",
                "status": "ACCEPTED",
                "created_at": NOW
            }
        }

    def get_by_id(self, request_id):
        return self.requests.get(request_id)

    def create(
        self,
        requested_book_id,
        requester_name,
        message=""
    ):
        request_id = f"request-{len(self.requests) + 1:03d}"

        request = {
            "request_id": request_id,
            "requested_book_id": requested_book_id,
            "requester_name": requester_name,
            "message": message,
            "status": "PENDING",
            "created_at": NOW
        }

        self.requests[request_id] = request
        return deepcopy(request)

    def update_status(self, request_id, status):
        request = self.requests.get(request_id)

        if request is None or request["status"] != "PENDING":
            return None

        request["status"] = status
        request["updated_at"] = NOW
        return deepcopy(request)

    def accept_request(self, request_id, book_id):
        request = self.requests.get(request_id)
        book = self.book_repository.get_by_id(book_id)

        if request is None or book is None:
            return None

        if request["status"] != "PENDING":
            return None

        if request["requested_book_id"] != book_id:
            return None

        if book["status"] != "AVAILABLE":
            return None

        request["status"] = "ACCEPTED"
        request["updated_at"] = NOW
        book["status"] = "RESERVED"

        return deepcopy(request)


@pytest.fixture
def test_environment(monkeypatch):
    books = FakeBookRepository()
    requests = FakeExchangeRepository(books)

    monkeypatch.setattr(
        exchanges,
        "get_book_repository",
        lambda: books
    )

    monkeypatch.setattr(
        exchanges,
        "get_exchange_repository",
        lambda: requests
    )

    with TestClient(app) as client:
        yield client, books, requests


def test_exchange_request_not_found(test_environment):
    client, _, _ = test_environment

    response = client.get(
        "/exchange-requests/not-exist"
    )

    assert response.status_code == 404


def test_create_request_book_not_found(test_environment):
    client, _, _ = test_environment

    response = client.post(
        "/exchange-requests",
        json={
            "requested_book_id": "not-exist",
            "requester_name": "Alice",
            "message": "Hello"
        }
    )

    assert response.status_code == 404


def test_create_request_book_unavailable(test_environment):
    client, _, _ = test_environment

    response = client.post(
        "/exchange-requests",
        json={
            "requested_book_id": "book-002",
            "requester_name": "Alice",
            "message": "Hello"
        }
    )

    assert response.status_code == 409


def test_cannot_reset_to_pending(test_environment):
    client, _, _ = test_environment

    response = client.patch(
        "/exchange-requests/request-001",
        json={"status": "PENDING"}
    )

    assert response.status_code == 422


def test_cannot_process_twice(test_environment):
    client, _, _ = test_environment

    response = client.patch(
        "/exchange-requests/request-002",
        json={"status": "REJECTED"}
    )

    assert response.status_code == 409


def test_accept_exchange_request(test_environment):
    client, books, requests = test_environment

    response = client.patch(
        "/exchange-requests/request-001",
        json={"status": "ACCEPTED"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ACCEPTED"

    assert (
        requests.get_by_id("request-001")["status"]
        == "ACCEPTED"
    )

    assert (
        books.get_by_id("book-001")["status"]
        == "RESERVED"
    )


def test_reject_exchange_request(test_environment):
    client, books, _ = test_environment

    response = client.patch(
        "/exchange-requests/request-001",
        json={"status": "REJECTED"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"

    # 拒絕申請不應保留書籍
    assert (
        books.get_by_id("book-001")["status"]
        == "AVAILABLE"
    )
