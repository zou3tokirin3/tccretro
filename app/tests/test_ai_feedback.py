"""AIFeedbackGeneratorモジュールのテスト."""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from tccretro.ai_feedback import AIFeedbackGenerator


@pytest.fixture
def sample_dataframe():
    """テスト用のサンプルDataFrameを作成する."""
    data = {
        "タイムライン日付": ["2025-11-03", "2025-11-03", "2025-11-03"],
        "タスク名": ["タスク1", "タスク2", "タスク3"],
        "プロジェクト名": ["プロジェクトA", "プロジェクトB", "プロジェクトA"],
        "モード名": ["Focus", "Living", "Focus"],
        "ルーチン名": ["ルーチン1", "", "ルーチン2"],
        "見積時間": ["01:00:00", "00:30:00", "00:45:00"],
        "実績時間": ["01:00:00", "00:30:00", "00:45:00"],
        "開始日時": [
            "2025-11-03 09:00:00",
            "2025-11-03 10:00:00",
            "2025-11-03 10:30:00",
        ],
        "終了日時": [
            "2025-11-03 10:00:00",
            "2025-11-03 10:30:00",
            "2025-11-03 11:15:00",
        ],
    }
    return pd.DataFrame(data)


class TestAIFeedbackGenerator:
    """AIFeedbackGeneratorのテスト."""

    def test_CSVサンプルデータが抽出される(self, sample_dataframe):
        """CSVから必要なカラムのみが抽出されることを確認."""
        generator = AIFeedbackGenerator()
        csv_sample = generator._extract_relevant_csv_data(sample_dataframe, max_rows=2)

        assert csv_sample != ""
        assert "タイムライン日付" in csv_sample
        assert "タスク名" in csv_sample
        assert "プロジェクト名" in csv_sample
        assert "モード名" in csv_sample
        assert "ルーチン名" in csv_sample
        assert "見積時間" in csv_sample
        assert "実績時間" in csv_sample

        # 行数を確認（ヘッダー + 2行 = 3行）
        lines = csv_sample.strip().split("\n")
        assert len(lines) == 3

    def test_空のDataFrameでCSVサンプルが空文字列を返す(self):
        """空のDataFrameで空文字列が返されることを確認."""
        generator = AIFeedbackGenerator()
        empty_df = pd.DataFrame()
        csv_sample = generator._extract_relevant_csv_data(empty_df)

        assert csv_sample == ""

    def test_休日情報が取得される_平日(self):
        """平日の休日情報が正しく取得されることを確認."""
        generator = AIFeedbackGenerator()
        # 2025-11-03は月曜日（文化の日）
        holiday_info = generator._get_holiday_info("2025-11-03", "2025-11-03")

        assert holiday_info != ""
        assert "2025-11-03" in holiday_info
        assert "祝日" in holiday_info
        assert "文化の日" in holiday_info

    def test_休日情報が取得される_土曜日(self):
        """土曜日の休日情報が正しく取得されることを確認."""
        generator = AIFeedbackGenerator()
        # 2025-11-01は土曜日
        holiday_info = generator._get_holiday_info("2025-11-01", "2025-11-01")

        assert holiday_info != ""
        assert "2025-11-01" in holiday_info
        assert "土曜日" in holiday_info

    def test_休日情報が取得される_日曜日(self):
        """日曜日の休日情報が正しく取得されることを確認."""
        generator = AIFeedbackGenerator()
        # 2025-11-02は日曜日
        holiday_info = generator._get_holiday_info("2025-11-02", "2025-11-02")

        assert holiday_info != ""
        assert "2025-11-02" in holiday_info
        assert "日曜日" in holiday_info

    def test_休日情報が取得される_複数日(self):
        """複数日の休日情報が正しく取得されることを確認."""
        generator = AIFeedbackGenerator()
        # 2025-11-01（土）〜 2025-11-03（月・祝日）
        holiday_info = generator._get_holiday_info("2025-11-01", "2025-11-03")

        assert holiday_info != ""
        assert "2025-11-01" in holiday_info
        assert "2025-11-02" in holiday_info
        assert "2025-11-03" in holiday_info
        assert "土曜日" in holiday_info
        assert "日曜日" in holiday_info
        assert "文化の日" in holiday_info

    def test_プロンプトに日付情報が含まれる(self, sample_dataframe):
        """プロンプトに日付情報が含まれることを確認."""
        generator = AIFeedbackGenerator()
        prompt = generator._build_prompt(
            project_summary={"total_projects": 2},
            mode_summary={"total_modes": 2},
            routine_summary={"total_hours": 2.25},
            data=sample_dataframe,
            start_date="2025-11-03",
            end_date="2025-11-03",
        )

        assert "分析対象日" in prompt
        assert "2025-11-03" in prompt
        assert "文化の日" in prompt

    def test_プロンプトにCSVサンプルが含まれる(self, sample_dataframe):
        """プロンプトにCSVサンプルデータが含まれることを確認."""
        generator = AIFeedbackGenerator()
        prompt = generator._build_prompt(
            project_summary={"total_projects": 2},
            mode_summary={"total_modes": 2},
            routine_summary={"total_hours": 2.25},
            data=sample_dataframe,
            start_date="2025-11-03",
            end_date="2025-11-03",
        )

        assert "生データサンプル" in prompt
        assert "タイムライン日付" in prompt
        assert "タスク名" in prompt

    def test_プロンプトにデータなしの場合_日付情報もCSVサンプルも含まれない(self):
        """データなしの場合、プロンプトに日付情報もCSVサンプルも含まれないことを確認."""
        generator = AIFeedbackGenerator()
        prompt = generator._build_prompt(
            project_summary={"total_projects": 2},
            mode_summary={"total_modes": 2},
            routine_summary={"total_hours": 2.25},
        )

        assert "分析対象日" not in prompt
        assert "生データサンプル" not in prompt

    def test_プロンプトテンプレートファイルが存在する場合_読み込まれる(self, sample_dataframe):
        """テンプレートファイルが存在する場合、そのファイルから読み込まれることを確認."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_path = Path(tmpdir) / "custom_template.md"
            template_content = """カスタムプロンプトテンプレート
{date_info_section}
{project_definitions_section}
{project_data}
{mode_data}
{routine_data}
{csv_sample_section}
"""
            template_path.write_text(template_content, encoding="utf-8")

            generator = AIFeedbackGenerator(prompt_template_path=str(template_path))
            prompt = generator._build_prompt(
                project_summary={"total_projects": 2},
                mode_summary={"total_modes": 2},
                routine_summary={"total_hours": 2.25},
                data=sample_dataframe,
                start_date="2025-11-03",
                end_date="2025-11-03",
            )

            assert "カスタムプロンプトテンプレート" in prompt
            assert "{date_info_section}" not in prompt  # プレースホルダーが置換されている
            assert "{project_data}" not in prompt

    def test_プロンプトテンプレートファイルが存在しない場合_標準プロンプトが使用される(
        self, sample_dataframe
    ):
        """テンプレートファイルが存在しない場合、標準プロンプトが使用されることを確認."""
        generator = AIFeedbackGenerator(
            prompt_template_path="/nonexistent/path/template.md"
        )
        prompt = generator._build_prompt(
            project_summary={"total_projects": 2},
            mode_summary={"total_modes": 2},
            routine_summary={"total_hours": 2.25},
            data=sample_dataframe,
            start_date="2025-11-03",
            end_date="2025-11-03",
        )

        # 標準プロンプトの内容が含まれていることを確認
        assert "時間管理とライフスタイル改善のエキスパート" in prompt
        assert "現状分析" in prompt
        assert "改善提案" in prompt
        assert "アクションプラン" in prompt

    def test_プロンプトテンプレートのプレースホルダーが正しく置換される(
        self, sample_dataframe
    ):
        """テンプレート内のプレースホルダーが正しく置換されることを確認."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_path = Path(tmpdir) / "test_template.md"
            template_content = """テストテンプレート
日付: {date_info_section}
プロジェクト: {project_data}
モード: {mode_data}
ルーチン: {routine_data}
CSV: {csv_sample_section}
"""
            template_path.write_text(template_content, encoding="utf-8")

            generator = AIFeedbackGenerator(prompt_template_path=str(template_path))
            prompt = generator._build_prompt(
                project_summary={"total_projects": 2, "projects": {"プロジェクトA": 1.5}},
                mode_summary={"total_modes": 2, "modes": {"Focus": 1.0}},
                routine_summary={"total_hours": 2.25, "routine_hours": 1.0},
                data=sample_dataframe,
                start_date="2025-11-03",
                end_date="2025-11-03",
            )

            # プレースホルダーが置換されていることを確認
            assert "{date_info_section}" not in prompt
            assert "{project_data}" not in prompt
            assert "{mode_data}" not in prompt
            assert "{routine_data}" not in prompt
            assert "{csv_sample_section}" not in prompt

            # 実際のデータが含まれていることを確認
            assert "2025-11-03" in prompt
            assert '"total_projects": 2' in prompt
            assert '"total_modes": 2' in prompt

    def test_標準プロンプトテンプレートが取得できる(self):
        """標準プロンプトテンプレートが正しく取得できることを確認."""
        generator = AIFeedbackGenerator()
        default_template = generator._get_default_prompt_template()

        assert default_template != ""
        assert "時間管理とライフスタイル改善のエキスパート" in default_template
        assert "{date_info_section}" in default_template
        assert "{project_data}" in default_template
        assert "{mode_data}" in default_template
        assert "{routine_data}" in default_template
        assert "{csv_sample_section}" in default_template


