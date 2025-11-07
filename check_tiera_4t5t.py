# -*- coding: utf-8 -*-
"""TIERA_DBの4-5T容器製品を分析"""
import pandas as pd
from repository.database_manager import DatabaseManager
from config_all import build_customer_db_config
from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from datetime import date

# Tiera DBの設定を取得
tiera_config = build_customer_db_config('tiera')
print(f'接続先: {tiera_config.database}@{tiera_config.host}')

# Tiera DBに接続
db_url = f"mysql+pymysql://{tiera_config.user}:{tiera_config.password}@{tiera_config.host}:{tiera_config.port}/{tiera_config.database}?charset=utf8mb4"
engine = create_engine(db_url, echo=False, future=True)
SessionLocal = scoped_session(sessionmaker(bind=engine, autocommit=False, autoflush=False))
session = SessionLocal()

# CSVを読み込み
csv_df = pd.read_csv('11-07ORDER.CSV')
product_ids = csv_df['product_id'].unique().tolist()

print('\n' + '=' * 100)
print('STEP 1: container_capacityテーブルの確認')
print('=' * 100)

# 全容器を取得
query = text('SELECT id, name FROM container_capacity ORDER BY id')
result = session.execute(query)
containers = result.fetchall()

print('容器マスタ:')
for c in containers[:20]:
    print(f'  ID:{c.id:3d} | {c.name}')
if len(containers) > 20:
    print(f'  ... 他 {len(containers)-20}容器')

# 4-5Tを含む容器を検索
print('\n' + '=' * 100)
print('STEP 2: 「4-5T」を含む容器を検索')
print('=' * 100)

query = text("SELECT id, name FROM container_capacity WHERE name LIKE '%4-5T%'")
result = session.execute(query)
container_4t5t = result.fetchall()

if container_4t5t:
    for c in container_4t5t:
        print(f'見つかりました: ID:{c.id:3d} | {c.name}')
        container_id = c.id

        # この容器を使用する製品を取得
        query2 = text('''
            SELECT p.id, p.product_code, p.product_name, p.capacity
            FROM products p
            WHERE p.used_container_id = :container_id
            ORDER BY p.product_code
        ''')
        result2 = session.execute(query2, {'container_id': container_id})
        products = result2.fetchall()

        print(f'\n  この容器を使用する製品: {len(products)}個')
        for prod in products:
            print(f'    {prod.product_code:15s} | 入り数:{prod.capacity:2d} | {prod.product_name[:50]}')
else:
    print('「4-5T」を含む容器が見つかりません。')

# 11/7の4-5T製品の注文データ
print('\n' + '=' * 100)
print('STEP 3: 11/7の4-5T容器製品の注文データ分析')
print('=' * 100)

if container_4t5t:
    container_id = container_4t5t[0].id

    # 4-5T容器を使用する製品のIDリスト
    query_prod_ids = text('''
        SELECT id FROM products WHERE used_container_id = :container_id
    ''')
    result = session.execute(query_prod_ids, {'container_id': container_id})
    product_4t5t_ids = [row.id for row in result.fetchall()]

    # CSVから4-5T製品のみ抽出
    csv_4t5t = csv_df[csv_df['product_id'].isin(product_4t5t_ids)].copy()

    if len(csv_4t5t) > 0:
        print(f'11/7の4-5T容器製品: {len(csv_4t5t)}件')
        print('-' * 100)

        total_qty = 0
        total_containers = 0

        for idx, row in csv_4t5t.iterrows():
            # 製品情報を取得
            query_prod = text('SELECT product_code, capacity FROM products WHERE id = :prod_id')
            result_prod = session.execute(query_prod, {'prod_id': row['product_id']})
            prod_info = result_prod.fetchone()

            if prod_info:
                capacity = prod_info.capacity if prod_info.capacity else 1
                containers = -(-row['order_quantity'] // capacity)  # 切り上げ
                total_qty += row['order_quantity']
                total_containers += containers
                print(f'{prod_info.product_code:15s} | {row["order_quantity"]:3d}個 | 入り数:{capacity:2d} | {containers:2d}容器')

        print('-' * 100)
        print(f'合計: {total_qty}個 → {total_containers}容器')

        # 現在のロジック（個数で分割）
        print('\n' + '=' * 100)
        print('【現在のロジック】個数を半分に分割:')
        print('=' * 100)

        current_trip1_qty = total_qty // 2
        current_trip4_qty = total_qty - current_trip1_qty
        print(f'1便目: {current_trip1_qty}個')
        print(f'4便目: {current_trip4_qty}個')

        # 各製品ごとに容器数を計算
        trip1_containers = 0
        trip4_containers = 0

        print('\n製品ごとの分割:')
        for idx, row in csv_4t5t.iterrows():
            query_prod = text('SELECT product_code, capacity FROM products WHERE id = :prod_id')
            result_prod = session.execute(query_prod, {'prod_id': row['product_id']})
            prod_info = result_prod.fetchone()

            if prod_info:
                capacity = prod_info.capacity if prod_info.capacity else 1
                qty1 = row['order_quantity'] // 2
                qty4 = row['order_quantity'] - qty1
                cont1 = -(-qty1 // capacity)
                cont4 = -(-qty4 // capacity)
                trip1_containers += cont1
                trip4_containers += cont4
                print(f'  {prod_info.product_code:15s} | 合計{row["order_quantity"]:2d}個 → 1便:{qty1:2d}個({cont1}容器) + 4便:{qty4:2d}個({cont4}容器)')

        print(f'\n合計容器数:')
        print(f'  1便目: {trip1_containers}容器')
        print(f'  4便目: {trip4_containers}容器')

        # 正しいロジック（容器数を半分に分割）
        print('\n' + '=' * 100)
        print('【正しいロジック】容器数を半分に分割:')
        print('=' * 100)
        target_trip1_containers = total_containers // 2
        target_trip4_containers = total_containers - target_trip1_containers
        print(f'1便目: {target_trip1_containers}容器（目標）')
        print(f'4便目: {target_trip4_containers}容器（目標）')
    else:
        print('11/7には4-5T容器の製品注文がありません。')

session.close()
