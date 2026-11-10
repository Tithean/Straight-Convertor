from dataclasses import dataclass

from app.converters.base import Converter
from app.converters.office_to_pdf import OfficeToPdfConverter
from app.converters.pdf_to_pptx import PdfToPptxConverter


@dataclass(frozen=True)
class Conversion:
    source: str
    target: str
    label: str
    description: str
    note: str
    requires_office: bool
    converter: Converter


CONVERSIONS = (
    Conversion(
        "docx",
        "pdf",
        "Word to PDF",
        "Make your document ready to share.",
        "Fonts and complex layouts may look slightly different in the PDF.",
        True,
        OfficeToPdfConverter(),
    ),
    Conversion(
        "pptx",
        "pdf",
        "PowerPoint to PDF",
        "Turn your slides into a portable document.",
        "Slides become static PDF pages. Animations and transitions are not included.",
        True,
        OfficeToPdfConverter(),
    ),
    Conversion(
        "pdf",
        "pptx",
        "PDF to PowerPoint",
        "Bring each PDF page into a presentation.",
        "Each page becomes an image slide. Text and objects will not be individually editable.",
        False,
        PdfToPptxConverter(),
    ),
)


def find_conversion(source: str, target: str) -> Conversion | None:
    return next(
        (
            item
            for item in CONVERSIONS
            if (item.source, item.target) == (source, target)
        ),
        None,
    )
