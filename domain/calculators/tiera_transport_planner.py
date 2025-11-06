# domain/calculators/tiera_transport_planner.py
"""
Tiera様専用の積載計画プランナー

【特徴】
- シンプルなロジック（前倒し無し、特便無し）
- リードタイム固定（製品のlead_time_daysを使用）
- 夕便（arrival_day_offset=1）優先
- 積めるだけ積む方式
"""

from typing import List, Dict, Any, Tuple
from datetime import datetime, date, timedelta
from collections import defaultdict
import pandas as pd


class TieraTransportPlanner:
    """Tiera様専用の積載計画プランナー"""

    def __init__(self, calendar_repo=None):
        self.calendar_repo = calendar_repo

    def calculate_loading_plan_from_orders(self,
                                          orders_df: pd.DataFrame,
                                          products_df: pd.DataFrame,
                                          containers: List[Any],
                                          trucks_df: pd.DataFrame,
                                          start_date: date,
                                          days: int = 7,
                                          calendar_repo=None,
                                          target_product_groups: List[str] = None) -> Dict[str, Any]:
        """
        Tiera様の積載計画作成

        シンプルなアルゴリズム：
        1. 納品日 - リードタイム = 積載日を計算
        2. 夕便優先でトラックを選択
        3. 積めるだけ積む（前倒し無し）

        Args:
            orders_df: 受注データ
            products_df: 製品データ
            containers: 容器リスト
            trucks_df: トラックデータ
            start_date: 計画開始日
            days: 計画日数
            calendar_repo: カレンダーリポジトリ
            target_product_groups: 対象製品グループのリスト（指定しない場合は全製品グループ）
        """
        self.calendar_repo = calendar_repo

        # 営業日のみで計画期間を構築
        working_dates = self._get_working_dates(start_date, days)

        # 対象製品グループでフィルタリング
        if target_product_groups is not None and len(target_product_groups) > 0:
            print(f"[DEBUG] フィルタ前の製品数: {len(products_df)}")
            print(f"[DEBUG] 対象グループ: {target_product_groups}")

            # group_codeがNullでないものだけをフィルタ
            if 'group_code' in products_df.columns:
                # NaNを除外してからフィルタリング
                products_df = products_df[
                    products_df['group_code'].notna() &
                    products_df['group_code'].isin(target_product_groups)
                ].copy()

                print(f"[DEBUG] フィルタ後の製品数: {len(products_df)}")

                # orders_dfも対象製品のみに絞り込む
                if not products_df.empty:
                    product_ids = products_df['id'].tolist()
                    orders_df = orders_df[orders_df['product_id'].isin(product_ids)].copy()
                    print(f"[DEBUG] フィルタ後の受注数: {len(orders_df)}")
                else:
                    print("[WARN] フィルタ後の製品が0件です")
                    orders_df = orders_df[orders_df['product_id'].isin([])].copy()
            else:
                print("[ERROR] products_dfにgroup_codeカラムがありません")

        # データ準備
        container_map = {c.id: c for c in containers}
        truck_map = {}
        for _, row in trucks_df.iterrows():
            try:
                truck_id = row['id']
                if pd.isna(truck_id):
                    continue
                truck_map[int(truck_id)] = row
            except (ValueError, TypeError):
                continue

        product_map = {}
        for _, row in products_df.iterrows():
            try:
                product_id = row['id']
                if pd.isna(product_id):
                    continue
                product_map[int(product_id)] = row
            except (ValueError, TypeError):
                continue

        # Step1: 積載日ごとに需要を整理（リードタイムを適用）
        daily_demands = self._organize_demands_by_loading_date(
            orders_df, product_map, container_map, working_dates
        )

        # Step2: 日次積載計画作成（シンプル版）
        daily_plans = {}
        for working_date in working_dates:
            date_str = working_date.strftime('%Y-%m-%d')
            if date_str not in daily_demands or not daily_demands[date_str]:
                daily_plans[date_str] = {
                    'trucks': [],
                    'total_trips': 0,
                    'warnings': [],
                    'remaining_demands': []
                }
                continue

            plan = self._create_simple_loading_plan(
                daily_demands[date_str],
                truck_map,
                container_map,
                product_map,
                working_date
            )
            daily_plans[date_str] = plan

        # ✅ 翌日着トラック（arrival_day_offset=1）の積載日を前日に調整
        self._adjust_for_next_day_arrival_trucks(daily_plans, truck_map, start_date)

        # 集計
        total_trips = sum(plan['total_trips'] for plan in daily_plans.values())
        total_warnings = sum(len(plan['warnings']) for plan in daily_plans.values())
        all_remaining = []
        for plan in daily_plans.values():
            all_remaining.extend(plan.get('remaining_demands', []))

        return {
            'daily_plans': daily_plans,
            'summary': {
                'total_days': days,
                'total_trips': total_trips,
                'total_warnings': total_warnings,
                'unloaded_count': len(all_remaining),
                'status': '警告あり' if total_warnings > 0 or len(all_remaining) > 0 else '正常'
            },
            'unloaded_tasks': all_remaining,
            'period': f"{start_date.strftime('%Y-%m-%d')} ~ {(start_date + timedelta(days=days-1)).strftime('%Y-%m-%d')}"
        }

    def _get_working_dates(self, start_date: date, days: int) -> List[date]:
        """営業日リストを取得"""
        working_dates = []
        current = start_date
        max_search_days = days * 3  # 最大検索日数

        for _ in range(max_search_days):
            if self.calendar_repo:
                if self.calendar_repo.is_working_day(current):
                    working_dates.append(current)
                    if len(working_dates) >= days:
                        break
            else:
                # カレンダー無しの場合は全日
                working_dates.append(current)
                if len(working_dates) >= days:
                    break
            current += timedelta(days=1)

        return working_dates

    def _calculate_loading_date_by_working_days(self, delivery_date: date, lead_time_days: int) -> date:
        """
        納品日から営業日ベースでリードタイム日数を引いて積載日を計算

        Args:
            delivery_date: 納品日
            lead_time_days: リードタイム（営業日）

        Returns:
            積載日
        """
        if lead_time_days <= 0:
            # リードタイムが0の場合は、納品日の前の営業日を返す
            loading_date = delivery_date
            if self.calendar_repo:
                # 納品日が休業日の場合は前の営業日に戻す
                max_search = 14
                for _ in range(max_search):
                    if self.calendar_repo.is_working_day(loading_date):
                        return loading_date
                    loading_date -= timedelta(days=1)
            return loading_date

        # 営業日ベースでリードタイム日数分前に戻る
        loading_date = delivery_date
        days_counted = 0
        max_search = 30  # 最大30日前まで検索

        for _ in range(max_search):
            loading_date -= timedelta(days=1)

            if self.calendar_repo:
                if self.calendar_repo.is_working_day(loading_date):
                    days_counted += 1
                    if days_counted >= lead_time_days:
                        return loading_date
            else:
                # カレンダー無しの場合は暦日ベース
                days_counted += 1
                if days_counted >= lead_time_days:
                    return loading_date

        # 見つからない場合は元の日付から暦日で引く（フォールバック）
        return delivery_date - timedelta(days=lead_time_days)

    def _organize_demands_by_loading_date(self, orders_df, product_map, container_map, working_dates):
        """納品日からリードタイムを引いて積載日ごとに需要を整理"""
        daily_demands = defaultdict(list)

        for _, order in orders_df.iterrows():
            try:
                product_id = order.get('product_id')
                if pd.isna(product_id):
                    continue
                product_id = int(product_id)
            except (ValueError, TypeError, KeyError):
                continue

            if product_id not in product_map:
                continue

            product = product_map[product_id]

            # 納期取得
            delivery_date = self._parse_date(order.get('delivery_date') or order.get('instruction_date'))
            if not delivery_date:
                continue

            # 容器情報取得
            container_id = product.get('used_container_id')
            if not container_id or pd.isna(container_id):
                continue

            try:
                container_id = int(container_id)
            except (ValueError, TypeError):
                continue

            container = container_map.get(container_id)
            if not container:
                continue

            # 入り数取得
            try:
                raw_capacity = product.get('capacity')
                if raw_capacity is None or pd.isna(raw_capacity):
                    raw_capacity = 1
                capacity = max(1, int(raw_capacity))
            except Exception:
                capacity = 1

            # 数量取得
            quantity = self._get_order_quantity(order)
            if quantity <= 0:
                continue

            # コンテナ数計算
            num_containers = (quantity + capacity - 1) // capacity
            remainder = quantity % capacity
            surplus = capacity - remainder if remainder > 0 else 0

            # 底面積計算
            floor_area_per_container = (container.width * container.depth) / 1_000_000
            max_stack = getattr(container, 'max_stack', 1)

            # 段積み可否：製品と容器の両方がstackable=Trueで、max_stack>1の場合のみ
            product_stackable = bool(product.get('stackable', 0))  # tinyint(1) -> bool
            container_stackable = getattr(container, 'stackable', False)

            if max_stack > 1 and product_stackable and container_stackable:
                stacked_containers = (num_containers + max_stack - 1) // max_stack
                total_floor_area_needed = floor_area_per_container * stacked_containers
            else:
                total_floor_area_needed = floor_area_per_container * num_containers

            # リードタイム取得
            try:
                product_lead_time = int(product.get('lead_time_days', 0))
                if pd.isna(product_lead_time):
                    product_lead_time = 0
            except (ValueError, TypeError):
                product_lead_time = 0

            # 積載日計算（営業日ベースでリードタイムを引く）
            loading_date = self._calculate_loading_date_by_working_days(
                delivery_date, product_lead_time
            )

            # 計画期間内のみ
            if loading_date in working_dates:
                date_str = loading_date.strftime('%Y-%m-%d')

                # トラックID取得
                truck_ids_str = product.get('used_truck_ids')
                if truck_ids_str and not pd.isna(truck_ids_str):
                    truck_ids = [int(tid.strip()) for tid in str(truck_ids_str).split(',')]
                else:
                    truck_ids = []

                daily_demands[date_str].append({
                    'product_id': product_id,
                    'product_code': product.get('product_code', ''),
                    'product_name': product.get('product_name', ''),
                    'container_id': container_id,
                    'container_name': getattr(container, 'name', '不明'),  # ✅ UI表示用
                    'num_containers': num_containers,
                    'total_quantity': quantity,
                    'capacity': capacity,
                    'remainder': remainder,
                    'surplus': surplus,
                    'floor_area': total_floor_area_needed,
                    'floor_area_per_container': floor_area_per_container,
                    'delivery_date': delivery_date,
                    'loading_date': loading_date,
                    'truck_ids': truck_ids,
                    'max_stack': max_stack,
                    'stackable': product_stackable and container_stackable  # ✅ 製品と容器の両方を確認
                })

        return daily_demands

    def _get_order_quantity(self, order):
        """受注数量を取得"""
        def _to_int(x, default=0):
            try:
                if x is None or (hasattr(pd, "isna") and pd.isna(x)):
                    return default
                return int(x)
            except Exception:
                return default

        # 手動計画数量優先
        manual_qty = order.get('manual_planning_quantity', None)
        if manual_qty is not None and not pd.isna(manual_qty):
            desired_qty = _to_int(manual_qty, 0)
            shipped_done = _to_int(order.get('shipped_quantity'), 0)
            return max(0, desired_qty - shipped_done)

        # remaining_quantity
        if 'remaining_quantity' in order.index:
            return max(0, _to_int(order.get('remaining_quantity'), 0))

        # order_quantity - shipped_quantity
        oq = _to_int(order.get('order_quantity'), 0)
        sq = order.get('shipped_quantity', None)
        if sq is not None:
            sq = _to_int(sq, 0)
            return max(0, oq - sq)

        return max(0, oq)

    def _create_simple_loading_plan(self, demands, truck_map, container_map, product_map, current_date):
        """シンプルな積載計画作成（夕便優先、積めるだけ積む）"""

        # 夕便優先でトラックをソート（arrival_day_offset=1を優先）
        available_trucks = []
        for truck_id, truck_info in truck_map.items():
            arrival_offset = int(truck_info.get('arrival_day_offset', 0) or 0)
            # 夕便（offset=1）を優先（値が小さいほど優先）
            priority = 0 if arrival_offset == 1 else 1
            available_trucks.append((priority, truck_id, truck_info))

        available_trucks.sort(key=lambda x: x[0])

        # トラック状態初期化
        truck_states = {}
        for _, truck_id, truck_info in available_trucks:
            truck_states[truck_id] = {
                'truck_id': truck_id,
                'truck_name': truck_info.get('name', f'トラック{truck_id}'),
                'total_floor_area': float(truck_info.get('width', 2400) * truck_info.get('depth', 9700)) / 1_000_000,
                'remaining_floor_area': float(truck_info.get('width', 2400) * truck_info.get('depth', 9700)) / 1_000_000,
                'loaded_items': [],
                'trip_number': 1
            }

        remaining_demands = []
        warnings = []

        # 需要を1つずつ処理
        for demand in demands:
            loaded = False
            container_id = demand['container_id']
            product_code = demand.get('product_code', '')

            # 🔍 デバッグ: 大量ケース製品を追跡
            if '6245' in product_code or demand['num_containers'] > 15:
                print(f"\n🔍 [Tiera-大量ケース] {product_code}: {demand['num_containers']}ケース, {demand['total_quantity']}個")
                print(f"   納期: {demand['delivery_date']}, 積載日: {current_date}")
                print(f"   底面積: {demand['floor_area']:.2f}m²")

            # トラックに順番に積載を試みる
            for _, truck_id, truck_info in available_trucks:
                # 全量積載完了したらループを抜ける
                if demand['num_containers'] <= 0:
                    loaded = True
                    break

                truck_state = truck_states[truck_id]

                # 🔍 デバッグ: トラック状態を表示
                if '6245' in product_code or demand['num_containers'] > 15:
                    print(f"   試行: {truck_state['truck_name']} (空き{truck_state['remaining_floor_area']:.2f}m² / 総{truck_state['total_floor_area']:.2f}m², 残り{demand['num_containers']}ケース)")

                # 同じ容器が既に積載されているか確認（段積み統合用）
                same_container_items = [item for item in truck_state['loaded_items']
                                       if item['container_id'] == container_id]

                # 🔍 デバッグ: 段積みチェック
                if '6245' in product_code or demand['num_containers'] > 15:
                    print(f"      段積みチェック: same_container_items={len(same_container_items)}個")

                if same_container_items:
                    # 同じ容器が既にある場合、段積みとして統合できるか確認
                    container = container_map.get(container_id)
                    if container and getattr(container, 'stackable', False):
                        max_stack = getattr(container, 'max_stack', 1)
                        floor_area_per_container = (container.width * container.depth) / 1_000_000

                        # 既存の容器数を計算（同じ容器IDの全製品）
                        existing_containers = sum(item['num_containers'] for item in same_container_items)
                        new_total_containers = existing_containers + demand['num_containers']

                        # 既存の配置数
                        existing_stacks = (existing_containers + max_stack - 1) // max_stack
                        # 新しい配置数
                        new_stacks = (new_total_containers + max_stack - 1) // max_stack
                        # 追加で必要な配置数
                        additional_stacks = new_stacks - existing_stacks
                        additional_floor_area = additional_stacks * floor_area_per_container

                        # 🔍 デバッグ: 段積み統合計算
                        if '6245' in product_code or demand['num_containers'] > 15:
                            print(f"      段積み統合: existing={existing_containers}, new_total={new_total_containers}, additional_floor={additional_floor_area:.2f}m², remaining={truck_state['remaining_floor_area']:.2f}m²")

                        if additional_floor_area <= truck_state['remaining_floor_area']:
                            # 🔍 デバッグ: 段積み統合成功
                            if '6245' in product_code or demand['num_containers'] > 15:
                                print(f"      ✅ 段積み統合成功!")

                            # 段積みとして統合可能
                            truck_state['loaded_items'].append({
                                'product_id': demand['product_id'],
                                'product_code': demand['product_code'],
                                'product_name': demand['product_name'],
                                'container_id': demand['container_id'],
                                'container_name': demand.get('container_name', '不明'),
                                'num_containers': demand['num_containers'],
                                'total_quantity': demand['total_quantity'],
                                'delivery_date': demand['delivery_date'],
                                'floor_area': demand['floor_area']
                            })
                            truck_state['remaining_floor_area'] -= additional_floor_area

                            # ✅ 全量積載完了をマーク
                            demand['num_containers'] = 0
                            demand['total_quantity'] = 0
                            demand['floor_area'] = 0
                            loaded = True
                            break
                        else:
                            # 🔍 デバッグ: 段積み統合失敗
                            if '6245' in product_code or demand['num_containers'] > 15:
                                print(f"      ❌ 段積み統合失敗: 追加底面積({additional_floor_area:.2f}m²)が空き({truck_state['remaining_floor_area']:.2f}m²)より大きい")

                # 🔍 デバッグ: 積載チェック
                if '6245' in product_code or demand['num_containers'] > 15:
                    print(f"      全量積載チェック: demand['floor_area']={demand['floor_area']:.2f}m² <= remaining={truck_state['remaining_floor_area']:.2f}m² ? {demand['floor_area'] <= truck_state['remaining_floor_area']}")

                # 同じ容器がない場合、または段積み統合できなかった場合は通常の積載を試みる
                if not loaded and demand['floor_area'] <= truck_state['remaining_floor_area']:
                    # 🔍 デバッグ: 積載成功
                    if '6245' in product_code or demand['num_containers'] > 15:
                        print(f"   ✅ {truck_state['truck_name']}に全量積載成功")

                    # 積載
                    truck_state['loaded_items'].append({
                        'product_id': demand['product_id'],
                        'product_code': demand['product_code'],
                        'product_name': demand['product_name'],
                        'container_id': demand['container_id'],
                        'container_name': demand.get('container_name', '不明'),  # ✅ UI表示用
                        'num_containers': demand['num_containers'],
                        'total_quantity': demand['total_quantity'],
                        'delivery_date': demand['delivery_date'],
                        'floor_area': demand['floor_area']
                    })
                    truck_state['remaining_floor_area'] -= demand['floor_area']
                    # ✅ 全量積載完了をマーク
                    demand['num_containers'] = 0
                    demand['total_quantity'] = 0
                    demand['floor_area'] = 0
                    loaded = True
                    break
                elif not loaded and truck_state['remaining_floor_area'] > 0:
                    # ✅ 分割積載：一部だけ積める場合
                    container = container_map.get(container_id)
                    if container:
                        floor_area_per_container = (container.width * container.depth) / 1_000_000
                        max_stack = getattr(container, 'max_stack', 1)
                        is_stackable = demand.get('stackable', False)

                        # 🔍 デバッグ: 容器情報
                        if '6245' in product_code or demand['num_containers'] > 15:
                            print(f"      容器情報: 底面積={floor_area_per_container:.4f}m², max_stack={max_stack}, stackable={is_stackable}")

                        # 積載可能な容器数を計算
                        if max_stack > 1 and is_stackable:
                            max_stacks = int(truck_state['remaining_floor_area'] / floor_area_per_container)
                            loadable_containers = max_stacks * max_stack
                        else:
                            loadable_containers = int(truck_state['remaining_floor_area'] / floor_area_per_container)

                        # 🔍 デバッグ: 積載可能数
                        if '6245' in product_code or demand['num_containers'] > 15:
                            print(f"      計算結果: loadable_containers={loadable_containers}, demand['num_containers']={demand['num_containers']}")

                        if loadable_containers >= demand['num_containers']:
                            # ✅ 全量積載可能（段積み最適化により）
                            if '6245' in product_code or demand['num_containers'] > 15:
                                print(f"   ✅ {truck_state['truck_name']}に全量積載成功（段積み最適化）")

                            # 積載可能数量を計算
                            capacity = demand.get('capacity', 1)
                            loadable_quantity = demand['total_quantity']
                            loadable_containers_actual = demand['num_containers']

                            # 底面積を再計算
                            if max_stack > 1 and is_stackable:
                                stacked = (loadable_containers_actual + max_stack - 1) // max_stack
                                loadable_floor_area = floor_area_per_container * stacked
                            else:
                                loadable_floor_area = floor_area_per_container * loadable_containers_actual

                            # 全量積載
                            truck_state['loaded_items'].append({
                                'product_id': demand['product_id'],
                                'product_code': demand['product_code'],
                                'product_name': demand['product_name'],
                                'container_id': demand['container_id'],
                                'container_name': demand.get('container_name', '不明'),
                                'num_containers': loadable_containers_actual,
                                'total_quantity': loadable_quantity,
                                'delivery_date': demand['delivery_date'],
                                'floor_area': loadable_floor_area
                            })
                            truck_state['remaining_floor_area'] -= loadable_floor_area

                            # 全量積載完了をマーク
                            demand['num_containers'] = 0
                            demand['total_quantity'] = 0
                            demand['floor_area'] = 0
                            loaded = True
                            break

                        elif loadable_containers > 0 and loadable_containers < demand['num_containers']:
                            # 🔍 デバッグ: 分割積載
                            if '6245' in product_code or demand['num_containers'] > 15:
                                print(f"   🔀 {truck_state['truck_name']}に分割積載: {loadable_containers}ケース（残り{demand['num_containers'] - loadable_containers}ケース）")

                            # 積載可能数量を計算
                            capacity = demand.get('capacity', 1)
                            loadable_quantity = min(loadable_containers * capacity, demand['total_quantity'])

                            # 底面積を再計算
                            if max_stack > 1 and is_stackable:
                                stacked = (loadable_containers + max_stack - 1) // max_stack
                                loadable_floor_area = floor_area_per_container * stacked
                            else:
                                loadable_floor_area = floor_area_per_container * loadable_containers

                            # 分割して積載
                            truck_state['loaded_items'].append({
                                'product_id': demand['product_id'],
                                'product_code': demand['product_code'],
                                'product_name': demand['product_name'],
                                'container_id': demand['container_id'],
                                'container_name': demand.get('container_name', '不明'),
                                'num_containers': loadable_containers,
                                'total_quantity': loadable_quantity,
                                'delivery_date': demand['delivery_date'],
                                'floor_area': loadable_floor_area
                            })
                            truck_state['remaining_floor_area'] -= loadable_floor_area

                            # 残りを更新
                            demand['num_containers'] -= loadable_containers
                            demand['total_quantity'] -= loadable_quantity
                            demand['floor_area'] -= loadable_floor_area
                            # 次のトラックで継続

            # 最終チェック：残りがある場合は積み残し
            if demand['num_containers'] > 0:
                # 🔍 デバッグ: 積み残し
                if '6245' in product_code or demand['num_containers'] > 15:
                    print(f"   ❌ 積み残し: {demand['num_containers']}ケース")
                    print(f"      理由: 全てのトラックに積載を試みたが、残りが積載できなかった")

                remaining_demands.append(demand)
                warnings.append(f"製品 {demand['product_code']} ({demand['num_containers']}ケース) が積載できませんでした")
            elif '6245' in product_code or loaded:
                # 🔍 デバッグ: 全量積載完了
                if '6245' in product_code:
                    print(f"   ✅ 全量積載完了（複数トラックに分割積載）")

        # 結果整形
        trucks_result = []
        trip_count = 0
        for truck_id, state in truck_states.items():
            if state['loaded_items']:
                # 積載率計算（床面積ベース）
                floor_area_rate = round((1.0 - (state['remaining_floor_area'] / state['total_floor_area'])) * 100, 1)

                trucks_result.append({
                    'truck_id': truck_id,
                    'truck_name': state['truck_name'],
                    'trip_number': state['trip_number'],
                    'loading_date': current_date,
                    'loaded_items': state['loaded_items'],  # ✅ 親と同じキー名
                    'utilization': {  # ✅ 親と同じ辞書形式
                        'floor_area_rate': floor_area_rate,
                        'volume_rate': floor_area_rate  # 簡易計算として同じ値を使用
                    }
                })
                trip_count += 1

        return {
            'trucks': trucks_result,
            'total_trips': trip_count,
            'warnings': warnings,
            'remaining_demands': remaining_demands
        }

    def _parse_date(self, date_value):
        """日付を解析"""
        if not date_value:
            return None
        if isinstance(date_value, date):
            return date_value
        if isinstance(date_value, str):
            try:
                return datetime.strptime(date_value, '%Y-%m-%d').date()
            except ValueError:
                pass
        return None

    def _adjust_for_next_day_arrival_trucks(self, daily_plans, truck_map, start_date):
        """
        翌日着トラック（arrival_day_offset=1）の積載日を前日に調整

        重要：到着日は納期日のまま変わらないため、can_advance（前倒し可否）のチェックは不要
        お客さんから見れば納期日に届くので「前倒し」ではない

        期間外でもOK（例：期間が10-15～10-28の場合、10-15のトラックを10-14に移動）
        """
        # 翌日着トラックの積載日調整を開始

        # 日付順にソート
        sorted_dates = sorted(daily_plans.keys())

        for date_str in sorted_dates:
            current_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            day_plan = daily_plans[date_str]

            # この日のトラックプランをチェック
            trucks_to_move = []
            for truck_plan in day_plan['trucks']:
                truck_id = truck_plan['truck_id']
                if truck_id not in truck_map:
                    continue

                truck_info = truck_map[truck_id]
                arrival_offset = int(truck_info.get('arrival_day_offset', 0) or 0)

                # arrival_day_offset=1のトラックを前日に移動
                if arrival_offset == 1:
                    trucks_to_move.append(truck_plan)

            # 移動対象のトラックを前日に移動
            for truck_plan in trucks_to_move:
                # 営業日の前日を探す
                prev_date = current_date - timedelta(days=1)

                # 非営業日の場合、営業日を遡る
                if self.calendar_repo:
                    max_attempts = 7  # 最大7日遡る
                    for _ in range(max_attempts):
                        if self.calendar_repo.is_working_day(prev_date):
                            break
                        prev_date -= timedelta(days=1)
                    else:
                        # 営業日が見つからない場合はそのまま処理継続
                        pass

                prev_date_str = prev_date.strftime('%Y-%m-%d')

                # 前日のプランが存在しない場合は作成
                if prev_date_str not in daily_plans:
                    daily_plans[prev_date_str] = {
                        'trucks': [],
                        'total_trips': 0,
                        'warnings': [],
                        'remaining_demands': []
                    }

                # トラックプランを前日に移動（到着日は変わらないため、can_advanceチェック不要）

                # 全ての積載アイテムのloading_dateを更新
                for item in truck_plan['loaded_items']:
                    item['loading_date'] = prev_date
                    item['adjusted_for_next_day_arrival'] = True  # フラグを追加

                # 前日のプランに追加
                daily_plans[prev_date_str]['trucks'].append(truck_plan)
                daily_plans[prev_date_str]['total_trips'] = len(daily_plans[prev_date_str]['trucks'])

                # 当日のプランから削除
                day_plan['trucks'].remove(truck_plan)
                day_plan['total_trips'] = len(day_plan['trucks'])

        # 翌日着トラックの積載日調整が完了
