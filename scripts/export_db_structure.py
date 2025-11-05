#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
情報スキーマから現在のデータベース構造を取得してCSVに出力するユーティリティ。
出力先: D:/共通ファイル
"""

import csv
import os
from pathlib import Path
from typing import Sequence

import pymysql


def get_connection():
    """環境変数で指定されたデータベースに接続する。"""
    host = os.getenv("DEV_DB_HOST", "localhost")
    user = os.getenv("DEV_DB_USER", "root")
    password = os.getenv("PRIMARY_DB_PASSWORD") or os.getenv("DEV_DB_PASSWORD", "")
    database = os.getenv("DEV_DB_NAME", "kubota_db")
    port = int(os.getenv("DEV_DB_PORT", "3306"))

    return pymysql.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        port=port,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def write_csv(path: Path, fieldnames: Sequence[str], rows: Sequence[dict]) -> None:
    """辞書のシーケンスをCSVへ書き出す。Excelでの閲覧を想定してUTF-8 BOM付き。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def export_structure():
    output_dir = Path(r"D:\共通ファイル")
    db_name = os.getenv("DEV_DB_NAME", "kubota_db")

    queries = (
        (
            "テーブルごとのカラム情報.csv",
            (
                "SELECT "
                "c.TABLE_NAME AS table_name, "
                "c.COLUMN_NAME AS column_name, "
                "c.COLUMN_TYPE AS column_type, "
                "c.IS_NULLABLE AS is_nullable, "
                "c.COLUMN_DEFAULT AS column_default, "
                "c.EXTRA AS extra, "
                "c.COLUMN_COMMENT AS column_comment "
                "FROM information_schema.COLUMNS AS c "
                "WHERE c.TABLE_SCHEMA = %s "
                "ORDER BY c.TABLE_NAME, c.ORDINAL_POSITION"
            ),
            (
                "table_name",
                "column_name",
                "column_type",
                "is_nullable",
                "column_default",
                "extra",
                "column_comment",
            ),
        ),
        (
            "インデックス情報.csv",
            (
                "SELECT "
                "s.TABLE_NAME AS table_name, "
                "s.INDEX_NAME AS index_name, "
                "s.NON_UNIQUE AS non_unique, "
                "s.SEQ_IN_INDEX AS seq_in_index, "
                "s.COLUMN_NAME AS column_name, "
                "s.COLLATION AS collation, "
                "s.INDEX_TYPE AS index_type "
                "FROM information_schema.STATISTICS AS s "
                "WHERE s.TABLE_SCHEMA = %s "
                "ORDER BY s.TABLE_NAME, s.INDEX_NAME, s.SEQ_IN_INDEX"
            ),
            (
                "table_name",
                "index_name",
                "non_unique",
                "seq_in_index",
                "column_name",
                "collation",
                "index_type",
            ),
        ),
        (
            "外部キー.csv",
            (
                "SELECT "
                "rc.CONSTRAINT_NAME AS constraint_name, "
                "rc.TABLE_NAME AS table_name, "
                "kcu.COLUMN_NAME AS column_name, "
                "rc.REFERENCED_TABLE_NAME AS referenced_table, "
                "kcu.REFERENCED_COLUMN_NAME AS referenced_column, "
                "rc.UPDATE_RULE AS update_rule, "
                "rc.DELETE_RULE AS delete_rule "
                "FROM information_schema.REFERENTIAL_CONSTRAINTS AS rc "
                "JOIN information_schema.KEY_COLUMN_USAGE AS kcu "
                "  ON rc.CONSTRAINT_SCHEMA = kcu.CONSTRAINT_SCHEMA "
                " AND rc.TABLE_NAME = kcu.TABLE_NAME "
                " AND rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME "
                "WHERE rc.CONSTRAINT_SCHEMA = %s "
                "ORDER BY rc.TABLE_NAME, rc.CONSTRAINT_NAME, kcu.POSITION_IN_UNIQUE_CONSTRAINT"
            ),
            (
                "constraint_name",
                "table_name",
                "column_name",
                "referenced_table",
                "referenced_column",
                "update_rule",
                "delete_rule",
            ),
        ),
    )

    with get_connection() as conn:
        with conn.cursor() as cursor:
            for filename, query, fieldnames in queries:
                cursor.execute(query, (db_name,))
                rows = cursor.fetchall()
                write_csv(output_dir / filename, fieldnames, rows)


if __name__ == "__main__":
    export_structure()
