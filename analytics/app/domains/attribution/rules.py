from dataclasses import dataclass
from datetime import datetime

from domains.projections.models.entities import Visitor
from domains.projections.models.mixins import AttributionSnapshotMixin


@dataclass(frozen=True)
class Touch:
    source: str
    occurred_at: datetime
    sales_channel_id: str
    campaign: str | None
    utm_source: str | None
    utm_medium: str | None
    utm_campaign: str | None
    utm_content: str | None
    utm_term: str | None
    gclid: str | None
    gbraid: str | None
    wbraid: str | None
    landing_page: str | None
    referrer: str | None

    @property
    def is_direct(self) -> bool:
        return self.source == "direct"


_SNAPSHOT_PAIRS = (
    ("first_touch_source", "attr_first_touch_source"),
    ("first_touch_campaign", "attr_first_touch_campaign"),
    ("first_touch_gclid", "attr_first_touch_gclid"),
    ("first_touch_gbraid", "attr_first_touch_gbraid"),
    ("first_touch_wbraid", "attr_first_touch_wbraid"),
    ("first_touch_utm_source", "attr_first_touch_utm_source"),
    ("first_touch_utm_medium", "attr_first_touch_utm_medium"),
    ("first_touch_utm_campaign", "attr_first_touch_utm_campaign"),
    ("first_touch_utm_content", "attr_first_touch_utm_content"),
    ("first_touch_utm_term", "attr_first_touch_utm_term"),
    ("first_touch_landing_page", "attr_first_touch_landing_page"),
    ("first_touch_referrer", "attr_first_touch_referrer"),
    ("first_touch_occurred_at", "attr_first_touch_occurred_at"),
    ("first_touch_sales_channel_id", "attr_first_touch_sales_channel_id"),
    ("last_non_direct_source", "attr_last_non_direct_source"),
    ("last_non_direct_campaign", "attr_last_non_direct_campaign"),
    ("last_non_direct_gclid", "attr_last_non_direct_gclid"),
    ("last_non_direct_gbraid", "attr_last_non_direct_gbraid"),
    ("last_non_direct_wbraid", "attr_last_non_direct_wbraid"),
    ("last_non_direct_utm_source", "attr_last_non_direct_utm_source"),
    ("last_non_direct_utm_medium", "attr_last_non_direct_utm_medium"),
    ("last_non_direct_utm_campaign", "attr_last_non_direct_utm_campaign"),
    ("last_non_direct_utm_content", "attr_last_non_direct_utm_content"),
    ("last_non_direct_utm_term", "attr_last_non_direct_utm_term"),
    ("last_non_direct_landing_page", "attr_last_non_direct_landing_page"),
    ("last_non_direct_referrer", "attr_last_non_direct_referrer"),
    ("last_non_direct_occurred_at", "attr_last_non_direct_occurred_at"),
    ("last_non_direct_sales_channel_id", "attr_last_non_direct_sales_channel_id"),
)


def apply_first_touch(visitor: Visitor, touch: Touch) -> None:
    stored = visitor.first_touch_occurred_at
    if stored is not None and touch.occurred_at >= stored:
        return
    visitor.first_touch_source = touch.source
    visitor.first_touch_campaign = touch.campaign
    visitor.first_touch_gclid = touch.gclid
    visitor.first_touch_gbraid = touch.gbraid
    visitor.first_touch_wbraid = touch.wbraid
    visitor.first_touch_utm_source = touch.utm_source
    visitor.first_touch_utm_medium = touch.utm_medium
    visitor.first_touch_utm_campaign = touch.utm_campaign
    visitor.first_touch_utm_content = touch.utm_content
    visitor.first_touch_utm_term = touch.utm_term
    visitor.first_touch_landing_page = touch.landing_page
    visitor.first_touch_referrer = touch.referrer
    visitor.first_touch_occurred_at = touch.occurred_at
    visitor.first_touch_sales_channel_id = touch.sales_channel_id


def apply_last_non_direct(visitor: Visitor, touch: Touch) -> None:
    if touch.is_direct:
        return
    stored = visitor.last_non_direct_occurred_at
    if stored is not None and touch.occurred_at < stored:
        return
    visitor.last_non_direct_source = touch.source
    visitor.last_non_direct_campaign = touch.campaign
    visitor.last_non_direct_gclid = touch.gclid
    visitor.last_non_direct_gbraid = touch.gbraid
    visitor.last_non_direct_wbraid = touch.wbraid
    visitor.last_non_direct_utm_source = touch.utm_source
    visitor.last_non_direct_utm_medium = touch.utm_medium
    visitor.last_non_direct_utm_campaign = touch.utm_campaign
    visitor.last_non_direct_utm_content = touch.utm_content
    visitor.last_non_direct_utm_term = touch.utm_term
    visitor.last_non_direct_landing_page = touch.landing_page
    visitor.last_non_direct_referrer = touch.referrer
    visitor.last_non_direct_occurred_at = touch.occurred_at
    visitor.last_non_direct_sales_channel_id = touch.sales_channel_id


def copy_attribution_snapshot(
    visitor: Visitor,
    entity: AttributionSnapshotMixin,
) -> None:
    for source_field, target_field in _SNAPSHOT_PAIRS:
        setattr(entity, target_field, getattr(visitor, source_field))
