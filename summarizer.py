"""日次サマリー生成モジュール"""

from __future__ import annotations


import json
import logging
from datetime import datetime
from collections import defaultdict

from google import genai
from google.genai import types

from config import Config
from db import LocalDB
from notion_logger import NotionLogger

logger = logging.getLogger(__name__)

# サマリー生成プロンプト
SUMMARY_PROMPT = """以下は1日のPC使用ログです。日本語で3〜5文で1日の振り返りサマリーを生成してください。
何に最も時間を使ったか、生産性の傾向、改善点などを含めてください。
サマリーテキストだけを返してください。

ログデータ:
{log_data}
"""


def generate_daily_summary(date: str | None = None):
    """指定日（デフォルト: 今日）の日次サマリーを生成してNotionに記録"""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    db = LocalDB()
    activities = db.get_activities_for_date(date)

    if not activities:
        logger.info(f"{date} のアクティビティがありません、サマリースキップ")
        return

    # 集計
    category_time: dict[str, float] = defaultdict(float)
    app_time: dict[str, float] = defaultdict(float)
    total_scores = []
    interval_hours = Config.CAPTURE_INTERVAL / 3600  # 1キャプチャあたりの推定時間

    for act in activities:
        cat = act.get("category", "その他")
        app = act.get("app_name", "不明")
        score = act.get("productivity_score", 3)

        category_time[cat] += interval_hours
        app_time[app] += interval_hours
        total_scores.append(score)

    total_hours = len(activities) * interval_hours
    avg_productivity = sum(total_scores) / len(total_scores) if total_scores else 0

    # Geminiで振り返りサマリー生成
    summary_text = _generate_summary_text(activities, category_time, app_time, total_hours)

    # Notionに記録
    notion = NotionLogger()
    notion_page_id = notion.log_daily_summary(
        date=date,
        total_hours=total_hours,
        category_breakdown=dict(category_time),
        app_breakdown=dict(app_time),
        avg_productivity=avg_productivity,
        summary_text=summary_text,
    )

    # ローカルDBにも保存
    db.save_daily_summary(
        date=date,
        total_hours=total_hours,
        avg_productivity=avg_productivity,
        summary_text=summary_text,
        category_json=json.dumps(dict(category_time), ensure_ascii=False),
        app_json=json.dumps(dict(app_time), ensure_ascii=False),
        notion_page_id=notion_page_id,
    )

    logger.info(f"日次サマリー生成完了: {date} ({total_hours:.1f}h, 生産性: {avg_productivity:.1f})")


def _generate_summary_text(
    activities: list[dict],
    category_time: dict[str, float],
    app_time: dict[str, float],
    total_hours: float,
) -> str:
    """Gemini APIでサマリーテキストを生成"""
    # ログデータを要約用にまとめる
    log_lines = []
    for act in activities[:50]:  # 最大50件に制限
        log_lines.append(
            f"[{act.get('timestamp', '?')}] {act.get('app_name', '?')} - {act.get('activity', '?')} (カテゴリ: {act.get('category', '?')}, 生産性: {act.get('productivity_score', '?')})"
        )

    cat_summary = ", ".join(f"{k}: {v:.1f}h" for k, v in category_time.items())
    app_summary = ", ".join(f"{k}: {v:.1f}h" for k, v in list(app_time.items())[:10])

    log_data = f"""総作業時間: {total_hours:.1f}時間
カテゴリ別: {cat_summary}
アプリ別: {app_summary}

時系列ログ:
""" + "\n".join(log_lines)

    try:
        client = genai.Client(api_key=Config.GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=SUMMARY_PROMPT.format(log_data=log_data))
                    ],
                )
            ],
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"サマリー生成エラー: {e}")
        return f"総作業時間: {total_hours:.1f}h\nカテゴリ別: {cat_summary}\nアプリ別: {app_summary}"
