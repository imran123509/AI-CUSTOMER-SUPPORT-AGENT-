"""FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, ORJSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestContextMiddleware
from app.core.redis import close_redis, get_redis
from app.ws.routes import ws_router

settings = get_settings()
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("app.startup", env=settings.app_env, version="0.1.0")
    # warm Redis pool
    await get_redis()
    yield
    await close_redis()
    logger.info("app.shutdown")


app = FastAPI(
    title="UNFYD.PIVOT API",
    description="AI Customer Support SaaS — multi-tenant FastAPI backend",
    version="0.1.0",
    default_response_class=ORJSONResponse,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ----------------------------- middleware ----------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["x-request-id"],
)
app.add_middleware(RequestContextMiddleware)


# ----------------------------- error handlers ------------------------------
@app.exception_handler(AppError)
async def _app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


# ----------------------------- health & metrics ----------------------------
@app.get("/", include_in_schema=False)
async def root():
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "env": settings.app_env,
        "docs": "/docs",
    }


@app.get("/healthz", tags=["meta"])
async def healthz():
    return {"status": "ok"}


@app.get("/readyz", tags=["meta"])
async def readyz():
    redis = await get_redis()
    pong = await redis.ping()
    return {"status": "ready", "redis": bool(pong)}


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    if not settings.prometheus_enabled:
        return Response(status_code=404)
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ----------------------------- routers -------------------------------------
app.include_router(api_router, prefix="/api/v1")
app.include_router(ws_router)
