"""cli.pyモジュールのテスト."""

from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from tccretro.cli import main


class TestCLI:
    """CLIのテストスイート."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Click CLIRunnerを作成."""
        return CliRunner()

    @contextmanager
    def _mock_cli_dependencies(self, runner: CliRunner | None = None):
        """CLIの依存関係をモック化するヘルパー."""
        # 分離されたファイルシステムを使用する場合
        if runner:
            with runner.isolated_filesystem():
                # 空の.envファイルを作成
                Path(".env").touch()
                yield from self._do_mock_cli_dependencies()
        else:
            yield from self._do_mock_cli_dependencies()

    def _do_mock_cli_dependencies(self):
        """実際のモック化処理."""
        with (
            patch("tccretro.cli.load_dotenv"),
            patch("tccretro.cli.sync_playwright") as mock_playwright,
            patch("tccretro.cli.create_login_from_env") as mock_create_login,
            patch("tccretro.cli.TaskChuteExporter") as mock_exporter_class,
        ):
            # Playwrightのモック
            mock_pw = MagicMock()
            mock_context = MagicMock()
            mock_page = MagicMock()
            mock_playwright.return_value.__enter__.return_value = mock_pw
            mock_pw.chromium.launch_persistent_context.return_value = mock_context
            mock_context.new_page.return_value = mock_page

            # ログインのモック
            mock_login = MagicMock()
            mock_create_login.return_value = mock_login

            # エクスポーターのモック
            mock_exporter = MagicMock()
            mock_exporter_class.return_value = mock_exporter

            yield {
                "playwright": mock_playwright,
                "pw": mock_pw,
                "context": mock_context,
                "page": mock_page,
                "login": mock_login,
                "exporter_class": mock_exporter_class,
                "exporter": mock_exporter,
            }

    def test_help_option(self, runner: CliRunner):
        """--helpオプションが正しく動作することを確認."""
        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "TaskChute Cloud エクスポート自動化ツール" in result.output
        # --login-timeoutオプションがヘルプに表示されることを確認
        assert "--login-timeout" in result.output

    def test_default_export_date_is_yesterday(self, runner: CliRunner):
        """デフォルトのエクスポート日付が昨日であることを確認."""
        with self._mock_cli_dependencies(runner) as mocks:
            mocks["login"].login.return_value = True
            mocks["exporter"].export_data.return_value = "/tmp/export.csv"

            result = runner.invoke(main, [])

            # 昨日の日付を計算
            yesterday = date.today() - timedelta(days=1)

            # export_dataが昨日の日付で呼ばれたことを確認
            assert result.exit_code == 0
            mocks["exporter"].export_data.assert_called_once_with(
                mocks["page"], start_date=yesterday, end_date=yesterday
            )

    def test_export_date_option(self, runner: CliRunner):
        """--export-dateオプションが正しく動作することを確認."""
        with self._mock_cli_dependencies(runner) as mocks:
            mocks["login"].login.return_value = True
            mocks["exporter"].export_data.return_value = "/tmp/export.csv"

            result = runner.invoke(main, ["--export-date", "2025-01-15"])

            assert result.exit_code == 0
            # export_dataが指定日付で呼ばれたことを確認
            mocks["exporter"].export_data.assert_called_once_with(
                mocks["page"], start_date=date(2025, 1, 15), end_date=date(2025, 1, 15)
            )

    def test_export_date_range_options(self, runner: CliRunner):
        """--export-start-dateと--export-end-dateオプションが正しく動作することを確認."""
        with self._mock_cli_dependencies(runner) as mocks:
            mocks["login"].login.return_value = True
            mocks["exporter"].export_data.return_value = "/tmp/export.csv"

            result = runner.invoke(
                main, ["--export-start-date", "2025-01-01", "--export-end-date", "2025-01-31"]
            )

            assert result.exit_code == 0
            # export_dataが指定範囲で呼ばれたことを確認
            mocks["exporter"].export_data.assert_called_once_with(
                mocks["page"], start_date=date(2025, 1, 1), end_date=date(2025, 1, 31)
            )

    def test_partial_date_range_error(self, runner: CliRunner):
        """開始日または終了日のみが指定された場合、エラーを返す."""
        with runner.isolated_filesystem():
            # 空の.envファイルを作成
            Path(".env").touch()

            with patch("tccretro.cli.load_dotenv"):
                result = runner.invoke(main, ["--export-start-date", "2025-01-01"])

                assert result.exit_code == 1
                assert "両方指定する必要があります" in result.output

    def test_login_only_option(self, runner: CliRunner):
        """--login-onlyオプションが正しく動作することを確認."""
        with self._mock_cli_dependencies(runner) as mocks:
            mocks["login"].login.return_value = True

            result = runner.invoke(main, ["--login-only"])

            assert result.exit_code == 0
            assert "ログインテスト完了" in result.output
            # wait_for_manual_login=Trueで呼ばれることを確認
            mocks["login"].login.assert_called_once_with(
                mocks["page"], wait_for_manual_login=True, manual_timeout_sec=300
            )
            # export_dataが呼ばれないことを確認
            mocks["exporter"].export_data.assert_not_called()

    def test_login_only_with_timeout_option(self, runner: CliRunner):
        """--login-only --login-timeoutオプションが正しく動作することを確認."""
        with self._mock_cli_dependencies(runner) as mocks:
            mocks["login"].login.return_value = True

            result = runner.invoke(main, ["--login-only", "--login-timeout", "600"])

            assert result.exit_code == 0
            # manual_timeout_sec=600で呼ばれることを確認
            mocks["login"].login.assert_called_once_with(
                mocks["page"], wait_for_manual_login=True, manual_timeout_sec=600
            )

    def test_login_only_headless_warning(self, runner: CliRunner):
        """--login-onlyをheadlessモードで実行した場合、警告が表示されることを確認."""
        with self._mock_cli_dependencies(runner) as mocks:
            mocks["login"].login.return_value = False

            result = runner.invoke(main, ["--login-only"])

            assert result.exit_code == 1
            assert "警告" in result.output or "[警告]" in result.output
            assert "headless" in result.output.lower() or "headless" in result.output
            assert "--debug" in result.output

    def test_login_only_with_debug_no_warning(self, runner: CliRunner):
        """--login-only --debugの場合、警告が表示されないことを確認."""
        with self._mock_cli_dependencies(runner) as mocks:
            mocks["login"].login.return_value = True

            result = runner.invoke(main, ["--login-only", "--debug"])

            assert result.exit_code == 0
            # 警告メッセージが含まれないことを確認
            assert "警告" not in result.output and "[警告]" not in result.output

    def test_login_only_failure_exits_with_code_1(self, runner: CliRunner):
        """--login-onlyでログイン失敗時、終了コード1で終了することを確認."""
        with self._mock_cli_dependencies(runner) as mocks:
            mocks["login"].login.return_value = False

            result = runner.invoke(main, ["--login-only"])

            assert result.exit_code == 1
            assert "ログインが検出されませんでした" in result.output

    def test_login_only_and_export_only_conflict(self, runner: CliRunner):
        """--login-onlyと--export-onlyが同時に指定された場合、エラーを返す."""
        with runner.isolated_filesystem():
            Path(".env").touch()
            with patch("tccretro.cli.load_dotenv"):
                result = runner.invoke(main, ["--login-only", "--export-only"])

                assert result.exit_code == 1
                assert "同時に指定できません" in result.output

    def test_login_failure_exits(self, runner: CliRunner):
        """ログイン失敗時にプログラムが終了することを確認."""
        with self._mock_cli_dependencies(runner) as mocks:
            mocks["login"].login.return_value = False

            result = runner.invoke(main, [])

            assert result.exit_code == 1
            assert "ログイン失敗" in result.output

    def test_export_failure_exits(self, runner: CliRunner):
        """エクスポート失敗時にプログラムが終了することを確認."""
        with self._mock_cli_dependencies(runner) as mocks:
            mocks["login"].login.return_value = True
            mocks["exporter"].export_data.return_value = None

            result = runner.invoke(main, [])

            assert result.exit_code == 1
            assert "エクスポート失敗" in result.output

    def test_debug_mode_option(self, runner: CliRunner):
        """--debugオプションがheadlessモードを無効化することを確認."""
        with self._mock_cli_dependencies(runner) as mocks:
            mocks["login"].login.return_value = True
            mocks["exporter"].export_data.return_value = "/tmp/export.csv"

            result = runner.invoke(main, ["--debug"])

            # headless=Falseで呼ばれることを確認
            assert result.exit_code == 0
            call_kwargs = mocks["pw"].chromium.launch_persistent_context.call_args.kwargs
            assert call_kwargs["headless"] is False

    def test_output_dir_option(self, runner: CliRunner, tmp_path: Path):
        """--output-dirオプションが正しく動作することを確認."""
        with self._mock_cli_dependencies(runner) as mocks:
            mocks["login"].login.return_value = True
            mocks["exporter"].export_data.return_value = "/tmp/export.csv"

            output_dir = tmp_path / "custom_output"
            result = runner.invoke(main, ["--output-dir", str(output_dir)])

            assert result.exit_code == 0
            # TaskChuteExporterが指定ディレクトリで初期化されることを確認
            mocks["exporter_class"].assert_called_once()
            call_kwargs = mocks["exporter_class"].call_args.kwargs
            assert call_kwargs["download_dir"] == str(output_dir)

    def test_keyboard_interrupt_handling(self, runner: CliRunner):
        """KeyboardInterruptが正しく処理されることを確認."""
        with self._mock_cli_dependencies(runner) as mocks:
            # ログインでKeyboardInterruptを発生させる
            mocks["login"].login.side_effect = KeyboardInterrupt()

            result = runner.invoke(main, [])

            assert result.exit_code == 130
            assert "中断されました" in result.output

    def test_exception_handling(self, runner: CliRunner):
        """一般的な例外が正しく処理されることを確認."""
        with runner.isolated_filesystem():
            Path(".env").touch()
            with (
                patch("tccretro.cli.load_dotenv"),
                patch("tccretro.cli.sync_playwright") as mock_playwright,
            ):
                # Playwrightで例外を発生させる
                mock_playwright.side_effect = Exception("Unexpected error")

                result = runner.invoke(main, [])

                assert result.exit_code == 1
                assert "エラー: Unexpected error" in result.output

    def test_slow_mo_option(self, runner: CliRunner):
        """--slow-moオプションが正しく動作することを確認."""
        with self._mock_cli_dependencies(runner) as mocks:
            mocks["login"].login.return_value = True
            mocks["exporter"].export_data.return_value = "/tmp/export.csv"

            result = runner.invoke(main, ["--slow-mo", "1000"])

            # slow_mo=1000で呼ばれることを確認
            assert result.exit_code == 0
            call_kwargs = mocks["pw"].chromium.launch_persistent_context.call_args.kwargs
            assert call_kwargs["slow_mo"] == 1000
