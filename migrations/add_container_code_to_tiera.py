#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""tiera_db の容器テーブルに容器コードカラムを追加"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql

def main():
    # tiera_db に直接接続
    conn = pymysql.connect(
        host=os.environ.get('TIERA_DB_HOST', 'mysql'),
        user=os.environ.get('TIERA_DB_USER', 'root'),
        password=os.environ.get('TIERA_DB_PASSWORD', 'rootpassword'),
        database=os.environ.get('TIERA_DB_NAME', 'tiera_db'),
        port=int(os.environ.get('TIERA_DB_PORT', 3306)),
        charset='utf8mb4'
    )

    cursor = conn.cursor()

    try:
        # container_code カラムを追加
        print("tiera_db: 容器コードカラムを追加中...")
        cursor.execute("""
            ALTER TABLE container_capacity
            ADD COLUMN container_code VARCHAR(20) NULL COMMENT '容器コード' AFTER name
        """)
        print("[OK] container_code カラム追加完了")

        # 既存データに容器コードを設定（容器名から推測）
        print("既存データに容器コードを設定中...")
        updates = [
            ("UPDATE container_capacity SET container_code = 'S90' WHERE name = 'S90'", "S90"),
            ("UPDATE container_capacity SET container_code = '19-6' WHERE name = '19-6'", "19-6"),
            ("UPDATE container_capacity SET container_code = 'SUS' WHERE name = 'SUS'", "SUS"),
            ("UPDATE container_capacity SET container_code = 'F2N' WHERE name = 'F2N'", "F2N"),
            ("UPDATE container_capacity SET container_code = '6ENSUS' WHERE name = '6ENSUS'", "6ENSUS"),
            ("UPDATE container_capacity SET container_code = '17U-5T' WHERE name = '17U-5T'", "17U-5T"),
            ("UPDATE container_capacity SET container_code = '19-6T' WHERE name = '19-6T'", "19-6T"),
            ("UPDATE container_capacity SET container_code = '6T' WHERE name = '6T'", "6T"),
            ("UPDATE container_capacity SET container_code = '7T7A' WHERE name = '7T7A'", "7T7A"),
            ("UPDATE container_capacity SET container_code = '7T7B' WHERE name = '7T7B'", "7T7B"),
            ("UPDATE container_capacity SET container_code = '7T5E' WHERE name = '7T5E'", "7T5E"),
            ("UPDATE container_capacity SET container_code = '7T5F' WHERE name = '7T5F'", "7T5F"),
            ("UPDATE container_capacity SET container_code = '19-6ENT' WHERE name = '19-6ENT'", "19-6ENT"),
            ("UPDATE container_capacity SET container_code = '7T5A' WHERE name = '7T5A'", "7T5A"),
        ]

        for sql, code in updates:
            cursor.execute(sql)
            print(f"  - {code} 設定")

        conn.commit()
        print("[OK] 容器コード設定完了")

        # 確認
        cursor.execute("SELECT id, name, container_code FROM container_capacity ORDER BY id")
        results = cursor.fetchall()
        print("\n=== tiera_db 容器一覧 ===")
        for row in results:
            print(f"ID: {row[0]}, 名前: {row[1]}, コード: {row[2]}")

    except pymysql.err.OperationalError as e:
        if "Duplicate column name" in str(e):
            print("[WARN] container_code カラムは既に存在します")
            # 確認
            cursor.execute("SELECT id, name, container_code FROM container_capacity ORDER BY id")
            results = cursor.fetchall()
            print("\n=== tiera_db 容器一覧 (既存) ===")
            for row in results:
                print(f"ID: {row[0]}, 名前: {row[1]}, コード: {row[2]}")
        else:
            raise
    finally:
        conn.close()

if __name__ == "__main__":
    main()
