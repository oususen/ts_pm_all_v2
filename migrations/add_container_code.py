#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""容器テーブルに容器コードカラムを追加"""

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
        # container_code カラムを追加
        print("容器コードカラムを追加中...")
        cursor.execute("""
            ALTER TABLE container_capacity
            ADD COLUMN container_code VARCHAR(20) NULL COMMENT '容器コード' AFTER name
        """)
        print("[OK] container_code カラム追加完了")

        # 既存データに容器コードを設定
        print("既存データに容器コードを設定中...")
        cursor.execute("UPDATE container_capacity SET container_code = 'AMI' WHERE name LIKE '%アミ%'")
        cursor.execute("UPDATE container_capacity SET container_code = 'HB37' WHERE name LIKE '%HB-37%' OR name LIKE '%HB37%'")
        cursor.execute("UPDATE container_capacity SET container_code = 'TP392' WHERE name LIKE '%TP392%'")
        cursor.execute("UPDATE container_capacity SET container_code = 'TP331' WHERE name LIKE '%TP331%'")
        cursor.execute("UPDATE container_capacity SET container_code = 'POLI' WHERE name LIKE '%ポリ%' AND container_code IS NULL")

        conn.commit()
        print("[OK] 容器コード設定完了")

        # 確認
        cursor.execute("SELECT id, name, container_code FROM container_capacity")
        results = cursor.fetchall()
        print("\n=== 容器一覧 ===")
        for row in results:
            print(f"ID: {row[0]}, 名前: {row[1]}, コード: {row[2]}")

    except pymysql.err.OperationalError as e:
        if "Duplicate column name" in str(e):
            print("[WARN] container_code カラムは既に存在します")
        else:
            raise
    finally:
        conn.close()

if __name__ == "__main__":
    main()
