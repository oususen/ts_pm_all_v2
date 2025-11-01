# app/ui/pages/change_password_page.py
import streamlit as st


class ChangePasswordPage:
    """パスワード変更ページ（一般ユーザー向け）"""

    def __init__(self, auth_service):
        self.auth_service = auth_service

    def show(self):
        """ページ表示"""
        st.title("🔐 パスワード変更")
        st.write("現在のパスワードを入力して、新しいパスワードに変更できます。")

        # ログインユーザー情報を取得
        current_user = st.session_state.get('user')
        if not current_user:
            st.error("⛔ ログインしてください")
            return

        # ユーザー情報表示
        st.info(f"👤 ユーザー名: **{current_user['username']}** ({current_user['full_name']})")

        st.markdown("---")

        # パスワード変更フォーム
        with st.form("change_password_form"):
            st.subheader("🔑 パスワード変更")

            old_password = st.text_input(
                "現在のパスワード",
                type="password",
                help="セキュリティのため、現在のパスワードを入力してください"
            )

            new_password = st.text_input(
                "新しいパスワード",
                type="password",
                help="8文字以上の英数字を推奨"
            )

            new_password_confirm = st.text_input(
                "新しいパスワード（確認）",
                type="password",
                help="確認のため、もう一度入力してください"
            )

            st.markdown("---")

            # セキュリティガイドライン
            with st.expander("🛡️ パスワードのセキュリティガイドライン"):
                st.markdown("""
                **強力なパスワードの作り方:**
                - 最低8文字以上（12文字以上を推奨）
                - 英字の大文字と小文字を組み合わせる
                - 数字を含める
                - 記号を含める（@, !, #, $ など）
                - 他のサービスと同じパスワードを使わない
                - 推測されやすい情報（名前、誕生日など）を避ける

                **避けるべきパスワード:**
                - ❌ 12345678
                - ❌ password
                - ❌ qwerty
                - ❌ 自分の名前や誕生日
                """)

            col1, col2 = st.columns([1, 3])

            with col1:
                submit_button = st.form_submit_button("🔒 変更する", type="primary", use_container_width=True)

        # パスワード変更処理（フォームの外）
        if submit_button:
            # 入力チェック
            if not old_password:
                st.error("❌ 現在のパスワードを入力してください")
            elif not new_password:
                st.error("❌ 新しいパスワードを入力してください")
            elif not new_password_confirm:
                st.error("❌ 新しいパスワード（確認）を入力してください")
            elif new_password != new_password_confirm:
                st.error("❌ 新しいパスワードが一致しません")
            elif len(new_password) < 6:
                st.warning("⚠️ パスワードは6文字以上にしてください")
            elif old_password == new_password:
                st.warning("⚠️ 新しいパスワードは現在のパスワードと異なるものにしてください")
            else:
                # パスワード変更を実行
                try:
                    success = self.auth_service.change_password(
                        current_user['id'],
                        old_password,
                        new_password
                    )

                    if success:
                        st.success("✅ パスワードを変更しました")
                        st.info("💡 次回ログイン時から新しいパスワードをご使用ください")

                        # session_stateに成功フラグを設定
                        st.session_state['password_changed'] = True
                    else:
                        st.error("❌ 現在のパスワードが正しくありません")

                except Exception as e:
                    st.error(f"❌ パスワード変更中にエラーが発生しました: {e}")

        # パスワード変更成功後のログアウトボタン（フォームの外）
        if st.session_state.get('password_changed'):
            st.markdown("---")
            if st.button("🚪 ログアウトする", type="primary", use_container_width=True):
                st.session_state.clear()
                st.rerun()

        st.markdown("---")

        # 注意事項
        st.caption("⚠️ パスワードを忘れた場合は、システム管理者にお問い合わせください")
