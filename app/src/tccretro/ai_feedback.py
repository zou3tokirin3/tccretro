"""Amazon Bedrock (Claude) によるAI分析モジュール."""

import json
import logging
import os
from pathlib import Path
from typing import Any

import boto3
import yaml
from botocore.config import Config

logger = logging.getLogger(__name__)


class AIFeedbackGenerator:
    """Amazon Bedrock (Claude) を使用してデータ分析とフィードバックを生成するクラス."""

    def __init__(
        self,
        model_id: str = "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        project_definitions_path: str | None = None,
        prompt_template_path: str | None = None,
    ):
        """AIFeedbackGeneratorを初期化する.

        Args:
            model_id: 使用するBedrockのモデルIDまたは推論プロファイルID
            project_definitions_path: プロジェクト定義YAMLファイルのパス（省略時はデフォルトパス）
            prompt_template_path: プロンプトテンプレートファイルのパス（省略時はデフォルトパス）
        """
        self.model_id = model_id
        self.bedrock_client = self._create_bedrock_client()
        self.project_definitions = self._load_project_definitions(project_definitions_path)
        self.prompt_template_path = prompt_template_path

    def _create_bedrock_client(self) -> Any:
        """Bedrock Runtimeクライアントを作成する.

        環境変数からAWS認証情報を取得します。

        Returns:
            boto3.client: Bedrock Runtimeクライアント

        Raises:
            Exception: AWS認証情報が設定されていない場合
        """
        try:
            # AWS認証情報を環境変数から取得
            aws_region = os.getenv("AWS_REGION", "us-east-1")

            # タイムアウト設定を追加（Claude Sonnet 4.5は応答に時間がかかるため）
            config = Config(
                read_timeout=180,  # 読み取りタイムアウト: 3分
                connect_timeout=60,  # 接続タイムアウト: 1分
            )

            client = boto3.client(
                service_name="bedrock-runtime",
                region_name=aws_region,
                config=config,
            )
            logger.info("Bedrock Runtimeクライアントを初期化しました (region: %s)", aws_region)
            return client
        except Exception as e:
            logger.error("Bedrock Runtimeクライアントの初期化に失敗しました: %s", e)
            raise

    def _load_project_definitions(self, definitions_path: str | None = None) -> dict[str, Any]:
        """プロジェクト定義YAMLファイルを読み込む.

        Args:
            definitions_path: YAMLファイルのパス（省略時はデフォルトパス）

        Returns:
            dict[str, Any]: プロジェクト定義の辞書

        Raises:
            FileNotFoundError: YAMLファイルが見つからない場合
            yaml.YAMLError: YAMLのパースエラー
        """
        if definitions_path is None:
            # デフォルトパス: このファイルの親ディレクトリの親の親/project_definitions.yaml
            current_file = Path(__file__)
            definitions_path = str(current_file.parent.parent.parent / "project_definitions.yaml")

        path = Path(definitions_path)

        if not path.exists():
            logger.warning(
                "プロジェクト定義ファイルが見つかりません: %s。空の定義を使用します。",
                definitions_path,
            )
            return {}

        try:
            with path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                logger.info("プロジェクト定義を読み込みました: %s", definitions_path)
                return data.get("projects", {}) if data else {}
        except yaml.YAMLError as e:
            logger.error("プロジェクト定義の読み込みに失敗しました: %s", e)
            return {}

    def _format_project_definitions(self) -> str:
        """プロジェクト定義をプロンプト用にフォーマットする.

        Returns:
            str: フォーマットされたプロジェクト定義文字列
        """
        if not self.project_definitions:
            return ""

        lines = ["# プロジェクト定義", "", "以下は各プロジェクトの定義です：", ""]

        for project_name, project_info in self.project_definitions.items():
            description = project_info.get("description", "").strip()
            if description:
                lines.append(f"## {project_name}")
                lines.append(description)
                lines.append("")

        return "\n".join(lines)

    def _load_prompt_template(self) -> str | None:
        """プロンプトテンプレートファイルを読み込む.

        Returns:
            str | None: テンプレートファイルの内容。ファイルが見つからない場合はNone
        """
        if self.prompt_template_path is None:
            # デフォルトパス: このファイルの親ディレクトリの親の親/config/prompt_template.md
            current_file = Path(__file__)
            template_path = current_file.parent.parent.parent / "config" / "prompt_template.md"
        else:
            template_path = Path(self.prompt_template_path)

        if not template_path.exists():
            logger.warning(
                "プロンプトテンプレートファイルが見つかりません: %s。標準プロンプトを使用します。",
                template_path,
            )
            return None

        try:
            with template_path.open("r", encoding="utf-8") as f:
                template = f.read()
                logger.info("プロンプトテンプレートを読み込みました: %s", template_path)
                return template
        except Exception as e:
            logger.error("プロンプトテンプレートの読み込みに失敗しました: %s", e)
            return None

    def _get_default_prompt_template(self) -> str:
        """標準プロンプトテンプレートを返す.

        Returns:
            str: 標準プロンプトテンプレート
        """
        return """あなたは時間管理とライフスタイル改善のエキスパートです。
以下のTaskChute Cloudのデータ分析結果をもとに、より良い暮らしのための時間の使い方についての詳細なフィードバックを提供してください。
{date_info_section}
{project_definitions_section}

# プロジェクト別分析データ
```json
{project_data}
```

# モード別分析データ
```json
{mode_data}
```

# ルーチン別分析データ
```json
{routine_data}
```
{csv_sample_section}
以下の観点から分析とフィードバックを提供してください：

## 1. 現状分析
- 時間の使い方の傾向と特徴
- バランスの良い点と課題点
- 特に注目すべきプロジェクトやモード
- ルーチンタスクと非ルーチンタスクの割合とその意味

## 2. 改善提案
- より良い時間配分のための具体的な提案
- ワークライフバランスの改善案
- 優先順位付けのアドバイス
- ルーチン化できるタスクやルーチンの見直しについて

## 3. アクションプラン
- 今週から実践できる具体的な行動
- 短期目標（1週間）と中期目標（1ヶ月）
- 進捗を測定する指標

回答はMarkdown形式で、見出しを使って構造化してください。
具体的で実践的なアドバイスを心がけてください。"""

    def _extract_relevant_csv_data(self, data: Any, max_rows: int = 1000) -> str:
        """CSVデータから必要なカラムのみを抽出してサンプルを作成する.

        Args:
            data: pandas DataFrame
            max_rows: 抽出する最大行数（デフォルト: 1000）

        Returns:
            str: CSV形式のサンプルデータ
        """
        try:
            # 分析に必要なカラムのみを抽出
            relevant_columns = [
                "タイムライン日付",
                "タスク名",
                "プロジェクト名",
                "モード名",
                "ルーチン名",
                "見積時間",
                "実績時間",
                "開始日時",
                "終了日時",
            ]

            # 存在するカラムのみを抽出
            available_columns = [col for col in relevant_columns if col in data.columns]

            if not available_columns:
                return ""

            # データ行数を確認し、上限を超える場合は警告
            total_rows = len(data)
            if total_rows > max_rows:
                logger.warning(
                    "CSVデータが%d行ありますが、プロンプトサイズの制限により最初の%d行のみを使用します。"
                    "より詳細な分析には、日付範囲を絞って実行することをお勧めします。",
                    total_rows,
                    max_rows,
                )

            # サンプルデータを抽出（最初のmax_rows行）
            sample_data = data[available_columns].head(max_rows)

            # CSV形式に変換
            csv_string: str | None = sample_data.to_csv(index=False)
            return csv_string if csv_string is not None else ""

        except Exception as e:
            logger.warning("CSVサンプルデータの抽出に失敗しました: %s", e)
            return ""

    def _get_holiday_info(self, start_date: str, end_date: str) -> str:
        """日付が休日・祝日かどうかを判定する.

        Args:
            start_date: 開始日（YYYY-MM-DD形式）
            end_date: 終了日（YYYY-MM-DD形式）

        Returns:
            str: 休日情報の文字列
        """
        try:
            import datetime

            import jpholiday

            # 日付をパース
            start = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()

            # 期間内の各日付を確認
            holiday_info_list = []
            current = start
            while current <= end:
                day_info = []

                # 曜日を取得
                weekday = current.strftime("%A")
                weekday_ja = {
                    "Monday": "月",
                    "Tuesday": "火",
                    "Wednesday": "水",
                    "Thursday": "木",
                    "Friday": "金",
                    "Saturday": "土",
                    "Sunday": "日",
                }.get(weekday, "")

                # 休日・祝日判定
                if jpholiday.is_holiday(current):
                    holiday_name = jpholiday.is_holiday_name(current)
                    day_info.append(f"{current} ({weekday_ja}曜日): 祝日 - {holiday_name}")
                elif current.weekday() == 5:  # 土曜日
                    day_info.append(f"{current} ({weekday_ja}曜日): 土曜日")
                elif current.weekday() == 6:  # 日曜日
                    day_info.append(f"{current} ({weekday_ja}曜日): 日曜日")
                else:
                    day_info.append(f"{current} ({weekday_ja}曜日): 平日")

                if day_info:
                    holiday_info_list.extend(day_info)

                current += datetime.timedelta(days=1)

            if holiday_info_list:
                return "\n" + "\n".join(holiday_info_list)
            return ""

        except Exception as e:
            logger.warning("休日情報の取得に失敗しました: %s", e)
            return ""

    def generate_feedback(
        self,
        project_summary: dict[str, Any],
        mode_summary: dict[str, Any],
        routine_summary: dict[str, Any],
        data: Any | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> str:
        """分析データをもとにAIフィードバックを生成する.

        Args:
            project_summary: プロジェクト別分析のサマリー
            mode_summary: モード別分析のサマリー
            routine_summary: ルーチン別分析のサマリー
            data: 元のCSVデータ（pandas DataFrame）
            start_date: 分析開始日（YYYY-MM-DD形式）
            end_date: 分析終了日（YYYY-MM-DD形式）

        Returns:
            str: 生成されたフィードバック（Markdown形式）
        """
        logger.info("AI分析を開始します")

        # プロンプトを構築
        prompt = self._build_prompt(
            project_summary,
            mode_summary,
            routine_summary,
            data,
            start_date,
            end_date,
        )

        try:
            # Bedrock APIを呼び出し
            response = self.bedrock_client.converse(
                modelId=self.model_id,
                messages=[
                    {
                        "role": "user",
                        "content": [{"text": prompt}],
                    }
                ],
                inferenceConfig={
                    "maxTokens": 4000,
                    "temperature": 0.7,
                },
            )

            # レスポンスからテキストを抽出
            feedback: str = response["output"]["message"]["content"][0]["text"]
            logger.info("AI分析が完了しました")
            return feedback

        except Exception as e:
            error_message = str(e)
            logger.error("AI分析に失敗しました: %s", error_message)

            # ResourceNotFoundExceptionの場合、より詳細なメッセージを追加
            if "ResourceNotFoundException" in error_message:
                if "use case details" in error_message.lower():
                    logger.warning(
                        "Anthropicモデルの利用には、AWSアカウントで利用ケース詳細フォームの提出が必要な場合があります。"
                        "AWS BedrockコンソールのModel catalogから該当モデルを選択し、"
                        "利用ケース詳細フォームを提出してください。"
                        "詳細: https://console.aws.amazon.com/bedrock/home#/model-catalog"
                    )

            return self._generate_fallback_feedback(project_summary, mode_summary, routine_summary)

    def _build_prompt(
        self,
        project_summary: dict[str, Any],
        mode_summary: dict[str, Any],
        routine_summary: dict[str, Any],
        data: Any | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> str:
        """AI分析用のプロンプトを構築する.

        Args:
            project_summary: プロジェクト別分析のサマリー
            mode_summary: モード別分析のサマリー
            routine_summary: ルーチン別分析のサマリー
            data: 元のCSVデータ（pandas DataFrame）
            start_date: 分析開始日（YYYY-MM-DD形式）
            end_date: 分析終了日（YYYY-MM-DD形式）

        Returns:
            str: 構築されたプロンプト
        """
        project_data = json.dumps(project_summary, ensure_ascii=False, indent=2)
        mode_data = json.dumps(mode_summary, ensure_ascii=False, indent=2)
        routine_data = json.dumps(routine_summary, ensure_ascii=False, indent=2)

        # プロジェクト定義セクションを取得
        project_definitions_section = self._format_project_definitions()

        # 日付情報セクション
        date_info_section = ""
        if start_date and end_date:
            holiday_info = self._get_holiday_info(start_date, end_date)
            if start_date == end_date:
                date_info_section = f"\n# 分析対象日\n{start_date}{holiday_info}\n"
            else:
                date_info_section = f"\n# 分析対象期間\n{start_date} 〜 {end_date}{holiday_info}\n"

        # CSVサンプルデータセクション
        csv_sample_section = ""
        if data is not None:
            csv_sample = self._extract_relevant_csv_data(data)
            if csv_sample:
                csv_sample_section = (
                    f"\n# 生データサンプル（参考情報）\n\n```csv\n{csv_sample}\n```\n"
                )

        # プロンプトテンプレートを読み込む（見つからない場合は標準プロンプトを使用）
        template = self._load_prompt_template()
        if template is None:
            template = self._get_default_prompt_template()

        # プレースホルダーを置換
        prompt = template.replace("{date_info_section}", date_info_section)
        prompt = prompt.replace("{project_definitions_section}", project_definitions_section)
        prompt = prompt.replace("{project_data}", project_data)
        prompt = prompt.replace("{mode_data}", mode_data)
        prompt = prompt.replace("{routine_data}", routine_data)
        prompt = prompt.replace("{csv_sample_section}", csv_sample_section)

        return prompt

    def _generate_fallback_feedback(
        self,
        project_summary: dict[str, Any],
        mode_summary: dict[str, Any],
        routine_summary: dict[str, Any],
    ) -> str:
        """AI分析が失敗した場合のフォールバックフィードバックを生成する.

        Args:
            project_summary: プロジェクト別分析のサマリー
            mode_summary: モード別分析のサマリー
            routine_summary: ルーチン別分析のサマリー

        Returns:
            str: 基本的なフィードバック（Markdown形式）
        """
        lines = [
            "## AI分析結果",
            "",
            "> **注意**: AI分析サービスに接続できませんでした。基本的な分析結果を表示します。",
            "",
            "### プロジェクト別の傾向",
            "",
            f"- 合計 {project_summary.get('total_projects', 0)} プロジェクトで活動",
            f"- 総時間: {project_summary.get('total_hours', 0):.2f} 時間",
        ]

        top_project = project_summary.get("top_project")
        if top_project:
            top_hours = project_summary.get("top_project_hours", 0)
            lines.append(f"- 最も時間を使ったプロジェクト: **{top_project}** ({top_hours:.2f}時間)")

        lines.extend(
            [
                "",
                "### モード別の傾向",
                "",
                f"- 合計 {mode_summary.get('total_modes', 0)} モードで活動",
                f"- 総時間: {mode_summary.get('total_hours', 0):.2f} 時間",
            ]
        )

        top_mode = mode_summary.get("top_mode")
        if top_mode:
            top_mode_hours = mode_summary.get("top_mode_hours", 0)
            lines.append(f"- 最も時間を使ったモード: **{top_mode}** ({top_mode_hours:.2f}時間)")

        lines.extend(
            [
                "",
                "### ルーチン別の傾向",
                "",
                f"- 総時間: {routine_summary.get('total_hours', 0):.2f} 時間",
                f"- ルーチンタスク: {routine_summary.get('routine_hours', 0):.2f} 時間 "
                f"({routine_summary.get('routine_percentage', 0):.1f}%)",
                f"- 非ルーチンタスク: {routine_summary.get('non_routine_hours', 0):.2f} 時間 "
                f"({routine_summary.get('non_routine_percentage', 0):.1f}%)",
            ]
        )

        lines.extend(
            [
                "",
                "### 推奨事項",
                "",
                "- 時間配分を定期的に見直しましょう",
                "- バランスの取れた生活を心がけましょう",
                "- 優先順位の高いタスクに集中しましょう",
                "- ルーチン化できるタスクを見つけて効率化しましょう",
                "",
            ]
        )

        return "\n".join(lines)
