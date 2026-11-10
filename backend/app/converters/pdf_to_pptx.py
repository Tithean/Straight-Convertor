import io
import math
from contextlib import closing
from pathlib import Path

import pypdfium2 as pdfium
from pptx import Presentation
from pptx.util import Inches

from app.core.errors import ConversionError


class PdfToPptxConverter:
    def convert(
        self, source: Path, output: Path, *, office_path: str | None, max_pages: int
    ) -> None:
        try:
            document = pdfium.PdfDocument(str(source))
        except pdfium.PdfiumError as exc:
            raise ConversionError(
                "This PDF is damaged or password protected. Please upload an unlocked PDF."
            ) from exc

        with document:
            if not 1 <= len(document) <= max_pages:
                raise ConversionError(
                    f"Please use a PDF with between 1 and {max_pages} pages."
                )
            presentation = Presentation()
            with closing(document[0]) as first_page:
                first_width, first_height = first_page.get_size()
            if min(first_width, first_height) <= 0:
                raise ConversionError("This PDF has an invalid page size.")
            # PPTX has one canvas size for every slide; mixed-size PDF pages are fitted,
            # centered, and never stretched. Extreme page ratios get a standard canvas.
            ratio = first_width / first_height
            ratio = ratio if 0.15 <= ratio <= 6 else 16 / 9
            presentation.slide_width = Inches(10 if ratio >= 1 else 10 * ratio)
            presentation.slide_height = Inches(10 / ratio if ratio >= 1 else 10)
            for page_index in range(len(document)):
                with closing(document[page_index]) as page:
                    width, height = page.get_size()
                    if min(width, height) <= 0 or not all(
                        map(math.isfinite, (width, height))
                    ):
                        raise ConversionError("This PDF has an invalid page size.")
                    # Bound bitmap dimensions so a small PDF with huge pages cannot exhaust RAM.
                    scale = min(2.0, 2400 / max(width, height))
                    with closing(page.render(scale=scale)) as bitmap:
                        with bitmap.to_pil() as rendered:
                            image = io.BytesIO()
                            rendered.save(image, format="PNG")
                    image.seek(0)
                    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
                    fit = min(
                        presentation.slide_width / width,
                        presentation.slide_height / height,
                    )
                    picture_width, picture_height = int(width * fit), int(height * fit)
                    slide.shapes.add_picture(
                        image,
                        (presentation.slide_width - picture_width) // 2,
                        (presentation.slide_height - picture_height) // 2,
                        width=picture_width,
                        height=picture_height,
                    )
                    image.close()
            presentation.save(str(output))
