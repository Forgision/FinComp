from starlette.requests import Request
from typing import List, Tuple, Union, Optional

def flash(request: Request, message: str, category: str = "message") -> None:
    if "_flashes" not in request.session:
        request.session["_flashes"] = []
    request.session["_flashes"].append((category, message))

def get_flashed_messages(
    request: Request, with_categories: bool = False, category_filter: Optional[List[str]] = None
) -> Union[List[str], List[Tuple[str, str]]]:
    flashes = request.session.pop("_flashes", [])
    if category_filter:
        flashes = [
            (cat, msg) for cat, msg in flashes if cat in category_filter
        ]

    if not with_categories:
        return [msg for cat, msg in flashes]

    return flashes