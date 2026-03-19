#!/bin/bash
# test_line_bot.sh - LINE 報價搜尋系統 v2 測試腳本

N8N_HOST="https://alstonn8n2026.zeabur.app"

echo "=== 測試 1：任意文字 → 主目錄 ==="
curl -sS -X POST "$N8N_HOST/webhook/line-quotation" \
  -H "Content-Type: application/json" \
  -d '{"events":[{"type":"message","message":{"type":"text","text":"hello"},"replyToken":"test-menu","source":{"userId":"U123"}}]}'
echo ""
echo "✅ 測試 1 完成"
sleep 2

echo ""
echo "=== 測試 2：搜尋加工類型 → 提示 ==="
curl -sS -X POST "$N8N_HOST/webhook/line-quotation" \
  -H "Content-Type: application/json" \
  -d '{"events":[{"type":"message","message":{"type":"text","text":"搜尋加工類型"},"replyToken":"test-prompt1","source":{"userId":"U123"}}]}'
echo ""
echo "✅ 測試 2 完成"
sleep 2

echo ""
echo "=== 測試 3：加工類型:表面處理 → 搜尋結果 ==="
curl -sS -X POST "$N8N_HOST/webhook/line-quotation" \
  -H "Content-Type: application/json" \
  -d '{"events":[{"type":"message","message":{"type":"text","text":"加工類型:表面處理"},"replyToken":"test-search1","source":{"userId":"U123"}}]}'
echo ""
echo "✅ 測試 3 完成"
sleep 2

echo ""
echo "=== 測試 4：搜尋廠商 → 提示 ==="
curl -sS -X POST "$N8N_HOST/webhook/line-quotation" \
  -H "Content-Type: application/json" \
  -d '{"events":[{"type":"message","message":{"type":"text","text":"搜尋廠商"},"replyToken":"test-prompt2","source":{"userId":"U123"}}]}'
echo ""
echo "✅ 測試 4 完成"
sleep 2

echo ""
echo "=== 測試 5：廠商:新三和 → 搜尋結果 ==="
curl -sS -X POST "$N8N_HOST/webhook/line-quotation" \
  -H "Content-Type: application/json" \
  -d '{"events":[{"type":"message","message":{"type":"text","text":"廠商:新三和"},"replyToken":"test-search2","source":{"userId":"U123"}}]}'
echo ""
echo "✅ 測試 5 完成"

echo ""
echo "🎯 全部測試完成！"
echo "如果顯示 404 錯誤，請到 n8n UI 手動開關 Active toggle"
