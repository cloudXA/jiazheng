import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import router
from app.config import get_settings
from app.database import close_database, create_schema

settings = get_settings()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings.validate_runtime()
    if settings.auto_create_tables:
        await create_schema()
    yield
    await close_database()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=settings.cors_origin_list != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


def error_body(message: str, *, code: int = 1) -> dict[str, Any]:
    return {"code": code, "data": None, "message": message}


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, error: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content=error_body(str(error.detail), code=error.status_code),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request,
    error: RequestValidationError,
) -> JSONResponse:
    first_error = error.errors()[0] if error.errors() else {}
    message = str(first_error.get("msg") or "请求参数不正确")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_body(
            message,
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        ),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, error: Exception) -> JSONResponse:
    logging.getLogger(__name__).exception(
        "Unhandled server error. error_type=%s",
        type(error).__name__,
    )
    return JSONResponse(
        status_code=500,
        content=error_body("服务暂时不可用，请稍后重试", code=500),
    )
