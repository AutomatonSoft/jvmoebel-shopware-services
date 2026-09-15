# app/domains/base/repository.py

from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.postgres import Base


ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    model: type[ModelType]

    async def get_all(
        self,
        session: AsyncSession,
    ) -> list[ModelType]:

        stmt = select(self.model).order_by(self.model.id)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(
        self,
        session: AsyncSession,
        obj_id: int,
    ) -> ModelType | None:

        return await session.get(
            self.model,
            obj_id,
        )

    async def create(
        self,
        session: AsyncSession,
        **kwargs,
    ) -> ModelType:

        obj = self.model(**kwargs)
        session.add(obj)
        await session.flush()
        return obj

    async def update(
        self,
        session: AsyncSession,
        obj: ModelType,
        **kwargs,
    ) -> ModelType:

        for field, value in kwargs.items():
            setattr(obj, field, value)
        await session.flush()
        return obj

    async def delete(
        self,
        session: AsyncSession,
        obj: ModelType,
    ) -> None:

        await session.delete(obj)
        await session.flush()