"""One disposable process per conversion: PDFium is not thread-safe."""

import argparse
import json
from pathlib import Path

from app.converters.registry import find_conversion
from app.core.errors import ConversionError


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--office-path")
    parser.add_argument("--max-pages", type=int, required=True)
    args = parser.parse_args()
    try:
        conversion = find_conversion(args.source.suffix[1:], args.output.suffix[1:])
        if not conversion:
            raise ConversionError("This conversion is not supported.")
        conversion.converter.convert(
            args.source,
            args.output,
            office_path=args.office_path,
            max_pages=args.max_pages,
        )
    except ConversionError as exc:
        print(
            json.dumps(
                {"message": exc.message, "code": exc.code, "status": exc.status_code}
            )
        )
        raise SystemExit(1)
    except Exception:
        # Do not expose parser internals or uploaded document contents in HTTP errors/logs.
        print(
            json.dumps(
                {
                    "message": "This file could not be converted. Check that it opens correctly and try again.",
                    "code": "conversion_failed",
                    "status": 422,
                }
            )
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
