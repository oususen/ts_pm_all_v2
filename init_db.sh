#!/bin/bash
set -e

# tiera_db データベースを作成
mysql -u root -p"${MYSQL_ROOT_PASSWORD}" -e "CREATE DATABASE IF NOT EXISTS tiera_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

echo "Databases initialized: kubota_db, tiera_db"
