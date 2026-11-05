from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class ExchangeStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class ExchangeRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requested_book_id: str = Field(
        min_length=1,
        max_length=100
    )

    requester_name: str = Field(
        min_length=1,
        max_length=100
    )

    message: str = Field(
        default="",
        max_length=1000
    )


class ExchangeRequestResponse(ExchangeRequestCreate):
    request_id: str
    status: ExchangeStatus
    created_at: datetime
    updated_at: Optional[datetime] = None


class ExchangeStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ExchangeStatus