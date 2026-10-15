from fastapi import APIRouter
from src.api.schemas.base import StandardResponse

router = APIRouter(
    prefix="/api/v1", tags=["Base"]
)

@router.get("/",response_model=StandardResponse[dict])
async def root()-> StandardResponse[dict]:
    """
    Root endpoint for the API.
    Returns a standard response indicating that the API is running.
    """
    return StandardResponse(
        status="success",
        message="API is running",
        data={"message": "Welcome to the API!"}
    )