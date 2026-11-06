import itertools

# Shared in-memory state. Both routers import from here,
# so neither has to import the other.
books: dict[int, dict] = {}
loans: dict[int, dict] = {}

book_ids = itertools.count(1)
loan_ids = itertools.count(1)


def active_loans_for_book(book_id: int) -> list[dict]:
    return [
        loan for loan in loans.values()
        if loan["book_id"] == book_id and loan["status"] == "active"
    ]


def active_loan_count(book_id: int) -> int:
    return len(active_loans_for_book(book_id))