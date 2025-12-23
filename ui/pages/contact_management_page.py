# app/ui/pages/contact_management_page.py
import streamlit as st
import pandas as pd
from sqlalchemy import text
from services.email_service import EmailService


class ContactManagementPage:
    """連絡先管理画面"""

    def __init__(self, auth_service):
        self.auth_service = auth_service
        self.email_service = EmailService(self.auth_service.db)

    def show(self):
        """ページ表示"""
        st.title("連絡先管理")
        st.write("メール送信先の連絡先を管理します")

        # 管理者のみアクセス可能
        current_user = st.session_state.get('user')
        if not current_user or not current_user.get('is_admin'):
            st.error("この画面は管理者のみアクセス可能です")
            return

        # 連絡先種別の定義
        contact_types = ["枚方集荷依頼", "一般連絡先", "緊急連絡先"]

        # 連絡先種別で絞り込み
        selected_type = st.selectbox("連絡先種別", options=contact_types)

        # 連絡先一覧取得
        contacts = self.email_service.get_contacts_by_type(selected_type)

        st.markdown("---")
        st.subheader(f"{selected_type} 一覧")

        if contacts:
            df = pd.DataFrame(contacts)
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "id": "ID",
                    "display_name": "連絡先名",
                    "email": "メールアドレス",
                    "phone": "電話番号",
                    "notes": "備考"
                }
            )
        else:
            st.info(f"{selected_type} の連絡先が登録されていません")

        st.markdown("---")
        st.subheader("新規連絡先登録")

        with st.form("create_contact_form"):
            col1, col2 = st.columns(2)

            with col1:
                company_name = st.text_input("会社名 *", placeholder="例: ○○株式会社")
                department = st.text_input("部署名", placeholder="例: 営業部")
                contact_person = st.text_input("担当者名", placeholder="例: 山田太郎")

            with col2:
                email = st.text_input("メールアドレス *", placeholder="example@company.com")
                phone = st.text_input("電話番号", placeholder="000-0000-0000")
                display_order = st.number_input("表示順", min_value=0, value=0, step=1)

            notes = st.text_area("備考", placeholder="連絡先に関するメモ")

            submitted = st.form_submit_button("登録", type="primary", use_container_width=True)

            if submitted:
                if not company_name or not email:
                    st.error("会社名とメールアドレスは必須です")
                else:
                    try:
                        session = self.auth_service.db.get_session()

                        query = text("""
                            INSERT INTO contacts (
                                contact_type, company_name, department, contact_person,
                                email, phone, is_active, display_order, notes
                            ) VALUES (
                                :contact_type, :company_name, :department, :contact_person,
                                :email, :phone, 1, :display_order, :notes
                            )
                        """)

                        session.execute(query, {
                            'contact_type': selected_type,
                            'company_name': company_name,
                            'department': department if department else None,
                            'contact_person': contact_person if contact_person else None,
                            'email': email,
                            'phone': phone if phone else None,
                            'display_order': display_order,
                            'notes': notes if notes else None
                        })

                        session.commit()
                        session.close()

                        st.success(f"連絡先「{company_name}」を登録しました")
                        st.rerun()

                    except Exception as e:
                        st.error(f"登録エラー: {e}")

        if contacts:
            st.markdown("---")
            st.subheader("連絡先編集・削除")

            contact_options = {c['display_name']: c for c in contacts}
            selected_contact_name = st.selectbox("編集する連絡先を選択", options=list(contact_options.keys()))

            if selected_contact_name:
                contact = contact_options[selected_contact_name]

                with st.form(f"edit_contact_{contact['id']}"):
                    col1, col2 = st.columns(2)

                    session = self.auth_service.db.get_session()
                    query = text("""
                        SELECT company_name, department, contact_person, email, phone, display_order, notes, is_active
                        FROM contacts
                        WHERE id = :contact_id
                    """)
                    result = session.execute(query, {'contact_id': contact['id']}).fetchone()
                    session.close()

                    with col1:
                        edit_company = st.text_input("会社名", value=result[0] or '')
                        edit_department = st.text_input("部署名", value=result[1] or '')
                        edit_person = st.text_input("担当者名", value=result[2] or '')

                    with col2:
                        edit_email = st.text_input("メールアドレス", value=result[3] or '')
                        edit_phone = st.text_input("電話番号", value=result[4] or '')
                        edit_order = st.number_input("表示順", min_value=0, value=result[5] or 0, step=1)

                    edit_notes = st.text_area("備考", value=result[6] or '')
                    edit_active = st.checkbox("有効", value=bool(result[7]))

                    col_update, col_delete = st.columns(2)

                    with col_update:
                        update_clicked = st.form_submit_button("更新", type="primary", use_container_width=True)

                        if update_clicked:
                            try:
                                session = self.auth_service.db.get_session()

                                update_query = text("""
                                    UPDATE contacts
                                    SET company_name = :company_name,
                                        department = :department,
                                        contact_person = :contact_person,
                                        email = :email,
                                        phone = :phone,
                                        display_order = :display_order,
                                        notes = :notes,
                                        is_active = :is_active
                                    WHERE id = :contact_id
                                """)

                                session.execute(update_query, {
                                    'contact_id': contact['id'],
                                    'company_name': edit_company,
                                    'department': edit_department if edit_department else None,
                                    'contact_person': edit_person if edit_person else None,
                                    'email': edit_email,
                                    'phone': edit_phone if edit_phone else None,
                                    'display_order': edit_order,
                                    'notes': edit_notes if edit_notes else None,
                                    'is_active': 1 if edit_active else 0
                                })

                                session.commit()
                                session.close()

                                st.success("連絡先を更新しました")
                                st.rerun()

                            except Exception as e:
                                st.error(f"更新エラー: {e}")

                    with col_delete:
                        delete_clicked = st.form_submit_button("削除", type="secondary", use_container_width=True)

                        if delete_clicked:
                            try:
                                session = self.auth_service.db.get_session()

                                delete_query = text("DELETE FROM contacts WHERE id = :contact_id")
                                session.execute(delete_query, {'contact_id': contact['id']})

                                session.commit()
                                session.close()

                                st.success("連絡先を削除しました")
                                st.rerun()

                            except Exception as e:
                                st.error(f"削除エラー: {e}")
