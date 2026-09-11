"""RabbitMQ consumer entrypoint (отдельно от HTTP backend)."""

import asyncio
import logging

import core.db.models  # noqa: F401 — register ORM models
from core.logger import configure_logging
from core.rabbit import consume_shopware_events

log = logging.getLogger(__name__)

configure_logging()


async def main() -> None:
    log.info("Analytics worker started")
    await consume_shopware_events()


if __name__ == "__main__":
    asyncio.run(main())
