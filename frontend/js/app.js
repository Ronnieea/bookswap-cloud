const API_URL = "https://a6gsap9tp1.execute-api.ap-southeast-2.amazonaws.com/prod";

let allBooks = [];

const bookList = document.getElementById("bookList");
const searchInput = document.getElementById("searchInput");

async function loadBooks() {
  const message = document.getElementById("message");

  message.textContent = "正在載入書籍...";
  message.className = "text-muted mb-3";

  try {
    const response = await fetch(`${API_URL}/books`);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    allBooks = await response.json();

    message.textContent = "";
    filterBooks();

  } catch (error) {
    console.error("載入書籍失敗：", error);

    message.textContent = "無法取得書籍資料，請稍後再試。";
    message.className = "alert alert-danger";

    bookList.replaceChildren();
  }
}

function renderBooks(books) {
  bookList.replaceChildren();

  if (books.length === 0) {
    const message = document.createElement("p");
    message.className = "text-muted";
    message.textContent = "目前沒有符合條件的書籍。";
    bookList.appendChild(message);
    return;
  }

  books.forEach(book => {
    const column = document.createElement("div");
    column.className = "col-md-6 col-lg-4";

    const card = document.createElement("div");
    card.className = "card book-card";

    const body = document.createElement("div");
    body.className = "card-body";

    const title = document.createElement("h5");
    title.className = "book-title";
    title.textContent = book.title;

    const author = document.createElement("p");
    author.className = "text-muted";
    author.textContent = book.author;

    const isbn = document.createElement("p");
    isbn.className = "small";
    isbn.textContent = `ISBN：${book.isbn || "未提供"}`;

    const status = document.createElement("span");
    status.className = book.status === "AVAILABLE"
      ? "badge bg-success"
      : "badge bg-secondary";
    status.textContent = book.status === "AVAILABLE"
      ? "可交換"
      : book.status === "RESERVED"
        ? "已預約"
        : "已交換";

    
    const editBtn = document.createElement("button");
    editBtn.type = "button";
    editBtn.className = "btn btn-outline-primary btn-sm ms-2";
    editBtn.textContent = "編輯";

    editBtn.addEventListener("click", () => {
    openEditBookModal(book);
    });

    
    const deleteBtn = document.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.className = "btn btn-outline-danger btn-sm ms-2";
    deleteBtn.textContent = "刪除";

    deleteBtn.addEventListener("click", () => {
    deleteBook(book);
    });

    const exchangeBtn = document.createElement("button");
    exchangeBtn.type = "button";
    exchangeBtn.className = "btn btn-primary btn-sm ms-2";
    exchangeBtn.textContent = "申請交換";

    if (book.status !== "AVAILABLE") {
    exchangeBtn.disabled = true;
    exchangeBtn.textContent = "無法交換";
    }

    exchangeBtn.addEventListener("click", () => {
    openExchangeModal(book);
    });

    body.append(
    title,
    author,
    isbn,
    status,
    exchangeBtn,
    editBtn,
    deleteBtn
    );
    card.appendChild(body);
    column.appendChild(card);
    bookList.appendChild(column);
  });
}

function filterBooks() {
  const keyword = searchInput.value.toLowerCase().trim();

  const filtered = allBooks.filter(book =>
    [book.title, book.author, book.isbn]
      .some(value => String(value || "")
        .toLowerCase().includes(keyword))
  );

  renderBooks(filtered);
}

searchInput.addEventListener("input", filterBooks);

loadBooks();

const addBookForm = document.getElementById("addBookForm");
const lookupIsbnBtn = document.getElementById("lookupIsbnBtn");
const saveBookBtn = document.getElementById("saveBookBtn");
const formMessage = document.getElementById("formMessage");

const bookIsbn = document.getElementById("bookIsbn");
const bookTitle = document.getElementById("bookTitle");
const bookAuthor = document.getElementById("bookAuthor");

