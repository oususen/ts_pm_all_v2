# プロジェクトファイル構造説明

このドキュメントは、ts_pm_all_v2 プロジェクトの全ファイル・ディレクトリの目的を説明します。

## 📁 ディレクトリ構造

```text
ts_pm_all_v2/
├── domain/              # ドメイン層（ビジネスロジック）
├── repository/          # データアクセス層
├── services/            # サービス層（ビジネスロジック統合）
├── ui/                  # UIコンポーネント・ページ
├── migrations/          # データベースマイグレーションスクリプト
├── sql/                 # SQLスクリプト集
├── scripts/             # ユーティリティスクリプト
├── docs/                # プロジェクトドキュメント
├── output/              # 出力ファイル用ディレクトリ
├── venv/                # Python仮想環境
├── .git/                # Gitリポジトリ
├── .streamlit/          # Streamlit設定
└── .claude/             # Claude Code設定
```

---

## 📄 ルートディレクトリのファイル

### メインアプリケーション

| ファイル | 目的 |
|---------|------|
| `main.py` | Streamlitアプリケーションのエントリーポイント |
| `config_all.py` | 環境設定・データベース接続管理 |
| `__init__.py` | Pythonパッケージ初期化ファイル |

### Docker関連

| ファイル | 目的 |
|---------|------|
| `Dockerfile` | Dockerイメージビルド設定 |
| `docker-compose.yml` | 開発環境用Docker Compose設定 |
| `docker-compose.prod.yml` | 本番環境用Docker Compose設定 |
| `.dockerignore` | Dockerビルド時の除外ファイル設定 |
| `init_db.sh` | データベース初期化シェルスクリプト |

### 環境設定

| ファイル | 目的 |
|---------|------|
| `.env` | 環境変数（機密情報含む）※Gitには含めない |
| `.env.example` | 環境変数テンプレート |
| `requirements.txt` | Python依存パッケージリスト |
| `.gitignore` | Git除外ファイル設定 |

### データインポート・エクスポート

| ファイル | 目的 |
|---------|------|
| `import_data.bat` | データインポート用Windowsバッチファイル |
| `export_data.bat` | データエクスポート用Windowsバッチファイル |

### ルール定義ファイル

| ファイル | 目的 |
|---------|------|
| `基本ルール.txt` | 底面積ベース積載計算アルゴリズム説明 |
| `基本ルール_容器積載版.txt` | 容器本数ベース積載計算アルゴリズム説明 |

### 参考データ

| ファイル | 目的 |
|---------|------|
| `all_roles_permissions.json` | ロール・権限マスタデータ（参考） |
| `gyomu_permissions.json` | 配送管理者権限定義（参考） |

---

## 📚 ドキュメント

すべてのドキュメントは [docs/](docs/) ディレクトリに格納されています。

### クイックリンク

#### 技術ドキュメント（開発者・管理者向け）

| ドキュメント | 対象読者 | 内容 |
|---------|---------|------|
| [README_DOCKER.md](docs/README_DOCKER.md) | 開発者・管理者 | Docker構築・運用ガイド |
| [SETUP_GUIDE.md](docs/SETUP_GUIDE.md) | 開発者 | 開発環境セットアップ手順 |
| [CUSTOMER_SWITCHING_GUIDE.md](docs/CUSTOMER_SWITCHING_GUIDE.md) | 開発者 | 顧客別データベース切り替え実装ガイド |
| [USER_AUTH_README.md](docs/USER_AUTH_README.md) | 開発者 | ユーザー認証・権限管理システム説明 |
| [TIERA_IMPLEMENTATION_SUMMARY.md](docs/TIERA_IMPLEMENTATION_SUMMARY.md) | 開発者 | ティエラ様対応実装サマリー |

#### エンドユーザー向けドキュメント

| ドキュメント | 対象読者 | 内容 |
|---------|---------|------|
| [SETUP_FOR_USERS.md](docs/SETUP_FOR_USERS.md) | エンドユーザー | エンドユーザー向けセットアップ手順 |
| [GYOMU_USER_MANUAL.md](docs/GYOMU_USER_MANUAL.md) | 配送管理者 | 配送計画システム操作マニュアル |

詳細は [docs/README.md](docs/README.md) を参照してください。

---

