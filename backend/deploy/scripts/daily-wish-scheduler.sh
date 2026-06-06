#!/bin/sh
set -eu

export TZ="${TZ:-Asia/Shanghai}"

REFRESH_TIME="${DAILY_WISH_REFRESH_TIME:-08:00}"
USER_ID="${DAILY_WISH_USER_ID:-}"
FORCE="${DAILY_WISH_FORCE:-false}"
RUN_ON_START="${DAILY_WISH_RUN_ON_START:-false}"
RUN_ONCE="${SCHEDULER_RUN_ONCE:-false}"

run_daily_wishes() {
  args=""
  if [ -n "$USER_ID" ]; then
    args="$args --user-id $USER_ID"
  fi
  if [ "$FORCE" = "true" ]; then
    args="$args --force"
  fi

  echo "[$(date -Iseconds)] Running daily wish refresh$args"
  # shellcheck disable=SC2086
  python manage.py generate_daily_wishes $args
}

seconds_until_next_run() {
  python - "$REFRESH_TIME" <<'PY'
from datetime import datetime, timedelta
import os
import sys
from zoneinfo import ZoneInfo

refresh_time = sys.argv[1]
hour, minute = [int(part) for part in refresh_time.split(":", 1)]
tz = ZoneInfo(os.getenv("TZ", "Asia/Shanghai"))
now = datetime.now(tz)
target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
if target <= now:
    target += timedelta(days=1)
print(max(1, int((target - now).total_seconds())))
PY
}

echo "[$(date -Iseconds)] Daily wish scheduler started. TZ=$TZ, time=$REFRESH_TIME"

if [ "$RUN_ON_START" = "true" ]; then
  run_daily_wishes
  if [ "$RUN_ONCE" = "true" ]; then
    exit 0
  fi
fi

while true; do
  sleep_seconds="$(seconds_until_next_run)"
  echo "[$(date -Iseconds)] Next daily wish refresh in ${sleep_seconds}s at ${REFRESH_TIME} ${TZ}"
  sleep "$sleep_seconds"
  run_daily_wishes
  if [ "$RUN_ONCE" = "true" ]; then
    exit 0
  fi
done
