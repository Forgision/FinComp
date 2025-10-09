from starlette.requests import Request
from typing import List, Tuple, Union, Optional

def flash(request: Request, message: str, category: str = "primary") -> None:
    if "_messages" not in request.session:
        request.session["_messages"] = []
    request.session["_messages"].append((category, message))

def get_flashed_messages(
    request: Request, with_categories: bool = False, category: Optional[List[str]] = None
) -> Union[List[str], List[Tuple[str, str]]]:
    messages = request.session.pop("_messages", [])
    if category:
        messages = [
            (cat, msg) for cat, msg in messages if cat in category
        ]

    if not with_categories:
        return [msg for cat, msg in messages]

    return messages