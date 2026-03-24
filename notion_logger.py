"""Notion API連携モジュール"""

from __future__ import annotations


import logging
from datetime import datetime
from pathlib import Path

from notion_client import Client

from config import Config
from analyzer import AnalysisResult

logger = logging.getLogger(__name__)


class NotionLogger:
    """Notionデータベースへのログ書き込みクラス"""

    def __init__(self):
        self.client = Client(auth=Config.NOTION_API_KEY)

    def log_activity(
        self,
        result: AnalysisResult,
        screenshot_path: Path,
        timestamp: datetime,
    ) -> str | None:
        """分析結果をNotionデータベースに記録。作成されたページIDを返す"""
        try:
            page = self.client.pages.create(
                parent={"database_id": Config.NOTION_DATABASE_ID},
                properties={
                    "タイトル": {
                        "title": [
                            {"text": {"content": result.activity[:100]}}
                        ]
                    },
                    "日時": {
                        "date": {
                            "start": timestamp.isoformat(),
                        }
                    },
                    "アプリ": {
                        "select": {"name": result.app_name[:100]}
                    },
                    "カテゴリ": {
                        "select": {"name": result.category}
                    },
                    "詳細": {
                        "rich_text": [
                            {"text": {"content": result.detail[:2000]}}
                        ]
                    },
                    "生産性": {
                        "number": result.productivity_score
                    },
                    "スクリーンショットパス": {
                        "rich_text": [
                            {"text": {"content": str(screenshot_path)}}
                        ]
                    },
                    "日付": {
                        "date": {
                            "start": timestamp.strftime("%Y-%m-%d"),
                        }
                    },
                },
            )
            page_id = page["id"]
            logger.info(f"Notionに記録完了: {page_id}")
            return page_id

        except Exception as e:
            logger.error(f"Notion記録エラー: {e}")
            return None

    def log_daily_summary(
        self,
        date: str,
        total_hours: float,
        category_breakdown: dict[str, float],
        app_breakdown: dict[str, float],
        avg_productivity: float,
        summary_text: str,
    ) -> str | None:
        """日次サマリーをNotionに記録"""
        db_id = Config.NOTION_SUMMARY_DATABASE_ID
        if not db_id:
            logger.warning("NOTION_SUMMARY_DATABASE_ID が未設定、スキップ")
            return None

        # カテゴリ別・アプリ別の内訳テキスト生成
        cat_text = "\n".join(
            f"- {k}: {v:.1f}h" for k, v in sorted(category_breakdown.items(), key=lambda x: -x[1])
        )
        app_text = "\n".join(
            f"- {k}: {v:.1f}h" for k, v in sorted(app_breakdown.items(), key=lambda x: -x[1])
        )

        try:
            page = self.client.pages.create(
                parent={"database_id": db_id},
                properties={
                    "日付": {
                        "title": [{"text": {"content": date}}]
                    },
                    "総作業時間": {
                        "number": round(total_hours, 1)
                    },
                    "カテゴリ別時間": {
                        "rich_text": [{"text": {"content": cat_text[:2000]}}]
                    },
                    "アプリ別時間": {
                        "rich_text": [{"text": {"content": app_text[:2000]}}]
                    },
                    "平均生産性": {
                        "number": round(avg_productivity, 1)
                    },
                    "日次レポート": {
                        "rich_text": [{"text": {"content": summary_text[:2000]}}]
                    },
                },
            )
            page_id = page["id"]
            logger.info(f"日次サマリーをNotionに記録: {page_id}")
            return page_id

        except Exception as e:
            logger.error(f"日次サマリー記録エラー: {e}")
            return None
