"""ユーティリティモジュール"""

from __future__ import annotations


import subprocess
import logging
from pathlib import Path
from datetime import datetime, timedelta

import imagehash
from PIL import Image

logger = logging.getLogger(__name__)


def is_screen_locked() -> bool:
    """macOSのスクリーンがロック/スリープ中かどうかを判定"""
    try:
        # スクリーンセーバーが動作中か確認
        result = subprocess.run(
            ["pgrep", "-x", "ScreenSaverEngine"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return True

        # ディスプレイがスリープ中か確認
        result = subprocess.run(
            [
                "/usr/sbin/ioreg",
                "-r",
                "-k",
                "AppleClamshellState",
                "-d",
                "1",
            ],
            capture_output=True,
            text=True,
        )
        if '"AppleClamshellState" = Yes' in result.stdout:
            return True

        # CGSessionのScreenIsLockedを確認
        result = subprocess.run(
            [
                "python3",
                "-c",
                "import Quartz; d=Quartz.CGSessionCopyCurrentDictionary(); print(d.get('CGSSessionScreenIsLocked',0) if d else 1)",
            ],
            capture_output=True,
            text=True,
        )
        if result.stdout.strip() == "1":
            return True

        return False
    except Exception as e:
        logger.warning(f"ロック状態検知でエラー: {e}")
        return False


def compute_image_hash(image_path: Path) -> str:
    """画像のperceptual hashを計算"""
    img = Image.open(image_path)
    return str(imagehash.phash(img))


def are_images_similar(hash1: str, hash2: str, threshold: float = 0.95) -> bool:
    """2つの画像ハッシュの類似度を比較"""
    h1 = imagehash.hex_to_hash(hash1)
    h2 = imagehash.hex_to_hash(hash2)
    # ハッシュ間のハミング距離。0が完全一致
    max_dist = len(h1.hash.flatten())
    distance = h1 - h2
    similarity = 1 - (distance / max_dist)
    return similarity >= threshold


def cleanup_old_screenshots(screenshot_dir: Path, retention_days: int):
    """古いスクリーンショットを削除"""
    cutoff = datetime.now() - timedelta(days=retention_days)
    removed = 0
    for day_dir in screenshot_dir.iterdir():
        if not day_dir.is_dir():
            continue
        try:
            dir_date = datetime.strptime(day_dir.name, "%Y-%m-%d")
            if dir_date < cutoff:
                import shutil
                shutil.rmtree(day_dir)
                removed += 1
                logger.info(f"古いスクリーンショットを削除: {day_dir.name}")
        except ValueError:
            continue
    if removed > 0:
        logger.info(f"{removed} 日分のスクリーンショットを削除しました")


def setup_logging():
    """ロギング設定"""
    from config import Config

    Config.ensure_dirs()
    log_file = Config.LOG_DIR / "lifelogger.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
