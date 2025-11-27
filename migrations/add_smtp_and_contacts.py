"""
マイグレーション: SMTP設定と連絡先テーブル追加

1. usersテーブルにSMTP設定列を追加
2. contactsテーブル（連絡先マスタ）を作成
"""

import sys
import os

# UTF-8出力設定
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from repository.database_manager import DatabaseManager
from sqlalchemy import text

def migrate():
    """マイグレーション実行"""
    db = DatabaseManager()
    session = db.get_session()

    try:
        print("=== SMTP設定と連絡先テーブル追加マイグレーション開始 ===")

        # 1. usersテーブルにSMTP設定列を追加
        print("\n1. usersテーブルにSMTP設定列を追加...")

        # 既存の列を確認
        result = session.execute(text("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'kubota_db'
            AND TABLE_NAME = 'users'
            AND COLUMN_NAME = 'smtp_host'
        """))

        if not result.fetchone():
            session.execute(text("""
                ALTER TABLE users
                ADD COLUMN smtp_host VARCHAR(255) NULL COMMENT 'SMTPサーバーホスト',
                ADD COLUMN smtp_port INT NULL DEFAULT 587 COMMENT 'SMTPポート番号',
                ADD COLUMN smtp_user VARCHAR(255) NULL COMMENT 'SMTP認証ユーザー名',
                ADD COLUMN smtp_password VARCHAR(255) NULL COMMENT 'SMTP認証パスワード'
            """))
            print("   ✅ SMTP設定列を追加しました")
        else:
            print("   ⚠️ SMTP設定列は既に存在します（スキップ）")

        # 2. contactsテーブル作成
        print("\n2. contactsテーブル（連絡先マスタ）作成...")
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS contacts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                contact_type VARCHAR(50) NOT NULL COMMENT '連絡先種別（枚方集荷依頼、その他）',
                company_name VARCHAR(255) NOT NULL COMMENT '会社名',
                department VARCHAR(255) NULL COMMENT '部署名',
                contact_person VARCHAR(255) NULL COMMENT '担当者名',
                email VARCHAR(255) NOT NULL COMMENT 'メールアドレス',
                phone VARCHAR(50) NULL COMMENT '電話番号',
                is_active TINYINT(1) DEFAULT 1 COMMENT '有効フラグ',
                display_order INT DEFAULT 0 COMMENT '表示順',
                notes TEXT NULL COMMENT '備考',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_contact_type (contact_type),
                INDEX idx_is_active (is_active),
                INDEX idx_display_order (display_order)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='連絡先マスタ'
        """))
        print("   ✅ contactsテーブルを作成しました")

        # 3. 初期データ投入（枚方集荷依頼の連絡先）
        print("\n3. 初期連絡先データ投入...")

        # 既存データ確認
        result = session.execute(text("""
            SELECT COUNT(*) as cnt FROM contacts WHERE contact_type = '枚方集荷依頼'
        """))
        count = result.fetchone()[0]

        if count == 0:
            session.execute(text("""
                INSERT INTO contacts (
                    contact_type, company_name, department, contact_person,
                    email, is_active, display_order, notes
                ) VALUES
                (
                    '枚方集荷依頼',
                    '大友ロジスティクスサービス株式会社',
                    '京都営業所',
                    '配車担当者',
                    'kyouto03@otomo-logi.co.jp',
                    1,
                    1,
                    '枚方製造所向け集荷依頼書の送信先'
                )
            """))
            print("   ✅ 初期連絡先データを投入しました")
        else:
            print(f"   ⚠️ 枚方集荷依頼の連絡先は既に{count}件存在します（スキップ）")

        # 4. デフォルトSMTP設定の投入（Gmail例）
        print("\n4. デフォルトSMTP設定確認...")
        result = session.execute(text("""
            SELECT id, username, smtp_host
            FROM users
            WHERE is_admin = 1
            LIMIT 1
        """))
        admin_user = result.fetchone()

        if admin_user and not admin_user[2]:  # smtp_hostが未設定の場合
            print(f"   ⚠️ 管理者ユーザー '{admin_user[1]}' にSMTP設定を手動で設定してください")
            print("   例: smtp.gmail.com, ポート 587")
        elif admin_user and admin_user[2]:
            print(f"   ✅ 管理者ユーザー '{admin_user[1]}' のSMTP設定済み: {admin_user[2]}")
        else:
            print("   ⚠️ 管理者ユーザーが見つかりません")

        session.commit()
        print("\n=== マイグレーション完了 ===")

    except Exception as e:
        session.rollback()
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        session.close()

def rollback():
    """ロールバック"""
    db = DatabaseManager()
    session = db.get_session()

    try:
        print("=== ロールバック開始 ===")

        # contactsテーブル削除
        session.execute(text("DROP TABLE IF EXISTS contacts"))
        print("✅ contactsテーブルを削除しました")

        # usersテーブルからSMTP設定列を削除
        session.execute(text("""
            ALTER TABLE users
            DROP COLUMN IF EXISTS smtp_host,
            DROP COLUMN IF EXISTS smtp_port,
            DROP COLUMN IF EXISTS smtp_user,
            DROP COLUMN IF EXISTS smtp_password
        """))
        print("✅ usersテーブルからSMTP設定列を削除しました")

        session.commit()
        print("=== ロールバック完了 ===")

    except Exception as e:
        session.rollback()
        print(f"❌ ロールバックエラー: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback()
    else:
        migrate()
