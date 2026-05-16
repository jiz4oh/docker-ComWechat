#!/usr/bin/env bash
set -euo pipefail

IMAGE="${IMAGE:-comwechat:smoke-test}"
PROJECT="${PROJECT:-comwechat-smoke-test}"
COMPOSE_FILE="$(mktemp "${TMPDIR:-/tmp}/comwechat-smoke-test.XXXXXX.yaml")"

cleanup() {
  docker compose -p "$PROJECT" -f "$COMPOSE_FILE" down -v >/dev/null 2>&1 || true
  rm -f "$COMPOSE_FILE"
}
trap cleanup EXIT

docker build -t "$IMAGE" .

docker run --rm "$IMAGE" sh -lc \
  'test -x /run.py && test ! -e /run2.py && test -f /comwechat_bridge.py && python3 -m py_compile /run.py /comwechat_bridge.py && command -v xdotool >/dev/null'

cat > "$COMPOSE_FILE" <<YAML
services:
  wechatpchook:
    image: ${IMAGE}
    environment:
      - VNCPASS=smoketest
      - COMWECHAT_LOGIN_RECOVERY_CLICK=true
      - COMWECHAT_LOGIN_STATE_INTERVAL=3
      - COMWECHAT_LOGIN_CLICK_INTERVAL=5
      - COMWECHAT_LOGIN_RECOVERY_TIMEOUT=60
      - COMWECHAT_BRIDGE_ENABLED=true
      - COMWECHAT_BRIDGE_API_HOST=0.0.0.0
      - COMWECHAT_BRIDGE_API_PORT=19088
      - COMWECHAT_API_PORT=18888
    ipc: host
    volumes:
      - comwechat_smoke_files:/home/user/.wine/drive_c/users/user/My Documents/WeChat Files/
      - comwechat_smoke_data:/home/user/.wine/drive_c/users/user/Application Data/
    privileged: true
    network_mode: bridge

volumes:
  comwechat_smoke_files:
  comwechat_smoke_data:
YAML

docker compose -p "$PROJECT" -f "$COMPOSE_FILE" down -v >/dev/null 2>&1 || true
docker compose -p "$PROJECT" -f "$COMPOSE_FILE" up -d

container_id=""
health_ready=0
for _ in $(seq 1 90); do
  container_id="$(docker compose -p "$PROJECT" -f "$COMPOSE_FILE" ps -q wechatpchook)"
  if [ -n "$container_id" ] && docker exec "$container_id" sh -lc \
    'python3 - <<PY
import json
import urllib.request

try:
    with urllib.request.urlopen("http://127.0.0.1:19088/healthz", timeout=2) as response:
        body = json.load(response)
except Exception:
    raise SystemExit(1)

raise SystemExit(0 if body.get("hooks_ready") is True else 1)
PY'
  then
    health_ready=1
    break
  fi
  sleep 2
done

if [ -z "$container_id" ] || [ "$health_ready" -ne 1 ]; then
  echo "Smoke-test container did not become healthy" >&2
  if [ -n "$container_id" ]; then
    docker logs --tail 180 "$container_id" >&2 || true
  fi
  exit 1
fi

docker exec "$container_id" sh -lc \
  'python3 - <<PY
import urllib.request

checks = [
    "http://127.0.0.1:18888/api/?type=0",
    "http://127.0.0.1:19088/healthz",
]

for url in checks:
    with urllib.request.urlopen(url, timeout=5) as response:
        print(url, response.status, response.read(200).decode("utf-8", "replace"))
PY'

logs="$(docker logs --tail 180 "$container_id")"
printf '%s\n' "$logs"

if ! printf '%s\n' "$logs" | grep -q "登录恢复点击监控已启动"; then
  echo "Login recovery click monitor did not start" >&2
  exit 1
fi
