# 本番PC データベース反映手順

## 概要
開発PCで実施したデータベース変更を本番PC（Docker環境）に反映する手順です。

## 変更内容
1. **usersテーブル**: SMTP設定列の追加（smtp_host, smtp_port, smtp_user, smtp_password）
2. **contactsテーブル**: 連絡先マスタの新規作成
3. **初期データ**: 枚方集荷依頼の連絡先を登録

---

## 反映手順

### 方法1: Adminer経由でSQLスクリプトを実行（推奨）

#### 1. SQLスクリプトの準備
開発PCの以下のファイルを使用します:
```
d:\ts_pm_all_v2\migrations\add_smtp_and_contacts.sql
```

#### 2. Adminerにアクセス
1. ブラウザで本番PCのAdminerにアクセス
   - URL: `http://本番PCのIPアドレス:ポート番号`

2. ログイン情報を入力
   - **System**: MySQL
   - **Server**: データベースコンテナ名（例: `db`）
   - **Username**: データベースユーザー名
   - **Password**: データベースパスワード
   - **Database**: `kubota_db`

#### 3. SQLスクリプトの実行
1. Adminerの左メニューから「**SQL command**」をクリック
2. `add_smtp_and_contacts.sql` の内容をコピー＆ペースト
3. 「**Execute**」ボタンをクリック

#### 4. 実行結果の確認
以下のメッセージが表示されれば成功:
```
✓ usersテーブルにSMTP設定列を追加しました
✓ contactsテーブルを作成しました
✓ 初期連絡先データを投入しました
✓ マイグレーション完了
```

#### 5. データの確認
Adminerで以下を確認:

**usersテーブルの確認:**
```sql
SELECT COLUMN_NAME, DATA_TYPE, COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'kubota_db'
  AND TABLE_NAME = 'users'
  AND COLUMN_NAME LIKE 'smtp%';
```

**contactsテーブルの確認:**
```sql
SELECT * FROM contacts;
```

---

### 方法2: Docker経由でコマンド実行

#### 1. SQLファイルを本番PCに転送
開発PCから本番PCにファイルをコピー:
```bash
# 開発PCから本番PCへSCP等でコピー
scp d:\ts_pm_all_v2\migrations\add_smtp_and_contacts.sql user@本番PC:/tmp/
```

#### 2. Dockerコンテナ内でSQL実行
本番PCで以下のコマンドを実行:
```bash
# MySQLコンテナ名を確認
docker ps

# SQLファイルを実行
docker exec -i <MySQLコンテナ名> mysql -u<ユーザー名> -p<パスワード> kubota_db < /tmp/add_smtp_and_contacts.sql
```

---

## トラブルシューティング

### エラー: "Column 'smtp_host' already exists"
すでに列が存在している場合のエラーです。SQLスクリプトは `IF NOT EXISTS` を使用しているため、通常は発生しません。

**対処法:**
- 無視して続行（既存の列がある場合はスキップされます）

### エラー: "Table 'contacts' already exists"
すでにテーブルが存在している場合のエラーです。

**対処法:**
```sql
-- 既存のcontactsテーブルを確認
SELECT * FROM contacts;

-- 問題なければそのまま使用
-- 削除して再作成する場合:
DROP TABLE contacts;
-- その後、add_smtp_and_contacts.sql を再実行
```

### 初期データが重複する場合
SQLスクリプトは重複チェックを行うため、通常は重複しません。

**確認方法:**
```sql
SELECT * FROM contacts WHERE email = 'kyouto03@otomo-logi.co.jp';
```

---

## 反映後の設定

### 1. SMTP設定の登録
1. アプリケーションにログイン
2. 「**ユーザー管理**」→「**ユーザー一覧**」タブを選択
3. 管理者ユーザーを編集
4. SMTP設定セクションに以下を入力:
   - **SMTPホスト**: `smtp.gmail.com`（Gmailの場合）
   - **SMTPポート**: `587`
   - **SMTPユーザー名**: 送信用メールアドレス
   - **SMTPパスワード**: アプリパスワード（Googleアカウントで生成）

**Googleアプリパスワードの生成方法:**
1. Googleアカウント → セキュリティ
2. 2段階認証を有効化
3. 「アプリパスワード」で新しいパスワードを生成
4. 生成されたパスワードを使用

### 2. 連絡先の追加（必要に応じて）
1. 「**ユーザー管理**」→「**連絡先管理**」タブ
2. 連絡先種別を選択
3. 新規連絡先を登録

---

## ロールバック手順（元に戻す場合）

万が一、変更を元に戻す必要がある場合:

```sql
-- usersテーブルからSMTP設定列を削除
ALTER TABLE users
DROP COLUMN smtp_host,
DROP COLUMN smtp_port,
DROP COLUMN smtp_user,
DROP COLUMN smtp_password;

-- contactsテーブルを削除
DROP TABLE contacts;
```

---

## 注意事項

1. **バックアップ推奨**: 本番反映前にデータベースのバックアップを取得してください
   ```bash
   docker exec <MySQLコンテナ名> mysqldump -u<ユーザー名> -p<パスワード> kubota_db > backup_$(date +%Y%m%d).sql
   ```

2. **営業時間外に実施**: 可能であれば、システム使用が少ない時間帯に実施してください

3. **テスト環境での事前確認**: 可能であれば、本番と同等のテスト環境で事前に確認してください

4. **SMTPパスワードのセキュリティ**: SMTPパスワードは平文で保存されます。将来的に暗号化の実装を検討してください

---

## 変更履歴

| 日付 | 作成者 | 変更内容 |
|------|--------|----------|
| 2025-11-27 | Claude | 初版作成 |
