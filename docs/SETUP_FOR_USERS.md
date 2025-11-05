# 生産計画アプリ セットアップガイド（使用者向け）

このガイドは、開発者以外の方が生産計画アプリを自分のPCで使用するための手順です。

## 必要な環境

- Windows 10/11 (64bit)
- 管理者権限
- インターネット接続

## セットアップ手順

### ステップ1: Git のインストール

1. [Git for Windows](https://git-scm.com/download/win) にアクセス
2. 「Download for Windows」をクリック
3. ダウンロードしたファイルを実行
4. すべてデフォルト設定のまま「Next」で進めてインストール

### ステップ2: Docker Desktop のインストール

1. [Docker Desktop](https://www.docker.com/products/docker-desktop/) にアクセス
2. 「Download for Windows」をクリック
3. ダウンロードしたファイルを実行
4. インストール時の重要な設定：
   - ✅ 「Use WSL 2 instead of Hyper-V」にチェック
   - ☐ 「Allow Windows Containers」はチェック不要
5. インストール完了後、**PCを再起動**
6. Docker Desktop を起動して、サインインまたはスキップ

### ステップ3: アプリをダウンロード

1. PowerShell を開く（Windowsキー + X → 「Windows PowerShell」）

2. 以下のコマンドを1行ずつ実行：

```powershell
# 保存先フォルダに移動（例：Dドライブ）
cd D:\

# アプリをダウンロード
git clone https://github.com/oususen/ts_pm_all.git

# アプリフォルダに移動
cd ts_pm_all
```

### ステップ4: 設定ファイルを作成

PowerShell で以下を実行：

```powershell
# 設定ファイルのテンプレートをコピー
copy .env.example .env
```

### ステップ5: アプリを起動

PowerShell で以下を実行：

```powershell
# データベースのパスワードを設定（好きなパスワードに変更してください）
$env:PRIMARY_DB_PASSWORD="MySecurePassword123"

# アプリを起動
docker-compose up -d
```

初回起動時は、必要なファイルをダウンロードするため **5～10分** かかります。

### ステップ6: ブラウザでアクセス

ブラウザ（Chrome、Edge など）を開いて、以下のアドレスにアクセス：

```
http://localhost:8501
```

## 重要な補足

### データの保存について

このアプリは **MySQL データベース**を使用してデータを保存します。

Docker を使用する場合：

- ✅ **Windows に MySQL を手動でインストールする必要はありません**
- ✅ Docker が自動的に MySQL コンテナを起動します
- ✅ データは Docker の専用領域（ボリューム）に安全に保存されます

つまり、**Docker さえインストールすれば、MySQL も Python も自動的に用意されます。**

**データの保存場所**:

- Docker が管理する `mysql_data` というボリュームに保存
- `docker-compose down` でコンテナを停止しても、**データは消えません** ✅
- `docker-compose down -v` を実行すると、データも削除されるので**注意してください** ⚠️

## 日常的な使い方

### アプリを起動する

PowerShell で以下を実行：

```powershell
# アプリフォルダに移動
cd D:\ts_pm_all

# アプリを起動
docker-compose up -d
```

ブラウザで `http://localhost:8501` にアクセス

### アプリを停止する

PowerShell で以下を実行：

```powershell
# アプリフォルダに移動
cd D:\ts_pm_all

# アプリを停止
docker-compose down
```

### アプリを最新版に更新する

PowerShell で以下を実行：

```powershell
# アプリフォルダに移動
cd D:\ts_pm_all

# いったん停止
docker-compose down

# 最新版を取得
git pull

# 再起動
docker-compose up -d
```

## トラブルシューティング

### 「docker」コマンドが見つからない

**原因**: Docker Desktop が起動していない

**解決方法**:

1. スタートメニューから「Docker Desktop」を起動
2. タスクバーに Docker のアイコンが表示されるまで待つ
3. 再度コマンドを実行

### ポート 8501 が既に使用されている

**原因**: 他のアプリが同じポートを使用している

**解決方法**:

1. `docker-compose.yml` ファイルを開く
2. 以下の行を探す：

   ```yaml
   ports:
     - "8501:8501"
   ```

3. 左側の数字を変更（例：`"8502:8501"`）
4. 保存して再起動
5. ブラウザで `http://localhost:8502` にアクセス

### データベース接続エラー

**原因**: MySQL コンテナが起動していない

**解決方法**:

```powershell
# 状態を確認
docker-compose ps

# 完全に停止してから再起動
docker-compose down
docker-compose up -d
```

### アプリが真っ白

**原因**: ブラウザのキャッシュの問題

**解決方法**:

1. ブラウザで `Ctrl + F5` を押す（強制リロード）
2. それでもダメな場合、ブラウザのキャッシュをクリア

## サポート

問題が解決しない場合は、開発担当者に以下の情報と共にお問い合わせください：

```powershell
# システム情報を取得
docker --version
docker-compose --version
```

---

**初回セットアップお疲れ様でした！**
