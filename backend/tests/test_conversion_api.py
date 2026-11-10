import io
import zipfile

import pytest
from pptx import Presentation


def assert_clean(settings):
    assert not list(settings.temporary_root.glob("conversion-*"))


def test_real_pdf_to_pptx_returns_two_slides_and_cleans_files(
    client, settings, pdf_bytes
):
    response = client.post(
        "/api/convert",
        files={"file": ("My report.PDF", pdf_bytes, "application/pdf")},
        data={"target": "pptx"},
    )
    assert response.status_code == 200, (
        response.text[:500] if response.status_code != 200 else ""
    )
    assert (
        response.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
    assert response.headers["cache-control"] == "no-store"
    assert (
        "My%20report.pptx" in response.headers["content-disposition"]
        or "My report.pptx" in response.headers["content-disposition"]
    )
    presentation = Presentation(io.BytesIO(response.content))
    assert len(presentation.slides) == 2
    for slide in presentation.slides:
        picture = slide.shapes[0]
        assert len(slide.shapes) == 1
        assert picture.left >= 0 and picture.top >= 0
        assert picture.left + picture.width <= presentation.slide_width
        assert picture.top + picture.height <= presentation.slide_height
    assert_clean(settings)


@pytest.mark.parametrize(
    "name,contents,target,status,code",
    [
        ("empty.pdf", b"", "pptx", 400, "empty_file"),
        ("fake.pdf", b"not a pdf", "pptx", 400, "invalid_file"),
        ("broken.pdf", b"%PDF-1.4\nnot a real pdf", "pptx", 422, "conversion_failed"),
        ("notes.txt", b"hello", "pdf", 400, "unsupported_conversion"),
        ("file.pdf", b"%PDF-1.4", "docx", 400, "unsupported_conversion"),
    ],
)
def test_bad_uploads_return_useful_errors(
    client, settings, name, contents, target, status, code
):
    response = client.post(
        "/api/convert", files={"file": (name, contents)}, data={"target": target}
    )
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert_clean(settings)


def test_upload_limit_before_processing(client, settings):
    response = client.post(
        "/api/convert",
        files={
            "file": (
                "large.pdf",
                b"%PDF-" + b"x" * (settings.max_upload_bytes + 100000),
            )
        },
        data={"target": "pptx"},
    )
    assert response.status_code == 413
    assert_clean(settings)


def test_exact_file_limit_independent_of_multipart_allowance(client, settings):
    response = client.post(
        "/api/convert",
        files={"file": ("large.pdf", b"%PDF-" + b"x" * settings.max_upload_bytes)},
        data={"target": "pptx"},
    )
    assert response.status_code == 413
    assert_clean(settings)


def test_page_limit(client, settings, pdf_bytes):
    settings.max_pdf_pages = 1
    response = client.post(
        "/api/convert",
        files={"file": ("pages.pdf", pdf_bytes)},
        data={"target": "pptx"},
    )
    assert response.status_code == 422
    assert "1 pages" in response.json()["error"]["message"]
    assert_clean(settings)


def test_missing_fields(client):
    response = client.post("/api/convert", data={"target": "pdf"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_empty_request_body(client):
    response = client.post("/api/convert")
    assert response.status_code == 422


def test_unavailable_office_is_reported(client, settings, monkeypatch):
    monkeypatch.setattr(type(settings), "find_libreoffice", lambda self: None)
    response = client.get("/api/formats")
    formats = response.json()["conversions"]
    assert [item["available"] for item in formats] == [False, False, True]
    result = client.post(
        "/api/convert",
        files={"file": ("document.docx", b"fake")},
        data={"target": "pdf"},
    )
    assert result.status_code == 503
    assert_clean(settings)


def test_busy_server_rejects_without_creating_workspace(client, settings, pdf_bytes):
    service = client.app.state.conversion_service
    for _ in range(settings.max_concurrent_conversions):
        service.slots.acquire()
    try:
        response = client.post(
            "/api/convert",
            files={"file": ("sample.pdf", pdf_bytes)},
            data={"target": "pptx"},
        )
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "server_busy"
        assert_clean(settings)
    finally:
        for _ in range(settings.max_concurrent_conversions):
            service.slots.release()


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["engines"]["pdf"] is True


@pytest.mark.parametrize("extension", ["docx", "pptx"])
def test_real_office_to_pdf(client, settings, extension):
    if not settings.find_libreoffice():
        pytest.skip("LibreOffice is not installed")
    stream = io.BytesIO()
    if extension == "pptx":
        presentation = Presentation()
        slide = presentation.slides.add_slide(presentation.slide_layouts[0])
        slide.shapes.title.text = "Conversion integration test"
        presentation.save(stream)
    else:
        # Minimal valid OOXML document; avoids a production dependency solely for fixtures.
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr(
                "[Content_Types].xml",
                '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>',
            )
            archive.writestr(
                "_rels/.rels",
                '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
            )
            archive.writestr(
                "word/document.xml",
                '<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Conversion integration test</w:t></w:r></w:p></w:body></w:document>',
            )
    response = client.post(
        "/api/convert",
        files={"file": (f"sample.{extension}", stream.getvalue())},
        data={"target": "pdf"},
    )
    assert response.status_code == 200, (
        response.text[:500] if response.status_code != 200 else ""
    )
    assert response.content.startswith(b"%PDF-")
    assert_clean(settings)
