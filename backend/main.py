"""
NetQuiz FastAPI Application Layer & API Bridge

Academic Concept:
FastAPI acts as an application bridge between the React web frontend (port 5173)
and the Python TCP socket server (port 5000).

Architectural Boundary:
- React Browser ──(HTTP REST)──> FastAPI (port 8000)
- FastAPI ──────(Direct Memory)─> TCPServer / QuizManager
- TCP Clients ───(Raw TCP)───────> TCPServer (port 5000)

FastAPI does NOT replace the TCP networking layer. It exposes network metrics,
client registries, and server-side leaderboard data to the web UI.
"""

import os
from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from backend.api.routes import router as api_router
from backend.config import FASTAPI_HOST, FASTAPI_PORT
from backend.networking.tcp_server import tcp_server_instance

logger = logging.getLogger("NetQuiz.FastAPI")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application Lifespan Context Manager.
    Manages background services across the FastAPI application lifecycle:
    1. On Startup: Ensures the Python TCP socket server is actively listening on port 5000.
    2. On Shutdown: Gracefully shuts down the TCP socket server and releases port 5000.
    """
    logger.info("[LIFESPAN] Starting NetQuiz FastAPI Application Layer...")
    
    # Ensure TCP server is running without creating duplicate instances
    if not tcp_server_instance.is_running:
        logger.info(f"[LIFESPAN] Starting background TCP socket server on {tcp_server_instance.host}:{tcp_server_instance.port}...")
        try:
            tcp_server_instance.start(run_in_background=True)
        except OSError as e:
            logger.warning(
                f"[LIFESPAN] Note: TCP server port {tcp_server_instance.port} might already be bound or restricted: {e}"
            )
        except Exception as e:
            logger.error(f"[LIFESPAN ERROR] Failed to start TCP server: {e}")
    else:
        logger.info("[LIFESPAN] TCP server is already active.")

    yield

    logger.info("[LIFESPAN] Shutting down NetQuiz FastAPI Application Layer...")
    if tcp_server_instance.is_running:
        tcp_server_instance.stop()
        logger.info("[LIFESPAN] Background TCP socket server stopped cleanly.")


app = FastAPI(
    title="NetQuiz API Bridge",
    description=(
        "HTTP REST Application Bridge for NetQuiz — Multi-User TCP Quiz Platform. "
        "Provides web endpoints for querying live TCP socket server metrics, "
        "client connection registries, question bank info, and server-side leaderboards."
    ),
    version="1.0.0",
    lifespan=lifespan
)

# Configure Cross-Origin Resource Sharing (CORS)
# Allows the local React development server (Vite on port 5173 or localhost)
# and deployed frontend URL to query API endpoints securely without browser CORS blocking.
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Allow custom deployed frontend origin via FRONTEND_URL environment variable
frontend_url_env = os.getenv("FRONTEND_URL")
if frontend_url_env:
    for url in frontend_url_env.split(","):
        clean_url = url.strip().rstrip("/")
        if clean_url and clean_url not in origins:
            origins.append(clean_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Mount all API routes under /api
app.include_router(api_router, prefix="/api")


@app.get("/", tags=["General"])
def root():
    """Welcome route providing service metadata and documentation links."""
    return {
        "project": "NetQuiz — Multi-User TCP Quiz Platform",
        "role": "FastAPI Application / UI Bridge Layer",
        "tcp_server_port": tcp_server_instance.port,
        "fastapi_port": FASTAPI_PORT,
        "endpoints": {
            "health": "/api/health",
            "tcp_server_status": "/api/server/status",
            "connected_clients": "/api/server/clients",
            "quiz_info": "/api/quiz/info",
            "leaderboard": "/api/quiz/leaderboard",
            "interactive_docs": "/docs"
        }
    }


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host=FASTAPI_HOST, port=FASTAPI_PORT, reload=True)
