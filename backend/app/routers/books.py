
from fastapi import APIRouter, HTTPException

from app.schemas.book import BookCreate, BookUpdate
from app.repositories.factory import get_book_repository


router = APIRouter(prefix="/books", tags=["Books"])


@router.get("")
def get_books():
    book_repository = get_book_repository()
    return book_repository.get_all()


@router.post("", status_code=201)
def create_book(book: BookCreate):
    book_repository = get_book_repository()
    return book_repository.create(book)


@router.get("/{book_id}")
def get_book(book_id: str):
    book_repository = get_book_repository()
    book = book_repository.get_by_id(book_id)

    if book is None:
        raise HTTPException(
            status_code=404,
            detail="Book not found"
        )

    return book


@router.patch("/{book_id}")
def update_book(book_id: str, book: BookUpdate):
    book_repository = get_book_repository()
    updated_book = book_repository.update(book_id, book)

    if updated_book is None:
        raise HTTPException(
            status_code=404,
            detail="Book not found"
        )

    return updated_book


@router.delete("/{book_id}")
def delete_book(book_id: str):
    book_repository = get_book_repository()
    deleted = book_repository.delete(book_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Book not found"
        )

    return {"message": "Book deleted successfully"}