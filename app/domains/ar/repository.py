# app/domains/ar/models/repository.py

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.base.repository import BaseRepository

from .models import ARModel


class ARModelRepository(
    BaseRepository[ARModel],
):
    model = ARModel

    async def get_model_by_sku(
        self,
        session: AsyncSession,
        sku: str,
    ) -> ARModel | None:

        stmt = select(self.model).where(
            self.model.sku == sku,
        )

        result = await session.execute(stmt)

        return result.scalar_one_or_none()