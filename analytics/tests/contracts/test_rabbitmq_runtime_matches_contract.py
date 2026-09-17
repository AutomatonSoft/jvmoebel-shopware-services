import inspect
import json
import re
from pathlib import Path
from urllib.parse import urlparse

import pytest
import yaml

from core.config import settings
from core.rabbit import (
    DLQ_QUEUE,
    DLX_EXCHANGE,
    EVENTS_EXCHANGE,
    RETRY_EXCHANGE,
    RETRY_QUEUE,
    ROUTING_KEYS,
    consume_shopware_events,
    declare_topology,
)
from domains.ingestion.consumer import handle_shopware_message, retry_or_dead_letter

ANALYTICS_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ANALYTICS_ROOT / "contracts" / "rabbitmq"
ENV_FILES = (
    ANALYTICS_ROOT / ".env.example",
    ANALYTICS_ROOT / ".env.dev.example",
    ANALYTICS_ROOT / ".env.test.example",
)
COMPOSE_FILES = (
    ANALYTICS_ROOT / "docker-compose.yml",
    ANALYTICS_ROOT / "docker-compose.dev.yml",
    ANALYTICS_ROOT / "compose.deploy.yml",
)
CANONICAL_VHOST = "shopware-analytics"


def _canonical_vhost(value: str) -> str:
    return value.strip().strip("/")


def _load_yaml(path: Path) -> dict:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key] = value
    return values


def _compose_rabbit_env(path: Path) -> dict[str, str]:
    services = _load_yaml(path)["services"]
    rabbit = services.get("rabbitmq") or services.get("rabbitmq_dev")
    assert rabbit is not None, f"{path.name} has no rabbitmq service"
    raw = rabbit.get("environment") or {}
    if isinstance(raw, dict):
        return {str(key): str(value) for key, value in raw.items()}
    mapped: dict[str, str] = {}
    for item in raw:
        key, _, value = str(item).partition("=")
        mapped[key] = value
    return mapped


def _url_vhost(url: str) -> str:
    return _canonical_vhost(urlparse(url).path)


def _url_username(url: str) -> str:
    return urlparse(url).username or ""


@pytest.fixture(scope="module")
def topology() -> dict:
    return _load_yaml(CONTRACTS / "infrastructure" / "rabbitmq-topology.yaml")


@pytest.fixture(scope="module")
def asyncapi() -> dict:
    return _load_yaml(CONTRACTS / "asyncapi.yaml")


@pytest.fixture(scope="module")
def routing() -> dict:
    return json.loads((CONTRACTS / "routing-keys.json").read_text(encoding="utf-8"))


def test_vhost_matches_contract(topology: dict, asyncapi: dict, routing: dict) -> None:
    assert _canonical_vhost(str(topology["vhost"])) == CANONICAL_VHOST
    assert _canonical_vhost(str(routing["vhost"])) == CANONICAL_VHOST

    server = asyncapi["servers"]["rabbitmq"]
    assert _canonical_vhost(str(server["pathname"])) == CANONICAL_VHOST

    channels = asyncapi["channels"]
    for name, channel in channels.items():
        exchange = channel["bindings"]["amqp"]["exchange"]
        assert _canonical_vhost(str(exchange["vhost"])) == CANONICAL_VHOST, name

    assert _url_vhost(settings.rabbitmq.url) == CANONICAL_VHOST

    for env_path in ENV_FILES:
        env = _parse_env(env_path)
        assert _url_vhost(env["RABBITMQ_URL"]) == CANONICAL_VHOST, env_path.name
        assert _url_username(env["RABBITMQ_URL"]) != "guest", env_path.name

    for compose_path in COMPOSE_FILES:
        rabbit_env = _compose_rabbit_env(compose_path)
        assert (
            _canonical_vhost(rabbit_env["RABBITMQ_DEFAULT_VHOST"]) == CANONICAL_VHOST
        ), compose_path.name

    init_users = (ANALYTICS_ROOT / "rabbitmq" / "init-users.sh").read_text(
        encoding="utf-8"
    )
    assert "RABBITMQ_DEFAULT_VHOST" in init_users
    assert f"/{CANONICAL_VHOST}" not in init_users
    assert "-p /" not in init_users


def test_rabbitmq_compose_hostname_is_stable() -> None:
    for compose_path in COMPOSE_FILES:
        services = _load_yaml(compose_path)["services"]
        rabbit = services.get("rabbitmq") or services.get("rabbitmq_dev")
        assert rabbit is not None, f"{compose_path.name} has no rabbitmq service"
        hostname = rabbit.get("hostname")
        assert hostname, f"{compose_path.name} rabbitmq hostname must be set"


