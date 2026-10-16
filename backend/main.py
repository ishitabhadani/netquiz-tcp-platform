from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from backend.api.routes import router as api_router
from backend.config import FASTAPI_HOST, FASTAPI_PORT

app = FastAPI(
    title="NetQuiz API",
    description="Application & API bridge layer for NetQuiz - Multi-User TCP Quiz Platform",
    version="1.0.0"
)

# Enable CORS for frontend communication (React dev server on port 5173 or other origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes under /api
app.include_router(api_router, prefix="/api")

@app.get("/")
def root():
    return {
        "project": "NetQuiz — Multi-User TCP Quiz Platform",
        "role": "FastAPI Application Bridge Layer",
        "health_check": "/api/health",
        "docs": "/docs"
    }

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host=FASTAPI_HOST, port=FASTAPI_PORT, reload=True)
