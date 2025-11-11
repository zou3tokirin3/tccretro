"""TaskChute Cloud ログインチェッカー (永続的プロファイル用)."""

import os
import time

from playwright.sync_api import Page


class TaskChuteLogin:
    """永続的プロファイルを使用した場合のTaskChute Cloudへのログイン状態をチェックします。"""

    def __init__(self, google_email: str, google_password: str):
        """Google認証情報で初期化 (後方互換性のため保持)。

        Args:
            google_email: Googleアカウントのメールアドレス (永続的プロファイルでは未使用)
            google_password: Googleアカウントのパスワード (永続的プロファイルでは未使用)
        """
        self.google_email = google_email
        self.google_password = google_password
        self.base_url = "https://taskchute.cloud"

    def login(
        self, page: Page, wait_for_manual_login: bool = False, manual_timeout_sec: int | None = None
    ) -> bool:
        """TaskChute Cloudへのログイン状態をチェックします。

        永続的Chromeプロファイルを使用する場合:
        - 初回: ユーザーがブラウザから手動でログインし、セッションが保存される
        - 2回目以降: 自動的にログイン済み状態になる

        Args:
            page: Playwright Pageオブジェクト
            wait_for_manual_login: Trueの場合、未ログイン時に手動ログインを待機
            manual_timeout_sec: 手動ログイン待機時間（秒）。Noneの場合は300秒（5分）

        Returns:
            ログインに成功した場合True、失敗した場合False
        """
        try:
            # TaskChute Cloudへ移動
            print("TaskChute Cloud にアクセス中...")
            page.goto(f"{self.base_url}/taskchute")
            page.wait_for_load_state("domcontentloaded")

            # ログイン状態を確認
            if self._is_logged_in(page):
                print("✓ ログイン済みです")
                return True
            else:
                print("\n✗ ログインが必要です")

                if wait_for_manual_login:
                    # ヘッドレスモードかどうかを確認
                    # PlaywrightのPageオブジェクトから直接確認できないため、
                    # 警告メッセージを表示（実際のヘッドレス判定はCLI側で行う）
                    print("\nブラウザで手動でログインしてください:")
                    print("1. ブラウザでログインボタンをクリック")
                    print("2. Googleログイン、Appleログイン、E-mailログインのいずれかでログイン")
                    print("3. ログイン完了後、自動的に検出されます")
                    print(f"\n現在のURL: {page.url}")
                    print(f"ページタイトル: {page.title()}")
                    print("\nログイン完了を待機中...")

                    # 手動ログイン待機
                    timeout = manual_timeout_sec if manual_timeout_sec is not None else 300
                    start_time = time.time()

                    while time.time() - start_time < timeout:
                        # 2秒ごとにログイン状態をチェック
                        page.wait_for_timeout(2000)

                        # ログイン状態を再確認
                        if self._is_logged_in(page):
                            print("\n✓ ログイン完了を検出しました！")
                            return True

                        # 進捗表示（30秒ごと）
                        elapsed = int(time.time() - start_time)
                        if elapsed > 0 and elapsed % 30 == 0:
                            remaining = timeout - elapsed
                            print(f"待機中... (残り約{remaining}秒)")

                    print(f"\nタイムアウト: {timeout}秒以内にログインが検出されませんでした")
                    return False
                else:
                    print("初回実行時は --login-only --debug オプションを使用して")
                    print("ブラウザでTaskChute Cloudにログインしてください。")
                    print("（Googleログイン、Appleログイン、E-mailログインのいずれでもOK）")
                    print("\n次回以降は自動的にログイン済みの状態で起動します。")
                    return False

        except Exception as e:
            print(f"エラー: {e}")
            import traceback

            traceback.print_exc()
            return False

    def _is_logged_in(self, page: Page) -> bool:
        """TaskChute Cloudにログイン済みかどうかをチェックします。

        Args:
            page: Playwright Pageオブジェクト

        Returns:
            ログイン済みの場合True、未ログインの場合False
        """
        current_url = page.url

        # /taskchute にいて /auth/ にいない場合、ログイン済み
        if "/taskchute" in current_url and "/auth/" not in current_url:
            return True

        # ログインフォームが表示されているかもチェック (未ログインを示す)
        try:
            # ログインページが表示されるか短時間待機
            page.wait_for_selector('button:has-text("LOGIN WITH")', timeout=2000)
            return False  # ログインボタンが見つかった、未ログイン
        except Exception:
            # ログインボタンが見つからない、おそらくログイン済み
            return True


def create_login_from_env() -> TaskChuteLogin:
    """環境変数からTaskChuteLoginインスタンスを作成します。

    期待する環境変数:
        TASKCHUTE_GOOGLE_EMAIL: Googleアカウントのメールアドレス
        TASKCHUTE_GOOGLE_PASSWORD: Googleアカウントのパスワード

    後方互換性のため、以下も受け付けます:
        TASKCHUTE_USERNAME: TASKCHUTE_GOOGLE_EMAILのエイリアス
        TASKCHUTE_PASSWORD: TASKCHUTE_GOOGLE_PASSWORDのエイリアス

    注意: 永続的プロファイルを使用する場合、認証情報は参照用のみです。
          実際の認証はブラウザで手動で行われます。

    Returns:
        TaskChuteLoginインスタンス
    """
    # まず新しい環境変数名を試す
    google_email = os.environ.get("TASKCHUTE_GOOGLE_EMAIL")
    google_password = os.environ.get("TASKCHUTE_GOOGLE_PASSWORD")

    # 後方互換性のため古い名前にフォールバック
    if not google_email:
        google_email = os.environ.get("TASKCHUTE_USERNAME", "")
    if not google_password:
        google_password = os.environ.get("TASKCHUTE_PASSWORD", "")

    # 永続的プロファイルでは認証情報はオプション
    if not google_email:
        google_email = "manual-login"
    if not google_password:
        google_password = "manual-login"

    return TaskChuteLogin(google_email, google_password)
