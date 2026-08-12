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


class SARModelRead(SARModelBase):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int # по тз не нужно возвращать. уточнить
    sku: str
    status: str
    file_format: str
    file_path: str