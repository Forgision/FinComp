from fastapi import APIRouter

router = APIRouter()

@router.get("/test")
async def read_test():
    """
    Test endpoint to ensure router is working.
    """
    return {"message": "API router is working!"}
