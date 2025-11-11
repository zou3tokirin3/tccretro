"""login.pyモジュールのテスト."""

from unittest.mock import Mock

import pytest

from tccretro.login import TaskChuteLogin, create_login_from_env


class TestTaskChuteLogin:
    """TaskChuteLoginクラスのテストスイート."""

    def test_init(self):
        """__init__: 初期化時に認証情報が正しく設定されることを確認."""
        email = "test@example.com"
        password = "test_password"

        login = TaskChuteLogin(email, password)

        assert login.google_email == email
        assert login.google_password == password
        assert login.base_url == "https://taskchute.cloud"

    def test_login_success_already_logged_in(self, mock_page: Mock):
        """login: すでにログイン済みの場合、Trueを返す."""
        login = TaskChuteLogin("test@example.com", "test_password")

        # ログイン済みURLをモック
        mock_page.url = "https://taskchute.cloud/taskchute"

        result = login.login(mock_page)

        assert result is True
        mock_page.goto.assert_called_once_with("https://taskchute.cloud/taskchute")
        mock_page.wait_for_load_state.assert_called_once_with("domcontentloaded")

    def test_login_failure_not_logged_in(self, mock_page: Mock):
        """login: ログインが必要な場合、Falseを返す."""
        login = TaskChuteLogin("test@example.com", "test_password")

        # ログインページのURLをモック
        mock_page.url = "https://taskchute.cloud/auth/login"
        # ログインボタンが見つかる場合（未ログイン）
        mock_page.wait_for_selector.return_value = True

        result = login.login(mock_page)

        assert result is False

    def test_login_wait_for_manual_login_timeout(self, mock_page: Mock, monkeypatch):
        """login: wait_for_manual_login=Trueでタイムアウトする場合、Falseを返す."""
        import time

        login = TaskChuteLogin("test@example.com", "test_password")

        # ログインページのURLをモック（未ログイン状態）
        mock_page.url = "https://taskchute.cloud/auth/login"
        mock_page.title.return_value = "TaskChute Cloud - Login"
        # ログインボタンが見つかる場合（未ログイン）
        mock_page.wait_for_selector.return_value = True

        # 時間をモックしてタイムアウトをシミュレート
        start_time = 1000.0
        call_count = 0

        def mock_time():
            nonlocal call_count
            call_count += 1
            # 最初の呼び出しでstart_timeを返し、その後2秒ごとに時間を進める
            if call_count == 1:
                return start_time
            # 2回目以降は2秒ずつ進む（call_count-1で調整）
            return start_time + ((call_count - 1) * 2)

        monkeypatch.setattr(time, "time", mock_time)

        # 短いタイムアウトでテスト（3秒、ループが実行されるように）
        result = login.login(mock_page, wait_for_manual_login=True, manual_timeout_sec=3)

        assert result is False
        # wait_for_timeoutが呼ばれていることを確認（少なくとも1回は呼ばれる）
        assert mock_page.wait_for_timeout.call_count > 0

    def test_login_wait_for_manual_login_success(self, mock_page: Mock, monkeypatch):
        """login: wait_for_manual_login=Trueでログイン成功する場合、Trueを返す."""
        import time

        login = TaskChuteLogin("test@example.com", "test_password")

        # 最初は未ログイン、その後ログイン済みになる
        call_count = 0

        def mock_is_logged_in(page):
            nonlocal call_count
            call_count += 1
            # 2回目の呼び出しでログイン済みになる
            if call_count == 1:
                return False
            return True

        monkeypatch.setattr(login, "_is_logged_in", mock_is_logged_in)

        # ログインページのURLをモック
        mock_page.url = "https://taskchute.cloud/auth/login"
        mock_page.title.return_value = "TaskChute Cloud - Login"

        # 時間をモック
        start_time = 1000.0
        time_call_count = 0

        def mock_time():
            nonlocal time_call_count
            time_call_count += 1
            return start_time + (time_call_count * 2)

        monkeypatch.setattr(time, "time", mock_time)

        result = login.login(mock_page, wait_for_manual_login=True, manual_timeout_sec=300)

        assert result is True
        # wait_for_timeoutが呼ばれていることを確認
        assert mock_page.wait_for_timeout.call_count > 0

    def test_login_backward_compatibility(self, mock_page: Mock):
        """login: 既存の呼び出し方法（引数なし）が後方互換性を保つことを確認."""
        login = TaskChuteLogin("test@example.com", "test_password")

        # ログイン済みURLをモック
        mock_page.url = "https://taskchute.cloud/taskchute"

        # 引数なしで呼び出し（既存のコード）
        result = login.login(mock_page)

        assert result is True

    def test_login_exception_handling(self, mock_page: Mock, capsys):
        """login: 例外が発生した場合、Falseを返しエラーメッセージを表示."""
        login = TaskChuteLogin("test@example.com", "test_password")

        # gotoで例外を発生させる
        mock_page.goto.side_effect = Exception("Network error")

        result = login.login(mock_page)

        assert result is False
        captured = capsys.readouterr()
        assert "エラー: Network error" in captured.out

    def test_is_logged_in_taskchute_url_without_auth(self, mock_page: Mock):
        """_is_logged_in: /taskchute URLで /auth/ がない場合、ログイン済みと判定."""
        login = TaskChuteLogin("test@example.com", "test_password")
        mock_page.url = "https://taskchute.cloud/taskchute"

        result = login._is_logged_in(mock_page)

        assert result is True

    def test_is_logged_in_auth_url(self, mock_page: Mock):
        """_is_logged_in: /auth/ を含むURLの場合、ログインボタンの有無で判定."""
        login = TaskChuteLogin("test@example.com", "test_password")
        mock_page.url = "https://taskchute.cloud/auth/login"

        # ログインボタンが見つかる場合（未ログイン）
        mock_page.wait_for_selector.return_value = True

        result = login._is_logged_in(mock_page)

        assert result is False
        mock_page.wait_for_selector.assert_called_once()

    def test_is_logged_in_no_login_button(self, mock_page: Mock):
        """_is_logged_in: ログインボタンが見つからない場合でも、/taskchuteでなければ未ログインと判定（保守的）."""
        login = TaskChuteLogin("test@example.com", "test_password")
        mock_page.url = "https://taskchute.cloud/some-page"

        # ログインボタンが見つからない（タイムアウト）
        mock_page.wait_for_selector.side_effect = Exception("Timeout")

        result = login._is_logged_in(mock_page)

        # 保守的な判定: /taskchuteでない場合はFalseを返す
        assert result is False

    def test_is_logged_in_no_login_button_but_taskchute_url(self, mock_page: Mock):
        """_is_logged_in: ログインボタンが見つからないが/taskchute URLの場合、ログイン済みと判定."""
        login = TaskChuteLogin("test@example.com", "test_password")
        mock_page.url = "https://taskchute.cloud/taskchute"

        # ログインボタンが見つからない（タイムアウト）
        mock_page.wait_for_selector.side_effect = Exception("Timeout")

        result = login._is_logged_in(mock_page)

        # /taskchute URLでログインボタンがない場合、ログイン済みと判定
        assert result is True

    def test_login_wait_for_manual_login_skips_initial_check(self, mock_page: Mock, monkeypatch):
        """login: wait_for_manual_login=Trueの場合、初回_is_logged_in()チェックをスキップして待機に入る."""
        import time

        login = TaskChuteLogin("test@example.com", "test_password")

        # _is_logged_in()が呼ばれた回数を追跡
        is_logged_in_call_count = 0

        def mock_is_logged_in(page):
            nonlocal is_logged_in_call_count
            is_logged_in_call_count += 1
            # 待機ループ内での呼び出しではFalseを返す（ログイン待ち）
            return False

        monkeypatch.setattr(login, "_is_logged_in", mock_is_logged_in)

        # ログインページのURLをモック
        mock_page.url = "https://taskchute.cloud/taskchute"
        mock_page.title.return_value = "TaskChute Cloud"

        # 時間をモックして短いタイムアウトでテスト
        start_time = 1000.0
        time_call_count = 0

        def mock_time():
            nonlocal time_call_count
            time_call_count += 1
            # 最初の呼び出しでstart_timeを返し、その後2秒ごとに時間を進める
            if time_call_count == 1:
                return start_time
            return start_time + ((time_call_count - 1) * 2)

        monkeypatch.setattr(time, "time", mock_time)

        # 短いタイムアウトでテスト（3秒、ループが実行されるように）
        result = login.login(mock_page, wait_for_manual_login=True, manual_timeout_sec=3)

        # タイムアウトでFalseを返す
        assert result is False
        # 初回チェックをスキップしているため、_is_logged_in()は待機ループ内でのみ呼ばれる
        # 待機ループは2秒ごとに実行されるため、3秒のタイムアウトでは少なくとも1回は呼ばれる
        assert is_logged_in_call_count > 0
        # wait_for_timeoutが呼ばれていることを確認
        assert mock_page.wait_for_timeout.call_count > 0


