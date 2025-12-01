-- マイグレーション: order_number列をVARCHAR(50)からVARCHAR(255)に拡張
-- 理由: 複数の注文番号を'+'で連結すると50文字を超える場合がある
-- 作成日: 2025-12-01
--
-- 【重要】このSQLは以下のデータベースに対して実行してください:
-- 1. tiera_db (ティエラ様用データベース)
-- 2. kubota_db (クボタ様用データベース)

-- production_instructions_detailテーブル
ALTER TABLE production_instructions_detail
MODIFY COLUMN order_number VARCHAR(255) DEFAULT NULL;

-- delivery_progressテーブル
ALTER TABLE delivery_progress
MODIFY COLUMN order_number VARCHAR(255) DEFAULT NULL;

-- 確認
SHOW COLUMNS FROM production_instructions_detail LIKE 'order_number';
SHOW COLUMNS FROM delivery_progress LIKE 'order_number';

SELECT 'マイグレーション完了: order_number列をVARCHAR(255)に拡張しました' AS status;
