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

```bash
docker-compose up -d
```

初回起動時は、イメージのビルドに数分かかる場合があります。

### 4. アプリケーションへのアクセス

ブラウザで以下の URL を開きます：

```
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
docker-compose down
docker-compose build --no-cache
docker-compose up -d
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
