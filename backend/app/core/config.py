import shutil
import tempfile
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    max_upload_mb: int = Field(default=20, ge=1, le=100)
    conversion_timeout_seconds: int = Field(default=120, ge=5, le=600)
    max_concurrent_conversions: int = Field(default=2, ge=1, le=8)
    max_pdf_pages: int = Field(default=100, ge=1, le=500)
    temporary_root: Path = Path(tempfile.gettempdir()) / "straight-converter"
    libreoffice_path: str | None = None
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    def find_libreoffice(self) -> str | None:
        candidates = (
            [self.libreoffice_path]
            if self.libreoffice_path
            else [
                shutil.which("soffice"),
                shutil.which("libreoffice"),
                "C:/Program Files/LibreOffice/program/soffice.com",
                "C:/Program Files/LibreOffice/program/soffice.exe",
                "C:/Program Files (x86)/LibreOffice/program/soffice.exe",
                "/Applications/LibreOffice.app/Contents/MacOS/soffice",
            ]
        )
        return next(
            (str(Path(p).resolve()) for p in candidates if p and Path(p).is_file()),
            None,
        )
