import json
from functools import lru_cache

from jsonschema import Draft202012Validator, RefResolver

# те же, что в contracts/http/tests/validate_contract.py
# иначе ingest мог бы принять то, что контракт-тесты отвергают (или наоборот)

from core.config import settings
from domains.ingestion.allowlist import HTTP_EVENT_TYPES, RABBIT_EVENT_TYPES
from domains.ingestion.exceptions import EventValidationError
from domains.ingestion.registry import (
    http_event_schema_path,
    rabbit_event_schema_path,
)
from domains.ingestion.sales_channels import (
    assert_http_channel_allowed,
    assert_rabbit_channel_allowed,
)


@lru_cache(maxsize=None)
def _http_event_validator(event_type: str) -> Draft202012Validator:
    schema_path = http_event_schema_path(event_type)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    # RefResolver подставляет json-схемы из файлов в текущую схему, если в ней указан $ref
    resolver = RefResolver(
        base_uri=schema_path.resolve().as_uri(),  # путь к корневой схеме
        referrer=schema,  # dict корневой схемы
    )

    # Draft202012Validator - проверяльщик JSON по правилам JSON Schema, версии draft 2020-12
    return Draft202012Validator(
        # schema -dict корневой схемы
        schema,
        # resolver - куда идти, если в схеме $ref
        resolver=resolver,
        # format_checker - проверять format (date-time, uri, uuid)
        # без него jsonschema смотрит только type: string,
        # и occurred_at="вчера" пройдёт.
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )


def validate_http_event(
    body: object,
    *,
    origin: str | None,
) -> dict:
    if not isinstance(body, dict):
        raise EventValidationError(
            detail="Event must be a JSON object",
        )

    event_type = body.get("event_type")
    if not isinstance(event_type, str) or event_type not in HTTP_EVENT_TYPES:
        raise EventValidationError(
            detail="Event type is not allowed for HTTP ingestion",
        )

    encoded_size = len(json.dumps(body, ensure_ascii=False).encode("utf-8"))
    if encoded_size > settings.max_event_payload_bytes:
        raise EventValidationError(
            detail="Event payload is too large",
        )

    # берет закешированный валидатор этого event_type, проверяет body по JSON Schema, возвращает все ошибки списком
    errors = list(_http_event_validator(event_type).iter_errors(body))
    if errors:
        error = errors[0]
        path = "/".join(str(part) for part in error.absolute_path)
        detail = error.message if not path else f"{path}: {error.message}"
        raise EventValidationError(detail=detail)

    sales_channel_id = body.get("sales_channel_id")
    if not isinstance(sales_channel_id, str):
        raise EventValidationError(
            detail="sales_channel_id is required",
        )

    market_code = body.get("market_code")
    domain = body.get("domain")
    assert_http_channel_allowed(
        sales_channel_id,
        origin=origin,
        market_code=(market_code if isinstance(market_code, str) else None),
        domain=(domain if isinstance(domain, str) else None),
    )
    return body


@lru_cache(maxsize=None)
def _rabbit_event_validator(event_type: str) -> Draft202012Validator:
    schema_path = rabbit_event_schema_path(event_type)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    resolver = RefResolver(
        base_uri=schema_path.resolve().as_uri(),
        referrer=schema,
    )
    return Draft202012Validator(
        schema,
        resolver=resolver,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )


def validate_rabbit_event(body: object) -> dict:
    if not isinstance(body, dict):
        raise EventValidationError(
            detail="Event must be a JSON object",
        )

    event_type = body.get("event_type")
    if not isinstance(event_type, str) or event_type not in RABBIT_EVENT_TYPES:
        raise EventValidationError(
            detail="Event type is not allowed for RabbitMQ ingestion",
        )

    encoded_size = len(json.dumps(body, ensure_ascii=False).encode("utf-8"))
    if encoded_size > settings.max_event_payload_bytes:
        raise EventValidationError(
            detail="Event payload is too large",
        )

    errors = list(_rabbit_event_validator(event_type).iter_errors(body))
    if errors:
        error = errors[0]
        path = "/".join(str(part) for part in error.absolute_path)
        detail = error.message if not path else f"{path}: {error.message}"
        raise EventValidationError(detail=detail)

    sales_channel_id = body.get("sales_channel_id")
    if not isinstance(sales_channel_id, str):
        raise EventValidationError(
            detail="sales_channel_id is required",
        )

    market_code = body.get("market_code")
    assert_rabbit_channel_allowed(
        sales_channel_id,
        market_code=(market_code if isinstance(market_code, str) else None),
    )
    return body
