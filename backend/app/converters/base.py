from pathlib import Path
from typing import Protocol


class Converter(Protocol):
    def convert(
        self, source: Path, output: Path, *, office_path: str | None, max_pages: int
    ) -> None:
        """Write the converted file to output or raise ConversionError."""
        ...
