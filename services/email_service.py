# app/services/email_service.py
"""メール送信サービス"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import List, Dict, Optional
from io import BytesIO
from sqlalchemy import text


class EmailService:
    """メール送信サービス"""

    def __init__(self, db_manager):
        self.db = db_manager

    def get_smtp_config(self, user_id: Optional[int] = None) -> Optional[Dict]:
        """
        SMTP設定を取得

        Args:
            user_id: ユーザーID（Noneの場合は管理者の設定を取得）

        Returns:
            Dict: SMTP設定（host, port, user, password）
        """
        session = self.db.get_session()

        try:
            if user_id:
                query = text("""
                    SELECT smtp_host, smtp_port, smtp_user, smtp_password
                    FROM users
                    WHERE id = :user_id AND is_active = 1
                """)
                result = session.execute(query, {'user_id': user_id}).fetchone()
            else:
                # 管理者の設定を取得
                query = text("""
                    SELECT smtp_host, smtp_port, smtp_user, smtp_password
                    FROM users
                    WHERE is_admin = 1 AND is_active = 1
                    ORDER BY id
                    LIMIT 1
                """)
                result = session.execute(query).fetchone()

            if result and result[0]:  # smtp_hostが設定されている場合
                return {
                    'host': result[0],
                    'port': result[1] or 587,
                    'user': result[2],
                    'password': result[3]
                }

            return None

        finally:
            session.close()

    def get_contacts_by_type(self, contact_type: str) -> List[Dict]:
        """
        連絡先種別で連絡先を取得

        Args:
            contact_type: 連絡先種別（例: '枚方集荷依頼'）

        Returns:
            List[Dict]: 連絡先リスト
        """
        session = self.db.get_session()

        try:
            query = text("""
                SELECT
                    id,
                    company_name,
                    department,
                    contact_person,
                    email,
                    phone,
                    notes
                FROM contacts
                WHERE contact_type = :contact_type
                  AND is_active = 1
                ORDER BY display_order, company_name
            """)

            results = session.execute(query, {'contact_type': contact_type}).fetchall()

            contacts = []
            for row in results:
                contact_name = row[1]  # company_name
                if row[2]:  # department
                    contact_name += f" {row[2]}"
                if row[3]:  # contact_person
                    contact_name += f" {row[3]}"

                contacts.append({
                    'id': row[0],
                    'display_name': contact_name,
                    'email': row[4],
                    'phone': row[5],
                    'notes': row[6]
                })

            return contacts

        finally:
            session.close()

    def send_email_with_attachment(
        self,
        to_emails: List[str],
        subject: str,
        body: str,
        attachment_data: BytesIO,
        attachment_filename: str,
        cc_emails: Optional[List[str]] = None,
        user_id: Optional[int] = None
    ) -> Dict:
        """
        添付ファイル付きメールを送信

        Args:
            to_emails: 宛先メールアドレスリスト
            subject: 件名
            body: 本文
            attachment_data: 添付ファイルデータ（BytesIO）
            attachment_filename: 添付ファイル名
            cc_emails: CCメールアドレスリスト
            user_id: 送信者ユーザーID

        Returns:
            Dict: 送信結果 {'success': bool, 'message': str}
        """
        # SMTP設定取得
        smtp_config = self.get_smtp_config(user_id)

        if not smtp_config:
            return {
                'success': False,
                'message': 'SMTP設定が見つかりません。管理者に連絡してください。'
            }

        try:
            # メッセージ作成
            msg = MIMEMultipart()
            msg['From'] = smtp_config['user']
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = subject

            if cc_emails:
                msg['Cc'] = ', '.join(cc_emails)

            # 本文追加
            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            # 添付ファイル追加
            attachment_data.seek(0)
            attachment = MIMEApplication(attachment_data.read(), _subtype='pdf')
            attachment.add_header(
                'Content-Disposition',
                'attachment',
                filename=attachment_filename
            )
            msg.attach(attachment)

            # SMTP接続して送信
            with smtplib.SMTP(smtp_config['host'], smtp_config['port']) as server:
                server.starttls()  # TLS開始
                server.login(smtp_config['user'], smtp_config['password'])

                # 送信先リスト作成
                recipients = to_emails.copy()
                if cc_emails:
                    recipients.extend(cc_emails)

                server.send_message(msg)

            return {
                'success': True,
                'message': f'メールを送信しました（宛先: {len(to_emails)}件）'
            }

        except smtplib.SMTPAuthenticationError:
            return {
                'success': False,
                'message': 'SMTP認証エラー: ユーザー名またはパスワードが正しくありません'
            }
        except smtplib.SMTPException as e:
            return {
                'success': False,
                'message': f'メール送信エラー: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'予期しないエラー: {str(e)}'
            }
