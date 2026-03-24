#!/usr/bin/env python3
"""Notionデータベースの自動セットアップスクリプト"""

from __future__ import annotations

import sys
import json
import requests
from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv(Path(__file__).parent / ".env")

from config import Config

NOTION_API_VERSION = "2022-06-28"


def notion_headers():
    return {
        "Authorization": f"Bearer {Config.NOTION_API_KEY}",
        "Notion-Version": NOTION_API_VERSION,
        "Content-Type": "application/json",
    }


def create_database(parent_page_id: str, title: str, properties: dict) -> str:
    """Notionデータベースを作成し、プロパティを設定"""
    # 1. データベース作成
    payload = {
        "parent": {"type": "page_id", "page_id": parent_page_id},
        "title": [{"type": "text", "text": {"content": title}}],
        "properties": {"Name": {"title": {}}},
    }
    r = requests.post(
        "https://api.notion.com/v1/databases",
        headers=notion_headers(),
        json=payload,
    )
    if r.status_code != 200:
        print(f"  エラー: DB作成失敗 ({r.status_code}): {r.text[:300]}")
        sys.exit(1)

    db_id = r.json()["id"]

    # 2. プロパティを追加（REST APIで直接PATCHする）
    # Nameをtitleプロパティとしてリネーム
    title_prop = None
    for k, v in properties.items():
        if "title" in v:
            title_prop = k
            break

    patch_props = {}
    for k, v in properties.items():
        if "title" in v:
            patch_props["Name"] = {"name": k}
        else:
            patch_props[k] = v

    r2 = requests.patch(
        f"https://api.notion.com/v1/databases/{db_id}",
        headers=notion_headers(),
        json={"properties": patch_props},
    )
    if r2.status_code != 200:
        print(f"  警告: プロパティ追加に失敗 ({r2.status_code}): {r2.text[:300]}")

    return db_id


def main():
    if not Config.NOTION_API_KEY:
        print("エラー: NOTION_API_KEY が .env に設定されていません")
        sys.exit(1)

    if len(sys.argv) < 2:
        print("使い方: python3 setup_notion.py <NotionページID>")
        print()
        print("手順:")
        print("1. Notionで空のページを作成")
        print("2. そのページのURLからIDを取得")
        print("   例: https://www.notion.so/My-Page-abc123def456...")
        print("   → abc123def456... がページID")
        print("3. Notion Integrationをそのページに接続")
        print("   (ページの ... → 接続 → LifeLogger を選択)")
        print("4. このスクリプトを実行:")
        print("   python3 setup_notion.py abc123def456...")
        sys.exit(1)

    parent_page_id = sys.argv[1].replace("-", "")

    print("Notionデータベースを作成中...")

    # アクティビティログDB
    activity_db_id = create_database(
        parent_page_id,
        "LifeLogger - アクティビティログ",
        {
            "タイトル": {"title": {}},
            "日時": {"date": {}},
            "アプリ": {"select": {"options": []}},
            "カテゴリ": {
                "select": {
                    "options": [
                        {"name": "仕事", "color": "blue"},
                        {"name": "SNS", "color": "purple"},
                        {"name": "エンタメ", "color": "pink"},
                        {"name": "学習", "color": "green"},
                        {"name": "コミュニケーション", "color": "yellow"},
                        {"name": "その他", "color": "gray"},
                    ]
                }
            },
            "詳細": {"rich_text": {}},
            "生産性": {"number": {"format": "number"}},
            "スクリーンショットパス": {"rich_text": {}},
            "日付": {"date": {}},
        },
    )
    print(f"  アクティビティログDB: {activity_db_id}")

    # 日次サマリーDB
    summary_db_id = create_database(
        parent_page_id,
        "LifeLogger - 日次サマリー",
        {
            "日付": {"title": {}},
            "総作業時間": {"number": {"format": "number"}},
            "カテゴリ別時間": {"rich_text": {}},
            "アプリ別時間": {"rich_text": {}},
            "平均生産性": {"number": {"format": "number"}},
            "日次レポート": {"rich_text": {}},
        },
    )
    print(f"  日次サマリーDB: {summary_db_id}")

    # .env更新
    env_path = Path(__file__).parent / ".env"
    env_content = env_path.read_text() if env_path.exists() else ""
    lines = env_content.split("\n")
    updated = []
    db_set = summary_set = False

    for line in lines:
        if line.startswith("NOTION_DATABASE_ID="):
            updated.append(f"NOTION_DATABASE_ID={activity_db_id}")
            db_set = True
        elif line.startswith("NOTION_SUMMARY_DATABASE_ID="):
            updated.append(f"NOTION_SUMMARY_DATABASE_ID={summary_db_id}")
            summary_set = True
        else:
            updated.append(line)

    if not db_set:
        updated.append(f"NOTION_DATABASE_ID={activity_db_id}")
    if not summary_set:
        updated.append(f"NOTION_SUMMARY_DATABASE_ID={summary_db_id}")

    env_path.write_text("\n".join(updated))

    print()
    print("セットアップ完了！ .env を自動更新しました。")
    print("動作テスト: python3 test_once.py")
    print("常駐化:     bash setup_launchd.sh install")


if __name__ == "__main__":
    main()
