# -*- coding: utf-8 -*-
"""11-07のCSVに含まれる全製品の容器情報を確認"""
import pandas as pd
from repository.database_manager import DatabaseManager
from sqlalchemy import text

# CSVを読み込み
csv_df = pd.read_csv('11-07ORDER.CSV')

# データベース接続
db = DatabaseManager()
session = db.get_session()

# CSVに含まれるproduct_idのリストを取得
product_ids = csv_df['product_id'].unique().tolist()

# 全製品の容器情報を取得
query = text('''
    SELECT
        p.id,
        p.product_code,
        p.product_name,
        p.capacity,
        cc.name as container_name
    FROM products p
    LEFT JOIN container_capacity cc ON p.used_container_id = cc.id
    WHERE p.id IN :product_ids
    ORDER BY cc.name, p.product_code
''')

result = session.execute(query, {'product_ids': tuple(product_ids)})
rows = result.fetchall()

print('=' * 100)
print('11/7 CSVに含まれる全製品の容器情報:')
print('=' * 100)

# 容器タイプごとにグループ化
from collections import defaultdict
container_groups = defaultdict(list)

for row in rows:
    container_name = row.container_name or 'なし'
    container_groups[container_name].append(row)

for container_name in sorted(container_groups.keys()):
    products = container_groups[container_name]
    print(f'\n【{container_name}】({len(products)}製品)')
    print('-' * 100)
    for p in products[:10]:  # 最初の10製品のみ表示
        print(f'  ID:{p.id:3d} | {p.product_code:15s} | 入り数:{p.capacity if p.capacity else 0:2d} | {p.product_name[:40]}')
    if len(products) > 10:
        print(f'  ... 他 {len(products)-10}製品')

# 4-5Tまたは4t5tを含む容器を特定
print('\n' + '=' * 100)
print('4-5T または 4t5t を含む容器:')
print('=' * 100)
found = False
for container_name, products in container_groups.items():
    if '4-5T' in container_name or '4t5t' in container_name.lower():
        found = True
        print(f'\n【{container_name}】({len(products)}製品)')
        for p in products:
            # CSVから注文数量を取得
            order_qty = csv_df[csv_df['product_id'] == p.id]['order_quantity'].sum()
            containers = -(-order_qty // p.capacity) if p.capacity else 0
            print(f'  {p.product_code:15s} | {order_qty:3d}個 | 入り数:{p.capacity:2d} | {containers}容器')

if not found:
    print('4-5T容器の製品が見つかりませんでした。')
    print('\n容器名の一覧:')
    for name in sorted(container_groups.keys()):
        print(f'  - {name}')

session.close()
