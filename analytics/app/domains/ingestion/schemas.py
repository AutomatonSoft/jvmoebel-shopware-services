from typing import Literal

from pydantic import BaseModel

IngestStatus = Literal["accepted", "duplicate"]
BatchItemStatus = Literal["accepted", "duplicate", "rejected"]


class IngestEventResponse(BaseModel):
    status: IngestStatus


class IngestBatchItem(BaseModel):
    index: int
    event_id: str | None = None
    status: BatchItemStatus
    detail: str | None = None


class IngestBatchResponse(BaseModel):
    results: list[IngestBatchItem]
