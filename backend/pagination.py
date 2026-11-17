"""Reglas compartidas para paginación administrativa segura."""
from dataclasses import dataclass


class PaginationError(ValueError):
    def __init__(self, field, message):
        super().__init__(message)
        self.field = field


@dataclass(frozen=True)
class Page:
    page: int
    page_size: int
    sort: str
    direction: str


def parse_page(args, allowed_sort, default_sort="id", reject_oversized=False):
    try:
        page = max(1, int(args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        size = int(args.get("page_size", args.get("per_page", 10)))
    except (TypeError, ValueError):
        size = 10
    if reject_oversized and size > 50:
        raise PaginationError("page_size", "El tamaño máximo permitido es 50.")
    if size not in (10, 25, 50):
        size = 10 if size < 10 else 50
    sort = args.get("sort", default_sort)
    if sort not in allowed_sort:
        raise ValueError("columna de orden no permitida")
    direction = str(args.get("direction", "asc")).lower()
    if direction not in ("asc", "desc"):
        raise ValueError("dirección no permitida")
    return Page(page, size, sort, direction)


def page_result(items, total, page, page_size):
    return {"items": items, "page": page, "page_size": page_size,
            "total": int(total), "total_pages": (int(total) + page_size - 1) // page_size}
