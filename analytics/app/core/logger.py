# app/core/logger.py

import logging


def configure_logging(level=logging.INFO):
    logging.basicConfig(
        level=level,
        datefmt="%Y-%m-%d %H:%M:%S",
        format=(
            "[%(asctime)s.%(msecs)03d] "
            "%(name)s:%(lineno)d "
            "%(levelname)s - "
            "%(message)s"
        )
    )