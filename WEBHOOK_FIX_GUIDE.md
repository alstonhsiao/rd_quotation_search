# 🔧 Webhook 手動修復指引

## 問題狀況

- ✅ Workflow 已建立並啟用（WUI9OBlNcbvalbs8）
- ✅ Parse & Route 節點已修正（支援 `input.body || input`）
- ✅ 資料已同步（quotations.json，490 筆）
- ❌ Webhook endpoint 返回 404：`POST line-quotation not registered`

## 根本原因

**n8n Zeabur 平台限制**：透過 API activate/deactivate 無法觸發 production webhook 註冊。必須在 Web UI 中手動操作 Active 開關才能正確註冊 webhook。

---

## ⚠️ 立即修復步驟（必須執行）

### 1. 登入 n8n Web UI

```
https://alstonn8n2026.zeabur.app
```

### 2. 找到 Workflow

- 在左側選單點選「Workflows」
- 找到「**LINE 報價搜尋系統**」（ID: `WUI9OBlNcbvalbs8`）
- 點選進入編輯器

### 3. 關閉 Active Toggle

- 在右上角找到 **Active** 開關（目前應該是藍色/開啟狀態）
- **點擊關閉**（變成灰色）
- 等待 **3 秒鐘**

### 4. 重新開啟 Active Toggle

- **點擊開啟** Active 開關（變成藍色）
- 應該會看到通知：「Workflow activated」

### 5. 驗證修復

在終端執行：

```bash
curl -X POST "https://alstonn8n2026.zeabur.app/webhook/line-quotation" \
  -H "Content-Type: application/json" \
  -d '{"events":[{"type":"message","message":{"type":"text","text":"品名:棘輪"},"replyToken":"test1","source":{"userId":"U123"}}]}'
```

**預期結果**：
- ✅ 無回應（200 OK）
- ❌ 不應該看到 404 錯誤

---

## 📱 LINE Bot 測試步驟

修復 webhook 後，在 LINE 中測試：

### 測試 1：品名搜尋
```
品名:棘輪
```

**預期結果**：
- Flex Message 卡片顯示「棘輪」相關報價
- 包含廠商、加工類型、填表人、日期
- 如有報價單連結，顯示「查看報價單 →」按鈕
- 底部有 Quick Reply 按鈕（🔍 品名搜尋、🏭 廠商搜尋、⚙️ 加工類型搜尋）

### 測試 2：廠商搜尋
```
廠商:新三和
```

**預期結果**：
- 顯示「新三和」的所有報價記錄
- 按時間排序（最新在前）
- 最多顯示 10 筆結果
- 如果超過 10 筆，會有「共 X 筆結果，顯示最新 10 筆」的提示卡片

### 測試 3：加工類型搜尋
```
加工類型:表面處理
```

**預期結果**：
- 顯示「表面處理」相關報價
- Carousel 卡片可以左右滑動瀏覽
- 每張卡片包含完整資訊

### 測試 4：查詢不存在的關鍵字
```
品名:不存在的產品名稱
```

**預期結果**：
- 文字訊息：「『不存在的產品名稱』查無相關報價資料 😕」
- 提示「請重新搜尋或點選按鈕」
- 顯示 Quick Reply 按鈕

---

## 🛠️ 技術細節

### Workflow 設定（已完成）

- **Webhook Path**: `line-quotation`
- **Response Mode**: `onReceived`（立即回應 200 OK）
- **HTTP Method**: POST
- **節點數量**: 8 個主要節點
  1. LINE Webhook
  2. Parse & Route（已修正：支援 `input.body || input`）
  3. Switch Action
  4. Reply Prompt
  5. Reply Help
  6. Read Quotations JSON
  7. Search & Build Flex
  8. Reply Result

### 資料來源

- **GitHub**: `https://raw.githubusercontent.com/alstonhsiao/rd_quotation_search/main/quotations.json`
- **資料筆數**: 490 筆
- **最後更新**: 2026-03-19T06:33:08
- **更新方式**: 手動執行 `python3 sync_sheets_manual.py`，然後 `git push`

### 指令格式（使用者輸入）

| 搜尋類型 | 格式 | 範例 |
|---|---|---|
| 品名 | `品名:關鍵字` | `品名:棘輪` |
| 廠商 | `廠商:關鍵字` | `廠商:新三和` |
| 加工類型 | `加工類型:關鍵字` | `加工類型:表面處理` |

**支援格式變化**：
- 全形冒號：`品名：棘輪`
- 空格分隔：`品名 棘輪`

---

## 📝 已知問題

1. **Google Drive 連結無法在 LINE 內預覽**
   - 報價單連結為 `open?id=` 格式
   - 點擊後會使用外部瀏覽器開啟
   - 無法在 LINE 內直接顯示圖片

2. **多個報價單連結僅顯示第一個**
   - 如果欄 F 有多個 Drive 連結（逗號分隔）
   - 目前只取第一個連結顯示

3. **資料非即時同步**
   - JSON 資料庫需要手動執行同步腳本
   - 不會自動從 Google Sheets 讀取最新資料

---

## 🔄 資料更新流程（未來維護）

當 Google Sheets 有新報價資料時：

```bash
# 1. 下載最新 CSV
# （手動從 Google Sheets 匯出 data.csv）

# 2. 執行同步腳本
python3 sync_sheets_manual.py

# 3. 提交到 GitHub
git add quotations.json
git commit -m "data: update quotations (新增 X 筆資料)"
git push

# 4. LINE Bot 會自動讀取更新後的 JSON
# （無需重新部署 workflow）
```

---

## ✅ 完成檢查清單

執行手動修復後，確認以下項目：

- [ ] n8n UI 中 Workflow Active toggle 為藍色（開啟）
- [ ] `curl` 測試 webhook 不再返回 404 錯誤
- [ ] LINE Bot 回應「品名:棘輪」能正確顯示 Flex Message
- [ ] 搜尋「廠商:新三和」能找到相關報價
- [ ] 搜尋「加工類型:表面處理」能正確篩選
- [ ] 查詢不存在的關鍵字會顯示「查無資料」訊息
- [ ] Quick Reply 按鈕能正常運作
- [ ] 報價單連結能正確開啟 Google Drive

---

## 📞 如果仍然失敗

如果手動開關 Active toggle 後仍然 404，請檢查：

1. **Workflow 版本**
   - 在 n8n UI 中確認 Workflow 內容是最新的
   - 檢查 Parse & Route 節點是否有 `const body = input.body || input;` 程式碼

2. **Webhook 設定**
   - 點擊 LINE Webhook 節點
   - 確認 **Path** = `line-quotation`
   - 確認 **Response Mode** = `On Received`（或顯示為「Immediately」）
   - 確認 **HTTP Method** = `POST`

3. **重新匯入 Workflow**
   - 如果設定不正確，可以刪除現有 workflow
   - 在 n8n UI 中選擇「Import from File」
   - 上傳專案中的 `n8n_workflow.json`
   - **記得手動開啟 Active toggle**

4. **LINE Webhook URL 設定**
   - 登入 [LINE Developers Console](https://developers.line.biz/)
   - 確認 Webhook URL 為：`https://alstonn8n2026.zeabur.app/webhook/line-quotation`
   - 確認「Use webhook」開關已開啟

---

**建議**：完成手動修復後，立即使用 `test_line_bot.sh` 腳本進行完整測試，確保所有功能正常運作。

```bash
./test_line_bot.sh
```

如果測試成功（不再顯示 404），就可以在 LINE app 中開始使用了！🎉
