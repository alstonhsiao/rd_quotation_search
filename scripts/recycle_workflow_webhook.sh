#!/usr/bin/env bash
set -euo pipefail

# recycle_workflow_webhook.sh
# 用途：
# 1) 確保 webhook 節點具有 webhookId（根因修復：n8n bug #21614）
# 2) 透過 n8n API 將 workflow deactivate -> activate
# 3) 立即探測 production webhook 是否已註冊成功
#
# 用法：
# ./scripts/recycle_workflow_webhook.sh [WORKFLOW_ID]
#
# 可選環境變數：
# - ENV_FILE (預設: ../.env.local)
# - ATTEMPTS (預設: 3)
# - SLEEP_SECONDS (預設: 2)
# - N8N_HOST / N8N_API_KEY / N8N_WEBHOOK_PATH (可直接覆蓋)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env.local}"
WORKFLOW_ID="${1:-Hr7UCyvl4DLJrQnc}"
ATTEMPTS="${ATTEMPTS:-3}"
SLEEP_SECONDS="${SLEEP_SECONDS:-2}"

get_env() {
  local key="$1"
  if [[ -f "$ENV_FILE" ]]; then
    grep -E "^${key}=" "$ENV_FILE" | head -n 1 | cut -d= -f2-
  fi
}

N8N_HOST="${N8N_HOST:-$(get_env N8N_HOST)}"
N8N_API_KEY="${N8N_API_KEY:-$(get_env N8N_API_KEY)}"
N8N_WEBHOOK_PATH="${N8N_WEBHOOK_PATH:-$(get_env N8N_WEBHOOK_PATH)}"
N8N_WEBHOOK_PATH="${N8N_WEBHOOK_PATH:-/webhook/line-quotation}"

if [[ -z "$N8N_HOST" || -z "$N8N_API_KEY" ]]; then
  echo "❌ 缺少 N8N_HOST 或 N8N_API_KEY"
  echo "請確認 $ENV_FILE 或環境變數設定。"
  exit 1
fi

probe_webhook() {
  local out_file
  out_file="$(mktemp)"
  local code
  code=$(curl -sS -o "$out_file" -w "%{http_code}" \
    -X POST "${N8N_HOST}${N8N_WEBHOOK_PATH}" \
    -H "Content-Type: application/json" \
    -d '{"events":[{"type":"message","message":{"type":"text","text":"probe"},"replyToken":"probe-token","source":{"userId":"Uprobe"}}]}' || true)
  local body
  body="$(cat "$out_file")"
  rm -f "$out_file"
  echo "$code|$body"
}

ensure_webhook_ids() {
  # Root cause fix: n8n bug #21614 / PR #27161
  # Webhook nodes without webhookId get the wrong path registered.
  echo "🔧 確保 webhook 節點都有 webhookId..."

  local wf_json
  wf_json=$(curl -sS \
    "${N8N_HOST}/api/v1/workflows/${WORKFLOW_ID}" \
    -H "X-N8N-API-KEY: ${N8N_API_KEY}")

  local needs_fix
  needs_fix=$(python3 -c "
import json, sys
wf = json.loads('''${wf_json//\'/\\\'}''')
for n in wf.get('nodes', []):
    if n.get('type') == 'n8n-nodes-base.webhook' and not n.get('webhookId'):
        print('yes')
        sys.exit(0)
print('no')
" 2>/dev/null || echo "error")

  if [[ "$needs_fix" == "yes" ]]; then
    echo "  發現缺少 webhookId 的 webhook 節點，正在修復..."
    python3 "${SCRIPT_DIR}/fix_webhook_id.py"
    return 0
  elif [[ "$needs_fix" == "no" ]]; then
    echo "  ✅ 所有 webhook 節點都已有 webhookId"
    return 1  # no fix needed, will still deactivate/activate
  else
    echo "  ⚠️  無法檢查 webhookId，繼續 deactivate/activate..."
    return 1
  fi
}

deactivate_activate_once() {
  curl -sS -X POST \
    "${N8N_HOST}/api/v1/workflows/${WORKFLOW_ID}/deactivate" \
    -H "X-N8N-API-KEY: ${N8N_API_KEY}" \
    -H "Content-Type: application/json" >/dev/null

  sleep "$SLEEP_SECONDS"

  curl -sS -X POST \
    "${N8N_HOST}/api/v1/workflows/${WORKFLOW_ID}/activate" \
    -H "X-N8N-API-KEY: ${N8N_API_KEY}" \
    -H "Content-Type: application/json" >/dev/null
}

echo "🔁 Workflow: ${WORKFLOW_ID}"
echo "🌐 Host: ${N8N_HOST}"
echo "🪝 Webhook: ${N8N_WEBHOOK_PATH}"
echo ""

# Step 0: Ensure webhookId exists (root cause fix)
if ensure_webhook_ids; then
  # fix_webhook_id.py already did deactivate/activate + probe
  echo ""
  probe="$(probe_webhook)"
  code="${probe%%|*}"
  if [[ "$code" != "404" ]]; then
    echo "✅ Webhook 已可用 (webhookId 修復後)"
    exit 0
  fi
fi

for ((i=1; i<=ATTEMPTS; i++)); do
  echo ""
  echo "== Attempt ${i}/${ATTEMPTS} =="
  deactivate_activate_once
  sleep "$SLEEP_SECONDS"

  probe="$(probe_webhook)"
  code="${probe%%|*}"
  body="${probe#*|}"

  echo "Webhook probe HTTP: ${code}"
  if [[ "$code" != "404" ]]; then
    echo "✅ Webhook 已可用"
    echo "Response: ${body}"
    exit 0
  fi

  echo "⚠️  仍為 404（未註冊）"
done

echo ""
echo "❌ API 自動切換後仍未註冊 webhook。"
echo "請到 n8n UI 手動切換 Active（關→開）一次。"
exit 2

