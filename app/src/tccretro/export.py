"""Playwrightを使用したTaskChute Cloudエクスポート自動化."""

from datetime import date, timedelta
from pathlib import Path

from playwright.sync_api import Download, Page


class TaskChuteExporter:
    """TaskChute Cloudからのデータエクスポートを処理します。"""

    def __init__(self, download_dir: str = "/tmp", debug: bool = False):
        """エクスポーターを初期化します。

        Args:
            download_dir: ダウンロードしたファイルを保存するディレクトリ
            debug: デバッグモードを有効化 (スクリーンショットと詳細ログ)
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.debug = debug

    def fill_date_range(self, page: Page, start_date: date, end_date: date) -> bool:
        """日付範囲ピッカーに開始日と終了日を入力します。

        Args:
            page: Playwright Pageオブジェクト
            start_date: 開始日
            end_date: 終了日

        Returns:
            成功した場合True、失敗した場合False
        """
        try:
            # 開始日を入力
            print(f"開始日を入力中: {start_date}")

            # 日付範囲入力フィールドを検索 (YYYY/MM/DD - YYYY/MM/DD 形式)
            date_input = page.locator('input[placeholder*="YYYY"]').first
            if date_input.count() > 0:
                print("YYYY プレースホルダーを持つ日付入力フィールドを発見")
                # フォーマット: YYYY/MM/DD - YYYY/MM/DD
                date_range_str = (
                    f"{start_date.strftime('%Y/%m/%d')} - {end_date.strftime('%Y/%m/%d')}"
                )
                print(f"日付範囲を入力中: {date_range_str}")
                date_input.click()
                page.wait_for_timeout(500)
                date_input.fill(date_range_str)
                page.wait_for_timeout(500)
                # Enterキーで確定
                date_input.press("Enter")
                page.wait_for_timeout(1000)
                print("日付範囲を正常に入力しました (単一入力方式)")
                return True

            # フォールバック: 個別フィールドでの元の方式を試行
            print("個別の日付フィールドでの元の方式を試行中...")

            # 年 (開始)
            year_field = page.locator('[aria-label="年"][data-range-position="start"]').first
            if year_field.count() == 0:
                print("data-range-position 属性を持つ年フィールドが見つかりませんでした")
                return False

            year_field.click()
            page.wait_for_timeout(200)
            year_field.fill(str(start_date.year))
            page.wait_for_timeout(200)

            # 月 (開始)
            month_field = page.locator('[aria-label="月"][data-range-position="start"]').first
            month_field.click()
            page.wait_for_timeout(200)
            month_field.fill(str(start_date.month))
            page.wait_for_timeout(200)

            # 日 (開始)
            day_field = page.locator('[aria-label="日"][data-range-position="start"]').first
            day_field.click()
            page.wait_for_timeout(200)
            day_field.fill(str(start_date.day))
            page.wait_for_timeout(200)

            # 終了日を入力
            print(f"終了日を入力中: {end_date}")

            # 年 (終了)
            year_field = page.locator('[aria-label="年"][data-range-position="end"]').first
            year_field.click()
            page.wait_for_timeout(200)
            year_field.fill(str(end_date.year))
            page.wait_for_timeout(200)

            # 月 (終了)
            month_field = page.locator('[aria-label="月"][data-range-position="end"]').first
            month_field.click()
            page.wait_for_timeout(200)
            month_field.fill(str(end_date.month))
            page.wait_for_timeout(200)

            # 日 (終了)
            day_field = page.locator('[aria-label="日"][data-range-position="end"]').first
            day_field.click()
            page.wait_for_timeout(200)
            day_field.fill(str(end_date.day))
            page.wait_for_timeout(500)  # 日付ピッカーが安定するまで待機

            print("日付範囲を正常に入力しました (個別フィールド方式)")
            return True

        except Exception as e:
            print(f"日付範囲の入力に失敗しました: {e}")
            import traceback

            traceback.print_exc()
            return False

    def _get_expected_filename(self, target_date: date) -> Path:
        """指定された日付に対応する期待されるファイル名を生成します。

        Args:
            target_date: 対象日付

        Returns:
            期待されるファイルパス
        """
        date_str = target_date.strftime("%Y%m%d")
        filename = f"tasks_{date_str}-{date_str}.csv"
        return self.download_dir / filename

    def _check_existing_files(
        self, start_date: date, end_date: date
    ) -> tuple[list[date], list[date]]:
        """日付範囲内の既存ファイルをチェックします。

        Args:
            start_date: 開始日
            end_date: 終了日

        Returns:
            (存在する日付のリスト, 欠けている日付のリスト)のタプル
        """
        existing_dates = []
        missing_dates = []

        current_date = start_date
        while current_date <= end_date:
            expected_file = self._get_expected_filename(current_date)
            if expected_file.exists():
                existing_dates.append(current_date)
            else:
                missing_dates.append(current_date)
            current_date += timedelta(days=1)

        return existing_dates, missing_dates

    def _group_consecutive_dates(self, dates: list[date]) -> list[tuple[date, date]]:
        """日付リストを連続する範囲にグループ化します。

        Args:
            dates: 日付のリスト（ソート済みである必要があります）

        Returns:
            連続する日付範囲のリスト [(start_date, end_date), ...]
        """
        if not dates:
            return []

        dates_sorted = sorted(dates)
        ranges = []
        range_start = dates_sorted[0]
        range_end = dates_sorted[0]

        for i in range(1, len(dates_sorted)):
            if dates_sorted[i] == range_end + timedelta(days=1):
                # 連続している
                range_end = dates_sorted[i]
            else:
                # 連続が途切れた
                ranges.append((range_start, range_end))
                range_start = dates_sorted[i]
                range_end = dates_sorted[i]

        # 最後の範囲を追加
        ranges.append((range_start, range_end))

        return ranges

    def _export_date_range(
        self, page: Page, start_date: date, end_date: date
    ) -> str | None:
        """指定された日付範囲のデータをエクスポートします（内部実装）。

        Args:
            page: Playwright Pageオブジェクト
            start_date: エクスポートの開始日
            end_date: エクスポートの終了日

        Returns:
            ダウンロードしたファイルのパス、またはエクスポート失敗時はNone
        """
        # エクスポートページへ移動
        export_url = "https://taskchute.cloud/export/csv-export"
        print(f"{export_url} へ移動中")
        page.goto(export_url, timeout=30000)

        # ページが安定した状態になるまで待機
        print("ページの読み込みを待機中...")
        page.wait_for_load_state("load", timeout=30000)

        # 日付入力フィールドが表示されるまで待機 (Reactアプリのレンダリング完了を確認)
        print("日付入力フィールドの表示を待機中...")
        try:
            page.wait_for_selector('input[placeholder*="YYYY"]', timeout=10000, state="visible")
        except Exception:
            # フォールバック: 個別フィールドを待機
            page.wait_for_selector('[aria-label="年"]', timeout=10000, state="visible")

        # ページ読み込み後のスクリーンショットを撮影 (デバッグモードのみ)
        if self.debug:
            screenshot_path = self.download_dir / "debug_page_loaded.png"
            page.screenshot(path=str(screenshot_path))
            print(f"スクリーンショット保存: {screenshot_path}")

        # 日付範囲を入力
        if not self.fill_date_range(page, start_date, end_date):
            print("日付範囲の入力に失敗しました")
            if self.debug:
                screenshot_path = self.download_dir / "debug_fill_date_failed.png"
                page.screenshot(path=str(screenshot_path))
                print(f"エラースクリーンショット保存: {screenshot_path}")
            return None

        # 日付入力後のスクリーンショットを撮影 (デバッグモードのみ)
        if self.debug:
            screenshot_path = self.download_dir / "debug_dates_filled.png"
            page.screenshot(path=str(screenshot_path))
            print(f"スクリーンショット保存: {screenshot_path}")

        # ダウンロードボタンを検索
        download_button = page.locator('button:has-text("ダウンロード")')
        button_count = download_button.count()
        print(f"ダウンロードボタンを {button_count} 個発見")

        if button_count == 0:
            print("ダウンロードボタンが見つかりませんでした")
            if self.debug:
                screenshot_path = self.download_dir / "debug_no_download_button.png"
                page.screenshot(path=str(screenshot_path))
                print(f"エラースクリーンショット保存: {screenshot_path}")
            return None

        # ダウンロードハンドラを設定してボタンをクリック
        download_path = None

        with page.expect_download(timeout=30000) as download_info:
            print("ダウンロードボタンをクリック中...")
            download_button.click()

        # ダウンロードオブジェクトを取得
        download: Download = download_info.value

        # ファイルを保存
        filename = download.suggested_filename
        download_path = self.download_dir / filename
        download.save_as(download_path)

        print(f"ファイルのダウンロードに成功: {download_path}")
        return str(download_path)

    def export_data(
        self, page: Page, start_date: date | None = None, end_date: date | None = None
    ) -> str | None:
        """TaskChute Cloudからデータをエクスポートします。

        この関数はエクスポートページに移動し、日付範囲を入力し、CSVをダウンロードします。
        既存ファイルが存在する場合はスキップし、欠けている日付のみをエクスポートします。

        Args:
            page: Playwright Pageオブジェクト (ログイン済みである必要があります)
            start_date: エクスポートの開始日 (デフォルト: 昨日)
            end_date: エクスポートの終了日 (デフォルト: 昨日)

        Returns:
            ダウンロードしたファイルのパス、またはエクスポート失敗時はNone
        """
        try:
            # 指定されていない場合はデフォルト日付を計算
            from datetime import date as date_class

            if start_date is None:
                start_date = date_class.today() - timedelta(days=1)
            if end_date is None:
                end_date = date_class.today() - timedelta(days=1)

            # 既存ファイルをチェック
            existing_dates, missing_dates = self._check_existing_files(start_date, end_date)

            # 全ての日付のファイルが存在する場合
            if not missing_dates:
                if existing_dates:
                    first_existing_file = self._get_expected_filename(existing_dates[0])
                    print(
                        f"全ての日付のファイルが既に存在します ({start_date} 〜 {end_date})。"
                        f"スキップします: {first_existing_file}"
                    )
                    return str(first_existing_file)
                else:
                    # 日付範囲が空の場合（通常は発生しない）
                    print("日付範囲が空です")
                    return None

            # 一部または全ての日付のファイルが欠けている場合
            if existing_dates:
                print(
                    f"既存ファイルが見つかりました ({len(existing_dates)} 日分)。"
                    f"欠けている日付のみをエクスポートします ({len(missing_dates)} 日分)"
                )

            # 欠けている日付を連続する範囲にグループ化
            missing_ranges = self._group_consecutive_dates(missing_dates)

            # 各範囲に対してエクスポート処理を実行
            exported_files = []
            for range_start, range_end in missing_ranges:
                if range_start == range_end:
                    print(f"エクスポート中: {range_start}")
                else:
                    print(f"エクスポート中: {range_start} 〜 {range_end}")

                exported_file = self._export_date_range(page, range_start, range_end)
                if exported_file:
                    exported_files.append(exported_file)
                else:
                    print(f"エクスポート失敗: {range_start} 〜 {range_end}")
                    # エラー時のスクリーンショットを撮影 (デバッグモードのみ)
                    if self.debug:
                        try:
                            screenshot_path = self.download_dir / "debug_error.png"
                            page.screenshot(path=str(screenshot_path))
                            print(f"エラースクリーンショット保存: {screenshot_path}")
                        except Exception as screenshot_error:
                            print(f"エラースクリーンショットの撮影に失敗: {screenshot_error}")
                    # 一部のエクスポートが失敗した場合でも、成功したファイルがあれば返す
                    if not exported_files:
                        return None

            # 最初にエクスポートしたファイルのパスを返す
            if exported_files:
                return exported_files[0]
            else:
                return None

        except Exception as e:
            print(f"エクスポートがエラーで失敗しました: {e}")
            # エラー時のスクリーンショットを撮影 (デバッグモードのみ)
            if self.debug:
                try:
                    screenshot_path = self.download_dir / "debug_error.png"
                    page.screenshot(path=str(screenshot_path))
                    print(f"エラースクリーンショット保存: {screenshot_path}")
                except Exception as screenshot_error:
                    print(f"エラースクリーンショットの撮影に失敗: {screenshot_error}")
            return None

    def wait_for_export_button(self, page: Page, timeout: int = 10000) -> bool:
        """エクスポートボタンが利用可能になるまで待機します。

        Args:
            page: Playwright Pageオブジェクト
            timeout: 最大待機時間 (ミリ秒)

        Returns:
            ボタンが見つかった場合True、見つからない場合False
        """
        export_button_selectors = [
            'button:has-text("エクスポート")',
            'button:has-text("Export")',
            'a:has-text("エクスポート")',
            'a:has-text("Export")',
        ]

        for selector in export_button_selectors:
            try:
                page.wait_for_selector(selector, timeout=timeout)
                return True
            except Exception:
                continue

        return False
