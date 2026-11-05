from typing import Literal
from pydantic import BaseModel, Field


BookStatus = Literal[
    "AVAILABLE",
    "RESERVED",
    "EXCHANGED"
]


class BookCreate(BaseModel):
    title: str = Field(min_length=1)
    author: str = Field(min_length=1)
    isbn: str = Field(min_length=10, max_length=13)


class BookUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    author: str | None = Field(default=None, min_length=1)
    isbn: str | None = Field(
        default=None,
        min_length=10,
        max_length=13
    )
    status: BookStatus | None = None