// ISBN 自動查詢
lookupIsbnBtn.addEventListener("click", async () => {
  const isbn = bookIsbn.value.trim().replace(/-/g, "");

  if (!/^(?:\d{9}[\dXx]|\d{13})$/.test(isbn)) {
    formMessage.textContent = "請輸入有效格式的 ISBN-10 或 ISBN-13。";
    formMessage.className = "text-danger small mb-2";
    return;
  }

  lookupIsbnBtn.disabled = true;
  formMessage.textContent = "正在查詢書籍資訊...";
  formMessage.className = "text-muted small mb-2";

  try {
    const response = await fetch(
      `${API_URL}/external/books?isbn=${encodeURIComponent(isbn)}`
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const book = await response.json();

    bookTitle.value = book.title || "";
    bookAuthor.value = (book.authors || []).join(", ");
    bookIsbn.value = isbn;

    formMessage.textContent =
      `查詢成功！資料來源：${book.source || "unknown"}`;
    formMessage.className = "text-success small mb-2";

  } catch (error) {
    console.error("ISBN 查詢失敗：", error);
    formMessage.textContent =
      "無法自動取得書籍資訊，請手動填寫書名與作者。";
    formMessage.className = "text-warning small mb-2";

  } finally {
    lookupIsbnBtn.disabled = false;
  }
});

// 新增書籍
addBookForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const newBook = {
    title: bookTitle.value.trim(),
    author: bookAuthor.value.trim(),
    isbn: bookIsbn.value.trim().replace(/-/g, "") || null
  };

  saveBookBtn.disabled = true;
  formMessage.textContent = "正在儲存書籍...";
  formMessage.className = "text-muted small mb-2";

  try {
    const response = await fetch(`${API_URL}/books`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(newBook)
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    // 新增成功，關閉視窗
    const modalElement = document.getElementById("addBookModal");
    const modal = bootstrap.Modal.getInstance(modalElement);
    modal.hide();

    addBookForm.reset();
    formMessage.textContent = "";

    // 重新取得 DynamoDB 書籍列表
    await loadBooks();

  } catch (error) {
    console.error("新增書籍失敗：", error);
    formMessage.textContent = "新增失敗，請稍後再試。";
    formMessage.className = "text-danger small mb-2";

  } finally {
    saveBookBtn.disabled = false;
  }
});


// 編輯書籍
const editBookForm = document.getElementById("editBookForm");
const editBookTitle = document.getElementById("editBookTitle");
const editBookAuthor = document.getElementById("editBookAuthor");
const editBookIsbn = document.getElementById("editBookIsbn");
const editFormMessage = document.getElementById("editFormMessage");
const updateBookBtn = document.getElementById("updateBookBtn");

let editingBookId = null;

// 開啟編輯視窗
function openEditBookModal(book) {
  editingBookId = book.book_id;

  editBookTitle.value = book.title || "";
  editBookAuthor.value = book.author || "";
  editBookIsbn.value = book.isbn || "";

  editFormMessage.textContent = "";

  const modalElement = document.getElementById("editBookModal");
  const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
  modal.show();
}

// 儲存編輯內容
editBookForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (!editingBookId) {
    editFormMessage.textContent = "找不到書籍 ID，無法修改。";
    editFormMessage.className = "text-danger small mb-2";
    return;
  }

  const updatedBook = {
    title: editBookTitle.value.trim(),
    author: editBookAuthor.value.trim(),
    isbn: editBookIsbn.value.trim().replace(/-/g, "") || null
  };

  updateBookBtn.disabled = true;
  editFormMessage.textContent = "正在更新書籍...";
  editFormMessage.className = "text-muted small mb-2";

  try {
    const response = await fetch(
      `${API_URL}/books/${encodeURIComponent(editingBookId)}`,
      {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(updatedBook)
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const modalElement = document.getElementById("editBookModal");
    bootstrap.Modal.getInstance(modalElement).hide();

    editingBookId = null;

    await loadBooks();

  } catch (error) {
    console.error("更新書籍失敗：", error);
    editFormMessage.textContent = "更新失敗，請稍後再試。";
    editFormMessage.className = "text-danger small mb-2";

  } finally {
    updateBookBtn.disabled = false;
  }
});


