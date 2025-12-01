-- マイグレーション: tiera_db の container_capacity に container_code カラムを追加
-- 理由: 容器情報取得時に container_code カラムが必要
-- 作成日: 2025-12-01
--
-- 【重要】このSQLは tiera_db に対して実行してください

USE tiera_db;

-- container_capacity テーブルに container_code を追加
ALTER TABLE container_capacity
ADD COLUMN IF NOT EXISTS container_code VARCHAR(20) NULL COMMENT '容器コード' AFTER name;

-- 既存データに容器コードを設定（容器名から推測）
UPDATE container_capacity SET container_code = 'S90' WHERE name = 'S90';
UPDATE container_capacity SET container_code = '19-6' WHERE name = '19-6';
UPDATE container_capacity SET container_code = 'SUS' WHERE name = 'SUS';
UPDATE container_capacity SET container_code = 'F2N' WHERE name = 'F2N';
UPDATE container_capacity SET container_code = '6ENSUS' WHERE name = '6ENSUS';
UPDATE container_capacity SET container_code = '17U-5T' WHERE name = '17U-5T';
UPDATE container_capacity SET container_code = '19-6T' WHERE name = '19-6T';
UPDATE container_capacity SET container_code = '6T' WHERE name = '6T';
UPDATE container_capacity SET container_code = '7T7A' WHERE name = '7T7A';
UPDATE container_capacity SET container_code = '7T7B' WHERE name = '7T7B';
UPDATE container_capacity SET container_code = '7T5E' WHERE name = '7T5E';
UPDATE container_capacity SET container_code = '7T5F' WHERE name = '7T5F';
UPDATE container_capacity SET container_code = '7T7A' WHERE name = '7T7A';
UPDATE container_capacity SET container_code = '19-6ENT' WHERE name = '19-6ENT';
UPDATE container_capacity SET container_code = '7T5A' WHERE name = '7T5A';

-- 確認
SELECT '容器コードカラムの追加完了' AS status;

-- データ確認
SELECT
    id,
    name AS 容器名,
    container_code AS 容器コード,
    CONCAT(width, 'x', depth, 'x', height, 'mm') AS サイズ
FROM container_capacity
ORDER BY id;
