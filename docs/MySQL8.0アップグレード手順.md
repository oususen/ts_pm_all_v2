# MySQL 8.0 アップグレード手順（本番PC Docker環境）

## 概要
本番PC（Docker環境）のMySQLを5.7から8.0にアップグレードする手順です。

## 重要な注意事項

⚠️ **現時点ではアップグレードは必須ではありません**
- 作成済みのマイグレーションスクリプト（`add_smtp_and_contacts.sql`）はMySQL 5.7/8.0両対応です
- 現在の5.7環境でも問題なく動作します

## アップグレードのメリット

MySQL 8.0では以下の機能が追加されています：
- `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` 構文のサポート
- より高速なパフォーマンス
- 改善されたセキュリティ機能
- ウィンドウ関数のサポート

---

## アップグレード手順

### 事前準備

#### 1. 現在の環境確認
```bash
# MySQLコンテナ名を確認
docker ps | grep mysql

# 現在のMySQLバージョン確認
docker exec <MySQLコンテナ名> mysql --version
```

#### 2. **必須：完全バックアップの取得**
```bash
# データベース全体をバックアップ
docker exec <MySQLコンテナ名> mysqldump -u<ユーザー名> -p<パスワード> --all-databases > backup_before_upgrade_$(date +%Y%m%d_%H%M%S).sql

# バックアップファイルのサイズ確認（0バイトでないことを確認）
ls -lh backup_*.sql
```

#### 3. docker-compose.ymlの確認
本番PCの `docker-compose.yml` ファイルを確認します：
```yaml
services:
  db:
    image: mysql:5.7  # ← この部分を変更します
    # ... その他の設定
```

---

### アップグレード実施

#### 方法1: docker-compose.ymlを編集してアップグレード（推奨）

**手順:**

1. **docker-compose.ymlを編集**
   ```bash
   # 本番PCで docker-compose.yml を開く
   nano docker-compose.yml  # または vi, vim など
   ```

2. **MySQLイメージバージョンを変更**
   ```yaml
   services:
     db:
       image: mysql:8.0  # 5.7 → 8.0 に変更
       # ... その他の設定はそのまま
   ```

3. **コンテナを停止**
   ```bash
   docker-compose down
   ```

4. **MySQL 8.0イメージをダウンロード**
   ```bash
   docker pull mysql:8.0
   ```

5. **コンテナを起動（自動アップグレード）**
   ```bash
   docker-compose up -d
   ```

6. **アップグレードログの確認**
   ```bash
   docker logs <MySQLコンテナ名> -f

   # 以下のようなメッセージが表示されればOK:
   # "MySQL Upgrade is complete"
   # "ready for connections. Version: '8.0.x'"
   ```

7. **接続確認**
   ```bash
   # MySQLに接続できるか確認
   docker exec -it <MySQLコンテナ名> mysql -u<ユーザー名> -p

   # バージョン確認
   SELECT VERSION();
   ```

8. **Adminerで動作確認**
   - ブラウザでAdminerにアクセス
   - データベース接続を確認
   - テーブル一覧が表示されるか確認

---

#### 方法2: データをエクスポート→新規MySQL 8.0コンテナ作成（より安全）

**手順:**

1. **全データをバックアップ**
   ```bash
   docker exec <MySQLコンテナ名> mysqldump -u<ユーザー名> -p<パスワード> --all-databases > all_databases_backup.sql
   ```

2. **現在のコンテナを停止・削除**
   ```bash
   docker-compose down
   # ボリュームも削除する場合（データが完全に消えます！バックアップ必須）
   docker-compose down -v
   ```

3. **docker-compose.ymlを編集**
   ```yaml
   services:
     db:
       image: mysql:8.0
       # ... その他の設定
   ```

4. **新しいMySQL 8.0コンテナを起動**
   ```bash
   docker-compose up -d
   ```

5. **データをリストア**
   ```bash
   docker exec -i <MySQLコンテナ名> mysql -u<ユーザー名> -p<パスワード> < all_databases_backup.sql
   ```

---

## アップグレード後の確認事項