## 🗄️ sql/ ディレクトリ

SQLスクリプト集。データベース初期化・ストアドプロシージャ定義など。

| ファイル | 目的 | 対象DB |
|---------|------|--------|
| `init_schema.sql` | メインデータベーススキーマ定義 | 全DB |
| `kubota_stored_procedures.sql` | 久保田様向けストアドプロシージャ2種（計画進捗／出荷残） | kubota_db |
| `tiera_stored_procedures.sql` | ティエラ様向けストアドプロシージャ2種（計画進捗／出荷残） | tiera_db |
| `copy_schema_kubota_to_tiera_auto.sql` | 久保田DBスキーマをティエラDBへコピー（自動生成） | kubota_db / tiera_db |
| `create_product_groups.sql` | 製品グループマスタデータ作成 | 全DB |

詳細は [sql/README.md](sql/README.md) を参照してください。

---

## 🔧 scripts/ ディレクトリ

データベース管理・メンテナンス用のユーティリティスクリプト。

| ファイル | 目的 | 実行タイミング |
|---------|------|---------------|
| `generate_copy_schema_script.py` | 久保田DBスキーマをティエラDBへコピーするSQLを生成 | スキーマ変更後など |
| `apply_product_groups.py` | 製品グループマスタデータをDBに適用 | 初回セットアップ時 |
| `export_db_structure.py` | データベース構造をエクスポート・ドキュメント化 | スキーマ変更前の状態保存時 |

**実行方法**:

```bash
# scriptsディレクトリから
cd scripts
python generate_copy_schema_script.py

# またはルートディレクトリから
python scripts/generate_copy_schema_script.py
```

詳細は [scripts/README.md](scripts/README.md) を参照してください。

---

## 🏗️ domain/ ディレクトリ

ドメイン駆動設計に基づくビジネスロジック層。

### domain/models/

ドメインモデル（エンティティ）

| ファイル | 目的 |
|---------|------|
| `base.py` | ベースモデル定義 |
| `product.py` | 製品モデル |
| `production.py` | 生産計画モデル |
| `transport.py` | 配送計画モデル |

### domain/calculators/

計算ロジック（アルゴリズム）

| ファイル | 目的 | 対象顧客 |
|---------|------|---------|
| `production_calculator.py` | 生産計画計算 | 共通 |
| `transport_planner.py` | 配送計画・積載計算（底面積ベース） | 久保田様 |
| `tiera_transport_planner.py` | 配送計画・積載計算（ティエラ様専用） | ティエラ様 |

### domain/validators/

バリデーションロジック

| ファイル | 目的 |
|---------|------|
| `loading_validator.py` | 積載計画バリデーション |

---

## 💾 repository/ ディレクトリ

データアクセス層（リポジトリパターン）。データベースCRUD操作を担当。

| ファイル | 目的 |
|---------|------|
| `database_manager.py` | データベース接続管理 |
| `calendar_repository.py` | カレンダーマスタのCRUD |
| `delivery_progress_repository.py` | 配送進捗データのCRUD |
| `loading_plan_repository.py` | 積載計画データのCRUD |
| `product_repository.py` | 製品マスタのCRUD |
| `production_repository.py` | 生産計画データのCRUD |
| `transport_repository.py` | 配送計画データのCRUD |

---

## 🔧 services/ ディレクトリ

サービス層（ビジネスロジック統合）。複数のリポジトリやドメインロジックを統合。

### 認証・権限管理

| ファイル | 目的 |
|---------|------|
| `auth_service.py` | ユーザー認証・権限チェック |

### データインポート

| ファイル | 目的 | 対象顧客 |
|---------|------|---------|
| `csv_import_service.py` | CSV内示データインポート | 久保田様 |
| `kubota_kakutei_csv_import_service.py` | CSV確定データインポート | 久保田様 |
| `tiera_csv_import_service.py` | CSV内示データインポート | ティエラ様 |
| `tiera_kakutei_csv_import_service.py` | CSV確定データインポート | ティエラ様 |
| `calendar_import_service.py` | カレンダーCSVインポート | 共通 |

### コアサービス

| ファイル | 目的 |
|---------|------|
| `production_service.py` | 生産計画管理 |
| `transport_service.py` | 配送計画管理（久保田様用） |
| `tiera_transport_service.py` | 配送計画管理（ティエラ様専用） |