// 刪除書籍
async function deleteBook(book) {
  if (!book.book_id) {
    alert("找不到書籍 ID，無法刪除。");
    return;
  }

  const confirmed = window.confirm(
    `確定要刪除「${book.title}」嗎？\n\n此操作無法復原。`
  );

  if (!confirmed) {
    return;
  }

  try {
    const response = await fetch(
      `${API_URL}/books/${encodeURIComponent(book.book_id)}`,
      {
        method: "DELETE"
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    await loadBooks();

  } catch (error) {
    console.error("刪除書籍失敗：", error);
    alert("刪除失敗，請稍後再試。");
  }
}


// 交換申請
const exchangeForm = document.getElementById("exchangeForm");
const exchangeBookTitle = document.getElementById("exchangeBookTitle");
const requesterName = document.getElementById("requesterName");
const exchangeMessage = document.getElementById("exchangeMessage");
const exchangeFormMessage = document.getElementById("exchangeFormMessage");
const submitExchangeBtn = document.getElementById("submitExchangeBtn");

let selectedExchangeBookId = null;

// 開啟交換申請視窗
function openExchangeModal(book) {
  if (book.status !== "AVAILABLE") {
    return;
  }

  selectedExchangeBookId = book.book_id;
  exchangeBookTitle.textContent = book.title;

  exchangeForm.reset();
  exchangeFormMessage.textContent = "";

  const modalElement = document.getElementById("exchangeModal");
  const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
  modal.show();
}

// 送出交換申請
exchangeForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (!selectedExchangeBookId) {
    exchangeFormMessage.textContent = "找不到書籍 ID。";
    exchangeFormMessage.className = "text-danger small mb-2";
    return;
  }

  const requestData = {
    requested_book_id: selectedExchangeBookId,
    requester_name: requesterName.value.trim(),
    message: exchangeMessage.value.trim()
  };

  if (!requestData.requester_name) {
    exchangeFormMessage.textContent = "請輸入申請人姓名。";
    exchangeFormMessage.className = "text-danger small mb-2";
    return;
  }

  submitExchangeBtn.disabled = true;
  exchangeFormMessage.textContent = "正在送出交換申請...";
  exchangeFormMessage.className = "text-muted small mb-2";

  try {
    const response = await fetch(`${API_URL}/exchange-requests`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(requestData)
    });

    if (!response.ok) {
      if (response.status === 409) {
        throw new Error("這本書目前無法交換，可能已被預約。");
      }
      throw new Error(`送出失敗（HTTP ${response.status}）`);
    }

    const result = await response.json();

    const modalElement = document.getElementById("exchangeModal");
    bootstrap.Modal.getInstance(modalElement).hide();

    selectedExchangeBookId = null;
    exchangeForm.reset();

    await loadBooks();

    const message = document.getElementById("message");
    message.textContent = `交換申請已送出！申請編號：${result.request_id}`;
    message.className = "alert alert-success mb-3";

  } catch (error) {
    console.error("交換申請失敗：", error);
    exchangeFormMessage.textContent = error.message;
    exchangeFormMessage.className = "text-danger small mb-2";

  } finally {
    submitExchangeBtn.disabled = false;
  }
});


// =====================================
// 交換申請列表
// =====================================

const booksTab = document.getElementById("booksTab");
const requestsTab = document.getElementById("requestsTab");

const booksSection = document.getElementById("booksSection");
const requestsSection = document.getElementById("requestsSection");

const requestsList = document.getElementById("requestsList");
const requestsMessage = document.getElementById("requestsMessage");
const refreshRequestsBtn = document.getElementById("refreshRequestsBtn");

