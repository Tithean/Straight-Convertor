from fastapi import APIRouter, File, Form, Request, UploadFile
from starlette.concurrency import run_in_threadpool
from starlette.responses import FileResponse

from app.converters.registry import CONVERSIONS
from app.services.conversion_service import ConversionService
from app.utils.temporary_files import remove_workspace

router = APIRouter(prefix="/api")


class TemporaryFileResponse(FileResponse):
    def __init__(self, *args, workspace, **kwargs):
        super().__init__(*args, **kwargs)
        self.workspace = workspace

    async def __call__(self, scope, receive, send):
        try:
            await super().__call__(scope, receive, send)
        finally:
            # A finally block also runs when the client disconnects during download.
            await run_in_threadpool(remove_workspace, self.workspace)


@router.get("/health")
def health(request: Request):
    office_available = bool(request.app.state.settings.find_libreoffice())
    return {"status": "ok", "engines": {"pdf": True, "office": office_available}}


@router.get("/formats")
def formats(request: Request):
    settings = request.app.state.settings
    office_available = bool(settings.find_libreoffice())
    return {
        "max_upload_bytes": settings.max_upload_bytes,
        "max_pdf_pages": settings.max_pdf_pages,
        "timeout_seconds": settings.conversion_timeout_seconds,
        "conversions": [
            {
                "source": item.source,
                "target": item.target,
                "label": item.label,
                "description": item.description,
                "note": item.note,
                "available": not item.requires_office or office_available,
            }
            for item in CONVERSIONS
        ],
    }


@router.post(
    "/convert",
    response_class=FileResponse,
    responses={
        400: {"description": "Invalid file"},
        413: {"description": "File too large"},
        422: {"description": "Conversion failed"},
        503: {"description": "Engine unavailable or busy"},
        504: {"description": "Conversion timed out"},
    },
)
def convert(request: Request, file: UploadFile = File(...), target: str = Form(...)):
    service: ConversionService = request.app.state.conversion_service
    try:
        result = service.convert(file, target.strip().lower())
        return TemporaryFileResponse(
            result.path,
            filename=result.filename,
            media_type=result.media_type,
            workspace=result.workspace,
            headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
        )
    finally:
        file.file.close()
