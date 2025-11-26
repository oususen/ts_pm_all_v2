-- 枚方集荷依頼書ページの権限を追加

-- すべてのロールに枚方集荷依頼書ページの閲覧・編集権限を追加
INSERT INTO page_permissions (role_id, page_name, can_view, can_edit)
SELECT id, '📦 枚方集荷依頼書', 1, 1
FROM roles
WHERE NOT EXISTS (
    SELECT 1 FROM page_permissions
    WHERE page_permissions.role_id = roles.id
    AND page_permissions.page_name = '📦 枚方集荷依頼書'
);
