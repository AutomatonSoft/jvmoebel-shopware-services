# app/domains/ar/schemas.py

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SARModelBase(BaseModel):
    # Уточнить по поводу decimal и метров по тз как лучше
    width: Decimal = Field(gt=0, examples=[1.2])
    height: Decimal = Field(gt=0, examples=[0.8])
    depth: Decimal = Field(gt=0, examples=[0.6])
    # юнит пока валидируем жестко, и в роутах  тоже!
    unit: Literal["m"] = Field(
        default="m",
        description="Measurement unit. Currently only meters are supported.",
    )


class SARModelCreate(SARModelBase):
    pass


class SARModelUpdate(SARModelBase):
    pass


class SARModelStatusUpdate(BaseModel):
    status: Literal["active", "not_active"]


class SARModelAvailableResponse(SARModelBase):
    model_config = ConfigDict(
        from_attributes=True,
    )

    sku: str
    available: Literal[True]
    format: str
    file_url: str


class SARModelUnavailableResponse(BaseModel):
    sku: str
    available: Literal[False]