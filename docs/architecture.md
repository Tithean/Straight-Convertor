# Architecture and maintenance guide

## The request lifecycle

1. The browser loads `/api/formats`. The backend registry is the source of truth for supported pairs, availability, and limits.
2. A selected file is checked for size and extension in React. This is immediate UX feedback; the backend repeats authoritative validation.
3. `POST /api/convert` receives multipart data. `LimitedBodyMiddleware` bounds total body size before multipart parsing, including requests without `Content-Length`. It spools to a temporary file instead of holding large bodies in memory.
4. The route calls `ConversionService` in FastAPI's thread pool. Synchronous file and subprocess operations therefore do not block the async event loop.
5. The service acquires a bounded conversion slot. When all slots are occupied it returns an actionable `503` instead of creating an unbounded queue.
6. The service creates a random, isolated workspace, writes `input.<extension>`, and checks the file signature/Office ZIP structure. User filenames never become server paths.
7. A fresh Python subprocess invokes the chosen adapter. PDFium isn't thread-safe, so this also isolates concurrent PDF rendering. LibreOffice gets its own user profile with macros disabled.
8. The service waits with a deadline. On timeout it terminates the process tree, including LibreOffice children. Normal output is returned as a file response; errors are converted into a consistent JSON shape.
9. `TemporaryFileResponse` streams the result and removes the workspace in `finally`, including send failures. Conversion failures also clean up in `finally`/exception handling. The upload spool is closed by the route/framework.

There is no database: the HTTP request owns the job. Only the frontend keeps transient UI state and a browser object URL for the download.

## Why the layers exist

**Route:** HTTP concerns only—multipart input, status codes, and binary response.

**Service:** Shared workflow—limits, validation, process management, naming, and cleanup. Conversion adapters don't need to repeat this.

**Converter:** One job: read a file and write the requested output. It raises `ConversionError` for expected failures. It does not know about HTTP, React, or databases.

**Registry:** Metadata plus the adapter. It keeps the UI and worker aligned rather than duplicating a format matrix in the frontend.

**Frontend feature:** API calls, state transitions, types, and related components live together. Shared page layout stays in `app` and CSS in `styles`.

## Add a conversion

1. Implement a class under `backend/app/converters/` matching `Converter.convert` in `base.py`.
2. Register a source/target pair and understandable limitation note in `registry.py`.
3. Add signature/content validation for any new input format in `utils/file_validation.py`.
4. Update the frontend `Format` union, accepted upload extensions/help text, and any labels for a new format. Existing input/output types are already driven by `/api/formats`.
5. Add a small real conversion fixture test that opens/verifies the output, and a failure case specific to that adapter.
6. Install any native dependencies in `backend/Dockerfile` and document fidelity limitations.

Do not silently offer a format that merely changes a file extension. Do not promise editable reconstruction for image-based results.

## State and UX

`idle → uploading → converting → ready | error`

Upload progress comes from `XMLHttpRequest.upload`; conversion itself uses an indeterminate indicator because the engines don't provide reliable progress. The user can retry failures with the same selection or remove the file. Selecting a file automatically chooses its compatible conversion. A new selection or unmount revokes the old download object URL to release browser memory.

During processing, switching conversions/removing files is disabled. The initial version has no cancel endpoint: aborting a network request is not a reliable guarantee that the backend has stopped processing.

## Limits and tradeoffs

- File and total request size, Office expanded ZIP size, PDF page count, render dimensions, conversion duration, and concurrent jobs are bounded.
- Font availability affects Office layout. Install appropriately licensed fonts on the server when visual matching matters.
- Each PDF page is rasterized at up to 144 DPI, bounded to a 2400-pixel longest edge. One shared PPTX canvas means mixed-size pages may have margins.
- Two conversions at a time is a per-process cap, not a global distributed limit. Run a single API worker for the initial deployment.
- Process isolation enables timeouts but is not a security boundary against arbitrary malicious documents. The container limits privileges/resources; public deployments also need network/ingress controls.
- Temporary cleanup is immediate on normal completion. Crash leftovers are swept on startup only after 24 hours, so an immediate restart does not guarantee instant deletion of every stale folder.

## Useful references

- [FastAPI file uploads](https://fastapi.tiangolo.com/tutorial/request-files/)
- [LibreOffice command-line PDF export](https://help.libreoffice.org/latest/en-US/text/shared/guide/pdf_params.html)
- [PDFium Python API and thread-safety notes](https://pypdfium2.readthedocs.io/en/stable/python_api.html)
- [python-pptx](https://python-pptx.readthedocs.io/en/latest/user/quickstart.html)
