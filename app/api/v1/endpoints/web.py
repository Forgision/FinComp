from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os

web_router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.getcwd(), "templates"))

@web_router.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "version": "1.0.0"})
