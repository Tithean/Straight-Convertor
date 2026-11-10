import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def settings(tmp_path):
    return Settings(
        _env_file=None, temporary_root=tmp_path / "uploads", max_upload_mb=1
    )


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def pdf_bytes():
    # A real two-page PDF exercises parsing, rendering, and PPTX packaging.
    with Image.new("RGB", (300, 200), "#3156ce") as first:
        with Image.new("RGB", (200, 300), "#d27d55") as second:
            stream = io.BytesIO()
            first.save(stream, format="PDF", save_all=True, append_images=[second])
            return stream.getvalue()
