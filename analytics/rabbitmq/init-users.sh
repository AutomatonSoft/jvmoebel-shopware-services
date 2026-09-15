#!/bin/bash
set -euo pipefail

vhost="${RABBITMQ_DEFAULT_VHOST:?RABBITMQ_DEFAULT_VHOST is required}"
publisher_user="${RABBITMQ_PUBLISHER_USER:?RABBITMQ_PUBLISHER_USER is required}"
publisher_password="${RABBITMQ_PUBLISHER_PASSWORD:?RABBITMQ_PUBLISHER_PASSWORD is required}"

for _ in $(seq 1 60); do
  if rabbitmqctl await_startup >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

if ! rabbitmqctl await_startup >/dev/null 2>&1; then
  echo "init-users: RabbitMQ did not start in time" >&2
  exit 1
fi

if ! rabbitmqctl add_user "${publisher_user}" "${publisher_password}"; then
  rabbitmqctl change_password "${publisher_user}" "${publisher_password}"
fi

rabbitmqctl set_permissions -p "${vhost}" "${publisher_user}" \
  '^shopware\.analytics\.events$' \
  '^shopware\.analytics\.events$' \
  '^$'

echo "init-users: publisher ${publisher_user} ready on vhost ${vhost}"