class TestCreateLoginFromEnv:
    """create_login_from_env関数のテストスイート."""

    def test_create_from_new_env_vars(self, mock_env: dict[str, str]):
        """create_login_from_env: 新しい環境変数から正しく作成."""
        login = create_login_from_env()

        assert login.google_email == "test@example.com"
        assert login.google_password == "test_password"

    def test_create_from_legacy_env_vars(self, monkeypatch: pytest.MonkeyPatch):
        """create_login_from_env: 古い環境変数からフォールバック."""
        monkeypatch.setenv("TASKCHUTE_USERNAME", "legacy@example.com")
        monkeypatch.setenv("TASKCHUTE_PASSWORD", "legacy_password")

        login = create_login_from_env()

        assert login.google_email == "legacy@example.com"
        assert login.google_password == "legacy_password"

    def test_create_with_new_overrides_legacy(self, monkeypatch: pytest.MonkeyPatch):
        """create_login_from_env: 新しい環境変数が古い環境変数より優先される."""
        monkeypatch.setenv("TASKCHUTE_GOOGLE_EMAIL", "new@example.com")
        monkeypatch.setenv("TASKCHUTE_GOOGLE_PASSWORD", "new_password")
        monkeypatch.setenv("TASKCHUTE_USERNAME", "legacy@example.com")
        monkeypatch.setenv("TASKCHUTE_PASSWORD", "legacy_password")

        login = create_login_from_env()

        assert login.google_email == "new@example.com"
        assert login.google_password == "new_password"

    def test_create_with_no_env_vars(self, monkeypatch: pytest.MonkeyPatch):
        """create_login_from_env: 環境変数がない場合、デフォルト値を使用."""
        # すべての関連環境変数を削除
        for key in [
            "TASKCHUTE_GOOGLE_EMAIL",
            "TASKCHUTE_GOOGLE_PASSWORD",
            "TASKCHUTE_USERNAME",
            "TASKCHUTE_PASSWORD",
        ]:
            monkeypatch.delenv(key, raising=False)

        login = create_login_from_env()

        assert login.google_email == "manual-login"
        assert login.google_password == "manual-login"

    def test_create_with_partial_env_vars(self, monkeypatch: pytest.MonkeyPatch):
        """create_login_from_env: 部分的な環境変数の場合、デフォルト値で補完."""
        monkeypatch.setenv("TASKCHUTE_GOOGLE_EMAIL", "partial@example.com")
        monkeypatch.delenv("TASKCHUTE_GOOGLE_PASSWORD", raising=False)
        monkeypatch.delenv("TASKCHUTE_USERNAME", raising=False)
        monkeypatch.delenv("TASKCHUTE_PASSWORD", raising=False)

        login = create_login_from_env()

        assert login.google_email == "partial@example.com"
        assert login.google_password == "manual-login"
