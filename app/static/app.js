const TOKEN_KEY = "bl_token";

class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

const $ = (selector) => document.querySelector(selector);

function getToken() {
  return sessionStorage.getItem(TOKEN_KEY);
}

function setToken(token) {
  sessionStorage.setItem(TOKEN_KEY, token);
}

function clearToken() {
  sessionStorage.removeItem(TOKEN_KEY);
}

function showMessage(text, isError = false) {
  const el = $("#message");
  el.textContent = text;
  el.dataset.kind = isError ? "error" : "info";
}

const reportError = (err) => showMessage(err.message, true);

function errorText(detail, status) {
  // Our errors use a string detail. FastAPI validation errors (422) use a list.
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((item) => item.msg).join("; ");
  return `Request failed (${status})`;
}

async function api(method, path, { body, query, auth = true } = {}) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";

  if (auth) {
    const token = getToken();
    if (!token) {
      window.location.href = "/ui/login";
      throw new ApiError(401, "Please log in first.");
    }
    headers["Authorization"] = `Bearer ${token}`;
  }

  const url = new URL(path, window.location.origin);
  for (const [key, value] of Object.entries(query || {})) {
    if (value !== null && value !== undefined && value !== "") {
      url.searchParams.set(key, value);
    }
  }

  const resp = await fetch(url, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (resp.status === 401 && auth) {
    clearToken();
    window.location.href = "/ui/login";
  }

  const text = await resp.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = null; // e.g. a plain-text 500 page
  }

  if (!resp.ok) {
    throw new ApiError(resp.status, errorText(data?.detail, resp.status));
  }
  return data;
}

function td(text) {
  const cell = document.createElement("td");
  cell.textContent = text ?? "";
  return cell;
}

function formatDate(value) {
  return value ? value.replace("T", " ").slice(0, 16) : "-";
}

/* ---------- Login and register ---------- */

function initLogin() {
  const credentials = () => ({
    username: $("#username").value.trim(),
    password: $("#password").value,
  });

  async function logIn() {
    const data = await api("POST", "/auth/login", { body: credentials(), auth: false });
    setToken(data.access_token);
    window.location.href = "/ui/books";
  }

  $("#login-form").addEventListener("submit", (event) => {
    event.preventDefault();
    logIn().catch(reportError);
  });

  $("#register-button").addEventListener("click", async () => {
    try {
      await api("POST", "/auth/register", { body: credentials(), auth: false });
      await logIn();
    } catch (err) {
      reportError(err);
    }
  });
}

/* ---------- Books ---------- */

const bookState = { page: 1, size: 10, q: "" };

function renderBooks(items) {
  const body = $("#books-body");
  body.replaceChildren();

  if (items.length === 0) {
    const row = document.createElement("tr");
    const cell = td("No books found");
    cell.colSpan = 5;
    row.append(cell);
    body.append(row);
    return;
  }

  for (const book of items) {
    const row = document.createElement("tr");
    row.dataset.testid = "book-row";

    const action = document.createElement("td");
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = "Borrow";
    button.dataset.testid = "borrow-button";
    button.dataset.bookId = book.id;
    action.append(button);

    row.append(
      td(book.title),
      td(book.author),
      td(book.available_copies),
      td(book.total_copies),
      action,
    );
    body.append(row);
  }
}

async function loadBooks() {
  const data = await api("GET", "/books", {
    auth: false,
    query: { page: bookState.page, size: bookState.size, q: bookState.q },
  });

  renderBooks(data.items);

  const pages = Math.max(1, Math.ceil(data.total / bookState.size));
  $("#page-info").textContent = `Page ${bookState.page} of ${pages}`;
  $("#prev-page").disabled = bookState.page <= 1;
  $("#next-page").disabled = bookState.page >= pages;
}

function initBooks() {
  $("#search-form").addEventListener("submit", (event) => {
    event.preventDefault();
    bookState.q = $("#search-input").value.trim();
    bookState.page = 1;
    loadBooks().catch(reportError);
  });

  $("#prev-page").addEventListener("click", () => {
    bookState.page -= 1;
    loadBooks().catch(reportError);
  });

  $("#next-page").addEventListener("click", () => {
    bookState.page += 1;
    loadBooks().catch(reportError);

  $("#add-book-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    showMessage("");
    try {
      await api("POST", "/books", {
        body: {
          title: $("#new-title").value.trim(),
          author: $("#new-author").value.trim(),
          isbn: $("#new-isbn").value.trim(),
          total_copies: Number($("#new-copies").value),
        },
      });
      event.target.reset();
      $("#add-book-panel").open = false;
      showMessage("Book added.");
      bookState.page = 1;
      await loadBooks();
    } catch (err) {
      reportError(err);
    }
  });
  });

  // Event delegation: one listener handles every Borrow button,
  // including buttons created after each reload.
  $("#books-body").addEventListener("click", async (event) => {
    const button = event.target.closest("[data-testid='borrow-button']");
    if (!button) return;
    showMessage("");  // clear the previous result so tests see only the new one
    try {
      await api("POST", "/loans", { body: { book_id: Number(button.dataset.bookId) } });
      showMessage("Book borrowed.");
      await loadBooks();
    } catch (err) {
      reportError(err);
    }
  });

  loadBooks().catch(reportError);
}

/* ---------- My loans ---------- */

async function fetchTitles(ids) {
  const entries = await Promise.all(
    ids.map(async (id) => {
      try {
        const book = await api("GET", `/books/${id}`, { auth: false });
        return [id, book.title];
      } catch {
        return [id, `Book #${id}`];
      }
    }),
  );
  return new Map(entries);
}

function renderLoans(loans, titles) {
  const body = $("#loans-body");
  body.replaceChildren();

  if (loans.length === 0) {
    const row = document.createElement("tr");
    const cell = td("No loans");
    cell.colSpan = 5;
    row.append(cell);
    body.append(row);
    return;
  }

  for (const loan of loans) {
    const row = document.createElement("tr");
    row.dataset.testid = "loan-row";
    row.dataset.loanId = loan.id;

    const action = document.createElement("td");
    if (loan.status === "active") {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = "Return";
      button.dataset.testid = "return-button";
      button.dataset.loanId = loan.id;
      action.append(button);
    }

    row.append(
      td(titles.get(loan.book_id) ?? `Book #${loan.book_id}`),
      td(formatDate(loan.borrowed_at)),
      td(formatDate(loan.due_date)),
      td(loan.status),
      action,
    );
    body.append(row);
  }
}

async function loadLoans() {
  const status = $("#status-filter").value;
  const loans = await api("GET", "/loans/me", { query: { status } });
  const titles = await fetchTitles([...new Set(loans.map((loan) => loan.book_id))]);
  renderLoans(loans, titles);
}

function initLoans() {
  $("#status-filter").addEventListener("change", () => {
    loadLoans().catch(reportError);
  });

  $("#loans-body").addEventListener("click", async (event) => {
    const button = event.target.closest("[data-testid='return-button']");
    if (!button) return;
    showMessage("");
    try {
      await api("POST", `/loans/${button.dataset.loanId}/return`);
      showMessage("Book returned.");
      await loadLoans();
    } catch (err) {
      reportError(err);
    }
  });

  loadLoans().catch(reportError);
}

/* ---------- Shared navigation and startup ---------- */

function initChrome() {
  const logout = $("#logout");
  logout.hidden = !getToken();
  logout.addEventListener("click", () => {
    clearToken();
    window.location.href = "/ui/login";
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initChrome();
  const page = document.body.dataset.page;
  if (page === "login") initLogin();
  if (page === "books") initBooks();
  if (page === "loans") initLoans();
});