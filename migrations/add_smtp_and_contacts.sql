-- ====================================================================
-- マイグレーション: SMTP設定と連絡先テーブル追加
-- 作成日: 2025-11-27
-- 対象DB: kubota_db
-- 説明: usersテーブルにSMTP設定列を追加し、contactsテーブルを作成
-- ====================================================================

USE kubota_db;

-- ====================================================================
-- 1. usersテーブルにSMTP設定列を追加
-- ====================================================================

-- 既存の列を確認（エラーを無視して続行）
SELECT '--- Step 1: usersテーブルにSMTP設定列を追加 ---' AS status;

-- smtp_host列の追加
ALTER TABLE users
ADD COLUMN IF NOT EXISTS smtp_host VARCHAR(255) NULL COMMENT 'SMTPサーバーホスト';

-- smtp_port列の追加
ALTER TABLE users
ADD COLUMN IF NOT EXISTS smtp_port INT NULL DEFAULT 587 COMMENT 'SMTPポート番号';

-- smtp_user列の追加
ALTER TABLE users
ADD COLUMN IF NOT EXISTS smtp_user VARCHAR(255) NULL COMMENT 'SMTP認証ユーザー名';

-- smtp_password列の追加
ALTER TABLE users
ADD COLUMN IF NOT EXISTS smtp_password VARCHAR(255) NULL COMMENT 'SMTP認証パスワード';

SELECT '✓ usersテーブルにSMTP設定列を追加しました' AS status;

-- ====================================================================
-- 2. contactsテーブルの作成
-- ====================================================================

SELECT '--- Step 2: contactsテーブル作成 ---' AS status;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='連絡先マスタ';

SELECT '✓ contactsテーブルを作成しました' AS status;

-- ====================================================================
-- 3. 初期データの投入
-- ====================================================================

SELECT '--- Step 3: 初期連絡先データ投入 ---' AS status;

-- 既存データの確認と重複挿入の防止
INSERT INTO contacts (
    contact_type, company_name, department, contact_person,
    email, is_active, display_order, notes
)
SELECT
    '枚方集荷依頼',
    '大友ロジスティクスサービス株式会社',
    '京都営業所',
    '配車担当者',
    'kyouto03@otomo-logi.co.jp',
    1,
    1,
    '枚方製造所向け集荷依頼書の送信先'
WHERE NOT EXISTS (
    SELECT 1 FROM contacts
    WHERE contact_type = '枚方集荷依頼'
    AND email = 'kyouto03@otomo-logi.co.jp'
);

SELECT '✓ 初期連絡先データを投入しました' AS status;

-- ====================================================================
-- 4. 確認クエリ
-- ====================================================================

SELECT '--- Step 4: 確認 ---' AS status;

-- usersテーブルの列確認
SELECT
    COLUMN_NAME,
    DATA_TYPE,
    COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'kubota_db'
  AND TABLE_NAME = 'users'
  AND COLUMN_NAME LIKE 'smtp%'
ORDER BY ORDINAL_POSITION;

-- contactsテーブルのデータ確認
SELECT
    id,
    contact_type,
    company_name,
    email,
    is_active
FROM contacts
ORDER BY contact_type, display_order;

SELECT '✓ マイグレーション完了' AS status;
