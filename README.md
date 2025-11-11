# tccretro

TaskChute Cloud Retrospective Analysis Tool - データエクスポート、分析、AI フィードバック生成

## 概要

このプロジェクトは、TaskChute Cloudからのデータエクスポートを自動化し、pandasによる分析・可視化、Amazon Bedrock (Claude) によるAIフィードバックを提供します:

- **Playwright** によるブラウザ自動化 (ログイン + エクスポート)
- **永続的Chromeプロファイル** による認証情報の保存
- **pandas** によるデータ分析・集計
- **matplotlib/seaborn** による可視化 (日本語対応)
- **Amazon Bedrock (Claude)** によるAI分析とフィードバック
- **Markdownレポート** の自動生成
- **uv** によるPython依存関係管理

## アーキテクチャ

```text
CLI実行 → Playwright → TaskChute Cloud → CSV → pandas分析 → Bedrock (Claude) → Markdownレポート
```

### 主要機能

1. **データエクスポート**: TaskChute Cloudから時間記録データを自動取得
2. **プロジェクト別分析**: プロジェクトごとの時間集計と可視化
3. **モード別分析**: モードごとの時間集計と可視化
4. **AI分析**: Amazon Bedrock (Claude) による詳細なフィードバック
5. **レポート生成**: グラフと分析結果を含むMarkdownレポート

### コンポーネント

- `app/src/tccretro/`: メインパッケージ
  - `login.py`: Playwrightログイン状態確認
  - `export.py`: エクスポート自動化
  - `analyzer/`: データ分析モジュール (プロジェクト別/モード別)
  - `ai_feedback.py`: AI分析とフィードバック生成
  - `report_generator.py`: Markdownレポート生成
  - `cli.py`: コマンドラインインターフェース

## 前提条件

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) - Pythonパッケージマネージャ
- TaskChute Cloudアカウント
- Chrome/Chromiumブラウザ (システムにインストール済み)

## セットアップ

### 1. リポジトリのクローンと依存関係インストール

```bash
# リポジトリをクローン
git clone <repository-url>
cd tccretro

# Python依存関係をインストール
cd app
uv sync

# Playwrightブラウザをインストール
uv run playwright install chromium

# pre-commitフックをインストール (オプション)
uv run pre-commit install
```

### 2. 環境変数の設定 (オプション)

環境変数ファイルは必須ではありませんが、参照用に作成できます:

```bash
cd app
cp .env.example .env
# .envファイルを編集 (ただし永続的プロファイルを使う場合は不要)
```

**注意**: 永続的Chromeプロファイルを使用するため、実際の認証はブラウザで手動で行います。

## 使用方法

### 初回実行: ログイン認証の保存

初回実行時は、ブラウザを表示して手動でログインします:

```bash
cd app
uv run python -m tccretro.cli --login-only --debug
```

ブラウザが起動したら:

1. TaskChute Cloudにログイン (Google/Apple/メールいずれでもOK)
2. ログインが完了したら、自動的に検出されてプログラムが終了します
3. 認証情報は `chrome-profile/` ディレクトリに保存されます
4. 次回以降は自動的にログイン済みの状態で起動します

**注意事項:**
- `--login-only` を使用する場合は、`--debug` オプションを付けることを強く推奨します
- headless モード（`--debug` なし）では、ブラウザが表示されないため手動ログイン操作ができません
- 手動ログインの待機時間は `--login-timeout` オプションで調整できます（デフォルト: 300秒 = 5分）

### 通常実行: データのエクスポートと分析

```bash
# 基本的な実行 (昨日のデータをエクスポート)
uv run python -m tccretro.cli

# エクスポート + データ分析 + AIフィードバック生成
uv run python -m tccretro.cli --analyze

# エクスポート + データ分析のみ (AI分析なし)
uv run python -m tccretro.cli --analyze --no-ai

# 特定の日付をエクスポート
uv run python -m tccretro.cli --export-date 2025-01-15

# 日付範囲を指定してエクスポート・分析
uv run python -m tccretro.cli --export-start-date 2025-01-01 --export-end-date 2025-01-31 --analyze

# 保存先を指定
uv run python -m tccretro.cli --output-dir ./my_exports

# デバッグモード (ブラウザを表示)
uv run python -m tccretro.cli --debug

# スローモーション実行 (動作確認用)
uv run python -m tccretro.cli --slow-mo 1000 --debug
```

### AI分析の設定

AI分析機能を使用する場合は、AWS Bedrock認証情報が必要です:

```bash
# 環境変数で設定
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key

# または ~/.aws/credentials ファイルで設定
[default]
aws_access_key_id = your_access_key
aws_secret_access_key = your_secret_key
```

AI分析を無効化する場合は `--no-ai` フラグを使用してください。

### CLIオプション一覧

```bash
# ヘルプを表示
uv run python -m tccretro.cli --help
```

主なオプション:

