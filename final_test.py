# -*- coding: utf-8 -*-
"""最終テスト: 4t5t分割ロジックの検証"""
from repository.database_manager import DatabaseManager
from config_all import build_customer_db_config
from services.shipping_order_service import ShippingOrderService
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

# Tiera DBに接続
tiera_config = build_customer_db_config('tiera')
db_url = f"mysql+pymysql://{tiera_config.user}:{tiera_config.password}@{tiera_config.host}:{tiera_config.port}/{tiera_config.database}?charset=utf8mb4"
engine = create_engine(db_url, echo=False, future=True)
SessionLocal = scoped_session(sessionmaker(bind=engine, autocommit=False, autoflush=False))

class TempDatabaseManager:
    def __init__(self, session_local, eng):
        self.SessionLocal = session_local
        self.engine = eng
    def get_session(self):
        return self.SessionLocal()
    def close(self):
        self.SessionLocal.remove()
        self.engine.dispose()

db_manager = TempDatabaseManager(SessionLocal, engine)
service = ShippingOrderService(db_manager)

# 11/7のデータを取得
target_date = date(2025, 11, 7)
shipping_data = service.get_shipping_data_by_date(target_date, 'tiera')

trip1 = shipping_data['trip1']
trip4 = shipping_data['trip4']

print('=' * 80)
print('4t5t Split Logic Test Result')
print('=' * 80)

if trip1 and trip4:
    trip1_total_qty = sum(item['order_quantity'] for item in trip1)
    trip1_total_containers = sum(-(-item['order_quantity'] // item.get('capacity', 1)) for item in trip1)

    trip4_total_qty = sum(item['order_quantity'] for item in trip4)
    trip4_total_containers = sum(-(-item['order_quantity'] // item.get('capacity', 1)) for item in trip4)

    print(f'Trip 1 (06:00): {trip1_total_qty} items -> {trip1_total_containers} containers')
    print(f'Trip 4 (13:00): {trip4_total_qty} items -> {trip4_total_containers} containers')
    print(f'Total: {trip1_total_qty + trip4_total_qty} items -> {trip1_total_containers + trip4_total_containers} containers')
    print('=' * 80)

    if trip1_total_containers == trip4_total_containers:
        print('SUCCESS: Containers are equally divided!')
    elif abs(trip1_total_containers - trip4_total_containers) <= 1:
        print('SUCCESS: Containers are almost equally divided (difference <= 1)')
    else:
        print(f'FAIL: Container difference is too large ({abs(trip1_total_containers - trip4_total_containers)} containers)')
else:
    print('No data found')

db_manager.close()
