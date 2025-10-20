from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.web.backend.api import (
    account,
    market_data,
    orders,
    telegram,
    utility
)

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="app/web/frontend/static"), name="static")

# Include API routers
app.include_router(account.router, prefix="/api/v1")
app.include_router(market_data.router, prefix="/api/v1")
app.include_router(orders.router, prefix="/api/v1")
app.include_router(telegram.router, prefix="/api/v1")
app.include_router(utility.router, prefix="/api/v1")

@app.get("/")
async def root():
    """
    Root endpoint for the OpenAlgo API.

    Returns:
        A welcome message.
    """