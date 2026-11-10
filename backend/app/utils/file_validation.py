import re
import zipfile
from pathlib import Path

from app.core.errors import ConversionError


def file_extension(filename: str) -> str:
    return Path(filename.replace("\\", "/")).suffix.lower().lstrip(".")


def download_name(filename: str, target: str) -> str:
    # The original filename is display-only; it is never used as a filesystem path.
    stem = Path(filename.replace("\\", "/")).stem
    stem = re.sub(r"[^\w .()-]", "_", stem, flags=re.UNICODE).strip(" .")[:100]
    return f"{stem or 'converted'}.{target}"


def validate_file(path: Path, extension: str, max_bytes: int) -> None:
    if not path.stat().st_size:
        raise ConversionError(
            "This file is empty. Please choose another file.", 400, "empty_file"
        )
    if extension == "pdf":
        with path.open("rb") as stream:
            if not stream.read(1024).lstrip().startswith(b"%PDF-"):
                raise ConversionError(
                    "This file is not a valid PDF.", 400, "invalid_file"
                )
        return
    expected = {"docx": "word/document.xml", "pptx": "ppt/presentation.xml"}.get(
        extension
    )
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            names = {entry.filename for entry in entries}
            if (
                not expected
                or expected not in names
                or "[Content_Types].xml" not in names
            ):
                raise ConversionError(
                    "The file contents do not match its extension.", 400, "invalid_file"
                )
            # OOXML is a ZIP container. Check expanded sizes before an engine opens it.
            if (
                len(entries) > 10000
                or sum(entry.file_size for entry in entries) > max_bytes * 10
            ):
                raise ConversionError(
                    "This document expands beyond the processing limit.",
                    413,
                    "expanded_file_too_large",
                )
            if any(entry.flag_bits & 1 for entry in entries):
                raise ConversionError(
                    "Please remove password protection before uploading.",
                    400,
                    "encrypted_file",
                )
            if any(name.lower().endswith("vbaproject.bin") for name in names):
                raise ConversionError(
                    "Documents containing macros are not supported.",
                    400,
                    "unsupported_file",
                )
    except (zipfile.BadZipFile, OSError) as exc:
        raise ConversionError(
            "This Office file is damaged or password protected.", 400, "invalid_file"
        ) from exc
