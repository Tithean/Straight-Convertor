import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from app.api.routes.conversions import router
from app.core.config import Settings
from app.core.errors import ConversionError
from app.services.conversion_service import ConversionService
from app.utils.limited_body import LimitedBodyMiddleware
from app.utils.temporary_files import remove_stale_workspaces


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        remove_stale_workspaces(settings.temporary_root)
        if not settings.find_libreoffice():
            logging.getLogger(__name__).warning(
                "LibreOffice not found: DOCX/PPTX to PDF disabled. Install LibreOffice or set LIBREOFFICE_PATH."
            )
        yield

    app = FastAPI(title="Straight conversion API", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.conversion_service = ConversionService(settings)
    # Allow a little room for multipart headers above the actual file limit.
    app.add_middleware(
        LimitedBodyMiddleware, max_bytes=settings.max_upload_bytes + 64 * 1024
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        expose_headers=["Content-Disposition"],
    )

    @app.exception_handler(ConversionError)
    async def conversion_error(request: Request, exc: ConversionError):
        return JSONResponse(
            {"error": {"code": exc.code, "message": exc.message}},
            status_code=exc.status_code,
            headers={"Cache-Control": "no-store"},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse(
            {
                "error": {
                    "code": "invalid_request",
                    "message": "Please provide one file and an output format.",
                }
            },
            status_code=422,
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return JSONResponse(
            {"error": {"code": "invalid_request", "message": str(exc.detail)}},
            status_code=exc.status_code,
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        logging.getLogger(__name__).error(
            "Unexpected conversion error (%s)", type(exc).__name__
        )
        return JSONResponse(
            {
                "error": {
                    "code": "internal_error",
                    "message": "Something went wrong. Please try again.",
                }
            },
            status_code=500,
        )

    app.include_router(router)
    return app


app = create_app()
