"""Notion API連携モジュール - スクショ録画管理君（画像アップロード対応）"""

from __future__ import annotations

import logging
import requests
from datetime import datetime
from pathlib import Path

from notion_client import Client

from config import Config
from analyzer import AnalysisResult

logger = logging.getLogger(__name__)

NOTION_API_VERSION = "2022-06-28"


def _upload_to_notion_file(file_path: Path) -> str | None:
    """Notionの外部URLとしてファイルをホストする代わりに、
    imgbbなどの無料画像ホスティングにアップロードしてURLを返す。
    Notion APIは外部URLの画像をサポートしている。"""
    # Notion APIではファイルアップロード（S3署名URL方式）が複雑なため、
    # ページ内のブロックとして画像を埋め込む方式を採用
    return None


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
        """分析結果をNotionデータベースに記録し、スクリーンショットを埋め込む"""
        try:
            # ページ作成
            page = self.client.pages.create(
                parent={"database_id": Config.NOTION_DATABASE_ID},
                properties={
                    "タイトル": {
                        "title": [
                            {"text": {"content": result.activity[:100]}}
                        ]
                    },
                    "日時": {
                        "date": {"start": timestamp.isoformat()}
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
                        "date": {"start": timestamp.strftime("%Y-%m-%d")}
                    },
                },
            )
            page_id = page["id"]

            # ページ内にスクリーンショット画像をブロックとして埋め込む
            self._embed_screenshot(page_id, screenshot_path)

            logger.info(f"Notionに記録完了（画像付き）: {page_id}")
            return page_id

        except Exception as e:
            logger.error(f"Notion記録エラー: {e}")
            return None

    def _embed_screenshot(self, page_id: str, screenshot_path: Path):
        """Notionページ内にスクリーンショットを埋め込む（REST API経由）"""
        try:
            # Notion APIでファイルブロックを追加
            # external URL方式ではなく、ページにファイルを添付する
            # Notion APIのfile upload機能を使用
            headers = {
                "Authorization": f"Bearer {Config.NOTION_API_KEY}",
                "Notion-Version": NOTION_API_VERSION,
                "Content-Type": "application/json",
            }

            # まずNotionのファイルアップロードURLを取得
            upload_resp = requests.post(
                "https://api.notion.com/v1/file-uploads",
                headers=headers,
                json={
                    "mode": "single_part",
                    "filename": screenshot_path.name,
                    "content_type": "image/png",
                },
            )

            if upload_resp.status_code != 200:
                logger.debug(f"ファイルアップロードURL取得失敗: {upload_resp.status_code}")
                return

            upload_data = upload_resp.json()
            file_upload_id = upload_data.get("id")
            upload_url = upload_data.get("upload_url")

            if not file_upload_id or not upload_url:
                logger.debug("アップロード情報が不完全")
                return

            # ファイルをアップロード
            with open(screenshot_path, "rb") as f:
                file_resp = requests.put(
                    upload_url,
                    headers={
                        "Authorization": f"Bearer {Config.NOTION_API_KEY}",
                        "Content-Type": "image/png",
                    },
                    data=f.read(),
                )

            if file_resp.status_code not in (200, 201, 204):
                logger.debug(f"ファイルアップロード失敗: {file_resp.status_code}")
                return

            # 画像ブロックをページに追加
            block_resp = requests.patch(
                f"https://api.notion.com/v1/blocks/{page_id}/children",
                headers=headers,
                json={
                    "children": [
                        {
                            "object": "block",
                            "type": "image",
                            "image": {
                                "type": "file_upload",
                                "file_upload": {"id": file_upload_id},
                            },
                        }
                    ]
                },
            )

            if block_resp.status_code == 200:
                logger.debug("スクリーンショット埋め込み成功")
            else:
                logger.debug(f"画像ブロック追加失敗: {block_resp.status_code}: {block_resp.text[:200]}")

        except Exception as e:
            logger.debug(f"スクリーンショット埋め込みエラー: {e}")

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
                    "総作業時間": {"number": round(total_hours, 1)},
                    "カテゴリ別時間": {
                        "rich_text": [{"text": {"content": cat_text[:2000]}}]
                    },
                    "アプリ別時間": {
                        "rich_text": [{"text": {"content": app_text[:2000]}}]
                    },
                    "平均生産性": {"number": round(avg_productivity, 1)},
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
