"""Slack通知モジュール - スクショ録画管理君"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import requests

from config import Config

logger = logging.getLogger(__name__)


def send_slack_notification(message: str) -> bool:
    """Slack Incoming Webhookでメッセージを送信"""
    webhook_url = Config.SLACK_WEBHOOK_URL
    if not webhook_url:
        logger.warning("SLACK_WEBHOOK_URL が未設定、通知スキップ")
        return False

    try:
        payload = {"text": message}
        resp = requests.post(
            webhook_url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )

        if resp.status_code == 200:
            logger.info("Slack通知送信成功")
            return True
        else:
            logger.error(f"Slack通知失敗: {resp.status_code} {resp.text}")
            return False

    except Exception as e:
        logger.error(f"Slack通知エラー: {e}")
        return False


def notify_daily_report(
    date: str,
    report_path: Path,
    total_hours: float,
    avg_productivity: float,
    record_count: int = 0,
):
    """日次レポートのSlack通知"""
    stars = "⭐" * round(avg_productivity)

    message = f"""📊 *スクショ録画管理君 - デイリーレポート*
━━━━━━━━━━━━━━━━━━━━
📅 日付: *{date}*
⏱ アクティブ時間: *{total_hours:.1f}時間*
📝 記録数: *{record_count}件*
{stars} 平均生産性: *{avg_productivity:.1f}/5.0*
━━━━━━━━━━━━━━━━━━━━
📄 レポートファイル: `{report_path}`
💡 Macの Finder で上記パスを開くとブラウザでレポートが確認できます"""

    send_slack_notification(message)
