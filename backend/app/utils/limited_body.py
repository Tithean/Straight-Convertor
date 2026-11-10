import tempfile

from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse


class LimitedBodyMiddleware:
    """Cap even chunked requests before the multipart parser creates upload files."""

    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "POST":
            return await self.app(scope, receive, send)

        async def reject():
            response = JSONResponse(
                {
                    "error": {
                        "code": "file_too_large",
                        "message": "The upload is too large. Please choose a smaller file.",
                    }
                },
                status_code=413,
            )
            await response(scope, receive, send)

        headers = dict(scope.get("headers", []))
        try:
            if int(headers.get(b"content-length", b"0")) > self.max_bytes:
                return await reject()
        except ValueError:
            return await JSONResponse(
                {
                    "error": {
                        "code": "invalid_request",
                        "message": "Invalid upload length.",
                    }
                },
                status_code=400,
            )(scope, receive, send)

        # Spooling bounds memory and covers requests without a Content-Length header.
        # It is closed on success, malformed multipart, disconnect, or size rejection.
        with tempfile.SpooledTemporaryFile(max_size=1024 * 1024) as body:
            total = 0
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                data = message.get("body", b"")
                total += len(data)
                if total > self.max_bytes:
                    return await reject()
                await run_in_threadpool(body.write, data)
                if not message.get("more_body", False):
                    break
            body.seek(0)
            replayed = 0
            finished = False

            async def replay():
                nonlocal replayed, finished
                if finished:
                    return await receive()
                data = await run_in_threadpool(body.read, 64 * 1024)
                replayed += len(data)
                finished = replayed >= total
                return {
                    "type": "http.request",
                    "body": data,
                    "more_body": replayed < total,
                }

            await self.app(scope, replay, send)