class TestReportGeneratorDateExtraction:
    """ReportGeneratorの日付抽出機能のテスト."""

    def test_日付範囲がファイル名から抽出される(self):
        """CSVファイル名から日付範囲が正しく抽出されることを確認."""
        from tccretro.report_generator import ReportGenerator

        # 一時CSVファイルを作成（特定のファイル名で）
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "tasks_20251103-20251103.csv"
            csv_path.write_text(
                "タイムライン日付,タスク名,プロジェクト名,モード名,ルーチン名,実績時間\n"
                "2025-11-03,タスク1,プロジェクトA,Focus,ルーチン1,01:00:00\n",
                encoding="utf-8",
            )

            generator = ReportGenerator(
                csv_path=csv_path,
                output_dir=Path(tmpdir),
                enable_ai=False,
            )

            start_date, end_date = generator._extract_date_range_from_csv()

            assert start_date == "2025-11-03"
            assert end_date == "2025-11-03"

    def test_日付範囲がCSVデータから抽出される(self):
        """ファイル名から抽出できない場合、CSVデータから日付範囲が抽出されることを確認."""
        from tccretro.report_generator import ReportGenerator

        # 一時CSVファイルを作成（標準的でないファイル名で）
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "custom_data.csv"
            csv_path.write_text(
                "タイムライン日付,タスク名,プロジェクト名,モード名,ルーチン名,実績時間\n"
                "2025-11-01,タスク1,プロジェクトA,Focus,ルーチン1,01:00:00\n"
                "2025-11-03,タスク2,プロジェクトB,Living,,00:30:00\n",
                encoding="utf-8",
            )

            generator = ReportGenerator(
                csv_path=csv_path,
                output_dir=Path(tmpdir),
                enable_ai=False,
            )

            start_date, end_date = generator._extract_date_range_from_csv()

            assert start_date == "2025-11-01"
            assert end_date == "2025-11-03"
