
from uuid import uuid4


class BookRepository:
    def __init__(self):
        self.books = {}

    def get_all(self):
        return list(self.books.values())

    def get_by_id(self, book_id: str):
        return self.books.get(book_id)

    def create(self, book):
        book_data = book.model_dump()

        book_id = str(uuid4())

        book_data["book_id"] = book_id
        book_data["status"] = "AVAILABLE"

        self.books[book_id] = book_data

        return book_data

    def update(self, book_id: str, book):
        if book_id not in self.books:
            return None

        update_data = book.model_dump(exclude_unset=True)

        self.books[book_id].update(update_data)

        return self.books[book_id]

    def delete(self, book_id: str):
        if book_id not in self.books:
            return False

        del self.books[book_id]
        return True


book_repository = BookRepository()