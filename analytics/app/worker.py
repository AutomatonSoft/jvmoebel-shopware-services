"""RabbitMQ consumer entrypoint (отдельно от HTTP backend)."""

import asyncio
import logging

from core.logger import configure_logging

log = logging.getLogger(__name__)

configure_logging()


async def main() -> None:
    log.info("Analytics worker started (consumer not implemented yet)")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
