#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""枚方集荷依頼書ページの権限を追加"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_all import build_db_config
import pymysql

def main():
    cfg = build_db_config()
    conn = pymysql.connect(
        host=cfg.host,
        user=cfg.user,
        password=cfg.password,
        database=cfg.database,
        charset='utf8mb4'
    )

    cursor = conn.cursor()

    try:
        # すべてのロールに枚方集荷依頼書ページの権限を追加
        print("枚方集荷依頼書ページの権限を追加中...")

        cursor.execute("""
            INSERT INTO page_permissions (role_id, page_name, can_view, can_edit)
            SELECT id, '📦 枚方集荷依頼書', 1, 1
            FROM roles
            WHERE NOT EXISTS (
                SELECT 1 FROM page_permissions
                WHERE page_permissions.role_id = roles.id
                AND page_permissions.page_name = '📦 枚方集荷依頼書'
            )
        """)

        conn.commit()
        affected_rows = cursor.rowcount
        print(f"[OK] {affected_rows}件のロールに枚方集荷依頼書ページの権限を追加しました")

        # 確認
        cursor.execute("""
            SELECT r.role_name, pp.can_view, pp.can_edit
            FROM page_permissions pp
            INNER JOIN roles r ON pp.role_id = r.id
            WHERE pp.page_name = '📦 枚方集荷依頼書'
        """)
        results = cursor.fetchall()

        if results:
            print("\n=== 枚方集荷依頼書の権限設定 ===")
            for row in results:
                view_status = "閲覧可" if row[1] else "閲覧不可"
                edit_status = "編集可" if row[2] else "編集不可"
                print(f"ロール: {row[0]}, {view_status}, {edit_status}")
        else:
            print("\n[INFO] 権限設定が見つかりませんでした")

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] エラーが発生しました: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    main()
