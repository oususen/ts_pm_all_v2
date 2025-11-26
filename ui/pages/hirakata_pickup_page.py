# app/ui/pages/hirakata_pickup_page.py
"""枚方集荷依頼書ページ"""

import streamlit as st
from datetime import date, timedelta
from services.hirakata_pickup_pdf_service import HirakataPickupPDFService


class HirakataPickupPage:
    """枚方集荷依頼書ページ"""

    def __init__(self, db_manager, auth_service=None):
        self.db_manager = db_manager
        self.auth_service = auth_service
        self.service = HirakataPickupPDFService(db_manager)

    def _can_edit_page(self) -> bool:
        """ページ編集権限チェック"""
        if not self.auth_service:
            return True
        return st.session_state.get('permissions', {}).get('📦 枚方集荷依頼書', {}).get('can_edit', False)

    def show(self):
        """ページ表示"""
        st.title("📦 枚方集荷依頼書")
        

        st.info("""
        **枚方集荷依頼書PDF生成**

        - 指定期間の枚方製品の出荷予定をもとに集荷依頼書PDFを生成します
        - 各日ごとの容器種類と数量が自動集計されます
        - 集荷日は出荷日の前日、配達日は出荷日当日で設定されます
        """)

        # 編集権限チェック
        can_edit = self._can_edit_page()
        if not can_edit:
            st.warning("⚠️ この画面の編集権限がありません。閲覧のみ可能です。")

        # 日付範囲選択
        col1, col2 = st.columns(2)

        with col1:
            start_date = st.date_input(
                "開始日",
                value=date.today(),
                key="hirakata_pickup_start_date"
            )

        with col2:
            end_date = st.date_input(
                "終了日",
                value=date.today() + timedelta(days=7),
                key="hirakata_pickup_end_date"
            )

        # バリデーション
        if start_date > end_date:
            st.error("開始日は終了日より前である必要があります")
            return

        # PDF生成ボタン
        if st.button("📄 集荷依頼書PDF生成", type="primary", disabled=not can_edit):
            with st.spinner("PDFを生成中..."):
                try:
                    pdf_buffer = self.service.generate_pickup_request_pdf(start_date, end_date)

                    # ファイル名生成
                    filename = f"枚方集荷依頼書_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pdf"

                    # ダウンロードボタン
                    st.success("✅ PDF生成完了")
                    st.download_button(
                        label="📥 PDFダウンロード",
                        data=pdf_buffer,
                        file_name=filename,
                        mime="application/pdf",
                        key="download_hirakata_pickup_pdf"
                    )

                except Exception as e:
                    st.error(f"PDF生成エラー: {e}")
                    import traceback
                    st.code(traceback.format_exc())

        # 説明
        with st.expander("📖 使い方"):
            st.markdown("""
            ## 集荷依頼書PDF生成の流れ

            1. **期間選択**: 開始日と終了日を選択します
            2. **PDF生成**: 「集荷依頼書PDF生成」ボタンをクリック
            3. **ダウンロード**: 生成されたPDFをダウンロード
            4. **メール送付**: 大友ロジスティクスサービスへメールで送信

            ## 注意事項

            - 集荷依頼は集荷前日の17時までにメールで送信してください
            - 送信先: wang@daiso-ind.co.jp（開発段階）
            - PDFには指定期間内の全ての出荷日が含まれます
            - 容器数は積載計画データから自動集計されます

            ## 容器種類

            - **ＭＭ**: アミ容器
            - **37N-2 #37N**: グレー・緑容器
            - **TP392**: 青容器
            - **TP331**: グレー小容器
            """)
