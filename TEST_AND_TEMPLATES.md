# LINE 報價搜尋系統 - 測試與範本

## ✅ 正確的輸入格式範本

### 1. 品名搜尋
```
品名:棘輪
```

```
品名:手柄
```

```
品名:板手
```

### 2. 廠商搜尋
```
廠商:新三和
```

```
廠商:亮新
```

```
廠商:東林
```

### 3. 加工類型搜尋
```
加工類型:表面處理
```

```
加工類型:塑膠成型
```

```
加工類型:車床
```

---

## 🔧 必要修復步驟（請按順序執行）

### 步驟 1：在 n8n UI 啟用 Workflow

**當前狀況**：Webhook 未正確註冊（API 限制）

**解決方式**：
1. 開啟：https://alstonn8n2026.zeabur.app
2. 登入後找到「**LINE 報價搜尋系統**」workflow
3. 點擊右上角的 **Activ開關：
   - 如果已是綠色（啟用），先點一下**關閉**（變灰）
   - 等待 3 秒
   - 再點一下**開啟**（變綠）✅
4. 確認看到「Workflow activated」提示

---

### 步驟 2：測試 Webhook（用 curl）

```bash
# 設定環境變數
N8N_HOST="https://alstonn8n2026.zeabur.app"

# 測試 webhook 是否回應
curl -X POST "$N8N_HOST/webhook/line-quotation" \
  -H "Content-Type: application/json" \
  -d '{
    "events": [{
      "type": "message",
      "message": {
        "type": "text",
        "text": "品名:棘輪"
      },
      "replyToken": "test-token-12345",
      "source": {
        "userId": "U1234567890abcdef"
      }
    }]
  }'
```

**預期結果**：
- ✅ 無回應（200 OK）= Webhook 正常（n8n 的 `onReceived` 模式）
- ❌ 404 錯誤 = Webhook 未註冊，需回到步驟 1

---

### 步驟 3：在 LINE App 測試

**開啟 LINE，傳送以下訊息給機器人**：

```
品名:棘輪
```

**預期結果**：
- ✅ 收到 Flex Message 卡片（顯示報價資料）
- ✅ 卡片包含：品名、廠商、加工類型、填表人、日期、備註
- ✅ 有「查看報價單」按鈕（連結到 Google Drive）

---

## 🧪 完整測試腳本

```bash
#!/bin/bash
# test_line_bot.sh

N8N_HOST="https://alstonn8n2026.zeabur.app"

echo "=== 測試 1：品名搜尋（棘輪）==="
curl -X POST "$N8N_HOST/webhook/line-quotation" \
  -H "Content-Type: application/json" \
  -d '{"events":[{"type":"message","message":{"type":"text","text":"品名:棘輪"},"replyToken":"test1","source":{"userId":"U123"}}]}' \
  && echo "✅ 測試 1 完成" || echo "❌ 測試 1 失敗"

sleep 2

echo ""
echo "=== 測試 2：廠商搜尋（新三和）==="
curl -X POST "$N8N_HOST/webhook/line-quotation" \
  -H "Content-Type: application/json" \
  -d '{"events":[{"type":"message","message":{"type":"text","text":"廠商:新三和"},"replyToken":"test2","source":{"userId":"U123"}}]}' \
  && echo "✅ 測試 2 完成" || echo "❌ 測試 2 失敗"

sleep 2

echo ""
echo "=== 測試 3：加工類型搜尋（表面處理）==="
curl -X POST "$N8N_HOST/webhook/line-quotation" \
  -H "Content-Type: application/json" \
  -d '{"events":[{"type":"message","message":{"type":"text","text":"加工類型:表面處理"},"replyToken":"test3","source":{"userId":"U123"}}]}' \
  && echo "✅ 測試 3 完成" || echo "❌ 測試 3 失敗"

echo ""
echo "=== 測試 4：查無資料（不存在的品名）==="
curl -X POST "$N8N_HOST/webhook/line-quotation" \
  -H "Content-Type: application/json" \
  -d '{"events":[{"type":"message","message":{"type":"text","text":"品名:不存在的產品xyz123"},"replyToken":"test4","source":{"userId":"U123"}}]}' \
  && echo "✅ 測試 4 完成" || echo "❌ 測試 4 失敗"
```

**使用方式**：
```bash
chmod +x test_line_bot.sh
./test_line_bot.sh
```

---

## 📊 當前系統狀態

- **資料庫**：490 筆資料 ✅
- **GitHub JSON**：https://raw.githubusercontent.com/alstonhsiao/rd_quotation_search/main/quotations.json ✅
- **Workflow ID**：`WUI9OBlNcbvalbs8`
- **Webhook URL**：`https://alstonn8n2026.zeabur.app/webhook/line-quotation`
- **Webhook 狀態**：❌ 未註冊（需在 UI 手動啟用）

---

## 🐛 已知問題與解決方式

### 問題 1：Webhook 404 錯誤
**原因**：n8n API 無法正確註冊 production webhook  
**解決**：必須在 n8n UI 手動開關 Active toggle

### 問題 2：執行記綠顯示 error 但無節點執行
**原因**：Webhook 未註冊，請求根本沒進入 workflow  
**解決**：同問題 1

### 問題 3：LINE 沒反應
**可能原因**：
1. Webhook 未註冊（404）→ 回到步驟 1
2. LINE Webhook URL 設定錯誤 → 檢查 LINE Developer Console
3. Token 過期 → 檢查 .env.local 的 LINE_CHANNEL_ACCESS_TOKEN

---

## 🎯 下一步行動

1. **立即執行**：到 n8n UI 手動開關 Active toggle
2. **測試**：用上面的測試腳本或直接在 LINE 測試
3. **驗證**：應該收到 Flex Message 回應
4. **完成**：系統正常運作 🎉
