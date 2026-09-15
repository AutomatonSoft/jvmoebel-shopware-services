# app/core/middleware.py
from starlette.exceptions import HTTPException
from starlette.status import HTTP_413_CONTENT_TOO_LARGE
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class RequestBodyTooLarge(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=HTTP_413_CONTENT_TOO_LARGE,
            detail="Request body too large",
        )


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
        response_started = False
        response_completed = False

        async def send_wrapper(message: Message) -> None:
            nonlocal response_started, response_completed

            if response_completed:
                return

            if message["type"] == "http.response.start":
                if response_started:
                    return
                response_started = True
                await send(message)
                return

            if message["type"] == "http.response.body":
                if not response_started:
                    return
                await send(message)
                if not message.get("more_body", False):
                    response_completed = True
                return

            await send(message)

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
                send_wrapper,
            )
        except RequestBodyTooLarge:
            if not response_started:
                await self._send_413(send_wrapper)

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
