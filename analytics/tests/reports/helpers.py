import json
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "contracts"

PERIOD = {
    "period_from": "2026-08-24T00:00:00Z",
    "period_to": "2026-08-24T23:59:59Z",
}
COMPARE_PERIOD = {
    "compare_from": "2026-08-17T00:00:00Z",
    "compare_to": "2026-08-17T23:59:59Z",
}

ALLOWED_CHANNEL = "018f1a2b3c4d5e6f7890abcdef123456"
UNKNOWN_CHANNEL = "f" * 32


def report_params(**extra: str) -> dict[str, str]:
    return {**PERIOD, **extra}


def comparison_params(**extra: str) -> dict[str, str]:
    return {**PERIOD, **COMPARE_PERIOD, **extra}


def http_event(stem: str) -> dict:
    path = CONTRACTS_DIR / "http" / "examples" / "valid" / f"{stem}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def uniquify_ids(event: dict, *, visitor: bool = False, session: bool = False) -> dict:
    copied = deepcopy(event)
    copied["event_id"] = str(uuid4())
    if visitor and "visitor_id" in copied:
        copied["visitor_id"] = str(uuid4())
    if session and "session_id" in copied:
        copied["session_id"] = str(uuid4())
    return copied
