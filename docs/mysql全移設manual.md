# MySQLデータベース移行マニュアル
## Windows PC → Docker MySQLコンテナ

---

## 概要
このマニュアルでは、Windows PCのMySQLデータベースを、他のPCで動作しているDockerのMySQLコンテナに移行する手順を説明します。

---

## 前提条件

### エクスポート元（Windows PC）
- MySQL Server 8.0がインストール済み
- mysqldumpコマンドが使用可能
- PowerShellでの操作

### インポート先（他のPC）
- Dockerがインストール済み
- MySQLコンテナが稼働中
- Adminerまたはmysqlコマンドが使用可能

---

## 手順

### 1. エクスポート元での作業（Windows PC）

#### 1-1. PowerShellを起動
管理者権限は不要です。通常のPowerShellで実行できます。

#### 1-2. PowerShellの文字エンコーディングを設定
```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

> **重要**: この設定により、日本語などのマルチバイト文字が正しくエクスポートされます。

#### 1-3. データベースをエクスポート
```powershell
mysqldump -u root -p --databases kubota_db tiera_db --default-character-set=utf8mb4 --result-file=backup_utf8.sql
```

**パラメータ説明**:
- `-u root`: rootユーザーで接続
- `-p`: パスワード入力プロンプトを表示
- `--databases kubota_db tiera_db`: エクスポートするデータベース名（複数指定可能）
- `--default-character-set=utf8mb4`: UTF-8文字セットを使用
- `--result-file=backup_utf8.sql`: 出力ファイル名

> **注意**: `--result-file`オプションを使用することで、PowerShellのリダイレクト（`>`）による文字化けを防ぎます。

#### 1-4. パスワードを入力
```
Enter password: ********************
```

#### 1-5. エクスポート完了の確認
```powershell
# ファイルサイズを確認
Get-Item backup_utf8.sql | Select-Object Name, Length

# ファイルの先頭を確認（文字化けチェック）
Get-Content backup_utf8.sql -Head 20
```

---

### 2. バックアップファイルの転送

#### 方法1: SCPでネットワーク転送
```powershell
scp backup_utf8.sql ユーザー名@転送先IPアドレス:/home/ユーザー名/
```

#### 方法2: USBメモリ・共有フォルダ経由
1. `backup_utf8.sql`をUSBメモリにコピー
2. 転送先PCにUSBメモリを接続
3. ファイルを適切な場所にコピー

#### 方法3: クラウドストレージ経由
- Google Drive、Dropbox、OneDriveなどを使用

---

### 3. インポート先での作業（Docker MySQLコンテナ）

#### 3-1. MySQLコンテナ名を確認
```bash
docker ps | grep mysql
```

コンテナ名（例: `mysql_container`）をメモしておきます。

#### 3-2. バックアップファイルをコンテナにコピー
```bash
docker cp backup_utf8.sql mysql_container:/tmp/backup.sql
```

> **注意**: `mysql_container`は実際のコンテナ名に置き換えてください。

#### 3-3. データベースをインポート

**方法A: コマンドラインから直接インポート（推奨）**
```bash
docker exec -i mysql_container mysql -u root -p --default-character-set=utf8mb4 < /tmp/backup.sql
```

パスワードを入力すると、インポートが開始されます。

**方法B: コンテナに入ってからインポート**
```bash
# コンテナに入る
docker exec -it mysql_container bash

# コンテナ内でインポート実行
mysql -u root -p --default-character-set=utf8mb4 < /tmp/backup.sql

# 完了後、コンテナから抜ける
exit
```

---

### 4. インポート確認

#### 4-1. データベースが作成されたか確認
```bash
docker exec -it mysql_container mysql -u root -p -e "SHOW DATABASES;"
```

`kubota_db`と`tiera_db`が表示されればOKです。

#### 4-2. テーブルとデータの確認
```bash
# kubota_dbのテーブル一覧
docker exec -it mysql_container mysql -u root -p -e "USE kubota_db; SHOW TABLES;"

# tiera_dbのテーブル一覧
docker exec -it mysql_container mysql -u root -p -e "USE tiera_db; SHOW TABLES;"
```

#### 4-3. Adminerで確認（オプション）
1. ブラウザでAdminerにアクセス（例: `http://localhost:8080`）
2. 以下の情報でログイン:
   - サーバー: `mysql_container`（またはlocalhost）
   - ユーザー名: `root`
   - パスワード: （設定したパスワード）
   - データベース: `kubota_db`または`tiera_db`
3. テーブル一覧とデータを目視確認
4. **文字化けがないか日本語データを確認**

---

## トラブルシューティング

### 問題1: 文字化けが発生する

**原因**: 文字エンコーディングの設定が正しくない

**解決策**:
1. エクスポート元の文字コード設定を確認
```powershell
mysql -u root -p -e "SHOW VARIABLES LIKE 'character%';"
```

