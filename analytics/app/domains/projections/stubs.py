from sqlalchemy.dialects.postgresql import insert as pg_insert

# если не использовать диалект, 
from sqlalchemy.ext.asyncio import AsyncSession

from domains.projections.models.entities import (
    Lead,
    ManualSale,
    Order,
    Session,
    Visitor,
)
from domains.projections.models.journal import Event


async def ensure_stubs(session: AsyncSession, event: Event) -> None:
    # если при попытке вставить строку в таблицу Visitors произойдет конфликт по полю visitor_id
    # (например visitor_id  уже существует) то ничего не делать. Это на случай, если придут 2 события,
    # которые подразумевают добавление заглушки в таблицу Visitors
    if event.visitor_id is not None:
        await session.execute(
            pg_insert(Visitor)
            .values(visitor_id=event.visitor_id)
            .on_conflict_do_nothing(index_elements=["visitor_id"])
        )

    if event.session_id is not None and event.visitor_id is not None:
        await session.execute(
            pg_insert(Session)
            .values(
                session_id=event.session_id,
                visitor_id=event.visitor_id,
            )
            .on_conflict_do_nothing(index_elements=["session_id"])
        )

    if event.lead_id is not None:
        await session.execute(
            pg_insert(Lead)
            .values(lead_id=event.lead_id)
            .on_conflict_do_nothing(index_elements=["lead_id"])
        )

    if event.order_id is not None:
        await session.execute(
            pg_insert(Order)
            .values(order_id=event.order_id)
            .on_conflict_do_nothing(index_elements=["order_id"])
        )

    if event.manual_sale_id is not None:
        await session.execute(
            pg_insert(ManualSale)
            .values(manual_sale_id=event.manual_sale_id)
            .on_conflict_do_nothing(index_elements=["manual_sale_id"])
        )

    await session.flush()
