# order_number列拡張マイグレーション手順書

## 概要
`order_number`列を`VARCHAR(50)`から`VARCHAR(255)`に拡張するマイグレーションです。

## 背景
ティエラ確定CSVのインポート時、複数の注文番号を`+`で連結して保存する際に、文字列が50文字を超えてエラーが発生していました。

例:
```
42163779+42163780+42163781+42163782+42163783+42163784+42163785+42163786+42163787
```
この文字列は81文字あり、VARCHAR(50)には収まりません。

## 対象テーブル
1. `production_instructions_detail`
2. `delivery_progress`

## 実行手順

### 本番環境での実行

**重要**: このマイグレーションは**tiera_db**と**kubota_db**の両方に適用する必要があります。

1. **MySQLにログイン**
   ```bash
   mysql -u root -p
   ```

2. **TIERAデータベースに適用**
   ```sql
   USE tiera_db;
   source d:/ts_pm_all_v2/migrations/extend_order_number_column.sql
   ```

3. **KUBOTAデータベースに適用**
   ```sql
   USE kubota_db;
   source d:/ts_pm_all_v2/migrations/extend_order_number_column.sql
   ```

4. **結果を確認**
   以下のような出力が表示されれば成功:
   ```
   +--------------+--------------+------+-----+---------+-------+
   | Field        | Type         | Null | Key | Default | Extra |
   +--------------+--------------+------+-----+---------+-------+
   | order_number | varchar(255) | YES  |     | NULL    |       |
   +--------------+--------------+------+-----+---------+-------+

   +--------------------------------------------------------------------+
   | status                                                             |
   +--------------------------------------------------------------------+
   | マイグレーション完了: order_number列をVARCHAR(255)に拡張しました |
   +--------------------------------------------------------------------+
   ```

## ロールバック手順

万が一問題が発生した場合、以下のSQLで元に戻せます（データが50文字以内の場合のみ）:

```sql
-- production_instructions_detailテーブル
ALTER TABLE production_instructions_detail
MODIFY COLUMN order_number VARCHAR(50) DEFAULT NULL;

-- delivery_progressテーブル
ALTER TABLE delivery_progress
MODIFY COLUMN order_number VARCHAR(50) DEFAULT NULL;
```

## 注意事項
- このマイグレーションはデータ損失を引き起こしません（VARCHAR(50) → VARCHAR(255)への拡張のため）
- 実行中はテーブルがロックされる可能性がありますが、通常は数秒で完了します
- 大量のデータがある場合は、事前にバックアップを取得することを推奨します

## テスト

マイグレーション後、ティエラ確定CSVのインポートを実行して、エラーが発生しないことを確認してください。
