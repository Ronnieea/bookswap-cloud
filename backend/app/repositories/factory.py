import os

from app.repositories.book_repository import (
    book_repository as memory_repository
)


def get_book_repository():
    backend = os.getenv(
        "STORAGE_BACKEND",
        "memory"
    ).lower()

    if backend == "memory":
        return memory_repository

    if backend == "dynamodb":
        from app.repositories.dynamodb_book_repository import (
            DynamoDBBookRepository
        )

        return DynamoDBBookRepository()

    raise ValueError(
        f"Unsupported STORAGE_BACKEND: {backend}"
    )