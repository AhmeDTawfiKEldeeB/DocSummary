from fastapi import APIRouter
from src.api.schemas.base import StandardResponse
from src.config.settings import settings

router = APIRouter(
    prefix=settings.api_prefix, tags=["Base"]
)


@router.get("/", response_model=StandardResponse[dict])
async def root() -> StandardResponse[dict]:
    """
    Root endpoint for the API.
    Returns a standard response indicating that the API is running.
    """
    return StandardResponse(
        status="success",
        message=f"{settings.app_name} API is running",
        data={
            "app_name": settings.app_name,
            "version": settings.api_version,
            "environment": settings.app_env,
        },
    )