def test_exchanges_match_contract(
    topology: dict, asyncapi: dict, routing: dict
) -> None:
    exchanges = topology["exchanges"]
    assert EVENTS_EXCHANGE == exchanges["events"]["name"] == routing["exchange"]
    assert RETRY_EXCHANGE == exchanges["retry"]["name"]
    assert DLX_EXCHANGE == exchanges["dlx"]["name"]
    assert routing["exchange_type"] == "topic"
    assert exchanges["events"]["type"] == "topic"
    assert exchanges["events"]["durable"] is True

    source = inspect.getsource(declare_topology)
    assert "ExchangeType.TOPIC" in source
    assert "durable=True" in source

    for name, channel in asyncapi["channels"].items():
        exchange = channel["bindings"]["amqp"]["exchange"]
        assert exchange["name"] == EVENTS_EXCHANGE, name
        assert exchange["type"] == "topic", name
        assert exchange["durable"] is True, name


def test_queues_and_dlx_match_contract(topology: dict) -> None:
    queues = topology["queues"]
    assert settings.rabbitmq.events_queue == queues["analytics"]["name"]
    assert RETRY_QUEUE == queues["retry"]["name"]
    assert DLQ_QUEUE == queues["dlq"]["name"]
    assert queues["analytics"]["dead_letter_exchange"] == DLX_EXCHANGE
    assert queues["retry"]["binding"]["exchange"] == RETRY_EXCHANGE
    assert queues["retry"]["binding"]["routing_key"] == "shopware.#"
    assert queues["dlq"]["binding"]["exchange"] == DLX_EXCHANGE
    assert queues["dlq"]["binding"]["routing_key"] == "#"

    for env_path in ENV_FILES:
        env = _parse_env(env_path)
        assert (
            env["RABBITMQ_EVENTS_QUEUE"] == queues["analytics"]["name"]
        ), env_path.name

    source = inspect.getsource(declare_topology)
    assert 'arguments={"x-dead-letter-exchange": DLX_EXCHANGE}' in source
    assert '"x-dead-letter-exchange": EVENTS_EXCHANGE' in source
    assert 'routing_key="shopware.#"' in source
    assert 'routing_key="#"' in source


def test_routing_keys_match_contract(
    topology: dict, asyncapi: dict, routing: dict
) -> None:
    topology_keys = {
        binding["routing_key"]
        for binding in topology["queues"]["analytics"]["bindings"]
    }
    runtime_keys = set(ROUTING_KEYS)
    contract_keys = set(routing["routing_keys"].values())
    asyncapi_keys = {channel["address"] for channel in asyncapi["channels"].values()}

    assert runtime_keys == topology_keys == contract_keys == asyncapi_keys


def test_persistent_delivery_and_manual_ack(topology: dict) -> None:
    delivery = topology["delivery"]
    assert delivery["publisher_delivery_mode"] == 2
    assert delivery["consumer_ack_mode"] == "manual"

    consume_source = inspect.getsource(consume_shopware_events)
    assert "no_ack=True" not in consume_source
    assert "events_queue.consume(on_message)" in consume_source

    handler_source = inspect.getsource(handle_shopware_message)
    assert "await message.ack()" in handler_source

    retry_source = inspect.getsource(retry_or_dead_letter)
    assert "DeliveryMode.PERSISTENT" in retry_source


def test_users_match_contract(topology: dict) -> None:
    users = topology["users"]
    assert "analytics_consumer" in users
    assert "shopware_publisher" in users
    publisher = users["shopware_publisher"]["permissions"]

    for env_path in ENV_FILES:
        env = _parse_env(env_path)
        assert env["RABBITMQ_CONSUMER_USER"] == "analytics_consumer", env_path.name
        assert env["RABBITMQ_PUBLISHER_USER"] == "shopware_publisher", env_path.name
        assert env["RABBITMQ_CONSUMER_USER"] != env["RABBITMQ_PUBLISHER_USER"]
        assert _url_username(env["RABBITMQ_URL"]) == env["RABBITMQ_CONSUMER_USER"]

    init_users = (ANALYTICS_ROOT / "rabbitmq" / "init-users.sh").read_text(
        encoding="utf-8"
    )
    match = re.search(
        r"rabbitmqctl set_permissions -p \"\$\{vhost\}\" \"\$\{publisher_user\}\""
        r"\s+\\?\s*'([^']+)'\s+\\?\s*'([^']+)'\s+\\?\s*'([^']+)'",
        init_users,
    )
    assert match is not None
    assert match.group(1) == publisher["configure"]
    assert match.group(2) == publisher["write"]
    assert match.group(3) == publisher["read"]
