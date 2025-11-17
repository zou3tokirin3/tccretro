"""export.pyモジュールのテスト."""

from contextlib import contextmanager
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from tccretro.export import TaskChuteExporter


class TestTaskChuteExporter:
    """TaskChuteExporterクラスのテストスイート."""

    def test_init_creates_download_dir(self, tmp_path: Path):
        """__init__: ダウンロードディレクトリが作成されることを確認."""
        download_dir = tmp_path / "test_downloads"

        exporter = TaskChuteExporter(download_dir=str(download_dir), debug=False)

        assert exporter.download_dir == download_dir
        assert download_dir.exists()
        assert exporter.debug is False

    def test_init_with_debug_mode(self, tmp_path: Path):
        """__init__: デバッグモードが正しく設定されることを確認."""
        exporter = TaskChuteExporter(download_dir=str(tmp_path), debug=True)

        assert exporter.debug is True

    def test_fill_date_range_single_input_success(self, mock_page: Mock, mock_locator: Mock):
        """fill_date_range: 単一入力方式で日付範囲を正常に入力."""
        exporter = TaskChuteExporter()
        start_date = date(2025, 1, 1)
        end_date = date(2025, 1, 31)

        # 単一入力フィールドが見つかる場合
        mock_locator.count.return_value = 1
        mock_page.locator.return_value = mock_locator

        result = exporter.fill_date_range(mock_page, start_date, end_date)

        assert result is True
        mock_page.locator.assert_called_once_with('input[placeholder*="YYYY"]')
        mock_locator.click.assert_called_once()
        mock_locator.fill.assert_called_once_with("2025/01/01 - 2025/01/31")
        mock_locator.press.assert_called_once_with("Enter")

    def test_fill_date_range_individual_fields_success(self, mock_page: Mock):
        """fill_date_range: 個別フィールド方式で日付範囲を正常に入力."""
        exporter = TaskChuteExporter()
        start_date = date(2025, 1, 15)
        end_date = date(2025, 1, 20)

        # 単一入力フィールドが見つからない場合
        mock_single_input = MagicMock()
        mock_single_input.count.return_value = 0

        # 個別フィールドのモック
        mock_year_start = MagicMock()
        mock_year_start.count.return_value = 1
        mock_month_start = MagicMock()
        mock_day_start = MagicMock()
        mock_year_end = MagicMock()
        mock_month_end = MagicMock()
        mock_day_end = MagicMock()

        # locatorの呼び出しごとに異なるモックを返す
        locator_map = {
            'input[placeholder*="YYYY"]': mock_single_input,
            '[aria-label="年"][data-range-position="start"]': mock_year_start,
            '[aria-label="月"][data-range-position="start"]': mock_month_start,
            '[aria-label="日"][data-range-position="start"]': mock_day_start,
            '[aria-label="年"][data-range-position="end"]': mock_year_end,
            '[aria-label="月"][data-range-position="end"]': mock_month_end,
            '[aria-label="日"][data-range-position="end"]': mock_day_end,
        }

        def locator_side_effect(selector: str):
            mock = locator_map.get(selector, MagicMock())
            mock.first = mock
            return mock

        mock_page.locator.side_effect = locator_side_effect

        result = exporter.fill_date_range(mock_page, start_date, end_date)

        assert result is True
        # 各フィールドに正しい値が入力されたことを確認
        mock_year_start.fill.assert_called_once_with("2025")
        mock_month_start.fill.assert_called_once_with("1")
        mock_day_start.fill.assert_called_once_with("15")
        mock_year_end.fill.assert_called_once_with("2025")
        mock_month_end.fill.assert_called_once_with("1")
        mock_day_end.fill.assert_called_once_with("20")

    def test_fill_date_range_failure_no_fields(self, mock_page: Mock):
        """fill_date_range: 日付フィールドが見つからない場合、Falseを返す."""
        exporter = TaskChuteExporter()
        start_date = date(2025, 1, 1)
        end_date = date(2025, 1, 31)

        # すべてのフィールドが見つからない
        mock_locator = MagicMock()
        mock_locator.count.return_value = 0
        mock_page.locator.return_value = mock_locator

        result = exporter.fill_date_range(mock_page, start_date, end_date)

        assert result is False

    def test_fill_date_range_exception_handling(self, mock_page: Mock, capsys):
        """fill_date_range: 例外が発生した場合、Falseを返す."""
        exporter = TaskChuteExporter()
        start_date = date(2025, 1, 1)
        end_date = date(2025, 1, 31)

        # locatorで例外を発生させる
        mock_page.locator.side_effect = Exception("Element not found")

        result = exporter.fill_date_range(mock_page, start_date, end_date)

        assert result is False
        captured = capsys.readouterr()
        assert "日付範囲の入力に失敗しました" in captured.out

    def test_export_data_success(
        self, mock_page: Mock, mock_locator: Mock, mock_download: Mock, temp_download_dir: Path
    ):
        """export_data: データエクスポートが正常に成功."""
        exporter = TaskChuteExporter(download_dir=str(temp_download_dir), debug=False)
        start_date = date(2025, 1, 1)
        end_date = date(2025, 1, 31)

        # fill_date_rangeをモック化
        with patch.object(exporter, "fill_date_range", return_value=True):
            # ダウンロードボタンのモック
            mock_locator.count.return_value = 1
            mock_page.locator.return_value = mock_locator

            # ダウンロードのモック
            @contextmanager
            def mock_expect_download(timeout):
                yield type("obj", (object,), {"value": mock_download})

            mock_page.expect_download = mock_expect_download

            result = exporter.export_data(mock_page, start_date, end_date)

            assert result is not None
            assert "test_export.csv" in result
            mock_page.goto.assert_called_once_with(
                "https://taskchute.cloud/export/csv-export", timeout=30000
            )
            mock_locator.click.assert_called_once()
            mock_download.save_as.assert_called_once()

    def test_export_data_default_dates(
        self, mock_page: Mock, mock_locator: Mock, mock_download: Mock, temp_download_dir: Path
    ):
        """export_data: 日付が指定されていない場合、デフォルト（昨日）を使用."""
        exporter = TaskChuteExporter(download_dir=str(temp_download_dir))

        with patch.object(exporter, "fill_date_range", return_value=True) as mock_fill:
            mock_locator.count.return_value = 1
            mock_page.locator.return_value = mock_locator

            @contextmanager
            def mock_expect_download(timeout):
                yield type("obj", (object,), {"value": mock_download})

            mock_page.expect_download = mock_expect_download

            exporter.export_data(mock_page)

            # fill_date_rangeが呼ばれたことを確認（具体的な日付の検証は省略）
            assert mock_fill.called

    def test_export_data_fill_date_failure(self, mock_page: Mock, temp_download_dir: Path):
        """export_data: 日付入力に失敗した場合、Noneを返す."""
        exporter = TaskChuteExporter(download_dir=str(temp_download_dir))

        with patch.object(exporter, "fill_date_range", return_value=False):
            result = exporter.export_data(mock_page, date(2025, 1, 1), date(2025, 1, 31))

            assert result is None

    def test_export_data_no_download_button(self, mock_page: Mock, temp_download_dir: Path):
        """export_data: ダウンロードボタンが見つからない場合、Noneを返す."""
        exporter = TaskChuteExporter(download_dir=str(temp_download_dir))

        with patch.object(exporter, "fill_date_range", return_value=True):
            # ダウンロードボタンが見つからない
            mock_locator = MagicMock()
            mock_locator.count.return_value = 0
            mock_page.locator.return_value = mock_locator

            result = exporter.export_data(mock_page, date(2025, 1, 1), date(2025, 1, 31))

            assert result is None

    def test_export_data_with_debug_screenshots(
        self, mock_page: Mock, mock_locator: Mock, mock_download: Mock, temp_download_dir: Path
    ):
        """export_data: デバッグモード時にスクリーンショットが保存される."""
        exporter = TaskChuteExporter(download_dir=str(temp_download_dir), debug=True)

        with patch.object(exporter, "fill_date_range", return_value=True):
            mock_locator.count.return_value = 1
            mock_page.locator.return_value = mock_locator

            @contextmanager
            def mock_expect_download(timeout):
                yield type("obj", (object,), {"value": mock_download})

            mock_page.expect_download = mock_expect_download

            exporter.export_data(mock_page, date(2025, 1, 1), date(2025, 1, 31))

            # スクリーンショットが複数回呼ばれることを確認
            assert mock_page.screenshot.call_count >= 2

    def test_export_data_exception_handling(self, mock_page: Mock, temp_download_dir: Path, capsys):
        """export_data: 例外が発生した場合、Noneを返す."""
        exporter = TaskChuteExporter(download_dir=str(temp_download_dir))

        # gotoで例外を発生させる
        mock_page.goto.side_effect = Exception("Network error")

        result = exporter.export_data(mock_page, date(2025, 1, 1), date(2025, 1, 31))

        assert result is None
        captured = capsys.readouterr()
        assert "エクスポートがエラーで失敗しました" in captured.out

    def test_wait_for_export_button_success(self, mock_page: Mock):
        """wait_for_export_button: エクスポートボタンが見つかった場合、Trueを返す."""
        exporter = TaskChuteExporter()

        # 最初のセレクタで見つかる
        mock_page.wait_for_selector.return_value = True

        result = exporter.wait_for_export_button(mock_page, timeout=5000)

        assert result is True
        mock_page.wait_for_selector.assert_called_once_with(
            'button:has-text("エクスポート")', timeout=5000
        )

    def test_wait_for_export_button_fallback_selector(self, mock_page: Mock):
        """wait_for_export_button: 複数のセレクタを試行し、見つかった場合Trueを返す."""
        exporter = TaskChuteExporter()

        # 最初のセレクタでは見つからず、2番目で見つかる
        call_count = 0

        def wait_side_effect(selector, timeout):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Not found")
            return True

        mock_page.wait_for_selector.side_effect = wait_side_effect

        result = exporter.wait_for_export_button(mock_page)

        assert result is True
        assert mock_page.wait_for_selector.call_count == 2

    def test_wait_for_export_button_not_found(self, mock_page: Mock):
        """wait_for_export_button: すべてのセレクタで見つからない場合、Falseを返す."""
        exporter = TaskChuteExporter()

        # すべてのセレクタで見つからない
        mock_page.wait_for_selector.side_effect = Exception("Not found")

        result = exporter.wait_for_export_button(mock_page)

        assert result is False
        # 4つのセレクタすべてが試行される
        assert mock_page.wait_for_selector.call_count == 4

    def test_get_expected_filename(self, temp_download_dir: Path):
        """get_expected_filename: 期待されるファイル名が正しく生成される."""
        exporter = TaskChuteExporter(download_dir=str(temp_download_dir))
        target_date = date(2025, 11, 15)

        result = exporter.get_expected_filename(target_date)

        assert result == temp_download_dir / "tasks_20251115-20251115.csv"

    def test_check_existing_files_all_exist(self, temp_download_dir: Path):
        """_check_existing_files: 全てのファイルが存在する場合."""
        exporter = TaskChuteExporter(download_dir=str(temp_download_dir))
        start_date = date(2025, 11, 10)
        end_date = date(2025, 11, 12)

        # ファイルを作成
        (temp_download_dir / "tasks_20251110-20251110.csv").touch()
        (temp_download_dir / "tasks_20251111-20251111.csv").touch()
        (temp_download_dir / "tasks_20251112-20251112.csv").touch()

        existing_dates, missing_dates = exporter.check_existing_files(start_date, end_date)

        assert len(existing_dates) == 3
        assert len(missing_dates) == 0
        assert existing_dates == [date(2025, 11, 10), date(2025, 11, 11), date(2025, 11, 12)]

    def test_check_existing_files_some_missing(self, temp_download_dir: Path):
        """_check_existing_files: 一部のファイルが欠けている場合."""
        exporter = TaskChuteExporter(download_dir=str(temp_download_dir))
        start_date = date(2025, 11, 10)
        end_date = date(2025, 11, 12)

        # 一部のファイルのみ作成
        (temp_download_dir / "tasks_20251110-20251110.csv").touch()
        # 2025-11-11は欠けている
        (temp_download_dir / "tasks_20251112-20251112.csv").touch()

        existing_dates, missing_dates = exporter.check_existing_files(start_date, end_date)

        assert len(existing_dates) == 2
        assert len(missing_dates) == 1
        assert existing_dates == [date(2025, 11, 10), date(2025, 11, 12)]
        assert missing_dates == [date(2025, 11, 11)]

    def test_check_existing_files_all_missing(self, temp_download_dir: Path):
        """_check_existing_files: 全てのファイルが欠けている場合."""
        exporter = TaskChuteExporter(download_dir=str(temp_download_dir))
        start_date = date(2025, 11, 10)
        end_date = date(2025, 11, 12)

        existing_dates, missing_dates = exporter.check_existing_files(start_date, end_date)

        assert len(existing_dates) == 0
        assert len(missing_dates) == 3
        assert missing_dates == [date(2025, 11, 10), date(2025, 11, 11), date(2025, 11, 12)]

    def test_check_existing_files_with_range_file(self, temp_download_dir: Path):
        """check_existing_files: 範囲ファイルが存在する場合."""
        exporter = TaskChuteExporter(download_dir=str(temp_download_dir))
        start_date = date(2025, 11, 11)
        end_date = date(2025, 11, 13)

        # 範囲ファイルを作成（3日分を1つのファイルに）
        (temp_download_dir / "tasks_20251111-20251113.csv").touch()

        existing_dates, missing_dates = exporter.check_existing_files(start_date, end_date)

        assert len(existing_dates) == 3
        assert len(missing_dates) == 0
        assert existing_dates == [date(2025, 11, 11), date(2025, 11, 12), date(2025, 11, 13)]

    def test_check_existing_files_partial_range_coverage(self, temp_download_dir: Path):
        """check_existing_files: 範囲ファイルが一部の日付をカバーしている場合."""
        exporter = TaskChuteExporter(download_dir=str(temp_download_dir))
        start_date = date(2025, 11, 10)
        end_date = date(2025, 11, 13)

        # 範囲ファイルを作成（11-12日のみ）
        (temp_download_dir / "tasks_20251111-20251112.csv").touch()

        existing_dates, missing_dates = exporter.check_existing_files(start_date, end_date)

        assert len(existing_dates) == 2
        assert len(missing_dates) == 2
        assert existing_dates == [date(2025, 11, 11), date(2025, 11, 12)]
        assert missing_dates == [date(2025, 11, 10), date(2025, 11, 13)]

    def test_parse_filename_date_range(self, temp_download_dir: Path):
        """_parse_filename_date_range: ファイル名から日付範囲を正しく抽出."""
        exporter = TaskChuteExporter(download_dir=str(temp_download_dir))

        # 単一日付
        start, end = exporter._parse_filename_date_range("tasks_20251110-20251110.csv")
        assert start == date(2025, 11, 10)
        assert end == date(2025, 11, 10)

        # 範囲日付
        start, end = exporter._parse_filename_date_range("tasks_20251111-20251113.csv")
        assert start == date(2025, 11, 11)
        assert end == date(2025, 11, 13)

        # 無効なファイル名
        start, end = exporter._parse_filename_date_range("invalid.csv")
        assert start is None
        assert end is None

    def test_group_consecutive_dates_single_range(self, temp_download_dir: Path):
        """_group_consecutive_dates: 連続する日付が1つの範囲にグループ化される."""
        exporter = TaskChuteExporter(download_dir=str(temp_download_dir))
        dates = [date(2025, 11, 10), date(2025, 11, 11), date(2025, 11, 12)]

        result = exporter._group_consecutive_dates(dates)

        assert len(result) == 1
        assert result[0] == (date(2025, 11, 10), date(2025, 11, 12))

    def test_group_consecutive_dates_multiple_ranges(self, temp_download_dir: Path):
        """_group_consecutive_dates: 連続しない日付が複数の範囲にグループ化される."""
        exporter = TaskChuteExporter(download_dir=str(temp_download_dir))
        dates = [date(2025, 11, 10), date(2025, 11, 11), date(2025, 11, 13), date(2025, 11, 14)]

        result = exporter._group_consecutive_dates(dates)

        assert len(result) == 2
        assert result[0] == (date(2025, 11, 10), date(2025, 11, 11))
        assert result[1] == (date(2025, 11, 13), date(2025, 11, 14))

    def test_group_consecutive_dates_single_date(self, temp_download_dir: Path):
        """_group_consecutive_dates: 単一の日付が1つの範囲にグループ化される."""
        exporter = TaskChuteExporter(download_dir=str(temp_download_dir))
        dates = [date(2025, 11, 10)]

        result = exporter._group_consecutive_dates(dates)

        assert len(result) == 1
        assert result[0] == (date(2025, 11, 10), date(2025, 11, 10))

    def test_group_consecutive_dates_empty(self, temp_download_dir: Path):
        """_group_consecutive_dates: 空のリストが空の範囲リストを返す."""
        exporter = TaskChuteExporter(download_dir=str(temp_download_dir))
        dates = []

        result = exporter._group_consecutive_dates(dates)

        assert len(result) == 0

    def test_export_data_all_files_exist_skip(
        self, mock_page: Mock, temp_download_dir: Path, capsys
    ):
        """export_data: 全てのファイルが存在する場合、エクスポートをスキップ."""
        exporter = TaskChuteExporter(download_dir=str(temp_download_dir))
        start_date = date(2025, 11, 10)
        end_date = date(2025, 11, 10)

        # ファイルを作成
        existing_file = temp_download_dir / "tasks_20251110-20251110.csv"
        existing_file.touch()

        result = exporter.export_data(mock_page, start_date, end_date)

        assert result == str(existing_file)
        # エクスポート処理が呼ばれていないことを確認
        mock_page.goto.assert_not_called()
        captured = capsys.readouterr()
        assert "全ての日付のファイルが既に存在します" in captured.out
        assert "スキップします" in captured.out

    def test_export_data_some_files_missing_partial_export(
        self, mock_page: Mock, mock_locator: Mock, mock_download: Mock, temp_download_dir: Path, capsys
    ):
        """export_data: 一部のファイルが欠けている場合、欠けている日付のみエクスポート."""
        exporter = TaskChuteExporter(download_dir=str(temp_download_dir))
        start_date = date(2025, 11, 10)
        end_date = date(2025, 11, 12)

        # 一部のファイルのみ作成
        (temp_download_dir / "tasks_20251110-20251110.csv").touch()
        # 2025-11-11は欠けている
        (temp_download_dir / "tasks_20251112-20251112.csv").touch()

        # fill_date_rangeとエクスポート処理をモック化
        with patch.object(exporter, "_export_date_range", return_value=str(temp_download_dir / "tasks_20251111-20251111.csv")):
            result = exporter.export_data(mock_page, start_date, end_date)

            assert result is not None
            assert "tasks_20251111-20251111.csv" in result
            # 欠けている日付のみエクスポートされることを確認
            exporter._export_date_range.assert_called_once_with(mock_page, date(2025, 11, 11), date(2025, 11, 11))
            captured = capsys.readouterr()
            assert "既存ファイルが見つかりました" in captured.out
            assert "欠けている日付のみをエクスポートします" in captured.out

    def test_export_data_all_files_missing_normal_export(
        self, mock_page: Mock, mock_locator: Mock, mock_download: Mock, temp_download_dir: Path
    ):
        """export_data: 全てのファイルが欠けている場合、通常通りエクスポート."""
        exporter = TaskChuteExporter(download_dir=str(temp_download_dir))
        start_date = date(2025, 11, 10)
        end_date = date(2025, 11, 10)

        # fill_date_rangeとエクスポート処理をモック化
        with patch.object(exporter, "_export_date_range", return_value=str(temp_download_dir / "tasks_20251110-20251110.csv")):
            result = exporter.export_data(mock_page, start_date, end_date)

            assert result is not None
            # 通常通りエクスポートされることを確認
            exporter._export_date_range.assert_called_once_with(mock_page, start_date, end_date)

    def test_export_data_multiple_missing_ranges(
        self, mock_page: Mock, temp_download_dir: Path
    ):
        """export_data: 複数の連続しない範囲が欠けている場合、各範囲を個別にエクスポート."""
        exporter = TaskChuteExporter(download_dir=str(temp_download_dir))
        start_date = date(2025, 11, 10)
        end_date = date(2025, 11, 14)

        # 一部のファイルのみ作成（2025-11-10, 2025-11-12, 2025-11-14は存在）
        (temp_download_dir / "tasks_20251110-20251110.csv").touch()
        (temp_download_dir / "tasks_20251112-20251112.csv").touch()
        (temp_download_dir / "tasks_20251114-20251114.csv").touch()
        # 2025-11-11と2025-11-13が欠けている

        # fill_date_rangeとエクスポート処理をモック化
        with patch.object(exporter, "_export_date_range") as mock_export:
            mock_export.side_effect = [
                str(temp_download_dir / "tasks_20251111-20251111.csv"),
                str(temp_download_dir / "tasks_20251113-20251113.csv"),
            ]

            result = exporter.export_data(mock_page, start_date, end_date)

            assert result is not None
            # 2つの範囲が個別にエクスポートされることを確認
            assert mock_export.call_count == 2
            mock_export.assert_any_call(mock_page, date(2025, 11, 11), date(2025, 11, 11))
            mock_export.assert_any_call(mock_page, date(2025, 11, 13), date(2025, 11, 13))
