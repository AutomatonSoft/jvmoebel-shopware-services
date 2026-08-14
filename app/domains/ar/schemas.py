# app/domains/ar/schemas.py

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SARModelBase(BaseModel):
    # Входные значения могут быть переданы в m, cm или mm.
    # Перед сохранением в БД сервис преобразует их в метры.
    width: Decimal = Field(gt=0, examples=[1.2])
    height: Decimal = Field(gt=0, examples=[0.8])
    depth: Decimal = Field(gt=0, examples=[0.6])
    unit: Literal["m", "cm", "mm"] = Field(
        default="m",
        description="Input measurement unit. Supported units: m, cm, mm.",
    )


class SARModelCreate(SARModelBase):
    pass


class SARModelUpdate(SARModelBase):
    pass


class SARModelStatusUpdate(BaseModel):
    status: Literal["active", "not_active"]


class SARModelAvailableResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    sku: str
    available: Literal[True]
    format: str
    file_url: str
    width: Decimal = Field(examples=[2.4])
    height: Decimal = Field(examples=[0.8])
    depth: Decimal = Field(examples=[0.6])
    unit: Literal["m"] = "m"


class SARModelUnavailableResponse(BaseModel):
    sku: str
    available: Literal[False]


class SARModelStatusResponse(BaseModel):
    sku: str
    status: Literal["active", "not_active"]