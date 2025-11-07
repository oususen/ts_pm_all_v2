# app/ui/pages/csv_import_page.py
import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from services.csv_import_service import CSVImportService
from services.tiera_csv_import_service import TieraCSVImportService
from services.tiera_kakutei_csv_import_service import TieraKakuteiCSVImportService
from services.tiera_riden_csv_import_service import TieraRidenCSVImportService
from services.kubota_kakutei_csv_import_service import KubotaKakuteiCSVImportService
from services.transport_service import TransportService

class CSVImportPage:
    """CSV受注インポートページ"""

    def __init__(self, db_manager, auth_service=None):
        self.db_manager = db_manager
        self.service = TransportService(db_manager)
        self.auth_service = auth_service

        # 顧客別インポートサービスは動的に選択
        self.import_service = None

    def _can_edit_page(self) -> bool:
        """ページ編集権限チェック"""
        if not self.auth_service:
            return True
        user = st.session_state.get('user')
        if not user:
            return False
        return self.auth_service.can_edit_page(user['id'], "CSV受注取込")    
    def show(self):
        """ページ表示"""
        st.title("📥 受注CSVインポート")

        # 現在の顧客を取得
        customer = st.session_state.get('current_customer', 'kubota')
        customer_display = "クボタ様" if customer == "kubota" else "ティエラ様"

        # 顧客情報を表示
        st.info(f"📋 現在の顧客: **{customer_display}**")
        st.write("お客様からのCSVファイルを読み込み、生産指示データとして登録します。")

        # ティエラ様の場合は、内示CSVと確定CSVの2つのタブを表示
        if customer == 'tiera':
            tab_naiji, tab_kakutei, tab_riden, tab_history, tab_docs = st.tabs([
                "📋 内示CSVインポート",
                "✅ 確定CSVインポート",
                "📦 リーデン注文書",
                "📊 インポート履歴",
                "ℹ️ 使い方"
            ])

            with tab_naiji:
                self.import_service = TieraCSVImportService(self.db_manager)
                st.subheader("📋 内示CSV（B17形式）")
                st.caption("フォーマット: 列6=図番、列8=納期、列11=数量、CP932")
                self._show_upload_form(tab_prefix="naiji_")

            with tab_kakutei:
                self.import_service = TieraKakuteiCSVImportService(self.db_manager)
                st.subheader("✅ 確定CSV（Y55形式）")
                st.caption("フォーマット: 列11=図番、列13=納期、列16=数量、CP932")
                self._show_upload_form(tab_prefix="kakutei_")

            with tab_riden:
                self.import_service = TieraRidenCSVImportService(self.db_manager)
                st.subheader("📦 リーデン注文書（ティエラ・確定受注）")
                st.caption("フォーマット: 品目コード（列6）/ 納期（列10：YYYY/MM/DD）/ 発注数量（列11）、CP932／確定受注として登録します")
                self._show_upload_form(tab_prefix="riden_")

            with tab_history:
                self.import_service = TieraCSVImportService(self.db_manager)
                self._show_import_history()

            with tab_docs:
                self._show_instructions()

        else:
            csv_format = "V2/V3形式 (Shift-JIS)"
            st.caption(f"フォーマット: {csv_format}")

            tab1, tab2, tab3, tab4 = st.tabs([
                "📤 内示CSVアップロード",
                "📦 確定受注CSVアップロード",
                "📊 インポート履歴",
                "ℹ️ 使い方"
            ])

            with tab1:
                self.import_service = CSVImportService(self.db_manager)
                st.subheader("📤 内示CSV（V2/V3形式）")
                self._show_upload_form(tab_prefix="kubota_naiji_")

            with tab2:
                self.import_service = KubotaKakuteiCSVImportService(self.db_manager)
                st.subheader("📦 確定受注CSV（JVAN形式）")
                st.caption("フォーマット: CP932 / 必須列: 品番, 納期, 検区, 発注数, 発行日")
                self._show_upload_form(tab_prefix="kubota_kakutei_")

            with tab3:
                self.import_service = CSVImportService(self.db_manager)
                self._show_import_history()

            with tab4:
                self._show_instructions()
    
    def _show_upload_form(self, tab_prefix=""):
        """アップロードフォーム表示"""
        st.header("📤 CSVファイルアップロード")

        # 編集権限チェック
        can_edit = self._can_edit_page()
        if not can_edit:
            st.warning("⚠️ この画面の編集権限がありません。閲覧のみ可能です。")

        # 顧客に応じたフォーマット説明を表示
        customer = st.session_state.get('current_customer', 'kubota')

        if customer == 'kubota':
            if isinstance(self.import_service, KubotaKakuteiCSVImportService):
                st.info("""
                **📦 対応フォーマット（クボタ確定受注CSV／JVAN形式）:**
                - エンコーディング: CP932
                - 必須列: 品番、納期（MMDD）、検区、発注数、発行日
                - 納期は発行日を基準に西暦へ自動補完します

                **インポート仕様:**
                - 同一品番・納期・検区の数量は合算して登録
                - 既存の配送進捗も最新数量へ置き換えます
                """)
            else:
                st.info("""
                **📤 対応フォーマット（クボタ内示CSV／V2・V3形式）:**
                - エンコーディング: Shift-JIS
                - レコード識別: V2（内示）、V3（数量）
                - 必須カラム: データNo、品番、検査区分、スタート月度など

                **インポート仕様:**
                - 既存データに追加されます
                - 同じ製品コード×日付のデータは数量が合算されます
                - 検査区分が違っても製品コードが同じなら納入進度では統合されます
                """)
        elif customer == 'tiera':
            st.info("""
            **対応フォーマット（ティエラ様）:**
            - エンコーディング: CP932（共通）
            - 内示CSV: 列6=図番、列8=納期（YYYYMMDD）、列11=数量
            - 確定CSV: 列11=図番、列13=納期、列16=数量
            - リーデン注文書: 品目コード（列6）/ 納期（列10：YYYY/MM/DD）/ 発注数量（列11）※確定受注データ

            **インポート仕様:**
            - 図番×納期でグループ化して集計されます
            - 既存データに追加されます
            - 同じ図番×納期のデータは数量が更新されます
            - リーデン注文書は order_type=確定 として登録されます
            """)
        with st.expander("計画進度の再計算"):
            product_id = st.number_input("製品ID", min_value=1, step=1, key=f"{tab_prefix}recalc_product_id_upload")
            recal_start_date = st.date_input("再計算開始日", key=f"{tab_prefix}recalc_start_date_upload")
            recal_end_date = st.date_input("再計算終了日", key=f"{tab_prefix}recalc_end_date_upload")

            col_recalc_single, col_recalc_all = st.columns(2)

            with col_recalc_single:
                if st.button("選択製品のみ再計算", key=f"{tab_prefix}recalc_single_upload", disabled=not can_edit):
                    self.service.recompute_planned_progress(product_id, recal_start_date, recal_end_date)
                    st.success("再計算が完了しました")

            with col_recalc_all:
                if st.button("全製品を再計算", key=f"{tab_prefix}recalc_all_upload", disabled=not can_edit):
                    self.service.recompute_planned_progress_all(recal_start_date, recal_end_date)
                    st.success("全ての製品に対する再計算が完了しました")
        # ファイルアップロード
        uploaded_file = st.file_uploader(
            "CSVファイルを選択",
            type=['csv'],
            help="Shift-JIS形式のCSVファイルをアップロードしてください",
            key=f"{tab_prefix}csv_uploader"
        )
        
        if uploaded_file is not None:
            # プレビュー表示
            try:
                # 顧客に応じたエンコーディングで読み込み
                customer = st.session_state.get('current_customer', 'kubota')
                if isinstance(self.import_service, KubotaKakuteiCSVImportService):
                    encoding = 'cp932'
                elif customer == 'kubota':
                    encoding = 'shift_jis'
                else:
                    encoding = 'cp932'

                df_preview = pd.read_csv(uploaded_file, encoding=encoding, nrows=10)
                uploaded_file.seek(0)

                st.subheader("📋 プレビュー（先頭10行）")
                st.dataframe(df_preview, use_container_width=True, height=200)

                # フォーマット確認（顧客別）
                if customer == 'kubota' and isinstance(self.import_service, CSVImportService):
                    # 久保田様：レコード識別の確認
                    if 'レコード識別' in df_preview.columns:
                        v2_count = len(df_preview[df_preview['レコード識別'] == 'V2'])
                        v3_count = len(df_preview[df_preview['レコード識別'] == 'V3'])

                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("総行数", len(df_preview))
                        with col2:
                            st.metric("V2行（日付）", v2_count)
                        with col3:
                            st.metric("V3行（数量）", v3_count)
                    else:
                        st.warning("⚠️ レコード識別列が見つかりません")

                elif customer == 'tiera':
                    # ティエラ様：列数確認
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("総行数", len(df_preview))
                    with col2:
                        st.metric("列数", len(df_preview.columns))

                    # 重要列の確認
                    if len(df_preview.columns) >= 12:
                        st.success("✅ 必要な列が揃っています（図番、納期、数量）")
                    else:
                        st.warning(f"⚠️ 列数が不足しています（必要: 12列以上、実際: {len(df_preview.columns)}列）")
                
                st.markdown("---")
                
                # インポートオプション
                st.subheader("⚙️ インポートオプション")

                create_progress = st.checkbox(
                    "納入進度も同時作成",
                    value=True,
                    help="生産指示データから納入進度データも自動生成します（製品コードで統合）",
                    key=f"{tab_prefix}create_progress"
                )
                
                # 顧客別のインポート詳細説明
                customer = st.session_state.get('current_customer', 'kubota')
                if customer == 'kubota':
                    if isinstance(self.import_service, KubotaKakuteiCSVImportService):
                        st.info("""
                        **📦 インポート概要（クボタ確定CSV）:**
                        - 生産指示: 品番×納期×検区で上書き（数量は合算）
                        - 納入計画: 同じ受注は最新数量へ更新します
                        - 履歴: CSVインポート履歴にも記録されます
                        """)
                    else:
                        st.info("""
                        **📤 インポート概要（クボタ内示CSV）:**
                        - 生産指示: 検査区分ごとに数量を登録
                        - 納入計画: 検査区分が異なっても数量は統合（検査区分コメント付き）
                        - V2/V3のバージョン情報を基に自動で更新します
                        """)
                elif customer == 'tiera':
                    st.info("""
                    **📌 インポート処理の詳細（ティエラ様）:**
                    - 製品マスタ: 図番ごとに登録
                    - 生産指示: 図番×納期ごとに登録
                    - 納入進度: 図番×納期ごとに1レコード（数量合計）
                    """)
                
                # インポート実行ボタン
                st.markdown("---")
                
                col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])

                with col_btn1:
                    if st.button("🔄 インポート実行", type="primary", use_container_width=True, disabled=not can_edit, key=f"{tab_prefix}import_btn"):
                        with st.spinner("データをインポート中..."):
                            try:
                                uploaded_file.seek(0)

                                success, message = self.import_service.import_csv_data(
                                    uploaded_file,
                                    create_progress=create_progress
                                )

                                if success:
                                    st.success(f"✅ {message}")
                                    st.balloons()

                                    self._log_import_history(uploaded_file.name, message)

                                    # 検査対象製品を表示
                                    

                                    st.info("💡 「配送便計画」ページでデータを確認してください")
                                else:
                                    st.error(f"❌ {message}")

                            except Exception as e:
                                st.error(f"予期しないエラー: {e}")
                                import traceback
                                st.code(traceback.format_exc())

                with col_btn2:
                    if st.button("🗑️ キャンセル", use_container_width=True, key=f"{tab_prefix}cancel_btn"):
                        st.rerun()
                
                self._show_quantity_changes_after_import(tab_prefix=tab_prefix)
                self._show_inspection_products_after_import(tab_prefix=tab_prefix)
                
            except Exception as e:
                customer = st.session_state.get('current_customer', 'kubota')
                encoding_name = "Shift-JIS" if customer == 'kubota' else "CP932"
                st.error(f"ファイル読み込みエラー: {e}")
                st.info(f"ファイルが{encoding_name}形式であることを確認してください")
                
    
    def _show_quantity_changes_after_import(self, tab_prefix=""):
        """インポート直後の数量変更一覧を表示"""
        changes = getattr(self.import_service, "latest_quantity_changes", None)
        window = getattr(self.import_service, "latest_quantity_change_window", (None, None))

        if changes is None:
            return

        window_start, window_end = window if isinstance(window, tuple) else (None, None)

        if window_start is None or window_end is None:
            return

        if not changes:
            if window_start and window_end:
                st.info(f"✅ {window_start:%Y-%m-%d} ～ {window_end:%Y-%m-%d} の範囲で数量変更はありませんでした。")
            else:
                st.info("✅ 数量変更は検出されませんでした。")
            return

        df = pd.DataFrame(changes).copy()
        df['instruction_date'] = pd.to_datetime(df['instruction_date']).dt.date
        df.sort_values(['instruction_date', 'product_code', 'inspection_category'], inplace=True)

        df.rename(columns={
            'instruction_date': '指示日',
            'product_code': '品番',
            'product_name': '品名',
            'inspection_category': '検査区分',
            'previous_quantity': '前回数量',
            'new_quantity': '今回数量',
            'difference': '差分'
        }, inplace=True)

        if 'order_numbers' in df.columns:
            df['order_numbers'] = df['order_numbers'].apply(
                lambda v: '、'.join(map(str, v)) if isinstance(v, (list, tuple, set)) else ('' if v in [None, 'nan'] else str(v))
            )
            df.rename({'order_numbers': '発注番号'}, inplace=True)

        df['前回数量'] = df['前回数量'].astype(int)
        df['今回数量'] = df['今回数量'].astype(int)
        df['差分'] = df['差分'].astype(int)

        st.subheader("📊 数量変更一覧（本日〜10日後）")
        if window_start and window_end:
            st.caption(f"対象期間: {window_start:%Y-%m-%d} ～ {window_end:%Y-%m-%d}")

        display_columns = ['指示日', '品番', '品名', '検査区分', '前回数量', '今回数量', '差分']
        if '発注番号' in df.columns:
            display_columns.insert(3, '発注番号')

        column_config = {
            '指示日': st.column_config.DateColumn('指示日', format='YYYY-MM-DD', width='small'),
            '品番': st.column_config.TextColumn('品番', width='medium'),
            '品名': st.column_config.TextColumn('品名', width='large'),
            '検査区分': st.column_config.TextColumn('検査区分', width='small'),
            '前回数量': st.column_config.NumberColumn('前回数量', format='%d個', width='small'),
            '今回数量': st.column_config.NumberColumn('今回数量', format='%d個', width='small'),
            '差分': st.column_config.NumberColumn('差分', format='%+d個', width='small')
        }
        if '発注番号' in df.columns:
            column_config['発注番号'] = st.column_config.TextColumn('発注番号', width='large')

        st.dataframe(
            df[display_columns],
            use_container_width=True,
            hide_index=True,
            column_config=column_config
        )

        st.caption("⚠️ 数量が変わった製品は納入計画の再確認をお願いします。")
    
    def _show_inspection_products_after_import(self, tab_prefix=""):
        """インポート後に検査対象製品（F/$含む）を表示"""
        from sqlalchemy import text

        session = self.import_service.db.get_session()
        with st.expander("計画進度の再計算"):
            product_id = st.number_input("製品ID", min_value=1, step=1, key=f"{tab_prefix}recalc_product_id_inspection")
            recal_start_date = st.date_input("再計算開始日", key=f"{tab_prefix}recalc_start_date_inspection")
            recal_end_date = st.date_input("再計算終了日", key=f"{tab_prefix}recalc_end_date_inspection")

            col_recalc_single, col_recalc_all = st.columns(2)

            with col_recalc_single:
                if st.button("選択製品のみ再計算", key=f"{tab_prefix}recalc_single_inspection"):
                    self.service.recompute_planned_progress(product_id, recal_start_date, recal_end_date)
                    st.success("再計算が完了しました")

            with col_recalc_all:
                if st.button("全製品を再計算", key=f"{tab_prefix}recalc_all_inspection"):
                    self.service.recompute_planned_progress_all(recal_start_date, recal_end_date)
                    st.success("全ての製品に対する再計算が完了しました")
        
        try:
            # 日付範囲を調整（当日～1ヶ月後）
            today = date.today()-timedelta(days=0)
            end_date = today + timedelta(days=30)
            
            # production_instructions_detailテーブルから直接検査区分を取得
            query = text("""
                SELECT 
                    pid.instruction_date as 日付,
                    pid.id as 指示ID,
                    pid.inspection_category as 検査区分,
                    pid.instruction_quantity as 受注数,
                    p.product_code as 製品コード,
                    p.product_name as 製品名
                FROM production_instructions_detail pid
                LEFT JOIN products p ON pid.product_id = p.id
                WHERE pid.instruction_date BETWEEN :start_date AND :end_date
                    AND (pid.inspection_category LIKE '%F%' OR pid.inspection_category LIKE '%$%')
                ORDER BY pid.instruction_date, pid.inspection_category
            """)
            
            result = session.execute(query, {
                'start_date': today.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d')
            })
            
            rows = result.fetchall()
            
            if rows:
                st.warning("⚠️ 検査対象製品（F/$含む）が含まれています")

                df = pd.DataFrame(rows, columns=result.keys())
                df['日付'] = pd.to_datetime(df['日付']).dt.date

                # 受注数が0でないレコードのみ表示
                df = df[df['受注数'] > 0]

                # 検査区分ごとの集計
                f_products = df[df['検査区分'].str.contains('F', na=False)]
                dollar_products = df[df['検査区分'].str.contains(r'\$', regex=True, na=False)]
                
                col_sum1, col_sum2, col_sum3 = st.columns(3)
                with col_sum1:
                    f_count = len(f_products)
                    f_total = f_products['受注数'].sum()
                    st.metric("Fを含む（最終検査）", f"{f_count}件 / {f_total:,}個")
                with col_sum2:
                    s_count = len(dollar_products)
                    s_total = dollar_products['受注数'].sum()
                    st.metric("$を含む（目視検査）", f"{s_count}件 / {s_total:,}個")
                with col_sum3:
                    total_count = len(df)
                    total_quantity = df['受注数'].sum()
                    st.metric("総計", f"{total_count}件 / {total_quantity:,}個")
                
                # 検査区分ごとの詳細サマリー
                st.subheader("🔍 検査区分別サマリー")
                category_summary = df.groupby('検査区分').agg({
                    '指示ID': 'count',
                    '受注数': 'sum'
                }).rename(columns={'指示ID': '件数', '受注数': '総数量'}).reset_index()

                # 総数量が0でないレコードのみ表示
                category_summary = category_summary[category_summary['総数量'] > 0]

                st.dataframe(
                    category_summary,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "件数": st.column_config.NumberColumn("件数", format="%d件"),
                        "総数量": st.column_config.NumberColumn("総数量", format="%d個"),
                    }
                )
                
                # 日付ごとの集計も表示
                st.subheader("📅 日付別サマリー")
                daily_summary = df.groupby('日付').agg({
                    '指示ID': 'count',
                    '受注数': 'sum'
                }).rename(columns={'指示ID': '件数', '受注数': '総数量'}).reset_index()

                # 総数量が0でないレコードのみ表示
                daily_summary = daily_summary[daily_summary['総数量'] > 0]

                st.dataframe(
                    daily_summary,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "日付": st.column_config.DateColumn("日付", format="YYYY-MM-DD"),
                        "件数": st.column_config.NumberColumn("件数", format="%d件"),
                        "総数量": st.column_config.NumberColumn("総数量", format="%d個"),
                    }
                )
                
                # 製品ごとの集計
                st.subheader("📦 製品別サマリー")
                product_summary = df.groupby(['製品コード', '製品名']).agg({
                    '指示ID': 'count',
                    '受注数': 'sum'
                }).rename(columns={'指示ID': '件数', '受注数': '総数量'}).reset_index()

                # 総数量が0でないレコードのみ表示
                product_summary = product_summary[product_summary['総数量'] > 0]

                st.dataframe(
                    product_summary,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "件数": st.column_config.NumberColumn("件数", format="%d件"),
                        "総数量": st.column_config.NumberColumn("総数量", format="%d個"),
                    }
                )
                
                st.subheader("📋 詳細データ")
                st.dataframe(
                    df[['日付', '指示ID', '製品コード', '製品名', '検査区分', '受注数']],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "日付": st.column_config.DateColumn("日付", format="YYYY-MM-DD"),
                        "受注数": st.column_config.NumberColumn("受注数", format="%d個"),
                    }
                )
                
                # 注意事項
                st.info("""
                **💡 注意事項:**
                - **Fを含む**: 最終検査が必要な製品
                - **$を含む**: 目視検査が必要な製品  
                - これらの製品は特別な検査プロセスが必要です
                - 生産計画時に検査工程の時間を確保してください
                """)
        
        except Exception as e:
            st.error(f"検査対象製品確認エラー: {e}")
            import traceback
            st.code(traceback.format_exc())
        finally:
            session.close()
    
    def _show_import_history(self):
        """インポート履歴表示"""
        st.header("📊 インポート履歴")
        
        try:
            history = self.import_service.get_import_history()
            
            if history:
                history_df = pd.DataFrame(history)
                
                st.dataframe(
                    history_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "インポート日時": st.column_config.DatetimeColumn(
                            "インポート日時",
                            format="YYYY-MM-DD HH:mm:ss"
                        ),
                    }
                )
            else:
                st.info("インポート履歴がありません")
        
        except Exception as e:
            st.error(f"履歴取得エラー: {e}")
    
    def _show_instructions(self):
        """使い方表示"""
        st.header("ℹ️ 使い方")
        
        st.markdown("""
        ## 📋 CSVファイルのフォーマット
        
        ### 必須カラム
        - **レコード識別**: V2（日付行）、V3（数量行）
        - **データＮＯ**: 製品識別番号
        - **品番**: 製品コード
        - **検査区分**: N, NS, FS, F $Sなど
        - **スタート月度**: YYYYMM形式
        
        ### データ構造
        1. **V2行**: 各日付の生産指示日
        2. **V3行**: 各日付の生産指示数量
        
        ### インポート手順
        1. CSVファイルをアップロード
        2. プレビューで内容を確認
        3. インポートオプションを選択
        4. 「インポート実行」ボタンをクリック
        
        ## 📊 データ処理の仕様
        
        ### 製品マスタ登録
        - 検査区分ごとに**別製品**として登録されます
        - 例: 同じ品番でも「N」と「F」は別レコード
        
        ### 生産指示データ
        - 検査区分ごとに**分けて**登録されます
        - `production_instructions_detail`テーブルに格納
        
        ### 納入進度データ
        - 同じ製品コード×日付なら検査区分が違っても**統合**されます
        - 数量は各検査区分の**合計値**となります
        - 例: 品番「ABC123」の「N」100個 + 「F」50個 = 150個として1レコード登録
        
        ## ⚠️ 注意事項
        
        - ファイルは **Shift-JIS** エンコーディングである必要があります
        - インポートは**追加モード**で実行されます（既存データは削除されません）
        - 同じオーダーIDが既に存在する場合は数量が加算されます
        - 大量データの場合は時間がかかることがあります
        
        ## 🔗 関連機能
        
        - インポート後は「納入進度」ページで進捗を確認できます
        - 「配送便計画」で自動的に積載計画が作成されます
        - 検査区分F/$を含む製品は自動的にハイライトされます
        """)
    
    def _log_import_history(self, filename: str, message: str):
        """インポート履歴を記録"""
        try:
            self.import_service.log_import_history(filename, message)
        except Exception as e:
            print(f"履歴記録エラー: {e}")

