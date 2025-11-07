# -*- coding: utf-8 -*-
"""修正後の4t5t分割ロジックをテスト"""
from repository.database_manager import DatabaseManager
from config_all import build_customer_db_config
from services.shipping_order_service import ShippingOrderService
from datetime import date

# Tiera DBに接続
tiera_config = build_customer_db_config('tiera')
print(f'接続先: {tiera_config.database}@{tiera_config.host}')

# 一時的にDatabaseManagerを作成
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

db_url = f"mysql+pymysql://{tiera_config.user}:{tiera_config.password}@{tiera_config.host}:{tiera_config.port}/{tiera_config.database}?charset=utf8mb4"
engine = create_engine(db_url, echo=False, future=True)
SessionLocal = scoped_session(sessionmaker(bind=engine, autocommit=False, autoflush=False))

# 一時的なDatabaseManagerクラスを作成
class TempDatabaseManager:
    def __init__(self, session_local):
        self.SessionLocal = session_local
        self.engine = engine

    def get_session(self):
        return self.SessionLocal()

    def close(self):
        self.SessionLocal.remove()
        self.engine.dispose()

db_manager = TempDatabaseManager(SessionLocal)

# ShippingOrderServiceを使用
service = ShippingOrderService(db_manager)

# 11/7のデータを取得
target_date = date(2025, 11, 7)
shipping_data = service.get_shipping_data_by_date(target_date, 'tiera')

print('\n' + '=' * 100)
print(f'出荷日: {shipping_data["date"]}')
print('=' * 100)

# 1便目のデータを分析
trip1 = shipping_data['trip1']
trip4 = shipping_data['trip4']

if trip1:
    print('\n【1便目（06:00）】')
    print('-' * 100)
    trip1_total_qty = 0
    trip1_total_containers = 0

    for item in trip1:
        capacity = item.get('capacity', 1)
        qty = item['order_quantity']
        containers = -(-qty // capacity)
        trip1_total_qty += qty
        trip1_total_containers += containers
        print(f'{item["product_code"]:15s} | {qty:3d}個 | 入り数:{capacity:2d} | {containers:2d}容器')

    print('-' * 100)
    print(f'合計: {trip1_total_qty}個 → {trip1_total_containers}容器')

if trip4:
    print('\n【4便目（13:00）】')
    print('-' * 100)
    trip4_total_qty = 0
    trip4_total_containers = 0

    for item in trip4:
        capacity = item.get('capacity', 1)
        qty = item['order_quantity']
        containers = -(-qty // capacity)
        trip4_total_qty += qty
        trip4_total_containers += containers
        print(f'{item["product_code"]:15s} | {qty:3d}個 | 入り数:{capacity:2d} | {containers:2d}容器')

    print('-' * 100)
    print(f'合計: {trip4_total_qty}個 → {trip4_total_containers}容器')

# 総合計
print('\n' + '=' * 100)
print('【総合計】')
print('=' * 100)
print(f'1便目: {trip1_total_qty if trip1 else 0}個 → {trip1_total_containers if trip1 else 0}容器')
print(f'4便目: {trip4_total_qty if trip4 else 0}個 → {trip4_total_containers if trip4 else 0}容器')
print(f'合計: {trip1_total_qty + trip4_total_qty if trip1 and trip4 else 0}個 → {trip1_total_containers + trip4_total_containers if trip1 and trip4 else 0}容器')

# 検証
print('\n' + '=' * 100)
print('【検証結果】')
print('=' * 100)

if trip1 and trip4:
    if trip1_total_containers == trip4_total_containers:
        print('✅ 成功: 1便目と4便目の容器数が均等です')
    elif abs(trip1_total_containers - trip4_total_containers) <= 1:
        print('✅ 成功: 1便目と4便目の容器数がほぼ均等です（差1容器以内）')
    else:
        print(f'❌ 失敗: 容器数の差が大きいです（差: {abs(trip1_total_containers - trip4_total_containers)}容器）')
else:
    print('データがありません')

db_manager.close()