2. PowerShellの設定を確認
```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

3. `--result-file`オプションを必ず使用する（`>`リダイレクトは使わない）

4. バイナリモードでエクスポート（最終手段）
```powershell
mysqldump -u root -p --databases kubota_db tiera_db --default-character-set=binary --hex-blob --single-transaction --result-file=backup_binary.sql
```

### 問題2: ファイルサイズが大きすぎてアップロードできない

**解決策**:
- データベースを個別にエクスポート
```powershell
mysqldump -u root -p --databases kubota_db --default-character-set=utf8mb4 --result-file=kubota_db.sql
mysqldump -u root -p --databases tiera_db --default-character-set=utf8mb4 --result-file=tiera_db.sql
```

### 問題3: コンテナ名が分からない

**確認方法**:
```bash
# 稼働中のコンテナ一覧
docker ps

# 停止中も含めたすべてのコンテナ
docker ps -a

# MySQLコンテナを検索
docker ps -a | grep mysql
```

### 問題4: インポート中にエラーが出る

**対処法**:
1. エラーメッセージを確認
2. データベースの権限を確認
```bash
docker exec -it mysql_container mysql -u root -p -e "SELECT user, host FROM mysql.user;"
```

3. ディスク容量を確認
```bash
docker exec -it mysql_container df -h
```

---

## 補足情報

### エクスポートオプションの詳細

- `--single-transaction`: InnoDB テーブルの一貫性のあるバックアップを作成
- `--routines`: ストアドプロシージャと関数を含める
- `--triggers`: トリガーを含める
- `--events`: イベントスケジューラのイベントを含める

**完全バックアップの例**:
```powershell
mysqldump -u root -p --databases kubota_db tiera_db --default-character-set=utf8mb4 --single-transaction --routines --triggers --events --result-file=full_backup.sql
```

### セキュリティに関する注意

- バックアップファイルには機密情報が含まれる可能性があります
- ファイル転送時は暗号化された方法（SCP、SFTP等）を使用してください
- 不要になったバックアップファイルは安全に削除してください
```bash
# コンテナ内の一時ファイルを削除
docker exec -it mysql_container rm /tmp/backup.sql
```

---

## チェックリスト

### エクスポート前
- [ ] エクスポート対象のデータベース名を確認
- [ ] MySQLのrootパスワードを準備
- [ ] 十分なディスク空き容量があることを確認

### エクスポート実行
- [ ] PowerShellの文字エンコーディングを設定
- [ ] `--result-file`オプションを使用してエクスポート
- [ ] エクスポートファイルのサイズを確認
- [ ] ファイルの内容を軽く確認（文字化けチェック）

### ファイル転送
- [ ] 安全な方法でファイルを転送
- [ ] 転送先でファイルが正しく受信されたことを確認

### インポート実行
- [ ] Dockerコンテナが稼働していることを確認
- [ ] コンテナ名を正しく指定
- [ ] `--default-character-set=utf8mb4`を指定してインポート

### インポート後確認
- [ ] データベースが作成されたことを確認
- [ ] テーブル一覧を確認
- [ ] サンプルデータを確認（特に日本語データ）
- [ ] 文字化けがないことを確認
- [ ] 不要な一時ファイルを削除

---

## よくある質問（FAQ）

### Q1: 複数のデータベースを一度にエクスポートできますか？
**A**: はい、`--databases`オプションの後にスペース区切りで複数指定できます。
```powershell
mysqldump -u root -p --databases db1 db2 db3 --default-character-set=utf8mb4 --result-file=multiple_dbs.sql
```

### Q2: すべてのデータベースをエクスポートしたい場合は？
**A**: `--all-databases`オプションを使用します。
```powershell
mysqldump -u root -p --all-databases --default-character-set=utf8mb4 --result-file=all_dbs.sql
```

### Q3: 特定のテーブルだけエクスポートできますか？
**A**: はい、データベース名の後にテーブル名を指定します。
```powershell
mysqldump -u root -p kubota_db table1 table2 --default-character-set=utf8mb4 --result-file=specific_tables.sql
```

### Q4: エクスポートにどれくらい時間がかかりますか？
**A**: データ量によります。目安として：
- 小規模（〜100MB）: 数秒〜数分
- 中規模（100MB〜1GB）: 数分〜数十分
- 大規模（1GB〜）: 数十分〜数時間

### Q5: インポート中にエラーが出た場合、やり直す必要がありますか？
**A**: はい、通常はやり直しが必要です。まず既存のデータベースを削除してから再インポートします。
```bash
docker exec -it mysql_container mysql -u root -p -e "DROP DATABASE IF EXISTS kubota_db; DROP DATABASE IF EXISTS tiera_db;"
```
その後、再度インポートを実行してください。

---

## 作成日時
2025年11月5日

## バージョン
1.0

## 作成者
移行作業実績に基づいて作成