### 1. バージョン確認
```sql
SELECT VERSION();
-- 結果: 8.0.x となっていればOK
```

### 2. データの整合性確認
```sql
USE kubota_db;

-- テーブル一覧
SHOW TABLES;

-- ユーザーテーブルの確認
SELECT COUNT(*) FROM users;

-- 連絡先テーブルの確認（マイグレーション後）
SELECT COUNT(*) FROM contacts;
```

### 3. アプリケーションの動作確認
- Streamlitアプリケーションを起動
- 各ページが正常に動作するか確認
- ユーザー管理、枚方集荷依頼書生成などの機能をテスト

---

## トラブルシューティング

### エラー: "Authentication plugin 'caching_sha2_password' cannot be loaded"

MySQL 8.0ではデフォルトの認証プラグインが変更されています。

**対処法:**
```sql
-- MySQL 8.0コンテナ内で実行
ALTER USER '<ユーザー名>'@'%' IDENTIFIED WITH mysql_native_password BY '<パスワード>';
FLUSH PRIVILEGES;
```

または、docker-compose.ymlで認証プラグインを指定：
```yaml
services:
  db:
    image: mysql:8.0
    command: --default-authentication-plugin=mysql_native_password
```

### エラー: "Table upgrade required"

**対処法:**
```bash
# MySQLアップグレードユーティリティを実行
docker exec <MySQLコンテナ名> mysql_upgrade -u<ユーザー名> -p<パスワード>

# コンテナを再起動
docker restart <MySQLコンテナ名>
```

### データが見つからない場合

**確認:**
```bash
# ボリュームが正しくマウントされているか確認
docker inspect <MySQLコンテナ名> | grep -A 10 Mounts
```

**対処法:**
バックアップからリストアする：
```bash
docker exec -i <MySQLコンテナ名> mysql -u<ユーザー名> -p<パスワード> < backup_before_upgrade_YYYYMMDD_HHMMSS.sql
```

---

## ロールバック手順（MySQL 5.7に戻す）

アップグレードに問題があった場合：

1. **コンテナを停止**
   ```bash
   docker-compose down
   ```

2. **docker-compose.ymlを5.7に戻す**
   ```yaml
   services:
     db:
       image: mysql:5.7
   ```

3. **データボリュームを削除（必要な場合）**
   ```bash
   docker volume rm <ボリューム名>
   ```

4. **コンテナを再起動**
   ```bash
   docker-compose up -d
   ```

5. **バックアップからリストア**
   ```bash
   docker exec -i <MySQLコンテナ名> mysql -u<ユーザー名> -p<パスワード> < backup_before_upgrade_YYYYMMDD_HHMMSS.sql
   ```

---

## 推奨事項

### アップグレードを実施する場合
- ✅ 営業時間外に実施
- ✅ 完全バックアップを複数箇所に保存
- ✅ テスト環境で事前に検証
- ✅ ロールバック手順を事前に確認

### アップグレードを見送る場合
- ✅ 現在のMySQL 5.7環境で問題なく動作
- ✅ 既存のマイグレーションスクリプトは5.7/8.0両対応
- ✅ 必要になったタイミングでアップグレード可能

---

## まとめ

**現時点での推奨:**
- **MySQL 5.7のまま運用継続**を推奨します
- マイグレーションスクリプトは既に5.7/8.0両対応済み
- アップグレードはリスクを伴うため、明確な理由がない限り不要

**アップグレードを検討すべきケース:**
- MySQL 5.7のサポート終了が近づいた時
- MySQL 8.0固有の機能が必要になった時
- パフォーマンス改善が必要な時

---

## 参考情報

- [MySQL 8.0 Upgrade Guide](https://dev.mysql.com/doc/refman/8.0/en/upgrading.html)
- [Docker Hub - MySQL Official Images](https://hub.docker.com/_/mysql)
- MySQL 5.7サポート終了日: 2023年10月（延長サポートあり）

---

## 変更履歴

| 日付 | 作成者 | 変更内容 |
|------|--------|----------|
| 2025-11-27 | Claude | 初版作成 |
