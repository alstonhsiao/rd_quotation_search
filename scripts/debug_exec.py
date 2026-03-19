#!/usr/bin/env python3
import json
import sys

exec_id = sys.argv[1] if len(sys.argv) > 1 else "33948"

with open(f'/tmp/exec_{exec_id}.json') as f:
    d = json.load(f)

print(f"=== 執行記錄 {exec_id} ===")
print(f"狀態: {d.get('status')}")
print(f"Workflow: {d.get('workflowId')}")
print(f"開始: {d.get('startedAt')}")
print(f"結束: {d.get('stoppedAt')}")

# 檢查主錯誤
err = d.get("data", {}).get("resultData", {}).get("error", {})
if err:
    print(f"\n❌ 主要錯誤:")
    print(f"  訊息: {err.get('message')}")
    print(f"  節點: {err.get('node', {}).get('name')}")
    print(f"  類型: {err.get('name')}")

# 查看各節點執行狀況
runs = d.get("data", {}).get("resultData", {}).get("runData", {})
print("\n📋 節點執行狀況:")
for node_name, execs in runs.items():
    if execs and len(execs) > 0:
        exec_data = execs[0]
        has_error = exec_data.get("error")
        has_data = exec_data.get("data")
        
        status = "❌ 錯誤" if has_error else ("✅ 成功" if has_data else "⚠️  未知")
        print(f"  {node_name}: {status}")
        
        if has_error:
            err_msg = exec_data['error'].get('message', 'unknown')
            print(f"     錯誤訊息: {err_msg[:150]}")
        elif has_data:
            main_data = exec_data['data'].get('main', [[]])[0]
            if main_data:
                print(f"     輸出: {len(main_data)} 項")
