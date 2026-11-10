import json
import os
import signal
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from app.converters.registry import find_conversion
from app.core.config import Settings
from app.core.errors import ConversionError
from app.utils.file_validation import download_name, file_extension, validate_file
from app.utils.temporary_files import create_workspace, remove_workspace

@dataclass(frozen=True)
class ConversionResult:
    path: Path
    filename: str
    media_type: str
    workspace: Path


def stop_process_tree(process: subprocess.Popen) -> None:
    # Killing only the worker would leave its LibreOffice child running.
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            check=False,
        )
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    process.communicate()


class ConversionService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.slots = threading.BoundedSemaphore(settings.max_concurrent_conversions)

    def convert(self, upload: UploadFile, target: str) -> ConversionResult:
        filename = upload.filename or ""
        source_format = file_extension(filename)
        conversion = find_conversion(source_format, target)
        if not conversion:
            raise ConversionError(
                "Choose a DOCX or PPTX file for PDF, or a PDF file for PowerPoint.",
                400,
                "unsupported_conversion",
            )
        office_path = self.settings.find_libreoffice()
        if conversion.requires_office and not office_path:
            raise ConversionError(
                "Office conversion is temporarily unavailable. Please try PDF to PowerPoint or return later.",
                503,
                "engine_unavailable",
            )
        if not self.slots.acquire(blocking=False):
            raise ConversionError(
                "The converter is busy. Please try again in a moment.",
                503,
                "server_busy",
            )
        workspace = None
        try:
            workspace = create_workspace(self.settings.temporary_root)
            source = workspace / f"input.{source_format}"
            output = workspace / f"converted.{target}"
            size = 0
            with source.open("wb") as destination:
                while chunk := upload.file.read(64 * 1024):
                    size += len(chunk)
                    if size > self.settings.max_upload_bytes:
                        raise ConversionError(
                            f"Please choose a file smaller than {self.settings.max_upload_mb} MB.",
                            413,
                            "file_too_large",
                        )
                    destination.write(chunk)
            validate_file(source, source_format, self.settings.max_upload_bytes)
            command = [
                sys.executable,
                "-m",
                "app.converters.worker",
                str(source),
                str(output),
                "--max-pages",
                str(self.settings.max_pdf_pages),
            ]
            if office_path:
                command.extend(["--office-path", office_path])
            process = subprocess.Popen(
                command,
                cwd=Path(__file__).resolve().parents[2],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=os.name != "nt",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            try:
                stdout, _ = process.communicate(
                    timeout=self.settings.conversion_timeout_seconds
                )
            except subprocess.TimeoutExpired as exc:
                stop_process_tree(process)
                raise ConversionError(
                    "Conversion took too long. Try a smaller or simpler document.",
                    504,
                    "conversion_timeout",
                ) from exc
            if process.returncode:
                try:
                    error = json.loads(stdout)
                    raise ConversionError(
                        error["message"], error["status"], error["code"]
                    )
                except (json.JSONDecodeError, KeyError, TypeError):
                    raise ConversionError(
                        "This file could not be converted. Please try another file."
                    )
            if not output.is_file() or output.stat().st_size == 0:
                raise ConversionError(
                    "Conversion produced no output. Please try another file."
                )
            media_type = (
                "application/pdf"
                if target == "pdf"
                else "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            )
            return ConversionResult(
                output, download_name(filename, target), media_type, workspace
            )
        except BaseException:
            if workspace:
                remove_workspace(workspace)
            raise
        finally:
            self.slots.release()
