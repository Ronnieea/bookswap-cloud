from fastapi import APIRouter, HTTPException, status

from app.repositories.dynamodb_book_repository import DynamoDBBookRepository
from app.repositories.factory import get_book_repository
from app.repositories.dynamodb_exchange_repository import DynamoDBExchangeRepository
from app.schemas.exchange import (
    ExchangeRequestCreate,
    ExchangeRequestResponse,
    ExchangeStatusUpdate,
    ExchangeStatus,
)


router = APIRouter(
    prefix="/exchange-requests",
    tags=["Exchange Requests"]
)


def get_exchange_repository():
    return DynamoDBExchangeRepository()


@router.post(
    "",
    response_model=ExchangeRequestResponse,
    status_code=status.HTTP_201_CREATED
)
def create_exchange_request(
    request: ExchangeRequestCreate
):
    book_repository = get_book_repository()
    book = book_repository.get_by_id(
        request.requested_book_id
    )

    if book is None:
        raise HTTPException(
            status_code=404,
            detail="Requested book not found"
        )

    if book.get("status") != "AVAILABLE":
        raise HTTPException(
            status_code=409,
            detail="Book is not available for exchange"
        )

    repository = get_exchange_repository()

    return repository.create(
        requested_book_id=request.requested_book_id,
        requester_name=request.requester_name,
        message=request.message
    )


@router.get(
    "",
    response_model=list[ExchangeRequestResponse]
)
def list_exchange_requests():
    repository = get_exchange_repository()
    return repository.get_all()


@router.get(
    "/{request_id}",
    response_model=ExchangeRequestResponse
)
def get_exchange_request(request_id: str):
    repository = get_exchange_repository()
    request = repository.get_by_id(request_id)

    if request is None:
        raise HTTPException(
            status_code=404,
            detail="Exchange request not found"
        )

    return request


@router.patch(
    "/{request_id}",
    response_model=ExchangeRequestResponse
)
def update_exchange_request(
    request_id: str,
    update: ExchangeStatusUpdate
):
    if update.status == ExchangeStatus.PENDING:
        raise HTTPException(
            status_code=422,
            detail="Cannot reset request to PENDING"
        )

    repository = get_exchange_repository()

    existing = repository.get_by_id(request_id)

    if existing is None:
        raise HTTPException(
            status_code=404,
            detail="Exchange request not found"
        )

    if existing.get("status") != "PENDING":
        raise HTTPException(
            status_code=409,
            detail="Exchange request has already been processed"
        )

    if update.status == ExchangeStatus.ACCEPTED:
        updated = repository.accept_request(
            request_id=request_id,
            book_id=existing["requested_book_id"]
        )
    else:
        updated = repository.update_status(
            request_id=request_id,
            status=update.status.value
        )

    if updated is None:
        raise HTTPException(
            status_code=409,
            detail="Exchange request could not be updated"
        )

    return updated