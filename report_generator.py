"""HTMLレポート生成モジュール - スクショ録画管理君"""

from __future__ import annotations

import logging
from datetime import datetime
from collections import defaultdict
from pathlib import Path

from config import Config
from db import LocalDB

logger = logging.getLogger(__name__)


def generate_html_report(date: str | None = None) -> Path | None:
    """指定日のHTMLレポートを生成して保存"""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    db = LocalDB()
    activities = db.get_activities_for_date(date)

    if not activities:
        logger.info(f"{date} のアクティビティがありません、レポートスキップ")
        return None

    # 集計
    category_time: dict[str, float] = defaultdict(float)
    app_time: dict[str, float] = defaultdict(float)
    scores = []
    interval_hours = Config.CAPTURE_INTERVAL / 3600

    for act in activities:
        category_time[act.get("category", "その他")] += interval_hours
        app_time[act.get("app_name", "不明")] += interval_hours
        scores.append(act.get("productivity_score", 3))

    total_hours = len(activities) * interval_hours
    avg_score = sum(scores) / len(scores) if scores else 0

    # タイムラインHTML生成
    timeline_html = ""
    for act in activities:
        time_str = act.get("timestamp", "")[11:19]
        score = act.get("productivity_score", 3)
        dots = "●" * score + "○" * (5 - score)
        cat = act.get("category", "その他")
        cat_colors = {
            "仕事": "#3b82f6", "開発": "#8b5cf6", "SNS": "#ec4899",
            "エンタメ": "#f59e0b", "学習": "#10b981", "コミュニケーション": "#06b6d4",
            "その他": "#6b7280",
        }
        color = cat_colors.get(cat, "#6b7280")
        timeline_html += f"""
        <div class="timeline-item">
            <div class="time">{time_str}</div>
            <div class="content">
                <div class="app" style="color:{color}">{act.get('app_name', '不明')}</div>
                <div class="activity">{act.get('activity', '')}</div>
                <div class="detail">{act.get('detail', '')}</div>
                <div class="score">{dots} ({score}/5)</div>
                <span class="badge" style="background:{color}20;color:{color}">{cat}</span>
            </div>
        </div>"""

    # カテゴリ内訳
    cat_bars = ""
    max_cat = max(category_time.values()) if category_time else 1
    for cat, hours in sorted(category_time.items(), key=lambda x: -x[1]):
        pct = (hours / max_cat) * 100 if max_cat > 0 else 0
        color = {"仕事": "#3b82f6", "開発": "#8b5cf6", "SNS": "#ec4899",
                 "エンタメ": "#f59e0b", "学習": "#10b981", "コミュニケーション": "#06b6d4",
                 "その他": "#6b7280"}.get(cat, "#6b7280")
        cat_bars += f"""
        <div class="bar-row">
            <span class="bar-label">{cat}</span>
            <div class="bar-track"><div class="bar-fill" style="width:{pct}%;background:{color}"></div></div>
            <span class="bar-value">{hours:.1f}h</span>
        </div>"""

    # アプリ内訳（上位10）
    app_bars = ""
    top_apps = sorted(app_time.items(), key=lambda x: -x[1])[:10]
    max_app = top_apps[0][1] if top_apps else 1
    for app, hours in top_apps:
        pct = (hours / max_app) * 100 if max_app > 0 else 0
        app_bars += f"""
        <div class="bar-row">
            <span class="bar-label">{app}</span>
            <div class="bar-track"><div class="bar-fill" style="width:{pct}%;background:#8b5cf6"></div></div>
            <span class="bar-value">{hours:.1f}h</span>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>スクショ録画管理君 - デイリーレポート {date}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0f172a;color:#e2e8f0;padding:20px;max-width:900px;margin:0 auto}}
h1{{font-size:1.8em;background:linear-gradient(135deg,#8b5cf6,#ec4899);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:5px}}
.subtitle{{color:#94a3b8;margin-bottom:30px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:15px;margin-bottom:30px}}
.card{{background:#1e293b;border-radius:12px;padding:20px;text-align:center}}
.card .value{{font-size:2em;font-weight:700;color:#8b5cf6}}
.card .label{{color:#94a3b8;font-size:.85em;margin-top:5px}}
h2{{font-size:1.3em;color:#f1f5f9;margin:25px 0 15px;padding-bottom:8px;border-bottom:1px solid #334155}}
.timeline-item{{display:flex;gap:15px;padding:12px 0;border-bottom:1px solid #1e293b}}
.time{{color:#8b5cf6;font-weight:600;min-width:65px;font-size:.9em}}
.content{{flex:1}}
.app{{font-weight:600;font-size:.95em}}
.activity{{color:#cbd5e1;margin:3px 0}}
.detail{{color:#64748b;font-size:.85em}}
.score{{color:#f59e0b;font-size:.85em;margin-top:4px}}
.badge{{display:inline-block;padding:2px 8px;border-radius:12px;font-size:.75em;margin-top:4px}}
.bar-row{{display:flex;align-items:center;gap:10px;margin:8px 0}}
.bar-label{{min-width:120px;font-size:.85em;color:#94a3b8;text-align:right}}
.bar-track{{flex:1;height:20px;background:#1e293b;border-radius:10px;overflow:hidden}}
.bar-fill{{height:100%;border-radius:10px;transition:width .3s}}
.bar-value{{min-width:50px;font-size:.85em;color:#94a3b8}}
.section{{background:#1e293b;border-radius:12px;padding:20px;margin-bottom:20px}}
.footer{{text-align:center;color:#475569;margin-top:30px;font-size:.8em}}
@media(prefers-color-scheme:light){{
body{{background:#f8fafc;color:#1e293b}}
.card,.section{{background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.1)}}
.timeline-item{{border-color:#e2e8f0}}
.bar-track{{background:#f1f5f9}}
h2{{color:#1e293b;border-color:#e2e8f0}}
.detail{{color:#64748b}}.activity{{color:#475569}}
}}
</style>
</head>
<body>
<h1>スクショ録画管理君</h1>
<p class="subtitle">デイリーレポート - {date}</p>

<div class="cards">
    <div class="card"><div class="value">{len(activities)}</div><div class="label">記録数</div></div>
    <div class="card"><div class="value">{total_hours:.1f}h</div><div class="label">アクティブ時間</div></div>
    <div class="card"><div class="value">{avg_score:.1f}</div><div class="label">平均生産性 / 5.0</div></div>
    <div class="card"><div class="value">{len(app_time)}</div><div class="label">使用アプリ数</div></div>
</div>

<h2>カテゴリ別</h2>
<div class="section">{cat_bars}</div>

<h2>アプリ別（上位10）</h2>
<div class="section">{app_bars}</div>

<h2>タイムライン</h2>
<div class="section">{timeline_html}</div>

<div class="footer">Generated by スクショ録画管理君 at {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
</body>
</html>"""

    # 保存
    report_path = Config.REPORT_DIR / f"report-{date}.html"
    Config.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path.write_text(html, encoding="utf-8")
    logger.info(f"HTMLレポート生成完了: {report_path}")
    return report_path
