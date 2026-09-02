from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from domains.projections.models.facts import OrderLine
from domains.projections.parsing import parse_money


async def replace_order_lines(
    session: AsyncSession,
    *,
    order_id: str,
    line_items: list[dict],
    currency: str,
    source_event_type: str,
    is_paid_snapshot: bool,
) -> None:
    await session.execute(
        delete(OrderLine).where(
            OrderLine.order_id == order_id,
            OrderLine.is_paid_snapshot == is_paid_snapshot,
        )
    )
    for item in line_items:
        session.add(
            OrderLine(
                order_id=order_id,
                line_item_id=item["line_item_id"],
                is_paid_snapshot=is_paid_snapshot,
                product_number=item.get("product_number"),
                item_type=item["item_type"],
                quantity=item["quantity"],
                unit_price=parse_money(item["unit_price"]),
                total_price=parse_money(item["total_price"]),
                currency=currency,
                source_event_type=source_event_type,
            )
        )
