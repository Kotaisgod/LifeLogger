# LifeLogger

MacBookの画面を定期的にスクリーンショット撮影し、AIで自動分析して、Notionデータベースに保存するアプリです。

## 何ができるの？

- **30秒ごと**に自動でスクリーンショット撮影
- **Gemini AI** が画像を分析 → 使用アプリ・カテゴリ・生産性スコアを自動判定
- **Notion** にすべて自動保存 → いつでも振り返り可能
- **日次サマリー** を毎日自動生成（カテゴリ別時間・アプリ別時間・AI振り返り）
- Mac起動時に自動で常駐（launchd）

## デモ

Notionに以下のようなデータが自動蓄積されます：

| 時刻 | アプリ | カテゴリ | 生産性 | 内容 |
|------|--------|---------|--------|------|
| 17:49 | Google Pay | その他 | 1 | オンラインストアで支払い情報を入力中 |
| 17:51 | ブラウザ | 仕事 | 4 | AMEX SafeKeyで本人認証手続き |
| 17:54 | ブラウザ | エンタメ | 3 | Omi.meストアで商品閲覧 |

## 必要なもの

- **macOS** (Apple Silicon / Intel)
- **Python 3.9+**
- **Gemini API Key** (無料枠あり) → [Google AI Studio](https://aistudio.google.com/apikey)
- **Notion アカウント** (無料) → [Notion](https://www.notion.so/)

## API費用の目安

| 使用時間 | 1日のキャプチャ数 | Gemini API費用 |
|---------|-----------------|---------------|
| 5時間/日 | 約300-400回 | 約3-8円/日 |
| 10時間/日 | 約600-800回 | 約7-15円/日 |
| 15時間/日 | 約900-1200回 | 約10-20円/日 |

※ 画面変化がない場合は自動スキップするため、実際のAPI呼び出し数は少なくなります。

## セットアップ手順

### 1. クローン & インストール

```bash
git clone https://github.com/koutatsunakao/LifeLogger.git
cd LifeLogger
pip3 install -r requirements.txt
```

### 2. Gemini API Key を取得

1. [Google AI Studio](https://aistudio.google.com/apikey) にアクセス
2. 「API キーを作成」をクリック
3. 表示されたキーをコピー

### 3. Notion Integration を作成

1. [Notion Integrations](https://www.notion.so/profile/integrations) にアクセス
2. 「新しいインテグレーションを作成」をクリック
3. 名前を「LifeLogger」に設定
4. ワークスペースを選択 → 「作成」
5. 表示されたシークレットキー（`ntn_...`）をコピー

### 4. Notion ページを準備

1. Notionで新しいページを作成（名前は自由、例: 「LifeLogger」）
2. 右上の「...」→ 下にスクロール →「接続」→「LifeLogger」を選択して接続
3. ページのURLからIDを取得
   - 例: `https://www.notion.so/LifeLogger-abc123def456...`
   - → `abc123def456...` がページID

### 5. 環境変数を設定

```bash
cp .env.example .env
```

`.env` ファイルを編集：

```env
GEMINI_API_KEY=あなたのGemini APIキー
NOTION_API_KEY=あなたのNotion Integration シークレット
```

### 6. Notion データベースを自動作成

```bash
python3 setup_notion.py <あなたのNotionページID>
```

これでNotionに「アクティビティログ」と「日次サマリー」のデータベースが自動作成され、`.env` に ID が書き込まれます。

### 7. 動作テスト

```bash
python3 test_once.py
```

スクリーンショット → AI分析 → Notion保存 の全工程がテストされます。

### 8. 常駐化（Mac起動時に自動実行）

```bash
bash setup_launchd.sh install
```

## 操作コマンド

```bash
# 状態確認
bash setup_launchd.sh status

# 再起動
bash setup_launchd.sh restart

# 停止（常駐解除）
bash setup_launchd.sh uninstall
```

## 設定変更

`.env` ファイルで以下を変更できます：

| 設定 | デフォルト | 説明 |
|------|----------|------|
| `CAPTURE_INTERVAL` | 30 | キャプチャ間隔（秒） |
| `LOCAL_RETENTION_DAYS` | 7 | スクリーンショットのローカル保持日数 |
| `SIMILARITY_THRESHOLD` | 0.95 | 画面変化検知の閾値（高いほど敏感） |
| `SUMMARY_TIME` | 23:00 | 日次サマリー生成時刻 |

## ファイル構成

```
LifeLogger/
├── main.py              # メインエントリーポイント
├── capture.py           # スクリーンショット撮影
├── analyzer.py          # Gemini AI分析
├── notion_logger.py     # Notion API連携
├── summarizer.py        # 日次サマリー生成
├── db.py                # SQLiteローカルキャッシュ
├── config.py            # 設定管理
├── utils.py             # ユーティリティ
├── setup_notion.py      # Notion DB自動作成スクリプト
├── setup_launchd.sh     # macOS常駐化スクリプト
├── test_once.py         # 動作テストスクリプト
├── requirements.txt     # 依存パッケージ
├── .env.example         # 環境変数テンプレート
└── .gitignore
```

## 注意事項

- **プライバシー**: スクリーンショットには個人情報が含まれる可能性があります。ローカル保持期間を適切に設定してください。
- **画面収録権限**: 初回実行時にmacOSの「画面収録」権限の許可が必要です（システム設定 → プライバシーとセキュリティ → 画面収録）
- **Gemini API**: 画像がGoogleのサーバーに送信されます。機密情報が映る可能性がある場合はご注意ください。

## ライセンス

MIT License
