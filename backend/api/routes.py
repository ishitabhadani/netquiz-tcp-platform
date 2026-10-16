from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def get_health():
    """
    Health check endpoint for the NetQuiz FastAPI application layer.
    Allows frontend to verify API connectivity.
    """
    return {
        "status": "ok",
        "service": "NetQuiz Backend"
    }
