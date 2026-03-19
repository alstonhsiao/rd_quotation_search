#!/bin/bash
# 本機自動同步腳本
# 使用方式：每天自動執行兩次

cd /Users/alston/Documents/AntiGravity/rd_quotation_search

# 方法 1：如果有 Service Account
# python3 sync_sheets_to_json.py

# 方法 2：手動匯出（推薦，因為沒有 Service Account）
# 1. 手動從 Google Sheets 下載最新 CSV
# 2. 將 CSV 放在此專案根目錄，命名為 latest.csv
# 3. 執行轉換
if [ -f "latest.csv" ]; then
    python3 sync_sheets_manual.py latest.csv
    
    # 推送到 GitHub
    git add quotations.json
    git commit -m "🔄 Auto-sync: $(date +'%Y-%m-%d %H:%M:%S')"
    git push
    
    echo "✅ 同步完成: $(date)"
else
    echo "❌ 找不到 latest.csv，請先從 Google Sheets 匯出"
fi

# 設定 crontab（執行以下命令）：
# crontab -e
# 
# 加入以下兩行（每天 09:00 和 21:00）：
# 0 9 * * * /Users/alston/Documents/AntiGravity/rd_quotation_search/sync_local.sh >> /tmp/sync_sheets.log 2>&1
# 0 21 * * * /Users/alston/Documents/AntiGravity/rd_quotation_search/sync_local.sh >> /tmp/sync_sheets.log 2>&1
