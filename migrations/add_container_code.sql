-- 容器テーブルに容器コードカラムを追加

-- container_capacity テーブルに container_code を追加
ALTER TABLE container_capacity
ADD COLUMN container_code VARCHAR(20) NULL COMMENT '容器コード' AFTER name;

-- 既存データに容器コードを設定（容器名から推測）
UPDATE container_capacity SET container_code = 'AMI' WHERE name LIKE '%アミ%';
UPDATE container_capacity SET container_code = 'HB37' WHERE name LIKE '%HB-37%' OR name LIKE '%HB37%';
UPDATE container_capacity SET container_code = 'TP392' WHERE name LIKE '%TP392%';
UPDATE container_capacity SET container_code = 'TP331' WHERE name LIKE '%TP331%';
UPDATE container_capacity SET container_code = 'POLI' WHERE name LIKE '%ポリ%' AND container_code IS NULL;

-- 容器コードにユニーク制約を追加（NULL許可）
-- ALTER TABLE container_capacity ADD UNIQUE KEY unique_container_code (container_code);
