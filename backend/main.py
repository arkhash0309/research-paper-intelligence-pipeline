"""
main.py — FastAPI application entry point for the Research Pipeline backend.

Run with:
    uvicorn backend.main:app --reload --port 8000
or from within the backend/ directory:
    uvicorn main:app --reload --port 8000

CORS is configured to allow the Vite dev server on http://localhost:5173.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from routers.research import router as research_router

# Load .env from the backend directory
_env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=_env_path)

# Also load the MCP server .env so API keys are available when the backend
# spawns the MCP subprocess (the subprocess inherits this process's env)
_mcp_env_path = Path(__file__).resolve().parent.parent / "mcp_server" / ".env"
load_dotenv(dotenv_path=_mcp_env_path, override=False)

app = FastAPI(
    title="Research Paper Intelligence Pipeline",
    description="API for searching, analysing, and synthesising academic literature.",
    version="1.0.0",
)

# Allow the Vite frontend dev server and any configured origins
_cors_origins_raw = os.environ.get("CORS_ORIGINS", "http://localhost:5173")
cors_origins: list[str] = [o.strip() for o in _cors_origins_raw.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("research-pipeline")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return unexpected errors as JSON so the frontend can show a readable message."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Unexpected server error: {type(exc).__name__}: {exc}"},
    )


# Mount the research router — all endpoints are prefixed with /api/research
app.include_router(research_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Simple health check endpoint for monitoring and CI."""
    return {"status": "ok", "service": "research-pipeline-backend"}
