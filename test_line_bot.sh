#!/bin/bash
# test_line_bot.sh - LINE 報價搜尋系統測試腳本

N8N_HOST="https://alstonn8n2026.zeabur.app"

echo "=== 測試 1：品名搜尋（棘輪）==="
curl -sS -X POST "$N8N_HOST/webhook/line-quotation" \
  -H "Content-Type: application/json" \
  -d '{"events":[{"type":"message","message":{"type":"text","text":"品名:棘輪"},"replyToken":"test1","source":{"userId":"U123"}}]}'

echo ""
echo "✅ 測試 1 完成"
sleep 2

echo ""
echo "=== 測試 2：廠商搜尋（新三和）==="
curl -sS -X POST "$N8N_HOST/webhook/line-quotation" \
  -H "Content-Type: application/json" \
  -d '{"events":[{"type":"message","message":{"type":"text","text":"廠商:新三和"},"replyToken":"test2","source":{"userId":"U123"}}]}'

echo ""
echo "✅ 測試 2 完成"
sleep 2

echo ""
echo "=== 測試 3：加工類型搜尋（表面處理）==="
curl -sS -X POST "$N8N_HOST/webhook/line-quotation" \
  -H "Content-Type: application/json" \
  -d '{"events":[{"type":"message","message":{"type":"text","text":"加工類型:表面處理"},"replyToken":"test3","source":{"userId":"U123"}}]}'

echo ""
echo "✅ 測試 3 完成"

echo ""
echo "🎯 測試完成！"
echo "如果顯示 404 錯誤，請到 n8n UI 手動開關 Active toggle"
