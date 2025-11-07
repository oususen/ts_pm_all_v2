# -*- coding: utf-8 -*-
"""
出荷指示書生成ページ
"""

import streamlit as st
from datetime import date, timedelta
import pandas as pd
import os
from pathlib import Path
from services.shipping_order_service import ShippingOrderService
from services.shipping_pdf_generator import generate_shipping_order_pdf


class ShippingOrderPage:
    """出荷指示書生成ページ"""

    def __init__(self, db_manager):
        self.db = db_manager
        self.service = ShippingOrderService(db_manager)

    def show(self):
        """ページ表示（main.pyから呼び出される）"""
        self.render()

    def render(self):
        """ページ描画"""
        st.header("📋 出荷指示書生成（Tiera様専用）")

        # 顧客チェック
        current_customer = st.session_state.get('current_customer', 'kubota')
        if current_customer != 'tiera':
            st.warning("⚠️ この機能はTiera様専用です。サイドバーで顧客を「Tiera」に切り替えてください。")
            return

        st.write("delivery_progressのデータから出荷指示書を生成します（Tiera製品のみ）")

        # 日付選択
        col1, col2, col3 = st.columns([2, 2, 4])

        with col1:
            # 利用可能な日付を取得
            available_dates = self.service.get_available_dates()

            if available_dates:
                default_date = date.today() + timedelta(days=1)
                # available_dates[0]
            else:
                default_date = date.today()

            selected_date = st.date_input(
                "出荷日を選択",
                value=default_date,
                help="delivery_progressに登録されている日付を選択してください"
            )

        with col2:
            if st.button("📊 データ取得", type="primary", use_container_width=True):
                st.session_state['shipping_data_loaded'] = True
                st.session_state['shipping_target_date'] = selected_date

        with col3:
            if st.session_state.get('shipping_data_loaded'):
                if st.button("📄 PDF生成", use_container_width=True):
                    self._generate_pdf()

        st.markdown("---")

        # データ取得と表示
        if st.session_state.get('shipping_data_loaded'):
            target_date = st.session_state.get('shipping_target_date', selected_date)

            with st.spinner(f'{target_date} のデータを取得中...'):
                shipping_data = self.service.get_shipping_data_by_date(target_date)

            # session_stateに保存（PDF生成で使用）
            st.session_state['shipping_data'] = shipping_data

            # 4便のデータを表示
            self._show_shipping_data(shipping_data)

    def _generate_pdf(self):
        """PDF生成処理"""
        shipping_data = st.session_state.get('shipping_data')

        if not shipping_data:
            st.error("データが取得されていません。先に「📊 データ取得」をクリックしてください。")
            return

        try:
            # 出力ディレクトリを作成
            output_dir = Path("d:/ts_pm_all/output/shipping_orders")
            output_dir.mkdir(parents=True, exist_ok=True)

            # ファイル名生成
            target_date = shipping_data.get('date')
            date_str = target_date.strftime('%Y%m%d') if target_date else 'unknown'
            filename = f"出荷指示書_{date_str}.pdf"
            output_path = output_dir / filename

            # PDF生成
            with st.spinner('PDF生成中...'):
                user_name = st.session_state.get('user', {}).get('username', 'システム')
                generate_shipping_order_pdf(
                    shipping_data=shipping_data,
                    output_path=str(output_path),
                    creator_name=user_name
                )

            st.success(f"✅ PDFを生成しました: {filename}")

            # ダウンロードボタンを表示
            with open(output_path, 'rb') as f:
                pdf_data = f.read()

            st.download_button(
                label="📥 PDFをダウンロード",
                data=pdf_data,
                file_name=filename,
                mime="application/pdf",
                use_container_width=True
            )

        except Exception as e:
            st.error(f"❌ PDF生成エラー: {e}")
            import traceback
            with st.expander("エラー詳細"):
                st.code(traceback.format_exc())

    def _show_shipping_data(self, data: dict):
        """出荷指示書データを表示"""

        st.subheader(f"📅 出荷日: {data['date']}")

        # 各便のタブ
        tab1, tab2, tab3, tab4 = st.tabs([
            "1便目 (06:00)",
            "2便目 (06:30)",
            "3便目 (10:00)",
            "4便目 (13:00)"
        ])

        with tab1:
            self._show_trip_data(
                "1便目 - 4t/5tブレード (1)",
                "06:00",
                data['trip1'],
                "容器が「4-5T」の製品"
            )

        with tab2:
            special_notes = data.get('trip2_special_annotations', [])
            if special_notes:
                info_text = " / ".join(
                    f"{note['group_code']}: {note['containers']}容器"
                    for note in special_notes
                )
                st.info(f"特記事項（2便目右端）：{info_text}")
            self._show_trip_data(
                "2便目 - ブレード",
                "06:30",
                data['trip2'],
                "建機モデル [391, 17U, 20U, 26U, 19-6, 390, KOTEIKYAKU] ＋ 製品群 SIGA/KANTATSU"
            )

        with tab3:
            self._show_trip_data(
                "3便目 - オイルタンク・シートベース",
                "10:00",
                data['trip3'],
                "製品群コードが [SEATBASE, TANK]"
            )

        with tab4:
            self._show_trip_data(
                "4便目 - 4t/5tブレード (2)",
                "13:00",
                data['trip4'],
                "1便目と同じ製品（数量半分）"
            )

    def _show_trip_data(self, title: str, time: str, trip_data: list, criteria: str):
        """各便のデータを表示"""

        st.write(f"**{title}**")
        st.caption(f"出発時刻: {time} | 振り分け基準: {criteria}")

        if not trip_data:
            st.info("該当する製品がありません")
            return

        # DataFrameに変換
        df = pd.DataFrame(trip_data)

        # 表示用カラムを選択
        display_columns = [
            'product_code',
            'product_name',
            'model_name',
            'order_quantity',
            'capacity',
            'container_name',
            'group_code'
        ]

        # 存在するカラムのみ選択
        available_columns = [col for col in display_columns if col in df.columns]
        display_df = df[available_columns].copy()

        # カラム名を日本語に変換
        column_names = {
            'product_code': '製品コード',
            'product_name': '製品名',
            'model_name': '機種名',
            'order_quantity': '注文数',
            'capacity': '入り数',
            'container_name': '使用容器',
            'group_code': '製品群'
        }
        display_df.rename(columns=column_names, inplace=True)

        # サマリー
        col_summary1, col_summary2, col_summary3 = st.columns(3)
        with col_summary1:
            st.metric("製品種類", f"{len(display_df)}種")
        with col_summary2:
            total_qty = df['order_quantity'].sum()
            st.metric("合計数量", f"{int(total_qty):,}")
        with col_summary3:
            if 'capacity' in df.columns:
                total_capacity = (df['order_quantity'] * df['capacity']).sum()
                st.metric("合計容量", f"{int(total_capacity):,}")

        # データテーブル
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )

        # 詳細表示（折りたたみ）
        with st.expander("詳細データを表示"):
            st.dataframe(df, use_container_width=True, hide_index=True)
