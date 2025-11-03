# Docker セットアップガイド

このプロジェクトを Docker で実行するためのガイドです。

## 前提条件

- Docker Desktop for Windows がインストールされていること
- WSL 2 が有効化されていること

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
