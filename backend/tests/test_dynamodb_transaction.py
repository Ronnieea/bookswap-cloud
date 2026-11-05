import pytest

from botocore.exceptions import ClientError
from boto3.dynamodb.types import TypeSerializer

from app.repositories.dynamodb_exchange_repository import (
    DynamoDBExchangeRepository,
)


class FakeDynamoDBClient:
    def __init__(self):
        self.transactions = []
        self.error = None

    def transact_write_items(self, **kwargs):
        if self.error is not None:
            raise self.error

        self.transactions.append(kwargs)
        return {}


class FakeTable:
    name = "test-exchange-requests"


@pytest.fixture
def repository():
    # 不執行 __init__，避免建立 AWS 連線
    repo = object.__new__(DynamoDBExchangeRepository)

    repo.client = FakeDynamoDBClient()
    repo.table = FakeTable()
    repo.serializer = TypeSerializer()
    repo.books_table_name = "test-books"

    # 模擬交易成功後讀取申請
    repo.get_by_id = lambda request_id: {
        "request_id": request_id,
        "requested_book_id": "book-001",
        "requester_name": "Test User",
        "message": "",
        "status": "ACCEPTED",
        "created_at": "2026-01-01T00:00:00+00:00",
    }

    return repo


def test_accept_uses_single_transaction(repository):
    result = repository.accept_request(
        request_id="request-001",
        book_id="book-001",
    )

    assert result["status"] == "ACCEPTED"

    assert len(repository.client.transactions) == 1

    transaction = repository.client.transactions[0]
    operations = transaction["TransactItems"]

    assert len(operations) == 2

    request_update = operations[0]["Update"]
    book_update = operations[1]["Update"]

    assert request_update["TableName"] == "test-exchange-requests"
    assert book_update["TableName"] == "test-books"

    assert (
        request_update["ExpressionAttributeValues"][":accepted"]["S"]
        == "ACCEPTED"
    )

    assert (
        book_update["ExpressionAttributeValues"][":reserved"]["S"]
        == "RESERVED"
    )


def test_transaction_has_conditions(repository):
    repository.accept_request(
        request_id="request-001",
        book_id="book-001",
    )

    operations = repository.client.transactions[0]["TransactItems"]

    request_condition = operations[0]["Update"]["ConditionExpression"]
    book_condition = operations[1]["Update"]["ConditionExpression"]

    assert "#status = :pending" in request_condition
    assert "requested_book_id = :book_id" in request_condition
    assert "#status = :available" in book_condition


def test_transaction_conditional_failure(repository):
    repository.client.error = ClientError(
        {
            "Error": {
                "Code": "TransactionCanceledException",
                "Message": "Transaction cancelled",
            },
            "CancellationReasons": [
                {"Code": "ConditionalCheckFailed"},
                {"Code": "None"},
            ],
        },
        "TransactWriteItems",
    )

    result = repository.accept_request(
        request_id="request-001",
        book_id="book-001",
    )

    assert result is None
    assert repository.client.transactions == []


def test_unexpected_transaction_error_is_raised(repository):
    repository.client.error = ClientError(
        {
            "Error": {
                "Code": "AccessDeniedException",
                "Message": "Access denied",
            }
        },
        "TransactWriteItems",
    )

    with pytest.raises(ClientError):
        repository.accept_request(
            request_id="request-001",
            book_id="book-001",
        )