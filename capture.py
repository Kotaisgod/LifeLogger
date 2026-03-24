"""スクリーンショット撮影モジュール"""

from __future__ import annotations


import subprocess
import logging
from pathlib import Path
from datetime import datetime

from config import Config
from utils import is_screen_locked, compute_image_hash, are_images_similar

logger = logging.getLogger(__name__)


class ScreenCapture:
    """macOSスクリーンショット撮影クラス"""

    def __init__(self):
        self._last_hash: str | None = None

    def capture(self) -> Path | None:
        """
        スクリーンショットを撮影して保存。
        スキップした場合はNoneを返す。
        """
        # ロック/スリープ中はスキップ
        if is_screen_locked():
            logger.debug("画面ロック中のためスキップ")
            return None

        # 保存先ディレクトリ作成
        now = datetime.now()
        day_dir = Config.SCREENSHOT_DIR / now.strftime("%Y-%m-%d")
        day_dir.mkdir(parents=True, exist_ok=True)

        # ファイルパス
        filename = now.strftime("%H-%M-%S") + ".png"
        filepath = day_dir / filename

        # macOS標準のscreencaptureコマンドで撮影
        try:
            result = subprocess.run(
                ["/usr/sbin/screencapture", "-x", "-C", str(filepath)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                logger.error(f"screencapture失敗: {result.stderr}")
                return None
        except subprocess.TimeoutExpired:
            logger.error("screencaptureがタイムアウト")
            return None
        except Exception as e:
            logger.error(f"スクリーンショット撮影エラー: {e}")
            return None

        # ファイルが実際に生成されたか確認
        if not filepath.exists():
            logger.error("スクリーンショットファイルが生成されませんでした")
            return None

        # 画像変化検知（前回と同じならスキップ）
        try:
            current_hash = compute_image_hash(filepath)
            if self._last_hash is not None and are_images_similar(
                self._last_hash, current_hash, Config.SIMILARITY_THRESHOLD
            ):
                # 変化なし → ファイル削除してスキップ
                filepath.unlink()
                logger.debug("画面に変化なし、スキップ")
                return None
            self._last_hash = current_hash
        except Exception as e:
            logger.warning(f"画像比較エラー（撮影は続行）: {e}")
            # ハッシュ計算に失敗しても撮影自体は有効とする

        logger.info(f"スクリーンショット保存: {filepath}")
        return filepath
