#!/bin/bash
set -e

echo "=== データベース初期化を開始 ==="

# kubota_db にテーブルを作成（init_schema.sqlが存在する場合）
if [ -f /tmp/init_schema.sql ]; then
    echo "kubota_db にテーブルを作成中..."
    mysql --default-character-set=utf8mb4 -u root -p"${MYSQL_ROOT_PASSWORD}" kubota_db < /tmp/init_schema.sql
    echo "✅ kubota_db のテーブル作成完了"
else
    echo "⚠️  init_schema.sql が見つかりません（テーブルは空のまま）"
fi

# tiera_db データベースを作成
echo "tiera_db データベースを作成中..."
mysql -u root -p"${MYSQL_ROOT_PASSWORD}" -e "CREATE DATABASE IF NOT EXISTS tiera_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# kubota_dbのテーブル構造をtiera_dbにコピー
if [ -f /tmp/init_schema.sql ]; then
    echo "tiera_db にテーブルをコピー中..."
    # kubota_db を tiera_db に置換してインポート
    sed 's/USE kubota_db;/USE tiera_db;/g' /tmp/init_schema.sql | mysql --default-character-set=utf8mb4 -u root -p"${MYSQL_ROOT_PASSWORD}"
    echo "✅ tiera_db のテーブル作成完了"
fi

echo "=== 初期化完了: kubota_db, tiera_db ==="
