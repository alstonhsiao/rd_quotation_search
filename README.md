# rd_quotation_search

LINE × n8n 供應商報價搜尋系統。透過 LINE 按鈕互動，搜尋 Google Sheets 報價管理表，以 Flex Message 卡片回傳結果。

---

## 功能概述

| 功能 | 說明 |
|---|---|
| Quick Reply 按鈕選擇搜尋維度 | 品名、廠商、加工類型 |
| 關鍵字模糊搜尋 | 中英文包含比對，不分大小寫 |
| Flex Message 卡片結果 | 每筆含品名、加工類型、廠商、填表人、日期、備註、報價單連結 |
| 結果限制 | 最多 10 筆，按時間由新到舊排序 |
| 無需認證讀取 | 直接讀取公開 Google Sheets CSV，無需 Service Account |
| Stateless 設計 | 使用指令格式（如 `品名:棘輪`），無需 session 管理 |

---

## 技術架構

```
Google Sheets (私有試算表)
    ↓ (手動/自動同步，每天 2 次)
本機/GitHub Actions 腳本
    ↓
quotations.json (存於 GitHub)
    ↓ (公開 URL)
n8n Workflow (讀取 JSON)
    ├─ 解析 LINE Event & 判斷指令格式
    ├─ 從 JSON 執行搜尋 + 排序
    ├─ 組裝 Flex Message 卡片
    └─ LINE Reply API
```

**設計特色**：
- ✅ 無需 Google Service Account（可手動同步）
- ✅ Stateless（無 session 狀態）
- ✅ JSON 資料庫（快速搜尋）
- ✅ 自動同步（每天 09:00 & 21:00）
- ✅ 單一 Workflow 完成所有邏輯

---

## 資料來源

**資料庫架構**：JSON 靜態檔案（每天自動同步 2 次）

- **來源試算表**：`首君 供應商報價管理表單-1`
- **試算表 ID**：`1WZ_sZvfBjUiIPHrY6WkdR1yBXLHdYB_Fb8T3VTYQ0GI`
- **主資料分頁**：`表單回應 1`
- **JSON 資料庫**：`quotations.json`（託管於 GitHub）
- **同步頻率**：每天 09:00 和 21:00（自動執行）

### 主資料欄位

| 欄 | 欄位名稱 | 說明 |
|---|---|---|
| A | 時間戳記 | 填表時間 |
| B | 加工類型 | 如：表面處理、車床/模具、沖壓/模具 |
| C | 廠商 | 供應商名稱 |
| D | 填表人 | 員工姓名 |
| E | 品名 | 品項名稱（模糊搜尋主要欄位） |
| F | 拍照報價單 | Google Drive 連結 |
| G | 備註 | 補充資訊、單價等 |

### Session 分頁欄位

| 欄 | 欄位名稱 |
|---|---|
| A | userId (LINE User ID) |
| B | searchMode (品名/廠商/加工) |
| C | timestamp (ISO 8601) |

---

## n8n Workflow 架構

### Nodes 清單

| # | Node 名稱 | 類型 | 說明 |
|---|---|---|---|
| 1 | LINE Webhook | Webhook Trigger | 接收 LINE POST |
| 2 | Parse Event | Code (JS) | 取 userId, replyToken, text |
| 3 | Route | Switch | 指令路由 |
| 4 | Read Session | Google Sheets Read | 查詢 sessions 分頁 |
| 5 | Check Session | IF | 有效 session 判斷 |
| 6 | Read Data | Google Sheets Read | 讀 `表單回應 1!A:G` |
| 7 | Search & Filter | Code (JS) | 模糊比對 + 排序 |
| 8 | Build Flex Message | Code (JS) | 組裝 LINE Flex JSON |
| 9 | LINE Reply | HTTP Request | 呼叫 LINE Reply API |
| 10 | Write Session | Google Sheets Write | 新增/更新 session |
| 11 | Delete Session | Google Sheets Delete | 搜尋完成後清除 session |

### 使用者操作流程

