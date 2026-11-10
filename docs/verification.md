# Verification — 2026-11-10

## Automated checks

- Backend: **22 tests passed**, including real DOCX → PDF, PPTX → PDF, and PDF → PPTX conversion.
- Frontend: **3 tests passed**.
- Production frontend build: passed, including TypeScript checks.
- Live HTTP request through Vite's `/api` proxy: returned HTTP 200 and a valid PPTX file that was reopened and checked for its slide count.
- All three conversions were reported as available by the running API.

The backend tests also cover malformed inputs, empty requests, total request and file size limits, page limits, ZIP expansion limits, saturation, timeout cleanup, and cleanup on interrupted downloads.

## Browser checks

- Inspected the page at 1366px, 390px, and 320px widths; no horizontal content overflow.
- Verified conversion navigation and engine-unavailable messaging, then confirmed the message disappeared after configuring LibreOffice.
- No browser JavaScript errors were captured during the checks.
- The in-app browser automation's file chooser did not open. Full click-to-upload/download browser automation remains unverified; real conversion and the frontend proxy were verified at HTTP level instead.

## Local runtime

The machine's registered standard Python launcher pointed to a missing executable. The existing bundled Python 3.12 runtime was used to create `backend/.venv`.

LibreOffice 26.2.7 was downloaded from the official Document Foundation source, its Windows signature was verified, and its MSI was administratively extracted into `.runtime/libreoffice`. It was not installed system-wide. The ignored `backend/.env` points to that copy. `.runtime` is intentionally excluded from source control; normal installations should use the README's LibreOffice or Docker instructions.

Docker is not installed on this machine, so the Compose deployment has not been built or run here. Conversion tests ran on Windows. Linux/container-specific runtime behavior remains a deployment verification step.

One dependency deprecation warning was emitted by Starlette's current httpx-based test client. Tests passed; no warning filters were added.
