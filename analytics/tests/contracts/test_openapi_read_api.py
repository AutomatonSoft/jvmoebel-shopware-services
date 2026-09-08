import json
from pathlib import Path

from jsonschema import Draft202012Validator, RefResolver
from pydantic import BaseModel

from domains.journeys.schemas import (
    JourneyEvent,
    JourneyResponse,
    JourneySearchHit,
    JourneySearchResponse,
)
from domains.reports.schemas import (
    Change,
    ContactChannelRow,
    ContactChannelsResponse,
    FunnelResponse,
    FunnelStep,
    IntChange,
    MoneyBreakdown,
    MoneyChange,
    OverviewDelta,
    OverviewResponse,
    PaymentMethodDelta,
    PaymentMethodRow,
    PaymentMethodsComparison,
    PaymentMethodsResponse,
    PeriodComparisonResponse,
    ProductRow,
    ProductsResponse,
    SourceRow,
    SourcesResponse,
)

CONTRACTS = Path(__file__).resolve().parents[2] / "contracts" / "http"
RESPONSES = CONTRACTS / "schemas" / "responses"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _object_schema(filename: str, def_name: str | None = None) -> dict:
    schema = _load(RESPONSES / filename)
    if def_name is None:
        return schema
    return schema["$defs"][def_name]


def _assert_fields_match(model: type[BaseModel], schema: dict) -> None:
    properties = set(schema["properties"])
    fields = set(model.model_fields)
    assert properties == fields, (model.__name__, properties ^ fields)
    required = set(schema.get("required", []))
    pydantic_required = {
        name for name, field in model.model_fields.items() if field.is_required()
    }
    assert required == pydantic_required, (
        model.__name__,
        required ^ pydantic_required,
    )


MODEL_SCHEMAS: tuple[tuple[type[BaseModel], str, str | None], ...] = (
    (MoneyBreakdown, "money-breakdown.schema.json", None),
    (OverviewResponse, "overview.schema.json", None),
    (FunnelResponse, "funnel.schema.json", None),
    (FunnelStep, "funnel.schema.json", "FunnelStep"),
    (SourcesResponse, "sources.schema.json", None),
    (SourceRow, "sources.schema.json", "SourceRow"),
    (ContactChannelsResponse, "contact-channels.schema.json", None),
    (ContactChannelRow, "contact-channels.schema.json", "ContactChannelRow"),
    (ProductsResponse, "products.schema.json", None),
    (ProductRow, "products.schema.json", "ProductRow"),
    (PaymentMethodRow, "payment-method-row.schema.json", None),
    (PaymentMethodsResponse, "payment-methods.schema.json", None),
    (PeriodComparisonResponse, "period-comparison.schema.json", None),
    (Change, "period-comparison.schema.json", "Change"),
    (IntChange, "period-comparison.schema.json", "IntChange"),
    (MoneyChange, "period-comparison.schema.json", "MoneyChange"),
    (OverviewDelta, "period-comparison.schema.json", "OverviewDelta"),
    (PaymentMethodDelta, "period-comparison.schema.json", "PaymentMethodDelta"),
    (PaymentMethodsComparison, "period-comparison.schema.json", "PaymentMethodsComparison"),
    (JourneyResponse, "journey.schema.json", None),
    (JourneyEvent, "journey.schema.json", "JourneyEvent"),
    (JourneySearchResponse, "journey-search.schema.json", None),
    (JourneySearchHit, "journey-search.schema.json", "JourneySearchHit"),
)


def test_read_api_schemas_match_pydantic() -> None:
    for model, filename, def_name in MODEL_SCHEMAS:
        _assert_fields_match(model, _object_schema(filename, def_name))


def test_openapi_lists_read_paths_and_response_schema_refs() -> None:
    openapi = (CONTRACTS / "openapi.yaml").read_text(encoding="utf-8")
    assert "./schemas/responses/overview.schema.json" in openapi
    assert "./schemas/responses/funnel.schema.json" in openapi
    assert "./schemas/responses/sources.schema.json" in openapi
    assert "  /analytics/overview:" in openapi
    assert "  /analytics/customers/{customer_id}/journey:" in openapi
    assert "readBearer:" in openapi


def test_response_examples_match_json_schema() -> None:
    examples = {
        "overview.json": "overview.schema.json",
        "funnel.json": "funnel.schema.json",
        "sources.json": "sources.schema.json",
        "contact-channels.json": "contact-channels.schema.json",
        "products.json": "products.schema.json",
        "payment-methods.json": "payment-methods.schema.json",
        "period-comparison.json": "period-comparison.schema.json",
        "journey.json": "journey.schema.json",
        "journey-search.json": "journey-search.schema.json",
    }
    for example_name, schema_name in examples.items():
        schema_path = RESPONSES / schema_name
        schema = _load(schema_path)
        validator = Draft202012Validator(
            schema,
            resolver=RefResolver(
                base_uri=schema_path.resolve().as_uri(),
                referrer=schema,
            ),
            format_checker=Draft202012Validator.FORMAT_CHECKER,
        )
        doc = _load(CONTRACTS / "examples" / "responses" / example_name)
        errors = list(validator.iter_errors(doc))
        assert errors == [], (example_name, [err.message for err in errors])