```
1. 用戶傳任意訊息
   → Bot 回傳「使用說明」+ Quick Reply 按鈕
      [品名搜尋] [廠商搜尋] [加工類型搜尋]

2. 用戶點選按鈕（例：品名搜尋）
   → 寫入 session {userId, „品名", timestamp}
   → Bot 回「請輸入品名關鍵字」

3. 用戶輸入關鍵字（例：棘輪）
   → 讀取 session → 確認搜尋模式為「品名」
   → 搜尋 Google Sheets E 欄包含「棘輪」
   → 取最新 10 筆
   → 組裝 Flex Carousel 卡片
   → 刪除 session
   → 回傳結果卡片

4. 無結果
   → 回傳「查無相關報價資料 😕」+ 再次顯示 Quick Reply 按鈕
```

---

## 環境變數

所有機密資訊存於 `.env.local`（不提交 git）。

| 變數名 | 說明 |
|---|---|
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Channel 長期 Access Token |
| `LINE_CHANNEL_SECRET` | LINE Channel Secret（用於驗證簽章） |
| `GOOGLE_SPREADSHEET_ID` | 試算表 ID |
| `GOOGLE_SHEET_DATA_TAB` | 主資料分頁名（預設：`表單回應 1`） |
| `N8N_HOST` | n8n 部署網址 |
| `N8N_WEBHOOK_PATH` | Webhook 路徑 |
| `N8N_API_KEY` | n8n API 金鑰（用於 Workflow 管理） |
| `N8N_API_KEY` | n8n API Key（可選） |

---

## 部署前置作業

### 1. 資料同步設定（首次部署）

請參考 **[JSON_DATABASE_SETUP.md](./JSON_DATABASE_SETUP.md)** 完整設定指南。

**快速開始**：
```bash
# 1. 從 Google Sheets 下載 CSV
# 2. 轉換為 JSON
python3 sync_sheets_manual.py latest.csv

# 3. 推送到 GitHub
git add quotations.json
git commit -m "🔄 Initial sync"
git push
```

### 2. LINE Messaging API
1. 前往 [LINE Developers Console](https://developers.line.biz/)
2. 在 Messaging API Channel 取得 `Channel Access Token`（長期）與 `Channel Secret`
3. 設定 Webhook URL：`https://alstonn8n2026.zeabur.app/webhook/line-quotation`
4. 啟用「Use webhook」
5. 關閉「Auto-reply messages」與「Greeting messages」

### 3. n8n Workflow 部署
✅ **已完成自動部署**
- Workflow 已透過 API 上傳至 `https://alstonn8n2026.zeabur.app`
- Workflow ID: `Vq6I9dhPOOWJ63Py`
- 狀態：已激活
- 配置：使用硬編碼 Token（繞過環境變數限制）

---

## 注意事項

- `.env.local` 已加入 `.gitignore`，切勿直接 commit 機密資訊
- **JSON 資料庫**：`quotations.json` 為公開檔案，確保不含敏感資訊
- **同步頻率**：預設每天 09:00 和 21:00 更新（可在 crontab 或 GitHub Actions 調整）
- **搜尋延遲**：資料更新後最長延遲 12 小時（視同步時間而定）
- Stateless 設計：每次搜尋獨立執行，無 session 狀態
- LINE Flex Carousel 最多支援 12 個 Bubble，本專案限制 10 筆確保相容

---

## 使用方式

### 指令格式

支援三種搜尋維度，使用**指令格式**直接搜尋：

1. **品名搜尋**：`品名:關鍵字`
   - 範例：`品名:棘輪`、`品名:起子手柄`

2. **廠商搜尋**：`廠商:廠商名`
   - 範例：`廠商:新三和`、`廠商:亮新`

3. **加工類型搜尋**：`加工類型:類型名`
   - 範例：`加工類型:表面處理`、`加工類型:車床`

### 對話流程

```
User → LINE Bot: 「品名:棘輪」

LINE Bot → User:
  ┌─────────────────────────┐
  │ 品名：棘輪               │
  ├─────────────────────────┤
  │ 品名：棘輪板手           │
  │ 加工：沖壓/模具          │
  │ 廠商：新三和             │
  │ 填表人：林啟生           │
  │ 日期：2026/03/15          │
  │ 備註：單價 $120...       │
  │ [查看報價單 →]           │
  └─────────────────────────┘
  （最多顯示 10 筆，由新到舊）
```

### 查無結果時

系統會提示用戶嘗試其他搜尋方式：

```
「棘輪123」查無相關報價資料 😕
請嘗試其他關鍵字或搜尋維度
```

---

## 技術文件

- [AGENTS.md](./AGENTS.md)：完整 n8n Node 設定與 JavaScript 程式碼
