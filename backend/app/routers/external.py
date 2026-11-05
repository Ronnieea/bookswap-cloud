import httpx
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(
    prefix="/external",
    tags=["External APIs"]
)

TIMEOUT = 10.0


async def search_open_library(client: httpx.AsyncClient, isbn: str):
    """主要來源：Open Library"""
    response = await client.get(
        f"https://openlibrary.org/isbn/{isbn}.json"
    )

    if response.status_code == 404:
        return None

    response.raise_for_status()
    data = response.json()

    # Open Library 的 authors 通常只有作者 ID，
    # 因此需要另外查詢作者姓名。
    authors = []
    author_entries = data.get("authors") or []

    # Edition 沒有作者時，嘗試從 Work 取得
    if not author_entries:
        works = data.get("works") or []

        if works:
            work_key = works[0].get("key")

            if work_key:
                try:
                    work_response = await client.get(
                        f"https://openlibrary.org{work_key}.json"
                    )
                    work_response.raise_for_status()
                    work_data = work_response.json()

                    author_entries = work_data.get("authors") or []

                except (httpx.HTTPError, ValueError):
                    pass

    # 將作者 ID 轉換成作者姓名
    for entry in author_entries[:5]:
        author_ref = entry.get("author", entry)
        author_key = author_ref.get("key")

        if not author_key:
            continue

        try:
            author_response = await client.get(
                f"https://openlibrary.org{author_key}.json"
            )
            author_response.raise_for_status()

            author_data = author_response.json()
            name = author_data.get("name")

            if name:
                authors.append(name)

        except (httpx.HTTPError, ValueError):
            continue
    
    covers = data.get("covers") or []

    thumbnail = (
        f"https://covers.openlibrary.org/b/id/{covers[0]}-M.jpg"
        if covers else None
    )

    return {
        "isbn": isbn,
        "title": data.get("title"),
        "authors": authors,
        "publisher": (
            data.get("publishers") or [None]
        )[0],
        "published_date": data.get("publish_date"),
        "description": (
            data.get("description", {}).get("value")
            if isinstance(data.get("description"), dict)
            else data.get("description")
        ),
        "thumbnail": thumbnail,
        "source": "open_library"
    }


async def search_google_books(client: httpx.AsyncClient, isbn: str):
    """備援來源：Google Books"""
    response = await client.get(
        "https://www.googleapis.com/books/v1/volumes",
        params={"q": f"isbn:{isbn}"}
    )

    response.raise_for_status()
    data = response.json()

    items = data.get("items", [])

    if not items:
        return None

    book_info = items[0].get("volumeInfo", {})

    return {
        "isbn": isbn,
        "title": book_info.get("title"),
        "authors": book_info.get("authors", []),
        "publisher": book_info.get("publisher"),
        "published_date": book_info.get("publishedDate"),
        "description": book_info.get("description"),
        "thumbnail": (
            book_info.get("imageLinks") or {}
        ).get("thumbnail"),
        "source": "google_books"
    }


@router.get("/books")
async def search_books(
    isbn: str = Query(
        min_length=10,
        max_length=13,
        pattern=r"^(?:[0-9]{9}[0-9Xx]|[0-9]{13})$"
    )
):
    # 紀錄第三方服務是否發生錯誤
    service_errors = []

    async with httpx.AsyncClient(
        timeout=TIMEOUT,
        follow_redirects=True
    ) as client:

        # 1. 優先查詢 Open Library
        try:
            book = await search_open_library(client, isbn)
            if book:
                return book

        except (httpx.HTTPError, ValueError):
            service_errors.append("Open Library")

        # 2. Open Library 找不到或發生錯誤時，使用 Google Books
        try:
            book = await search_google_books(client, isbn)
            if book:
                return book

        except (httpx.HTTPError, ValueError):
            service_errors.append("Google Books")

    # 3. 兩個來源都無法使用
    if len(service_errors) == 2:
        raise HTTPException(
            status_code=503,
            detail=(
                "Book information services are temporarily "
                "unavailable. Please enter book information manually."
            )
        )

    # 4. 有服務正常回應，但沒有找到書籍
    raise HTTPException(
        status_code=404,
        detail=(
            "Book not found. Please enter book information manually."
        )
    )