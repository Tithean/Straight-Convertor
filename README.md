# Straight — a simple file converter

A React + TypeScript frontend and Python + FastAPI backend. Upload one document, convert it, and download the result. No accounts, database, cloud storage, or persistent conversion history.

This workspace already has frontend dependencies, a backend virtual environment, and a project-local LibreOffice runtime configured in the ignored `backend/.env`. To use that prepared setup, start the backend with `.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload` from `backend`, and run `npm.cmd run dev` from `frontend` in another terminal. Do not overwrite the prepared `.env` unless you want to change the LibreOffice path.

## Supported conversions

| Input | Output | Engine | What to expect |
| --- | --- | --- | --- |
| DOCX | PDF | LibreOffice Writer | Fonts and complex layouts can differ from Microsoft Word. |
| PPTX | PDF | LibreOffice Impress | Static slides; animations and transitions are not retained. |
| PDF | PPTX | PDFium + python-pptx | One image per slide. Text and objects are **not individually editable**. |

PDF pages with different dimensions are centered on a shared slide size without stretching. Password-protected files, macros, unsupported conversions, and malformed documents are rejected. Defaults: **20 MB per file**, **100 PDF pages**, **120 seconds per conversion**, **2 conversions at a time**.

## Quick start with Docker

Install Docker with Compose, then run from this directory:

```sh
docker compose up --build
```

Open **http://localhost:8080**. This builds both services and includes LibreOffice and common fonts. The first build downloads the conversion engines and may take a few minutes.

```sh
docker compose down
```

The backend runs as an unprivileged user with bounded container resources. Temporary files live in container tmpfs. Only the frontend port is published; nginx forwards `/api` to Python.

## Local development

Requirements: **Python 3.11+**, **Node.js 22.12+**, and **LibreOffice** for DOCX/PPTX to PDF. Use an official CPython installation on Windows; MSYS/MinGW Python may not support the binary wheels used by the PDF libraries.

### 1. Backend

Windows PowerShell:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

macOS / Linux:

```sh
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
cp .env.example .env
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Install LibreOffice from https://www.libreoffice.org/download/download-libreoffice/ or your OS package manager. Standard Windows/macOS paths and `PATH` are searched automatically. To override, set this in `backend/.env` and restart the backend:

```dotenv
LIBREOFFICE_PATH=C:/Program Files/LibreOffice/program/soffice.com
```

Without LibreOffice, PDF → PPTX still works. The API reports Office conversions as unavailable, and the UI disables their conversion button with a clear message.

API docs: **http://localhost:8000/docs**. Health: **http://localhost:8000/api/health**.

### 2. Frontend (a second terminal)

```sh
cd frontend
npm ci
npm run dev
```

Open **http://localhost:5173**. Vite proxies `/api` to the backend, so no frontend environment configuration is necessary. In PowerShell, use `npm.cmd` if your execution policy blocks `npm.ps1`.

For a separately hosted backend, set `VITE_API_BASE_URL` in `frontend/.env` and add the frontend origin to `CORS_ORIGINS` in `backend/.env`. Vite reads its variables at build/start time.

## Find your way around the code

```text
frontend/src/
  app/App.tsx                         Page composition and file selection
  features/conversion/
    api.ts                            HTTP requests and real upload progress
    types.ts                          Shared frontend types
    fileUtils.ts                      File selection validation and names
    useConversion.ts                  Conversion state and download URL lifecycle
    components/                       Dropzone, format selector, and status UI
  styles/global.css                   Responsive layout and visual tokens

backend/app/
  main.py                             App creation, middleware, and error handlers
  api/routes/conversions.py           Thin HTTP routes and download cleanup
  core/                               Settings and user-facing error type
  services/conversion_service.py      Validate → run worker → return result
  converters/
    base.py                           The converter interface
    registry.py                       Supported conversions and their metadata
    worker.py                         Disposable conversion process entry point
    office_to_pdf.py                   LibreOffice adapter
    pdf_to_pptx.py                     Render PDF pages and create slides
  utils/                              File validation, size limits, temporary files
```

Start reading `App.tsx` for the browser flow, or the `convert` route for the backend flow. Read [docs/architecture.md](docs/architecture.md) for lifecycle details and how to add a converter. Comments explain decisions such as process isolation and cleanup timing rather than repeating obvious code.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/formats` | Available conversions, limits, descriptions, and fidelity notes |
| POST | `/api/convert` | Multipart fields `file` and `target`; returns a binary download |
| GET | `/api/health` | Server status and engine availability |

Example:

```sh
curl -X POST http://localhost:8000/api/convert \
  -F "file=@slides.pdf" -F "target=pptx" -o slides.pptx
```

Check the HTTP status before saving in your own API client: failed requests return JSON, not a document.

```json
{"error":{"code":"unsupported_conversion","message":"Choose a DOCX or PPTX file for PDF, or a PDF file for PowerPoint."}}
```

## Tests and build

From `backend` with its virtual environment active:

```sh
python -m pytest -q
```

The suite performs a real PDF → PPTX conversion and checks output slides, malformed files, size/page limits, server saturation, timeouts, and cleanup after success/failure/disconnection. DOCX/PPTX → PDF integration tests run when LibreOffice is installed, otherwise they are explicitly skipped.

From `frontend`:

```sh
npm test
npm run build
```

`npm run build` includes TypeScript checks. Frontend tests cover filename handling and upload-selection validation. `package-lock.json` pins frontend dependencies. Backend dependency ranges are declared in `pyproject.toml`.

Formatting: `npm run format` in `frontend`, and `python -m black app tests` in `backend`. See [docs/verification.md](docs/verification.md) for the completed checks and verification limits.

## Deployment notes

Use a VM/container host that can execute Python and LibreOffice; a static website host alone cannot run these conversions. Deploy the provided Compose services behind HTTPS. No Sites deployment is included because its Worker runtime cannot launch the required native conversion processes.

Keep one Uvicorn worker initially: the concurrency cap is per Python process. Increase server resources and benchmark before increasing limits. Match nginx's `client_max_body_size` and proxy timeout to any changed backend limits. Large workloads would eventually benefit from a job queue, but the current request/response workflow does not need a database or Redis.

This is a bounded first version, not a hardened public document sandbox. Before exposing it to arbitrary internet traffic, add ingress rate limits and network isolation for conversion workers, and keep parsers/LibreOffice patched. Do not mount personal directories or secrets into the conversion container.

Files are temporarily written to disk; they are not kept in an application database. Normal requests clean up after response delivery or conversion failure. A client leaving during processing may leave that work running until it finishes or reaches its timeout; cleanup still follows. Crashed-process leftovers older than 24 hours are removed at the next API startup. Downloaded blobs remain in the browser until the user resets the form or leaves the page.
