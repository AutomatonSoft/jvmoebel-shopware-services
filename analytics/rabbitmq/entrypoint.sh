#!/bin/bash
set -euo pipefail

/usr/local/bin/init-users.sh &
exec docker-entrypoint.sh rabbitmq-server "$@"
