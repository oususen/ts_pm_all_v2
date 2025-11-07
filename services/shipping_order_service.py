# -*- coding: utf-8 -*-
"""
出荷指示書サービス
delivery_progressとproductsから出荷指示書用のデータを取得・振り分け
"""

from datetime import date
from typing import List, Dict, Any, Optional
import pandas as pd
from repository.database_manager import DatabaseManager
from sqlalchemy import text


class ShippingOrderService:
    """出荷指示書データを取得・振り分けるサービス"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def get_shipping_data_by_date(self, target_date: date, customer: str = 'tiera') -> Dict[str, Any]:
        """
        指定日の出荷指示書データを取得し、4便に振り分ける（Tiera製品のみ）

        Args:
            target_date: 対象日付
            customer: 顧客名（デフォルト: 'tiera'）

        Returns:
            {
                'date': date,
                'trip1': [...],  # 06:00便
                'trip2': [...],  # 06:30便
                'trip3': [...],  # 10:00便
                'trip4': [...]   # 13:00便
            }
        """
        session = self.db.get_session()
        try:
            # Tiera製品のみを対象とする
            # 出荷指示書の対象製品（容器4-5T、特定機種名、製品群SEATBASE/TANK）
            query = text("""
                SELECT
                    dp.order_id,
                    dp.product_id,
                    dp.order_quantity,
                    p.product_code,
                    p.product_name,
                    p.model_name,
                    p.capacity,
                    p.used_container_id,
                    p.product_group_id,
                    pg.group_code,
                    pg.group_name,
                    cc.name as container_name
                FROM delivery_progress dp
                INNER JOIN products p ON dp.product_id = p.id
                LEFT JOIN product_groups pg ON p.product_group_id = pg.id
                LEFT JOIN container_capacity cc ON p.used_container_id = cc.id
                WHERE DATE(dp.order_date) = :target_date
                    AND dp.order_quantity > 0
                    AND (
                        -- 容器が4-5Tの製品
                        cc.name LIKE '%4-5T%'
                        -- または機種名が特定の7種
                        OR UPPER(TRIM(p.model_name)) IN ('391', '17U', '20U', '26U', '19-6', '390', 'KOTEIKYAKU')
                        -- または製品群がSEATBASE/TANK
                        OR UPPER(TRIM(pg.group_code)) IN ('SEATBASE', 'TANK')
                    )
                ORDER BY p.product_code
            """)

            result = session.execute(query, {'target_date': target_date})
            rows = result.fetchall()

            if not rows:
                return {
                    'date': target_date,
                    'trip1': [],
                    'trip2': [],
                    'trip3': [],
                    'trip4': []
                }

            # DataFrameに変換
            df = pd.DataFrame([
                {
                    'order_id': row.order_id,
                    'product_id': row.product_id,
                    'product_code': row.product_code,
                    'product_name': row.product_name,
                    'model_name': row.model_name or '',
                    'order_quantity': row.order_quantity,
                    'capacity': row.capacity or 0,
                    'container_id': row.used_container_id,
                    'container_name': row.container_name or '',
                    'product_group_id': row.product_group_id,
                    'group_code': row.group_code or '',
                    'group_name': row.group_name or ''
                }
                for row in rows
            ])

            # 便ごとに振り分け
            trip1_data = self._filter_trip1(df)
            trip2_data = self._filter_trip2(df)
            trip3_data = self._filter_trip3(df)
            trip4_data = self._split_trip1_to_trip4(trip1_data)

            return {
                'date': target_date,
                'trip1': trip1_data,
                'trip2': trip2_data,
                'trip3': trip3_data,
                'trip4': trip4_data
            }

        finally:
            session.close()

    def _filter_trip1(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        1便目: 容器名が「4-5T」の製品
        """
        filtered = df[df['container_name'].str.contains('4-5T', case=False, na=False)]
        return filtered.to_dict('records')

    def _filter_trip2(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        2便目: 機種名が特定の7種
        ['391', '17U', '20U', '26U', '19-6', '390', 'KOTEIKYAKU']
        """
        target_models = ['391', '17U', '20U', '26U', '19-6', '390', 'KOTEIKYAKU']

        # 機種名を正規化（大文字・小文字、空白を統一）
        df['model_name_normalized'] = df['model_name'].str.strip().str.upper()

        # 完全一致または部分一致で検索
        filtered = df[df['model_name_normalized'].isin([m.upper() for m in target_models])]

        return filtered.to_dict('records')

    def _filter_trip3(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        3便目: 製品群コードが「SEATBASE」または「TANK」
        """
        target_groups = ['SEATBASE', 'TANK']

        # group_codeを正規化
        df['group_code_normalized'] = df['group_code'].str.strip().str.upper()

        filtered = df[df['group_code_normalized'].isin([g.upper() for g in target_groups])]

        return filtered.to_dict('records')

    def _split_trip1_to_trip4(self, trip1_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        4便目: 1便目と同じ製品、容器数を均等に分割

        全体の容器数を計算し、目標容器数に達するまで製品を1便目に割り当て、
        残りを4便目に割り当てることで、容器数を均等に分配する
        """
        if not trip1_data:
            return []

        # 各製品の容器数を計算
        product_containers = []
        total_containers = 0

        for item in trip1_data:
            capacity = item.get('capacity', 1)
            if capacity <= 0:
                capacity = 1

            qty = item['order_quantity']
            containers = -(-qty // capacity)  # 切り上げ
            total_containers += containers

            product_containers.append({
                'item': item,
                'original_qty': qty,
                'capacity': capacity,
                'containers': containers
            })

        # 目標容器数を計算（1便目が多くなるように）
        target_trip1_containers = -(-total_containers // 2)  # 切り上げ

        # 1便目と4便目に振り分け
        trip1_actual_containers = 0
        trip4_data = []

        for prod_info in product_containers:
            item = prod_info['item']
            original_qty = prod_info['original_qty']
            capacity = prod_info['capacity']
            containers = prod_info['containers']

            # まだ1便目の目標に達していない場合
            if trip1_actual_containers < target_trip1_containers:
                # この製品を1便目に追加しても目標を超えない場合は全て1便目へ
                if trip1_actual_containers + containers <= target_trip1_containers:
                    # 1便目に全量
                    item['order_quantity'] = original_qty
                    # 4便目には0
                    item_copy = item.copy()
                    item_copy['order_quantity'] = 0
                    trip4_data.append(item_copy)
                    trip1_actual_containers += containers
                else:
                    # 1便目の目標まで割り当て、残りを4便目へ
                    remaining_trip1_containers = target_trip1_containers - trip1_actual_containers

                    # 1便目の個数を計算
                    trip1_qty = remaining_trip1_containers * capacity
                    trip1_qty = min(trip1_qty, original_qty)

                    # 4便目は残り
                    trip4_qty = original_qty - trip1_qty

                    item['order_quantity'] = trip1_qty

                    item_copy = item.copy()
                    item_copy['order_quantity'] = trip4_qty
                    trip4_data.append(item_copy)

                    trip1_actual_containers += remaining_trip1_containers
            else:
                # 既に1便目の目標に達している場合は全て4便目へ
                item['order_quantity'] = 0
                item_copy = item.copy()
                item_copy['order_quantity'] = original_qty
                trip4_data.append(item_copy)

        return trip4_data

    def get_available_dates(self) -> List[date]:
        """
        delivery_progressに存在する日付一覧を取得
        """
        session = self.db.get_session()
        try:
            query = text("""
                SELECT DISTINCT DATE(order_date) as order_date
                FROM delivery_progress
                WHERE order_quantity > 0
                ORDER BY order_date DESC
                LIMIT 30
            """)

            result = session.execute(query)
            rows = result.fetchall()

            return [row.order_date for row in rows]

        finally:
            session.close()
