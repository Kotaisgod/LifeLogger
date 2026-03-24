"""Gemini AIによる画像分析モジュール"""

from __future__ import annotations


import json
import logging
from pathlib import Path
from dataclasses import dataclass

from google import genai
from google.genai import types

from config import Config

logger = logging.getLogger(__name__)

# 分析プロンプト
ANALYSIS_PROMPT = """この画面のスクリーンショットを分析して、以下のJSON形式で回答してください。
日本語で回答してください。

{
  "activity": "何をしていたかの1行要約",
  "app_name": "使用中のアプリケーション名",
  "category": "仕事 | SNS | エンタメ | 学習 | コミュニケーション | その他",
  "detail": "詳細な内容（3行以内）",
  "productivity_score": 1〜5の整数（1=非生産的、5=非常に生産的）
}

ルール:
- JSONのみを返す。説明文は不要
- app_nameはアプリケーションの正式名称を使用
- categoryは指定された6つのいずれかを使用
- productivity_scoreは整数のみ
"""


@dataclass
class AnalysisResult:
    """分析結果のデータクラス"""
    activity: str
    app_name: str
    category: str
    detail: str
    productivity_score: int
    raw_json: dict


def analyze_screenshot(image_path: Path) -> AnalysisResult | None:
    """スクリーンショットをGemini APIで分析"""
    try:
        client = genai.Client(api_key=Config.GEMINI_API_KEY)

        # 画像をアップロード
        with open(image_path, "rb") as f:
            image_data = f.read()

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_bytes(data=image_data, mime_type="image/png"),
                        types.Part.from_text(text=ANALYSIS_PROMPT),
                    ],
                )
            ],
        )

        # レスポンスからJSONをパース
        text = response.text.strip()
        # マークダウンのコードブロックを除去
        if text.startswith("```"):
            text = text.split("\n", 1)[1]  # 最初の行を除去
            text = text.rsplit("```", 1)[0]  # 最後の```を除去
            text = text.strip()

        data = json.loads(text)

        result = AnalysisResult(
            activity=data.get("activity", "不明"),
            app_name=data.get("app_name", "不明"),
            category=data.get("category", "その他"),
            detail=data.get("detail", ""),
            productivity_score=int(data.get("productivity_score", 3)),
            raw_json=data,
        )
        logger.info(f"分析完了: [{result.app_name}] {result.activity}")
        return result

    except json.JSONDecodeError as e:
        logger.error(f"Gemini応答のJSONパースエラー: {e}")
        logger.debug(f"応答テキスト: {text}")
        return None
    except Exception as e:
        logger.error(f"Gemini分析エラー: {e}")
        return None
