# app/ui/pages/hirakata_pickup_page.py
"""枚方集荷依頼書ページ"""

import streamlit as st
from datetime import date, timedelta
from services.hirakata_pickup_pdf_service import HirakataPickupPDFService
from services.email_service import EmailService


class HirakataPickupPage:
    """枚方集荷依頼書ページ"""

    def __init__(self, db_manager, auth_service=None):
        self.db_manager = db_manager
        self.auth_service = auth_service
        self.service = HirakataPickupPDFService(db_manager)
        self.email_service = EmailService(db_manager)

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

                    # 日別製品リストを取得
                    daily_products = self.service.get_daily_product_list(start_date, end_date)

                    # セッション状態に保存
                    st.session_state['generated_pdf'] = pdf_buffer
                    st.session_state['generated_pdf_filename'] = filename
                    st.session_state['pdf_start_date'] = start_date
                    st.session_state['pdf_end_date'] = end_date
                    st.session_state['daily_products'] = daily_products

                    st.success("✅ PDF生成完了")

                except Exception as e:
                    st.error(f"PDF生成エラー: {e}")
                    import traceback
                    st.code(traceback.format_exc())

        # PDFが生成されている場合、ダウンロードと送信ボタンを表示
        if 'generated_pdf' in st.session_state:
            col_dl, col_send = st.columns(2)

            with col_dl:
                st.download_button(
                    label="📥 PDFダウンロード",
                    data=st.session_state['generated_pdf'],
                    file_name=st.session_state['generated_pdf_filename'],
                    mime="application/pdf",
                    key="download_hirakata_pickup_pdf"
                )

            with col_send:
                if st.button("📧 集荷依頼書を送信", type="secondary", disabled=not can_edit):
                    st.session_state['show_email_dialog'] = True

        # メール送信ダイアログ
        if st.session_state.get('show_email_dialog', False):
            self._show_email_dialog()

        # 日別製品リスト表示
        if 'daily_products' in st.session_state and st.session_state['daily_products']:
            self._show_daily_product_list()

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

    def _show_email_dialog(self):
        """メール送信ダイアログ表示"""
        st.markdown("---")
        st.subheader("📧 集荷依頼書をメール送信")

        # 連絡先取得
        contacts = self.email_service.get_contacts_by_type('枚方集荷依頼')

        if not contacts:
            st.warning("連絡先が登録されていません。管理者に連絡してください。")
            if st.button("キャンセル"):
                st.session_state['show_email_dialog'] = False
                st.rerun()
            return

        # 送信先選択
        contact_options = {c['display_name']: c for c in contacts}
        selected_contact_names = st.multiselect(
            "送信先を選択",
            options=list(contact_options.keys()),
            default=list(contact_options.keys())[:1] if contact_options else []
        )

        # 選択された連絡先のメールアドレス
        selected_emails = [contact_options[name]['email'] for name in selected_contact_names]

        if selected_emails:
            st.info(f"送信先: {', '.join(selected_emails)}")

        # CCアドレス
        cc_emails_input = st.text_input(
            "CC（複数の場合はカンマ区切り）",
            placeholder="example1@example.com, example2@example.com"
        )

        cc_emails = []
        if cc_emails_input.strip():
            cc_emails = [email.strip() for email in cc_emails_input.split(',') if email.strip()]

        # メール件名
        start_date = st.session_state.get('pdf_start_date', date.today())
        end_date = st.session_state.get('pdf_end_date', date.today())
        default_subject = f"【枚方集荷依頼】{start_date.strftime('%Y/%m/%d')}～{end_date.strftime('%Y/%m/%d')}"

        subject = st.text_input("件名", value=default_subject)

        # メール本文
        default_body = f"""お世話になっております。
ダイソウ工業株式会社の辻岡です。

{start_date.strftime('%Y年%m月%d日')}～{end_date.strftime('%Y年%m月%d日')}の期間における枚方製造所向けの集荷依頼書を送付いたします。

添付のPDFをご確認の上、集荷手配をお願いいたします。

よろしくお願いいたします。

---
ダイソウ工業株式会社
辻岡(ツジオカ)
"""

        body = st.text_area("本文", value=default_body, height=250)

        # 送信ボタン
        col1, col2 = st.columns(2)

        with col1:
            if st.button("✉️ 送信", type="primary", disabled=not selected_emails):
                if not selected_emails:
                    st.error("送信先を選択してください")
                    return

                with st.spinner("メール送信中..."):
                    try:
                        # 現在のユーザーIDを取得（認証がある場合）
                        user_id = st.session_state.get('user_id', None)

                        result = self.email_service.send_email_with_attachment(
                            to_emails=selected_emails,
                            subject=subject,
                            body=body,
                            attachment_data=st.session_state['generated_pdf'],
                            attachment_filename=st.session_state['generated_pdf_filename'],
                            cc_emails=cc_emails if cc_emails else None,
                            user_id=user_id
                        )

                        if result['success']:
                            st.success(result['message'])
                            st.session_state['show_email_dialog'] = False
                            st.balloons()
                            st.rerun()
                        else:
                            st.error(result['message'])

                    except Exception as e:
                        st.error(f"送信エラー: {e}")
                        import traceback
                        st.code(traceback.format_exc())

        with col2:
            if st.button("キャンセル"):
                st.session_state['show_email_dialog'] = False
                st.rerun()

    def _show_daily_product_list(self):
        """日別製品リスト表示"""
        st.markdown("---")
        st.subheader("📋 日別製品リスト")

        daily_products = st.session_state.get('daily_products', {})

        if not daily_products:
            st.info("対象期間に出荷予定の製品がありません")
            return

        # 日付順にソート
        sorted_dates = sorted(daily_products.keys())

        for delivery_date in sorted_dates:
            products = daily_products[delivery_date]

            # 日付ごとのエキスパンダー
            with st.expander(f"📅 {delivery_date.strftime('%Y年%m月%d日')} ({len(products)}製品)", expanded=False):
                # テーブルデータ作成
                import pandas as pd

                df_data = []
                for product in products:
                    df_data.append({
                        '製品コード': product['product_code'],
                        '製品名': product['product_name'],
                        '数量': f"{product['quantity']:,}",
                        '容器種類': product['container_name'],
                        '必要容器数': product['containers_needed']
                    })

                df = pd.DataFrame(df_data)

                # テーブル表示（インデックス非表示）
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True
                )

                # 合計表示
                total_quantity = sum(p['quantity'] for p in products)
                total_containers = sum(p['containers_needed'] for p in products)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("製品種類数", f"{len(products)}種")
                with col2:
                    st.metric("合計数量", f"{total_quantity:,}")
                with col3:
                    st.metric("合計容器数", f"{total_containers}")
