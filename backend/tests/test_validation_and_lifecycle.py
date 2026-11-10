import asyncio
import io
import subprocess
import zipfile

import pytest
from fastapi import UploadFile

from app.api.routes.conversions import TemporaryFileResponse
from app.core.errors import ConversionError
from app.services.conversion_service import ConversionService
from app.utils.file_validation import download_name, validate_file
from app.utils.limited_body import LimitedBodyMiddleware


def test_office_zip_bomb_is_rejected(tmp_path):
    path = tmp_path / "large.docx"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "types")
        archive.writestr("word/document.xml", "x" * 10001)
    with pytest.raises(ConversionError, match="expands"):
        validate_file(path, "docx", max_bytes=1000)


def test_disguised_office_document_is_rejected(tmp_path):
    path = tmp_path / "fake.docx"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("readme.txt", "not an Office document")
    with pytest.raises(ConversionError, match="contents"):
        validate_file(path, "docx", max_bytes=1000)


def test_download_filename_drops_path_and_controls():
    assert download_name("../../private/report.docx", "pdf") == "report.pdf"
    assert download_name("C:\\users\\report.docx", "pdf") == "report.pdf"
    assert "\n" not in download_name("a\nb.pdf", "pptx")


def test_timeout_kills_worker_and_cleans_workspace(settings, pdf_bytes, monkeypatch):
    killed = []

    class StalledProcess:
        def communicate(self, timeout=None):
            raise subprocess.TimeoutExpired("worker", timeout)

    monkeypatch.setattr(
        "app.services.conversion_service.subprocess.Popen",
        lambda *a, **kw: StalledProcess(),
    )
    monkeypatch.setattr(
        "app.services.conversion_service.stop_process_tree",
        lambda process: killed.append(process),
    )
    service = ConversionService(settings)
    upload = UploadFile(io.BytesIO(pdf_bytes), filename="sample.pdf")
    with pytest.raises(ConversionError) as error:
        service.convert(upload, "pptx")
    assert error.value.status_code == 504
    assert len(killed) == 1
    assert not list(settings.temporary_root.glob("conversion-*"))
    assert service.slots.acquire(blocking=False)
    service.slots.release()


def test_cleanup_when_download_disconnects(tmp_path):
    workspace = tmp_path / "conversion-test"
    workspace.mkdir()
    output = workspace / "result.pdf"
    output.write_bytes(b"%PDF-test")
    response = TemporaryFileResponse(output, workspace=workspace)

    async def send(message):
        raise OSError("client disconnected")

    async def receive():
        return {"type": "http.disconnect"}

    async def run():
        with pytest.raises(OSError):
            await response(
                {"type": "http", "method": "GET", "headers": [], "extensions": {}},
                receive,
                send,
            )

    asyncio.run(run())
    assert not workspace.exists()


def test_chunked_upload_limit_does_not_require_content_length():
    responses = []

    async def app(scope, receive, send):
        pytest.fail("An oversized body must not reach the multipart parser")

    chunks = iter(
        [
            {"type": "http.request", "body": b"123456", "more_body": True},
            {"type": "http.request", "body": b"78901", "more_body": False},
        ]
    )

    async def receive():
        return next(chunks)

    async def send(message):
        responses.append(message)

    asyncio.run(
        LimitedBodyMiddleware(app, 10)(
            {"type": "http", "method": "POST", "headers": []}, receive, send
        )
    )
    assert responses[0]["status"] == 413
