#!/usr/bin/env python3
from __future__ import annotations
"""スクショ録画管理君 - メインエントリーポイント"""

import sys
import signal
import logging
import time
from datetime import datetime

import schedule

from config import Config
from utils import setup_logging, cleanup_old_screenshots
from capture import ScreenCapture
from analyzer import analyze_screenshot
from notion_logger import NotionLogger
from db import LocalDB
from summarizer import generate_daily_summary

logger = logging.getLogger(__name__)

_running = True


def signal_handler(signum, frame):
    global _running
    logger.info(f"シグナル {signum} を受信、シャットダウンします...")
    _running = False


def process_screenshot(capture: ScreenCapture, db: LocalDB, notion: NotionLogger):
    """1回のスクリーンショット撮影→分析→保存サイクル"""
    try:
        screenshot_path = capture.capture()
        if screenshot_path is None:
            return

        timestamp = datetime.now()

        result = analyze_screenshot(screenshot_path)
        if result is None:
            logger.warning("分析失敗、スキップ")
            return

        notion_page_id = notion.log_activity(result, screenshot_path, timestamp)
        db.save_activity(timestamp, screenshot_path, result, notion_page_id)

    except Exception as e:
        logger.error(f"処理サイクルエラー: {e}", exc_info=True)


def retry_unsent(db: LocalDB, notion: NotionLogger):
    """Notion未送信のログをリトライ"""
    from analyzer import AnalysisResult
    from pathlib import Path

    unsent = db.get_unsent_activities()
    if not unsent:
        return

    logger.info(f"未送信ログ {len(unsent)} 件をリトライ")
    for act in unsent[:10]:
        try:
            result = AnalysisResult(
                activity=act["activity"],
                app_name=act["app_name"],
                category=act["category"],
                detail=act["detail"],
                productivity_score=act["productivity_score"],
                raw_json={},
            )
            page_id = notion.log_activity(
                result,
                Path(act["screenshot_path"]),
                datetime.fromisoformat(act["timestamp"]),
            )
            if page_id:
                db.update_notion_page_id(act["id"], page_id)
        except Exception as e:
            logger.error(f"リトライ失敗 (id={act['id']}): {e}")


def main():
    global _running

    setup_logging()
    logger.info("=" * 50)
    logger.info("スクショ録画管理君 起動")
    logger.info("=" * 50)

    errors = Config.validate()
    if errors:
        for err in errors:
            logger.error(f"設定エラー: {err}")
        logger.error("必須設定が不足しています。.envファイルを確認してください。")
        sys.exit(1)

    Config.ensure_dirs()

    capture = ScreenCapture()
    db = LocalDB()
    notion = NotionLogger()

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    interval = Config.CAPTURE_INTERVAL

    # 日次サマリー + HTMLレポート + LINE通知（毎日23:00）
    summary_time = Config.SUMMARY_TIME
    schedule.every().day.at(summary_time).do(generate_daily_summary)
    logger.info(f"日次サマリー + レポート + LINE通知: 毎日 {summary_time}")

    # 古いスクリーンショットのクリーンアップ（毎日4:00）
    schedule.every().day.at("04:00").do(
        cleanup_old_screenshots, Config.SCREENSHOT_DIR, Config.LOCAL_RETENTION_DAYS,
    )

    # 未送信ログのリトライ（5分ごと）
    schedule.every(5).minutes.do(retry_unsent, db, notion)

    logger.info(f"キャプチャ間隔: {interval}秒")
    logger.info(f"スクリーンショット保存先: {Config.SCREENSHOT_DIR}")
    logger.info("スクショ録画管理君 稼働開始")

    last_capture = 0
    while _running:
        try:
            schedule.run_pending()
            now = time.time()
            if now - last_capture >= interval:
                process_screenshot(capture, db, notion)
                last_capture = now
            time.sleep(1)
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"メインループエラー: {e}", exc_info=True)
            time.sleep(5)

    logger.info("スクショ録画管理君 停止")


if __name__ == "__main__":
    main()
