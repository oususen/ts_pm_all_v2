# Docker セットアップガイド

このプロジェクトを Docker で実行するためのガイドです。

## 前提条件

- Docker Desktop for Windows がインストールされていること
- WSL 2 が有効化されていること

### 重要：MySQLのインストールは不要です

Dockerを使用する場合、ホストPC（他のPC）に**MySQLをインストールする必要はありません**。
docker-compose.ymlに定義されたMySQLコンテナが自動的に起動します。

必要なのは：

- ✅ Docker Desktop のみ
- ❌ MySQL（不要）
- ❌ Python（不要）
- ❌ その他の依存関係（不要）

## セットアップ手順

### 1. 環境変数ファイルの作成

`.env.example` をコピーして `.env` を作成：

```bash
copy .env.example .env
```

必要に応じて `.env` 内の設定を編集してください。

### 2. データベースパスワードの設定

Windows のシステム環境変数を設定：

```powershell
$env:PRIMARY_DB_PASSWORD="your_secure_password_here"
```

または、`.env` ファイルに直接パスワードを設定することもできます（非推奨）。

### 3. Docker コンテナの起動

**開発環境（コード変更を反映、やや遅い）:**

```bash
docker-compose up -d
```

**本番環境（高速、コード変更は反映されない）:**

```bash
docker-compose -f docker-compose.prod.yml up -d
```

初回起動時は、イメージのビルドに数分かかる場合があります。

**パフォーマンス改善のため、本番用設定（docker-compose.prod.yml）の使用を推奨します。**

### 4. アプリケーションへのアクセス

ブラウザで以下の URL を開きます：

```text
http://localhost:8501
```

## Docker MySQL の詳細説明

### MySQLのユーザーIDとパスワード

#### 設定場所

MySQLの認証情報は `.env` ファイルと `docker-compose.yml` で管理されています。

**.envファイルの設定：**

```env
# データベースのrootパスワード
PRIMARY_DB_PASSWORD=your_secure_password

# アプリケーション接続用
DEV_DB_USER=root
DEV_DB_PASSWORD=your_secure_password
```

**docker-compose.ymlでの使用：**

```yaml
mysql:
  environment:
    MYSQL_ROOT_PASSWORD: ${PRIMARY_DB_PASSWORD:-rootpassword}
    # デフォルトは "rootpassword"（.envに設定がない場合）

app:
  environment:
    DEV_DB_USER: root
    DEV_DB_PASSWORD: ${PRIMARY_DB_PASSWORD:-rootpassword}
    DEV_DB_HOST: mysql  # コンテナ名で接続
```

#### ユーザー情報まとめ

| 項目 | 値 | 説明 |
|------|-----|------|
| ユーザー名 | `root` | MySQL管理者アカウント |
| パスワード | `.env`の`PRIMARY_DB_PASSWORD` | デフォルト: `rootpassword` |
| ホスト名（コンテナ内） | `mysql` | docker-composeのサービス名 |
| ホスト名（ホストから） | `localhost` | ポート3306でマッピング |
| ポート | `3306` | MySQLの標準ポート |

#### セキュリティのベストプラクティス

```bash
# 本番環境では必ず強力なパスワードに変更
PRIMARY_DB_PASSWORD=MyS3cur3P@ssw0rd!2024

# パスワードの推奨条件：
# - 12文字以上
# - 大文字・小文字・数字・記号を含む
# - 推測されにくい文字列
```

### データの保存場所

#### 1. Dockerボリューム（永続化ストレージ）

データは**Dockerボリューム**に保存され、コンテナを削除してもデータは残ります。

```yaml
# docker-compose.yml
volumes:
  mysql_data:
    driver: local

services:
  mysql:
    volumes:
      - mysql_data:/var/lib/mysql  # ←ここにデータが保存
```

#### データの実際の保存場所

**Windowsの場合：**

```text
\\wsl$\docker-desktop-data\data\docker\volumes\ts_pm_all_mysql_data\_data

または

C:\Users\<ユーザー名>\AppData\Local\Docker\wsl\data\ext4.vhdx
（仮想ディスクイメージ内）
```

