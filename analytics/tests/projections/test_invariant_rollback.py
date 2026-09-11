import pytest
from sqlalchemy import func, select

from domains.projections.exceptions import ProjectionInvariantError
from domains.projections.models.entities import Lead
from domains.projections.models.journal import Event


async def test_missing_lead_id_rolls_back_journal(
    persist_event,
    load_shopware_event,
    db_session,
) -> None:
    body = load_shopware_event("lead-created")
    body.pop("lead_id")

    with pytest.raises(ProjectionInvariantError, match="lead_id"):
        await persist_event(body)

    events = await db_session.scalar(select(func.count()).select_from(Event))
    leads = await db_session.scalar(select(func.count()).select_from(Lead))
    assert events == 0
    assert leads == 0


async def test_version_skip_still_commits_journal(
    persist_event,
    load_shopware_event,
    db_session,
) -> None:
    created = load_shopware_event("lead-created")
    created["aggregate_version"] = 2
    await persist_event(created)

    older = load_shopware_event("lead-status-changed")
    older["lead_id"] = created["lead_id"]
    older["visitor_id"] = created["visitor_id"]
    older["aggregate_version"] = 1
    older["payload"] = {
        "previous_status": "new",
        "new_status": "lost",
    }
    await persist_event(older)

    events = await db_session.scalar(select(func.count()).select_from(Event))
    lead = await db_session.get(Lead, created["lead_id"])
    assert events == 2
    assert lead is not None
    assert lead.status == "new"
    assert lead.lost_at is None
