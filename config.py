"""設定管理モジュール - スクショ録画管理君"""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv(Path(__file__).parent / ".env")


class Config:
    """アプリケーション設定"""

    # API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    NOTION_API_KEY: str = os.getenv("NOTION_API_KEY", "")
    NOTION_DATABASE_ID: str = os.getenv("NOTION_DATABASE_ID", "")
    NOTION_SUMMARY_DATABASE_ID: str = os.getenv("NOTION_SUMMARY_DATABASE_ID", "")
    LINE_NOTIFY_TOKEN: str = os.getenv("LINE_NOTIFY_TOKEN", "")

    # スクリーンショット設定
    CAPTURE_INTERVAL: int = int(os.getenv("CAPTURE_INTERVAL", "30"))
    SCREENSHOT_DIR: Path = Path(
        os.getenv("SCREENSHOT_DIR", "~/LifeLogger/screenshots")
    ).expanduser()
    LOCAL_RETENTION_DAYS: int = int(os.getenv("LOCAL_RETENTION_DAYS", "7"))
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.95"))

    # サマリー設定
    SUMMARY_TIME: str = os.getenv("SUMMARY_TIME", "23:00")

    # レポート保存先
    REPORT_DIR: Path = Path(__file__).parent / "reports"

    # SQLiteパス
    DB_PATH: Path = Path(__file__).parent / "lifelogger.db"

    # ログ
    LOG_DIR: Path = Path(__file__).parent / "logs"

    @classmethod
    def validate(cls) -> list[str]:
        """必須設定の検証。エラーメッセージのリストを返す"""
        errors = []
        if not cls.GEMINI_API_KEY:
            errors.append("GEMINI_API_KEY が設定されていません")
        if not cls.NOTION_API_KEY:
            errors.append("NOTION_API_KEY が設定されていません")
        if not cls.NOTION_DATABASE_ID:
            errors.append("NOTION_DATABASE_ID が設定されていません")
        return errors

    @classmethod
    def ensure_dirs(cls):
        """必要なディレクトリを作成"""
        cls.SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)
        cls.REPORT_DIR.mkdir(parents=True, exist_ok=True)
