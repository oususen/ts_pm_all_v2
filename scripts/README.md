# ユーティリティスクリプト

このディレクトリには、データベース管理やメンテナンス用のユーティリティスクリプトが格納されています。

## 📄 スクリプト一覧

### 1. generate_copy_schema_script.py

**目的**: kubota_dbのスキーマをtiera_dbにコピーするSQLスクリプトを自動生成

**機能**:

- kubota_dbの全テーブル構造を取得

- tiera_db用のCREATE TABLE文を自動生成
- `../sql/copy_schema_kubota_to_tiera_auto.sql` に出力

**使用タイミング**:

- スキーマ変更後、他の顧客DBに反映する前
- 新規顧客DB追加時

**実行方法**:

```bash
# scriptsディレクトリから実行
cd scripts
python generate_copy_schema_script.py

# またはルートディレクトリから
python scripts/generate_copy_schema_script.py
```

**前提条件**:

- kubota_dbが存在し、テーブルが作成済み
- .envファイルに正しいDB接続情報が設定済み

**出力**:

- `../sql/copy_schema_kubota_to_tiera_auto.sql`

---

### 2. apply_product_groups.py

**目的**: 製品グループマスタデータをデータベースに適用

**機能**:

- `../sql/create_product_groups.sql` を読み込み

- kubota_db と tiera_db の両方に製品グループテーブルを作成
- 製品グループデータを挿入
- 製品グループ別の製品数を確認

**使用タイミング**:

- 初回セットアップ時

- 製品グループマスタの初期化が必要なとき

**実行方法**:

```bash
# scriptsディレクトリから実行
cd scripts
python apply_product_groups.py

# またはルートディレクトリから
python scripts/apply_product_groups.py
```

**前提条件**:

- kubota_db と tiera_db が存在
- products テーブルが作成済み
- `../sql/create_product_groups.sql` が存在

**実行結果**:

- 製品グループテーブル作成
- 製品グループデータ挿入
- 統計情報表示

---

### 3. export_db_structure.py

**目的**: データベース構造をエクスポート・ドキュメント化

**機能**:

- データベースの全テーブル構造を取得

- テーブル定義、カラム情報、インデックス情報を出力
- ドキュメント生成やスキーマ比較に使用

**使用タイミング**:

- データベース構造のドキュメント作成時
- スキーマ変更前の状態保存
- 顧客間のスキーマ差分確認

**実行方法**:

```bash
# scriptsディレクトリから実行
cd scripts
python export_db_structure.py

# またはルートディレクトリから
python scripts/export_db_structure.py
```

**前提条件**:

- 対象データベースが存在
- .envファイルに正しいDB接続情報が設定済み

---

## 🔧 共通の前提条件

### 環境変数

すべてのスクリプトは `.env` ファイルから以下の環境変数を読み込みます：

```env
# データベース接続情報
DEV_DB_HOST=localhost
DEV_DB_USER=root
DEV_DB_PORT=3306
PRIMARY_DB_PASSWORD=your_password

# 顧客別DB名
KUBOTA_DB_NAME=kubota_db
TIERA_DB_NAME=tiera_db
```

### Pythonパッケージ

以下のパッケージが必要です（`requirements.txt` に含まれています）：

---
pymysql

python-dotenv

---

## 📝 実行順序の推奨

### 初回セットアップ時

1. **スキーマ作成**

   ```bash
   # Docker環境の場合
   docker-compose up

   # 手動の場合
   mysql -u root -p < sql/init_schema.sql
   ```

2. **製品グループ適用**

   ```bash
   python scripts/apply_product_groups.py
   ```

3. **スキーマコピースクリプト生成（新規顧客追加時）**

   ```bash
   python scripts/generate_copy_schema_script.py
   ```

### スキーマ変更時

1. **構造エクスポート（変更前）**

   ```bash
   python scripts/export_db_structure.py > before_change.txt
   ```

2. **スキーマ変更を適用**

   ```sql
   -- マイグレーションスクリプト実行
   ```

3. **構造エクスポート（変更後）**

   ```bash
   python scripts/export_db_structure.py > after_change.txt
   ```

4. **スキーマコピースクリプト再生成**

   ```bash
   python scripts/generate_copy_schema_script.py
   ```

---

## ⚠️ 注意事項

1. **本番環境での実行**
   - 本番環境で実行する前に、必ずバックアップを取得してください
   - テスト環境で事前に動作確認してください

2. **データベース接続**
   - すべてのスクリプトは `.env` ファイルの設定を使用します
   - 本番環境の認証情報は厳重に管理してください

3. **エラーハンドリング**
   - エラーが発生した場合、詳細なトレースバックが表示されます
   - エラーメッセージを確認し、原因を特定してください

4. **文字エンコーディング**
   - すべてのスクリプトはUTF-8エンコーディングを使用します
   - Windows環境でのコンソール出力に対応しています

---

## 📚 関連ドキュメント

- [README.md](../README.md) - プロジェクト全体のファイル構造
- [sql/README.md](../sql/README.md) - SQLスクリプト詳細説明
- [docs/README_DOCKER.md](../docs/README_DOCKER.md) - Docker環境構築
- [docs/CUSTOMER_SWITCHING_GUIDE.md](../docs/CUSTOMER_SWITCHING_GUIDE.md) - 顧客別DB切り替え

---

## 🐛 トラブルシューティング

### エラー: "ModuleNotFoundError: No module named 'pymysql'"

**解決方法**:

```bash
pip install -r requirements.txt
```

### エラー: "Access denied for user 'root'@'localhost'"

**解決方法**:

- `.env` ファイルの `PRIMARY_DB_PASSWORD` を確認
- データベースサーバーが起動しているか確認

### エラー: "Can't connect to MySQL server on 'localhost'"

**解決方法**:

```bash
# Docker環境の場合
docker-compose up -d mysql

# ローカルMySQLの場合
# MySQLサービスを起動
```

### エラー: "FileNotFoundError: [Errno 2] No such file or directory: '../sql/...'"

**解決方法**:

- スクリプトを正しいディレクトリから実行しているか確認
- `scripts/` ディレクトリまたはルートディレクトリから実行してください