### エクスポート・出力

| ファイル | 目的 |
|---------|------|
| `excel_export_service.py` | Excelエクスポート |
| `shipping_order_service.py` | 出荷指示書データ管理 |
| `shipping_pdf_generator.py` | 出荷指示書PDF生成 |

---

## 🎨 ui/ ディレクトリ

ユーザーインターフェース層（Streamlit）。

### ui/components/

再利用可能なUIコンポーネント

| ファイル | 目的 |
|---------|------|
| `charts.py` | グラフ・チャート描画 |
| `forms.py` | フォーム入力コンポーネント |
| `tables.py` | テーブル表示コンポーネント |

### ui/layouts/

レイアウトコンポーネント

| ファイル | 目的 |
|---------|------|
| `sidebar.py` | サイドバーナビゲーション |

### ui/pages/

画面（ページ）定義

| ファイル | 目的 | 対象顧客 |
|---------|------|---------|
| `login_page.py` | ログイン画面 | 共通 |
| `user_management_page.py` | ユーザー管理画面 | 共通 |
| `change_password_page.py` | パスワード変更画面 | 共通 |
| `dashboard_page.py` | ダッシュボード | 共通 |
| `product_page.py` | 製品マスタ管理 | 共通 |
| `product_group_page.py` | 製品グループ管理 | 共通 |
| `production_page.py` | 生産計画管理 | 共通 |
| `manufacturing_process_page.py` | 製造工程管理 | 共通 |
| `constraints_page.py` | 制約条件管理 | 共通 |
| `csv_import_page.py` | CSVインポート | 共通 |
| `transport_page.py` | 配送計画管理（久保田様用） | 久保田様 |
| `tiera_transport_page.py` | 配送計画管理（ティエラ様専用） | ティエラ様 |
| `delivery_progress_page.py` | 配送進捗管理 | 共通 |
| `shipping_order_page.py` | 出荷指示書管理（ティエラ様専用） | ティエラ様 |
| `calendar_page.py` | カレンダー管理 | 共通 |

---

## 🔄 migrations/ ディレクトリ

データベースマイグレーションスクリプト。スキーマ変更履歴。

| ファイル | 目的 |
|---------|------|
| `add_user_auth_tables.py` | ユーザー認証関連テーブル追加 |
| `add_tab_can_edit.py` | タブ編集権限カラム追加 |
| `add_planned_shipments_table.py` | 計画出荷テーブル追加 |

---

## 🎯 ファイルの重要度分類

### 🔴 絶対に変更・削除してはいけない

- `main.py` - アプリケーションエントリーポイント
- `config_all.py` - 環境設定
- `sql/init_schema.sql` - データベーススキーマ定義
- `domain/`, `repository/`, `services/`, `ui/` 配下の全ファイル
- `requirements.txt` - 依存パッケージ
- `.env` - 環境変数（機密情報）

### 🟡 慎重に扱うべき

- `Dockerfile`, `docker-compose.yml` - 本番環境で使用
- `sql/` 配下のストアドプロシージャ
- `migrations/` 配下のマイグレーションスクリプト
- 各種マニュアル（`.md`ファイル）

### 🟢 参考・補助的なファイル

- `基本ルール.txt`, `基本ルール_容器積載版.txt` - アルゴリズム説明
- `*.json` - 参考データ
- `export_db_structure.py`, `generate_copy_schema_script.py` - ユーティリティ

---

## 📝 補足説明

### 顧客別実装について

このシステムは複数顧客（久保田様・ティエラ様）に対応しており、一部のファイルは顧客別に分かれています：

- **久保田様専用**: `transport_planner.py`, `csv_import_service.py`, `transport_page.py`
- **ティエラ様専用**: `tiera_*` プレフィックスが付いたファイル
- **共通**: その他のファイル

### アーキテクチャ

プロジェクトはドメイン駆動設計（DDD）とレイヤードアーキテクチャに基づいています：

```text
UI層 (ui/)
    ↓
サービス層 (services/)
    ↓
ドメイン層 (domain/)
    ↓
データアクセス層 (repository/)
    ↓
データベース
```

各層は明確に責務が分離されており、保守性・拡張性が高い設計になっています。
