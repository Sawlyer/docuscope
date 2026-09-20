#!/bin/sh
set -eu

python -m alembic -c alembic.ini upgrade head
exec "$@"