// 切換至探索書籍
booksTab.addEventListener("click", () => {
  booksSection.classList.remove("d-none");
  requestsSection.classList.add("d-none");

  booksTab.classList.add("active");
  requestsTab.classList.remove("active");

  loadBooks();
});

// 切換至交換申請列表
requestsTab.addEventListener("click", () => {
  booksSection.classList.add("d-none");
  requestsSection.classList.remove("d-none");

  booksTab.classList.remove("active");
  requestsTab.classList.add("active");

  loadExchangeRequests();
});

// 重新整理
refreshRequestsBtn.addEventListener("click", loadExchangeRequests);

// 取得交換申請資料
async function loadExchangeRequests() {
  requestsMessage.textContent = "正在載入交換申請...";
  requestsMessage.className = "text-muted mb-3";
  requestsList.replaceChildren();

  refreshRequestsBtn.disabled = true;

  try {
    const [requestsResponse, booksResponse] = await Promise.all([
      fetch(`${API_URL}/exchange-requests`),
      fetch(`${API_URL}/books`)
    ]);

    if (!requestsResponse.ok || !booksResponse.ok) {
      throw new Error("無法取得交換申請資料");
    }

    const requests = await requestsResponse.json();
    const books = await booksResponse.json();

    const booksById = new Map(
      books.map(book => [book.book_id, book])
    );

    requestsMessage.textContent = "";

    renderExchangeRequests(requests, booksById);

  } catch (error) {
    console.error("載入交換申請失敗：", error);

    requestsMessage.textContent =
      "無法取得交換申請，請稍後再試。";
    requestsMessage.className = "alert alert-danger";

  } finally {
    refreshRequestsBtn.disabled = false;
  }
}

// 顯示交換申請卡片
function renderExchangeRequests(requests, booksById) {
  requestsList.replaceChildren();

  if (requests.length === 0) {
    const empty = document.createElement("p");
    empty.className = "text-muted";
    empty.textContent = "目前沒有交換申請紀錄。";
    requestsList.appendChild(empty);
    return;
  }

  const statusConfig = {
    PENDING: {
      text: "待處理",
      className: "bg-warning text-dark"
    },
    ACCEPTED: {
      text: "已接受",
      className: "bg-success"
    },
    REJECTED: {
      text: "已拒絕",
      className: "bg-danger"
    }
  };

  requests.forEach(request => {
    const book = booksById.get(request.requested_book_id);
    const bookTitle = book?.title || "書籍已不存在";

    const status = statusConfig[request.status] || {
      text: request.status,
      className: "bg-secondary"
    };

    const column = document.createElement("div");
    column.className = "col-md-6 col-lg-4";

    const card = document.createElement("div");
    card.className = "card h-100 shadow-sm";

    const body = document.createElement("div");
    body.className = "card-body";

    const title = document.createElement("h5");
    title.className = "card-title fw-bold";
    title.textContent = bookTitle;

    const badge = document.createElement("span");
    badge.className = `badge ${status.className} mb-3`;
    badge.textContent = status.text;

    const name = document.createElement("p");
    name.className = "mb-2";
    name.textContent = `申請人：${request.requester_name}`;

    const message = document.createElement("p");
    message.className = "text-muted small mb-2";
    message.textContent = request.message
      ? `留言：${request.message}`
      : "留言：無";

    const date = document.createElement("p");
    date.className = "text-muted small mb-0";

    const parsedDate = new Date(request.created_at);
    date.textContent = `申請時間：${
      Number.isNaN(parsedDate.getTime())
        ? "未知"
        : parsedDate.toLocaleString("zh-TW", {
            timeZone: "Asia/Taipei"
          })
    }`;

    body.append(title, badge, name, message, date);
    card.appendChild(body);
    column.appendChild(card);
    requestsList.appendChild(column);
  });
}