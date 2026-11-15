from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

# Only page shells live here. The data comes from the existing JSON API,
# which the browser calls with fetch(). No API route is changed.
router = APIRouter(prefix="/ui", include_in_schema=False)


def _render(request: Request, template: str, page: str) -> HTMLResponse:
    return templates.TemplateResponse(request, template, {"page": page})


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return _render(request, "login.html", "login")


@router.get("/books", response_class=HTMLResponse)
def books_page(request: Request):
    return _render(request, "books.html", "books")


@router.get("/loans", response_class=HTMLResponse)
def loans_page(request: Request):
    return _render(request, "loans.html", "loans")
    