#### データの確認方法

```bash
# ボリュームの一覧表示
docker volume ls

# ボリュームの詳細情報
docker volume inspect ts_pm_all_mysql_data

# 出力例：
# {
#     "Name": "ts_pm_all_mysql_data",
#     "Mountpoint": "/var/lib/docker/volumes/ts_pm_all_mysql_data/_data",
#     "Driver": "local",
#     ...
# }
```

#### データの永続性

| 操作 | データへの影響 |
|------|---------------|
| `docker-compose down` | ✅ **データは保持される** |
| `docker-compose down -v` | ❌ **データも削除される** |
| `docker-compose restart` | ✅ **データは保持される** |
| コンテナ再ビルド | ✅ **データは保持される** |
| Dockerのアンインストール | ❌ **データも削除される** |

### データ操作の方法

#### 方法1: MySQLコマンドライン（推奨）

**基本的な接続方法：**

```bash
# MySQLコンテナに接続
docker exec -it ts_pm_mysql mysql -u root -p

# パスワード入力後、MySQLプロンプトが表示される
# mysql>
```

**よく使うSQL操作：**

```sql
-- データベース一覧
SHOW DATABASES;

-- データベースの選択
USE kubota_db;

-- テーブル一覧
SHOW TABLES;

-- テーブル構造の確認
DESCRIBE products;

-- データの確認
SELECT * FROM products LIMIT 10;

-- データの件数確認
SELECT COUNT(*) FROM products;
SELECT COUNT(*) FROM delivery_progress;

-- 特定のデータ検索
SELECT * FROM products WHERE product_code LIKE '%A%';

-- データの挿入
INSERT INTO products (product_code, product_name) VALUES ('TEST001', 'テスト製品');

-- データの更新
UPDATE products SET product_name = '新しい名前' WHERE product_code = 'TEST001';

-- データの削除
DELETE FROM products WHERE product_code = 'TEST001';

-- 終了
EXIT;
```

#### 方法2: SQLファイルの実行

```bash
# SQLファイルを実行
docker exec -i ts_pm_mysql mysql -u root -p kubota_db < my_script.sql

# 複数のコマンドを一度に実行
docker exec -i ts_pm_mysql mysql -u root -p <<EOF
USE kubota_db;
SELECT COUNT(*) FROM products;
SELECT COUNT(*) FROM delivery_progress;
EXIT;
EOF
```

#### 方法3: GUIツールでの接続

**MySQL Workbench や DBeaver などのGUIツールを使用：**

接続情報：

- **ホスト名**: `localhost`
- **ポート**: `3306`
- **ユーザー名**: `root`
- **パスワード**: `.env`の`PRIMARY_DB_PASSWORD`
- **データベース**: `kubota_db` または `tiera_db`

**接続手順（MySQL Workbench）：**

1. 「New Connection」をクリック
2. Connection Name: `Docker MySQL`
3. Hostname: `localhost`
4. Port: `3306`
5. Username: `root`
6. Password: 「Store in Keychain」をクリックしてパスワード入力
7. 「Test Connection」で接続確認
8. 「OK」をクリック

#### 方法4: Pythonスクリプトから操作

**アプリケーションコンテナ内で実行：**

```bash
# アプリコンテナに入る
docker exec -it ts_pm_app bash

# Pythonスクリプト実行
python << EOF
from repository.database_manager import CustomerDatabaseManager

db = CustomerDatabaseManager()
db.switch_customer('kubota')

# クエリ実行
result = db.execute_query("SELECT COUNT(*) as cnt FROM products")
print(f"製品数: {result[0]['cnt']}")
EOF
```

#### データバックアップのベストプラクティス

```bash
# 定期バックアップの例（export_data.batを自動実行）

# Windowsタスクスケジューラで毎日実行
# 1. タスクスケジューラを開く
# 2. 「基本タスクの作成」
# 3. トリガー: 毎日 AM 2:00
# 4. 操作: D:\ts_pm_all\export_data.bat
```

