# SQL スクリプト集

このディレクトリには、データベース初期化・ストアドプロシージャ定義などのSQLスクリプトが格納されています。

## 📄 ファイル一覧

### 1. init_schema.sql

**目的**: メインデータベーススキーマ定義
**対象DB**: kubota_db / tiera_db
**実行タイミング**: 初回セットアップ時

**内容**:

- 全テーブル定義
- インデックス定義
- 外部キー制約
- デフォルトデータ

**実行方法**:

```bash
# Docker環境の場合（自動実行）
docker-compose up

# 手動実行の場合
mysql -u root -p < sql/init_schema.sql
```

---

### 2. kubota_stored_procedures.sql

**目的**: 久保田様データベース用ストアドプロシージャ
**対象DB**: kubota_db
**実行タイミング**: DB初期化後

**定義されているストアドプロシージャ**:

#### (1) recompute_planned_progress_by_product（Kubota版）

- **機能**: 計画進捗残の再計算
- **パラメータ**:
  - `p_product_id` (INT): 製品ID
  - `p_start_date` (DATE): 開始日
  - `p_end_date` (DATE): 終了日
- **計算式**: `前日残 + (出荷実績 or 計画数) - 注文数`
- **更新対象**: `delivery_progress.planned_progress_quantity`

#### (2) recompute_shipped_remaining_by_product（Kubota版）

- **機能**: 出荷残の再計算
- **パラメータ**:
  - `p_product_id` (INT): 製品ID
  - `p_start_date` (DATE): 開始日
  - `p_end_date` (DATE): 終了日
- **計算式**: `前日残 + 出荷実績 - 注文数`
- **更新対象**: `delivery_progress.shipped_remaining_quantity`

**実行方法**:

```sql
USE kubota_db;
SOURCE sql/kubota_stored_procedures.sql;

-- 使用例
CALL recompute_planned_progress_by_product(1, '2025-10-01', '2025-10-31');
CALL recompute_shipped_remaining_by_product(1, '2025-10-01', '2025-10-31');
```

---

### 3. tiera_stored_procedures.sql

**目的**: ティエラ様データベース用ストアドプロシージャ
**対象DB**: tiera_db
**実行タイミング**: DB初期化後

**定義されているストアドプロシージャ**:

#### (1) recompute_planned_progress_by_product（Tiera版）

- 久保田様版と同一のロジック

#### (2) recompute_shipped_remaining_by_product（Tiera版）

- 久保田様版と同一のロジック

**実行方法**:

```sql
USE tiera_db;
SOURCE sql/tiera_stored_procedures.sql;

-- 使用例
CALL recompute_planned_progress_by_product(1, '2025-10-01', '2025-10-31');
CALL recompute_shipped_remaining_by_product(1, '2025-10-01', '2025-10-31');
```

---

### 4. copy_schema_kubota_to_tiera_auto.sql

**目的**: 久保田DBのスキーマをティエラDBにコピー（自動生成版）
**対象DB**: kubota_db → tiera_db
**実行タイミング**: 新規顧客DB追加時

**処理内容**:

1. `tiera_db` データベースを作成
2. `kubota_db` の全テーブル構造をコピー
3. インデックス・外部キーを複製

**実行方法**:

```bash
mysql -u root -p < sql/copy_schema_kubota_to_tiera_auto.sql
```

**注意事項**:

- データはコピーされません（構造のみ）
- 既存の `tiera_db` は削除されます（DROP DATABASE）
- このスクリプトは `generate_copy_schema_script.py` により自動生成されました

---

### 5. create_product_groups.sql

**目的**: 製品グループマスタデータの作成
**対象DB**: kubota_db / tiera_db
**実行タイミング**: 初回セットアップ時

**処理内容**:

- 製品グループテーブルへのサンプルデータ挿入
- 製品と製品グループの紐付け

**実行方法**:

```sql
USE kubota_db;
SOURCE sql/create_product_groups.sql;
```

---

## 🔄 実行順序

初回セットアップ時の推奨実行順序：

```text
1. init_schema.sql           # スキーマ定義
2. kubota_stored_procedures.sql  # 久保田様ストアドプロシージャ
3. tiera_stored_procedures.sql   # ティエラ様ストアドプロシージャ
4. create_product_groups.sql     # マスタデータ（オプション）
```

新規顧客追加時：

```text
1. copy_schema_kubota_to_tiera_auto.sql  # スキーマコピー
2. (新顧客名)_stored_procedures.sql      # 顧客用ストアドプロシージャ
```

---

## 🛠️ メンテナンス

### スキーマ変更時の手順

1. `init_schema.sql` を編集
2. マイグレーションスクリプトを作成（`migrations/` ディレクトリ）
3. 既存データベースに対してマイグレーション実行
4. 必要に応じて `copy_schema_kubota_to_tiera_auto.sql` を再生成

   ```bash
   python generate_copy_schema_script.py
   ```

### ストアドプロシージャ変更時の手順

1. 該当する `*_stored_procedures.sql` を編集
2. データベースに対して再実行

   ```sql
   SOURCE sql/kubota_stored_procedures.sql;
   ```

---

## ⚠️ 注意事項

1. **バックアップ**: SQLスクリプト実行前は必ずデータベースをバックアップしてください
2. **本番環境**: 本番環境での実行は慎重に行ってください
3. **トランザクション**: 大規模なデータ変更時は、トランザクションを使用してください
4. **権限**: 実行には適切なデータベース権限が必要です
5. **文字コード**: すべてのスクリプトはUTF-8エンコーディングで保存されています

---

## 📚 関連ドキュメント

- [README_DOCKER.md](../docs/README_DOCKER.md) - Docker環境でのDB初期化
- [CUSTOMER_SWITCHING_GUIDE.md](../docs/CUSTOMER_SWITCHING_GUIDE.md) - 顧客別DB切り替え
- [README.md](../README.md) - プロジェクト全体のファイル構造
