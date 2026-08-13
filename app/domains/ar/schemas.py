# app/domains/ar/schemas.py

from decimal import Decimal

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class SARModelBase(BaseModel):
    # Уточнить по поводу decimal и метров по тз как лучше
    width: Decimal = Field(gt=0)
    height: Decimal = Field(gt=0)
    depth: Decimal = Field(gt=0)
    unit: Literal["m"] = "m"

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
    width: Decimal | None = None
    height: Decimal | None = None
    depth: Decimal | None = None
    # и здесь пока что тоже жестко обозначаем метры, уточнить по тз
    unit: Literal["m"] = "m"
