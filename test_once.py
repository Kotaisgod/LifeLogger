#!/usr/bin/env python3
from __future__ import annotations
"""1回だけキャプチャ→分析→保存のテスト"""

import sys
import logging
from datetime import datetime

from config import Config
from utils import setup_logging
from capture import ScreenCapture
from analyzer import analyze_screenshot
from notion_logger import NotionLogger
from db import LocalDB

setup_logging()
logger = logging.getLogger(__name__)

errors = Config.validate()
if errors:
    for err in errors:
        print(f"エラー: {err}")
    sys.exit(1)

Config.ensure_dirs()

print("=== LifeLogger テスト実行 ===")

# 1. スクリーンショット
print("1. スクリーンショット撮影中...")
capture = ScreenCapture()
path = capture.capture()
if path is None:
    print("   スクリーンショットがスキップされました（画面ロック中 or 変化なし）")
    # 強制的に撮影
    import subprocess
    from pathlib import Path
    test_dir = Config.SCREENSHOT_DIR / "test"
    test_dir.mkdir(parents=True, exist_ok=True)
    path = test_dir / "test.png"
    subprocess.run(["screencapture", "-x", str(path)], check=True)
    print(f"   強制撮影: {path}")

print(f"   保存先: {path}")

# 2. AI分析
print("2. Gemini AI分析中...")
result = analyze_screenshot(path)
if result is None:
    print("   分析失敗！")
    sys.exit(1)

print(f"   アクティビティ: {result.activity}")
print(f"   アプリ: {result.app_name}")
print(f"   カテゴリ: {result.category}")
print(f"   生産性: {result.productivity_score}")
print(f"   詳細: {result.detail}")

# 3. ローカルDB保存
print("3. ローカルDB保存中...")
db = LocalDB()
timestamp = datetime.now()
db.save_activity(timestamp, path, result, None)
print("   ローカルDB保存完了")

# 4. Notion保存
print("4. Notionに保存中...")
notion = NotionLogger()
page_id = notion.log_activity(result, path, timestamp)
if page_id:
    print(f"   Notion保存完了: {page_id}")
    db.update_notion_page_id(1, page_id)
else:
    print("   Notion保存失敗！")

print("\n=== テスト完了 ===")
