# app/domains/ar/models/schemas.py

from pydantic import BaseModel, ConfigDict


class SARModelBase(BaseModel):
    width: float
    height: float
    depth: float
    unit: str


class SARModelCreate(SARModelBase):
    pass


class SARModelUpdate(SARModelBase):
    pass


class SARModelResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    sku: str
    available: bool
    format: str | None = None
    file_url: str | None = None
    width: float | None = None
    height: float | None = None
    depth: float | None = None
    unit: str | None = None