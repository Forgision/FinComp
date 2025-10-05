from fastapi import APIRouter

core_router = APIRouter()

@core_router.get("/health")
async def health_check():
    return {"status": "ok"}