### データ操作の注意事項

⚠️ **重要な警告：**

1. **本番データの変更前に必ずバックアップ**

   ```bash
   # バックアップを取る
   docker exec ts_pm_mysql mysqldump -u root -p --all-databases > backup_before_change.sql
   ```

2. **DELETE/UPDATE文は必ずWHERE句を確認**

   ```sql
   -- 危険！全データ削除
   DELETE FROM products;

   -- 安全：条件付き削除
   DELETE FROM products WHERE product_code = 'OLD001';
   ```

3. **テスト環境で先に試す**

   ```bash
   # 開発用コンテナを別に起動してテスト
   docker-compose -f docker-compose.yml up -d
   ```

4. **大量データの操作はトランザクションを使用**

   ```sql
   START TRANSACTION;
   UPDATE products SET status = 'active';
   -- 確認してから
   COMMIT;  -- または ROLLBACK;
   ```

## データの移行（他のPCへのデータ転送）

### このPCのデータを他のPCに移行する手順

#### ステップ1: このPC（データ元）でデータをエクスポート

```bash
# 全データベースをダンプファイルにエクスポート
docker exec ts_pm_mysql mysqldump -u root -p --all-databases > mysql_backup.sql

# パスワードを求められたら、.env の PRIMARY_DB_PASSWORD を入力
```

または、特定のデータベースのみエクスポート：

```bash
# 久保田様のデータベースのみ
docker exec ts_pm_mysql mysqldump -u root -p kubota_db > kubota_db_backup.sql

# ティエラ様のデータベースのみ
docker exec ts_pm_mysql mysqldump -u root -p tiera_db > tiera_db_backup.sql
```

#### ステップ2: ダンプファイルを他のPCにコピー

- USBメモリ、ネットワーク共有、メールなどで `mysql_backup.sql` を他のPCに転送

#### ステップ3: 他のPC（データ先）でDockerコンテナを起動

```bash
# 他のPCで最初にコンテナを起動
docker-compose -f docker-compose.prod.yml up -d
```

#### ステップ4: 他のPCでデータをインポート

```bash
# ダンプファイルがあるディレクトリで実行
docker exec -i ts_pm_mysql mysql -u root -p < mysql_backup.sql

# パスワードを求められたら、.env の PRIMARY_DB_PASSWORD を入力
```

#### ステップ5: データの確認

```bash
# MySQLに接続してデータベースを確認
docker exec -it ts_pm_mysql mysql -u root -p

# MySQL内で実行
SHOW DATABASES;
USE kubota_db;
SHOW TABLES;
SELECT COUNT(*) FROM products;
EXIT;
```

### 簡単な移行スクリプト（推奨）

プロジェクトに便利なスクリプトファイルが含まれています：

- `export_data.bat` - データエクスポート用（このPCで実行）
- `import_data.bat` - データインポート用（他のPCで実行）

#### 使い方

**このPCでの操作：**

1. `export_data.bat` をダブルクリック
2. パスワードを入力（.env の PRIMARY_DB_PASSWORD）
3. 生成された `mysql_backup_YYYYMMDD.sql` を他のPCにコピー

**他のPCでの操作：**

1. プロジェクトフォルダに `mysql_backup_YYYYMMDD.sql` をコピー
2. `docker-compose -f docker-compose.prod.yml up -d` を実行
3. `import_data.bat` をダブルクリック
4. ファイル名を入力（例: `mysql_backup_20250103.sql`）
5. パスワードを入力（.env の PRIMARY_DB_PASSWORD）

## 便利なコマンド

### コンテナの状態確認

```bash
docker-compose ps
```

### ログの確認

```bash
# アプリのログ
docker-compose logs -f app

# データベースのログ
docker-compose logs -f mysql
```

### コンテナの停止

```bash
docker-compose down
```

### コンテナとデータの完全削除

```bash
docker-compose down -v
```

### データベースへの直接接続

