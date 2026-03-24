"""LINE通知モジュール - スクショ録画管理君"""

from __future__ import annotations

import logging
from pathlib import Path
import requests

from config import Config

logger = logging.getLogger(__name__)

LINE_NOTIFY_API = "https://notify-api.line.me/api/notify"


def send_line_notification(message: str, image_path: Path | None = None) -> bool:
    """LINE Notifyでメッセージを送信"""
    token = Config.LINE_NOTIFY_TOKEN
    if not token:
        logger.warning("LINE_NOTIFY_TOKEN が未設定、通知スキップ")
        return False

    headers = {"Authorization": f"Bearer {token}"}
    data = {"message": message}

    try:
        if image_path and image_path.exists():
            with open(image_path, "rb") as f:
                files = {"imageFile": f}
                resp = requests.post(LINE_NOTIFY_API, headers=headers, data=data, files=files)
        else:
            resp = requests.post(LINE_NOTIFY_API, headers=headers, data=data)

        if resp.status_code == 200:
            logger.info("LINE通知送信成功")
            return True
        else:
            logger.error(f"LINE通知失敗: {resp.status_code} {resp.text}")
            return False

    except Exception as e:
        logger.error(f"LINE通知エラー: {e}")
        return False


def notify_daily_report(date: str, report_path: Path, total_hours: float, avg_productivity: float):
    """日次レポートのLINE通知"""
    message = f"""
📊 スクショ録画管理君 - デイリーレポート
📅 {date}
⏱ アクティブ時間: {total_hours:.1f}時間
⭐ 平均生産性: {avg_productivity:.1f}/5.0
📄 レポート: {report_path}

Macの Finder で上記パスを開くとブラウザでレポートが確認できます。"""

    send_line_notification(message)
