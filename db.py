"""SQLiteローカルキャッシュモジュール"""

from __future__ import annotations


import sqlite3
import logging
from pathlib import Path
from datetime import datetime

from config import Config
from analyzer import AnalysisResult

logger = logging.getLogger(__name__)


class LocalDB:
    """SQLiteによるローカルデータ管理"""

    def __init__(self):
        self.db_path = Config.DB_PATH
        self._init_db()

    def _init_db(self):
        """テーブル作成"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    date TEXT NOT NULL,
                    screenshot_path TEXT NOT NULL,
                    activity TEXT,
                    app_name TEXT,
                    category TEXT,
                    detail TEXT,
                    productivity_score INTEGER,
                    notion_page_id TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_date ON activity_logs(date)
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT UNIQUE NOT NULL,
                    total_hours REAL,
                    avg_productivity REAL,
                    summary_text TEXT,
                    category_json TEXT,
                    app_json TEXT,
                    notion_page_id TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        logger.info("ローカルDB初期化完了")

    def save_activity(
        self,
        timestamp: datetime,
        screenshot_path: Path,
        result: AnalysisResult,
        notion_page_id: str | None = None,
    ):
        """アクティビティログを保存"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO activity_logs
                (timestamp, date, screenshot_path, activity, app_name,
                 category, detail, productivity_score, notion_page_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    timestamp.isoformat(),
                    timestamp.strftime("%Y-%m-%d"),
                    str(screenshot_path),
                    result.activity,
                    result.app_name,
                    result.category,
                    result.detail,
                    result.productivity_score,
                    notion_page_id,
                ),
            )
            conn.commit()

    def get_activities_for_date(self, date: str) -> list[dict]:
        """指定日のアクティビティ一覧を取得"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM activity_logs WHERE date = ? ORDER BY timestamp",
                (date,),
            ).fetchall()
            return [dict(row) for row in rows]

    def save_daily_summary(
        self,
        date: str,
        total_hours: float,
        avg_productivity: float,
        summary_text: str,
        category_json: str,
        app_json: str,
        notion_page_id: str | None = None,
    ):
        """日次サマリーを保存"""
        import json

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO daily_summaries
                (date, total_hours, avg_productivity, summary_text,
                 category_json, app_json, notion_page_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    date,
                    total_hours,
                    avg_productivity,
                    summary_text,
                    category_json,
                    app_json,
                    notion_page_id,
                ),
            )
            conn.commit()

    def get_unsent_activities(self) -> list[dict]:
        """Notionに未送信のアクティビティを取得"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM activity_logs WHERE notion_page_id IS NULL ORDER BY timestamp"
            ).fetchall()
            return [dict(row) for row in rows]

    def update_notion_page_id(self, activity_id: int, page_id: str):
        """Notion送信後にpage_idを更新"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE activity_logs SET notion_page_id = ? WHERE id = ?",
                (page_id, activity_id),
            )
            conn.commit()
