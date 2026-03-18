#!/usr/bin/env python3
"""
同步 Google Sheets 到 JSON 檔案
需求：pip install gspread oauth2client
"""

import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# 設定
SPREADSHEET_ID = "1WZ_sZvfBjUiIPHrY6WkdR1yBXLHdYB_Fb8T3VTYQ0GI"
SHEET_NAME = "表單回應 1"
OUTPUT_FILE = "quotations.json"

def sync_sheets_to_json():
    """讀取 Google Sheets 並轉換為 JSON"""
    
    # 使用 Service Account 認證（如果有的話）
    try:
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        
        # 如果有 service account，放在 .env.local 的 GOOGLE_SERVICE_ACCOUNT_JSON
        # 這裡先用手動方式
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            'service_account.json', scope)
        client = gspread.authorize(creds)
        
        # 開啟試算表
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
        
        # 取得所有資料
        data = sheet.get_all_records()
        
        # 加入更新時間戳記
        output = {
            "lastUpdated": datetime.utcnow().isoformat() + "Z",
            "totalRecords": len(data),
            "data": data
        }
        
        # 寫入 JSON 檔案
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 成功同步 {len(data)} 筆資料到 {OUTPUT_FILE}")
        print(f"📅 更新時間: {output['lastUpdated']}")
        
    except FileNotFoundError:
        print("❌ 找不到 service_account.json")
        print("請參考 README.md 設定 Google Service Account")

if __name__ == "__main__":
    sync_sheets_to_json()