- `--login-only`: ログインテストのみ実行（未ログイン時は手動ログインを待機）
- `--login-timeout`: 手動ログイン待機時間（秒、`--login-only` 使用時のみ有効、デフォルト: 300）
- `--export-only`: エクスポートのみ実行 (ログイン済み前提)
- `--analyze`: データ分析とレポート生成を実行
- `--no-ai`: AI分析を無効化 (グラフと集計のみ)
- `--debug`: デバッグモード (ブラウザを表示、`--login-only` 使用時は推奨)
- `--slow-mo`: スローモーション実行 (ミリ秒)
- `--output-dir`: ダウンロードファイルの保存先 (デフォルト: `./downloads`)
- `--export-date`: エクスポート日付 (YYYY-MM-DD形式)
- `--export-start-date`: エクスポート開始日
- `--export-end-date`: エクスポート終了日
- `--env-file`: .envファイルのパス (デフォルト: `.env`)

## 出力ファイル

エクスポートと分析によって生成されるファイル:

```text
downloads/
├── tasks_20251019-20251019.csv      # エクスポートされたCSVデータ
├── charts/                          # グラフ画像 (--analyze 使用時)
│   ├── project_analysis.png         # プロジェクト別グラフ
│   └── mode_analysis.png            # モード別グラフ
└── report_20251019_153045.md        # 分析レポート (--analyze 使用時)
```

### レポートの内容

生成されるMarkdownレポートには以下が含まれます:

- **プロジェクト別時間分析**: 各プロジェクトの時間配分と割合
- **モード別時間分析**: 各モードの時間配分と割合
- **グラフ**: 円グラフと棒グラフによる可視化
- **AI分析**: Bedrock (Claude) による詳細なフィードバックと改善提案

## 開発

### テスト

このプロジェクトはpytestを使用した包括的なUnit Testを提供しています (カバレッジ: 92.54%):

```bash
cd app

# テスト実行
uv run pytest tests/ -v

# カバレッジ付きテスト実行
uv run pytest tests/ --cov=src/tccretro --cov-report=term

# HTMLカバレッジレポート生成
uv run pytest tests/ --cov=src/tccretro --cov-report=html
# ブラウザでhtmlcov/index.htmlを開く
```

**テスト方針:**

- カバレッジ目標: 85%以上
- DRY原則に基づく共通フィクスチャとヘルパーメソッドの活用
- 正常系・異常系・エッジケースを網羅的にカバー

**テスト構成:**

```text
app/tests/
├── conftest.py          # 共通フィクスチャ
├── test_login.py        # login.pyのテスト
├── test_export.py       # export.pyのテスト
└── test_cli.py          # cli.pyのテスト
```

### コード品質

このプロジェクトはpre-commitフックを使用してコード品質を維持します:

```bash
# すべてのpre-commitフックを手動実行
uv run pre-commit run --all-files

# 特定のフックを実行
uv run pre-commit run ruff --all-files
```

### リンティングとフォーマット

**Python:**

```bash
# Pythonコードをフォーマット
uv run ruff format app/

# Pythonコードをリント
uv run ruff check app/ --fix

# 型チェック
uv run mypy app/src/
```

## プロジェクト構造

```text
tccretro/
├── app/                          # Pythonアプリケーション
│   ├── src/
│   │   └── tccretro/
│   │       ├── __init__.py
│   │       ├── login.py          # ログイン状態確認
│   │       ├── export.py         # エクスポート自動化
│   │       └── cli.py            # CLIインターフェース
│   ├── pyproject.toml            # uvプロジェクト設定
│   └── .env.example              # 環境変数テンプレート
├── chrome-profile/               # 永続的Chromeプロファイル (自動生成)
├── downloads/                    # エクスポートファイル保存先 (自動生成)
└── README.md                     # このファイル
```

## トラブルシューティング

### ログイン失敗

**症状**: ログインボタンが見つからない、またはログインできない

**対処法**:

1. `--login-only --debug` オプションを使用してブラウザを表示
2. 手動でログインを試行
3. TaskChute Cloud UIが変更されている場合は `login.py` のセレクタを更新

### エクスポート失敗

**症状**: エクスポートボタンが見つからない、またはダウンロードが開始されない

**対処法**:

1. `--debug` オプションを使用して画面を確認
2. スクリーンショットを確認 (デバッグモードで自動保存)
3. TaskChute Cloud UIが変更されている場合は `export.py` のセレクタを更新

### Chromeプロファイルのリセット

認証情報をリセットしたい場合:

```bash
# chrome-profile ディレクトリを削除
rm -rf chrome-profile/

# 再度ログイン
uv run python -m tccretro.cli --login-only --debug
```

## セキュリティに関する考慮事項

- 認証情報はローカルのChromeプロファイル (`chrome-profile/`) に保存されます
- `.gitignore` によりChromeプロファイルはGit管理外です
- pre-commitフックで秘密情報の誤コミットを検出 (gitleaks)

## 今後の拡張案

- 複数のエクスポート形式をサポート
- エクスポートデータの自動分析機能
- エクスポート履歴の管理
- スケジュール実行機能 (cron等との連携)

## ライセンス

MIT
