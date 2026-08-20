# app/core/middleware.py
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class RequestBodyTooLarge(Exception):
    pass


class MaxBodySizeMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        max_size: int,
    ):
        self.app = app
        self.max_size = max_size

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ):
        # Middleware работает только с HTTP-запросами.
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Проверяем Content-Length до запуска FastAPI
        # и multipart parser.
        content_length = self._get_content_length(scope)

        if (
            content_length is not None
            and content_length > self.max_size
        ):
            await self._send_413(send)
            return

        total_read = 0

        async def receive_wrapper() -> Message:
            nonlocal total_read

            message = await receive()

            if message["type"] == "http.request":
                body = message.get("body", b"")

                total_read += len(body)

                if total_read > self.max_size:
                    raise RequestBodyTooLarge()

            return message

        try:
            await self.app(
                scope,
                receive_wrapper,
                send,
            )
        except RequestBodyTooLarge:
            await self._send_413(send)

    def _get_content_length(
        self,
        scope: Scope,
    ) -> int | None:
        for name, value in scope.get("headers", []):
            if name.lower() == b"content-length":
                try:
                    return int(value)
                except ValueError:
                    return None

        return None

    async def _send_413(
        self,
        send: Send,
    ):
        body = b'{"detail":"Request body too large"}'

        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (
                        b"content-length",
                        str(len(body)).encode(),
                    ),
                ],
            }
        )

        await send(
            {
                "type": "http.response.body",
                "body": body,
            }
        )