import json

from domains.ingestion.registry import HTTP_CONTRACTS_ROOT

# из файла event-rules.json достаем список типов событий HTTP, которые HTTP ingest имеет право принять
HTTP_EVENT_TYPES: frozenset[str] = frozenset(
    json.loads(
        (HTTP_CONTRACTS_ROOT / "event-rules.json").read_text(
            encoding="utf-8",
        )
    )["http_allowlist"]
)