```bash
docker exec -it ts_pm_mysql mysql -u root -p
```

### コンテナ内でのコマンド実行

```bash
# アプリコンテナ内でシェルを起動
docker exec -it ts_pm_app bash
```

## トラブルシューティング

### ポートが既に使用されている

ポート 8501 または 3306 が既に使用されている場合、`docker-compose.yml` の `ports` 設定を変更してください：

```yaml
ports:
  - "8502:8501"  # 左側のポート番号を変更
```

### データベース接続エラー

1. MySQL コンテナが起動しているか確認：

   ```bash
   docker-compose ps
   ```

2. データベースのヘルスチェック：

   ```bash
   docker-compose logs mysql
   ```

### イメージの再ビルド

依存関係を変更した場合：

```bash
# 開発環境
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# 本番環境（推奨）
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

### streamlit が見つからないエラー

エラーメッセージ：`streamlit: command not found` または `ModuleNotFoundError: No module named 'streamlit'`

**原因**:

- Dockerfile の `pywin32` 除外処理が正しく動作していない
- 古いDockerイメージキャッシュを使用している

**解決策**:

```bash
# キャッシュなしで完全再ビルド
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# または個別にビルド
docker build --no-cache -t ts_pm_app .
```

## Dockerfileの重要な設定

### Windows専用パッケージの除外

このプロジェクトでは Windows 専用パッケージ（`pywin32`）を含む `requirements.txt` を使用していますが、Linux コンテナでは不要です。

Dockerfile では以下のように `pywin32` を除外してインストールしています：

```dockerfile
# pywin32 を除外して依存関係をインストール
# sedを使用してpywin32を含む行をコメントアウト
RUN sed '/pywin32/s/^/#/' requirements.txt > requirements_docker.txt && \
    pip install --no-cache-dir -r requirements_docker.txt && \
    rm requirements_docker.txt
```

この処理により、`streamlit` を含む全てのLinux対応パッケージが正しくインストールされます。

## パフォーマンス最適化

### 開発環境 vs 本番環境

このプロジェクトには2つのdocker-compose設定があります：

| 設定ファイル | 用途 | 速度 | ホットリロード |
|------------|------|------|--------------|
| `docker-compose.yml` | 開発環境 | 遅い | ✓ 有効 |
| `docker-compose.prod.yml` | 本番・実行環境 | **高速** | ✗ 無効 |

### なぜ開発環境は遅いのか？

`docker-compose.yml` では、コード変更を即座に反映するために全てのファイルをボリュームマウントしています（66行目: `- .:/app`）。

WindowsとLinuxコンテナ間のファイル共有は、I/Oパフォーマンスに大きなオーバーヘッドが発生します。これが遅延の主な原因です。

### パフォーマンス改善方法

推奨：本番用設定を使用**

```bash
# 本番用で起動（高速）
docker-compose -f docker-compose.prod.yml up -d

# コードを変更する必要がない場合は、本番用設定を使用してください：

```bash
# 本番用で起動（高速）
docker-compose -f docker-compose.prod.yml up -d --build
```

本番用設定の特徴：**

- ✓ ボリュームマウントなし（ファイルはイメージに焼き込み）

- ✓ Streamlitのファイル監視無効化
- ✓ MySQLのパフォーマンス最適化
- ✓ リソース制限の明示（CPU: 2コア、メモリ: 2GB）

**注意：** コードを変更した場合は、イメージを再ビルドする必要があります。

```bash
# コード変更後の再ビルド
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build
```

## 開発時の注意事項

- コードの変更は自動的にコンテナに反映されます（ホットリロード）
- `requirements.txt` を変更した場合は、イメージの再ビルドが必要です
- データベースのデータは Docker ボリュームに永続化されます

## 本番環境での使用

本番環境で使用する場合：

1. `.env` の `APP_ENV` を `production` に変更
2. 強力なデータベースパスワードを設定
3. `docker-compose.yml` のボリュームマウントを無効化（セキュリティ向上）
4. リバースプロキシ（Nginx など）の設定を追加
