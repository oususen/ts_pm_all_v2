# app/repository/loading_plan_repository.py
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from typing import Dict, Any, List, Optional
from datetime import date
from .database_manager import DatabaseManager


class LoadingPlanRepository:
    """積載計画保存・取得リポジトリ"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    def save_loading_plan(self, plan_result: Dict[str, Any], plan_name: str = None) -> int:
        """積載計画を保存 + delivery_progressに計画数を登録"""
        session = self.db.get_session()
        
        try:
            # 計画名の自動生成
            if not plan_name:
                period = plan_result.get('period', '')
                plan_name = f"積載計画_{period.split(' ~ ')[0]}"
            
            summary = plan_result['summary']
            period_parts = plan_result['period'].split(' ~ ')
            start_date = period_parts[0]
            end_date = period_parts[1]
            
            # 1. ヘッダー保存
            header_sql = text("""
                INSERT INTO loading_plan_header 
                (plan_name, start_date, end_date, total_days, total_trips, status)
                VALUES (:plan_name, :start_date, :end_date, :total_days, :total_trips, '作成済')
            """)
            
            result = session.execute(header_sql, {
                'plan_name': plan_name,
                'start_date': start_date,
                'end_date': end_date,
                'total_days': summary['total_days'],
                'total_trips': summary['total_trips']
            })
            
            session.flush()
            plan_id = result.lastrowid
            
            # 2. 明細保存 + delivery_progress更新用のデータを収集
            daily_plans = plan_result.get('daily_plans', {})
            progress_updates = {}    # {product_id: {delivery_date: planned_quantity}}

            # ✅ フレームコンプ製品群向けの特別トラック適用ロジック
            target_product_ids = set()
            target_truck_info = None

            try:
                # 製品群IDを特定（完全一致→部分一致の順に検索）
                group_row = None
                for candidate_name in ('フレームコンプ製品群', 'フレームコンプ'):
                    group_row = session.execute(
                        text("SELECT id FROM product_groups WHERE group_name = :name"),
                        {'name': candidate_name}
                    ).fetchone()
                    if group_row:
                        break
                if not group_row:
                    group_row = session.execute(
                        text("""
                            SELECT id FROM product_groups
                            WHERE group_name LIKE :pattern
                            ORDER BY id
                            LIMIT 1
                        """),
                        {'pattern': '%フレームコンプ%'}
                    ).fetchone()

                if group_row:
                    product_rows = session.execute(
                        text("SELECT id FROM products WHERE product_group_id = :group_id"),
                        {'group_id': group_row[0]}
                    ).fetchall()
                    target_product_ids = {row[0] for row in product_rows}
                    print(f"[DEBUG] フレームコンプ製品群 product_ids: {target_product_ids}")
                else:
                    print("[DEBUG] フレームコンプ製品群が見つかりませんでした")
            except SQLAlchemyError as e:
                print(f"[ERROR] フレームコンプ製品群の取得に失敗: {e}")

            if target_product_ids:
                try:
                    truck_row = session.execute(
                        text("""
                            SELECT id, name
                            FROM truck_master
                            WHERE name IN ('NO_6_1OT', 'NO_6_10T')
                            ORDER BY CASE name
                                WHEN 'NO_6_1OT' THEN 1
                                WHEN 'NO_6_10T' THEN 2
                                ELSE 3
                            END
                            LIMIT 1
                        """)
                    ).fetchone()

                    if not truck_row:
                        truck_row = session.execute(
                            text("""
                                SELECT id, name
                                FROM truck_master
                                WHERE name LIKE :pattern
                                ORDER BY id
                                LIMIT 1
                            """),
                            {'pattern': 'NO_6%'}
                        ).fetchone()
                    if truck_row:
                        target_truck_info = {'id': truck_row[0], 'name': truck_row[1]}
                        print(f"[DEBUG] 特別トラック情報: {target_truck_info}")
                    else:
                        print("[DEBUG] トラックNO_6_1OT/10Tが見つかりませんでした")
                except SQLAlchemyError as e:
                    print(f"[ERROR] 特別トラック情報の取得に失敗: {e}")

            if target_product_ids and target_truck_info:
                for date_str, plan in daily_plans.items():
                    daily_total = 0
                    trucks = plan.get('trucks') or []

                    for truck_plan in trucks:
                        for item in truck_plan.get('loaded_items', []):
                            if item.get('product_id') in target_product_ids:
                                quantity = item.get('total_quantity') or 0
                                try:
                                    daily_total += float(quantity)
                                except (TypeError, ValueError):
                                    print(f"[DEBUG] total_quantityを数値化できませんでした: {quantity}")

                    if daily_total >= 120:
                        print(f"[DEBUG] {date_str} はフレームコンプ製品群 {daily_total} 台 -> 特別トラック適用")
                        for truck_plan in trucks:
                            contains_target = any(
                                item.get('product_id') in target_product_ids
                                for item in truck_plan.get('loaded_items', [])
                            )
                            if contains_target:
                                truck_plan['truck_id'] = target_truck_info['id']
                                truck_plan['truck_name'] = target_truck_info['name']
            
            for date_str, plan in daily_plans.items():
                for truck_plan in plan.get('trucks', []):
                    trip_number = 1
                    
                    for item in truck_plan.get('loaded_items', []):
                        # 明細保存
                        detail_sql = text("""
                            INSERT INTO loading_plan_detail
                            (plan_id, loading_date, truck_id, truck_name, trip_number,
                            product_id, product_code, product_name, container_id,
                            num_containers, total_quantity, delivery_date,
                            is_advanced, original_date, volume_utilization, weight_utilization)
                            VALUES 
                            (:plan_id, :loading_date, :truck_id, :truck_name, :trip_number,
                            :product_id, :product_code, :product_name, :container_id,
                            :num_containers, :total_quantity, :delivery_date,
                            :is_advanced, :original_date, :volume_util, :weight_util)
                        """)
                        
                        is_advanced = item.get('original_date') and \
                                    item['original_date'].strftime('%Y-%m-%d') != date_str
                        
                        session.execute(detail_sql, {
                            'plan_id': plan_id,
                            'loading_date': date_str,
                            'truck_id': truck_plan['truck_id'],
                            'truck_name': truck_plan['truck_name'],
                            'trip_number': trip_number,
                            'product_id': item['product_id'],
                            'product_code': item.get('product_code', ''),
                            'product_name': item.get('product_name', ''),
                            'container_id': item['container_id'],
                            'num_containers': item['num_containers'],
                            'total_quantity': item['total_quantity'],
                            'delivery_date': item['delivery_date'],
                            'is_advanced': is_advanced,
                            'original_date': item.get('original_date'),
                            'volume_util': truck_plan['utilization']['volume_rate'],
                            'weight_util': 0
                        })
                        
                        # ✅ delivery_progress更新用データを収集
                        product_id = item['product_id']
                        # ✅ 積載日（loading_date）をdate型に正規化
                        loading_date_for_progress = None
                        try:
                            from datetime import datetime as _dt
                            loading_date_for_progress = _dt.strptime(date_str, '%Y-%m-%d').date()
                        except Exception:
                            pass

                        quantity = item['total_quantity']

                        # ✅ キーは (product_id, 積載日) で管理
                        key = (product_id, loading_date_for_progress)
                        if key not in progress_updates:
                            progress_updates[key] = {
                                'product_id': product_id,
                                'delivery_date': loading_date_for_progress,  # 積載日をdelivery_dateとして使用
                                'planned_quantity': 0,
                                'loading_date': date_str,
                                'truck_id': truck_plan['truck_id']
                            }
                        # デバッグ: 各アイテムの集計前の数量を出力
                        print(f"[DEBUG] accumulate item - product_id={product_id}, loading_date={loading_date_for_progress}, quantity={quantity}")
                        progress_updates[key]['planned_quantity'] += quantity

            # デバッグ: 収集した progress_updates の内容を出力
            print(f"[DEBUG] progress_updates collected: {progress_updates}")

            # ✅ 3. 計画期間内のplanned_quantityを一旦0にリセット（今回未計画分を0化）
            try:
                reset_sql = text("""
                    UPDATE delivery_progress
                    SET planned_quantity = 0,
                        status = CASE 
                            WHEN shipped_quantity >= order_quantity THEN '出荷完了'
                            WHEN shipped_quantity > 0 THEN '一部出荷'
                            ELSE status
                        END
                    WHERE DATE(delivery_date) BETWEEN :start_date AND :end_date
                """)
                session.execute(reset_sql, {
                    'start_date': start_date,
                    'end_date': end_date
                })
                print(f"[DEBUG] reset planned_quantity to 0 between {start_date} and {end_date}")
            except Exception as _:
                pass

            # ✅ 4. delivery_progressに計画数を登録/更新（積載日基準）
            for (product_id, loading_date), update_data in progress_updates.items():
                # 既存のdelivery_progressレコードを検索（積載日で照合）
                check_sql = text("""
                    SELECT id, order_quantity, planned_quantity
                    FROM delivery_progress
                    WHERE product_id = :product_id
                    AND DATE(delivery_date) = :delivery_date
                """)
                
                existing_rows = session.execute(check_sql, {
                    'product_id': product_id,
                    'delivery_date': loading_date  # 積載日で検索
                }).fetchall()

                # デバッグ: 検索結果を出力
                print(f"[DEBUG] existing_rows for product_id={product_id}, loading_date={loading_date}: {existing_rows}")
                
                if existing_rows:
                    # 既存レコードを更新
                    update_sql = text("""
                        UPDATE delivery_progress
                        SET planned_quantity = :planned_quantity,
                            status = CASE 
                                WHEN shipped_quantity >= order_quantity THEN '出荷完了'
                                WHEN shipped_quantity > 0 THEN '一部出荷'
                                ELSE '計画済'
                            END
                        WHERE id = :progress_id
                    """)
                    session.execute(update_sql, {
                        'progress_id': existing_rows[0][0],
                        'planned_quantity': update_data['planned_quantity']
                    })

                    # デバッグ: 更新処理の内容を出力
                    # existing_rows[0] = (id, order_quantity, planned_quantity)
                    try:
                        old_planned = existing_rows[0][2]
                    except Exception:
                        old_planned = None
                    print(f"[DEBUG] update progress id={existing_rows[0][0]}: old_planned_quantity={old_planned} -> new_planned_quantity={update_data['planned_quantity']}")
                else:
                    # 既存の納入進度がない場合は新規作成しない
                    print(f"[DEBUG] skip creating delivery_progress for product_id={product_id}, loading_date={loading_date} (既存レコードなし)")
            
            # 4. 警告保存
            for date_str, plan in daily_plans.items():
                for warning in plan.get('warnings', []):
                    warning_sql = text("""
                        INSERT INTO loading_plan_warnings
                        (plan_id, warning_date, warning_type, warning_message)
                        VALUES (:plan_id, :warning_date, :warning_type, :warning_message)
                    """)
                    
                    warning_type = '前倒し' if '前倒し' in warning else '容量不足'
                    
                    session.execute(warning_sql, {
                        'plan_id': plan_id,
                        'warning_date': date_str,
                        'warning_type': warning_type,
                        'warning_message': warning
                    })
            
            # 5. 積載不可アイテム保存
            unloaded_tasks = plan_result.get('unloaded_tasks', [])
            for task in unloaded_tasks:
                unloaded_sql = text("""
                    INSERT INTO loading_plan_unloaded
                    (plan_id, product_id, product_code, product_name, container_id,
                    num_containers, total_quantity, delivery_date, reason)
                    VALUES
                    (:plan_id, :product_id, :product_code, :product_name, :container_id,
                    :num_containers, :total_quantity, :delivery_date, '積載容量不足')
                """)
                
                session.execute(unloaded_sql, {
                    'plan_id': plan_id,
                    'product_id': task['product_id'],
                    'product_code': task.get('product_code', ''),
                    'product_name': task.get('product_name', ''),
                    'container_id': task.get('container_id'),
                    'num_containers': task.get('num_containers'),
                    'total_quantity': task.get('total_quantity'),
                    'delivery_date': task.get('delivery_date')
                })
            
            session.commit()
            return plan_id
            
        except SQLAlchemyError as e:
            session.rollback()
            print(f"積載計画保存エラー: {e}")
            raise
        finally:
            session.close()    

    
   

# app/repository/loading_plan_repository.py の get_loading_plan メソッドを完全修正

    def get_loading_plan(self, plan_id: int) -> Dict[str, Any]:
        """積載計画を取得 - daily_plans付き完全版"""
        session = self.db.get_session()
        
        try:
            # ヘッダー取得
            header_sql = text("""
                SELECT * FROM loading_plan_header WHERE id = :plan_id
            """)
            header_result = session.execute(header_sql, {'plan_id': plan_id}).fetchone()
            
            if not header_result:
                print(f"❌ ヘッダーが見つかりません: plan_id={plan_id}")
                return None
            
            header = dict(header_result._mapping)
            print(f"✅ ヘッダー取得成功: {header}")
            
            # 明細取得
            detail_sql = text("""
                SELECT * FROM loading_plan_detail 
                WHERE plan_id = :plan_id 
                ORDER BY loading_date, truck_id, trip_number
            """)
            details = session.execute(detail_sql, {'plan_id': plan_id}).fetchall()
            print(f"✅ 明細取得: {len(details)}件")
            
            # 警告取得
            warning_sql = text("""
                SELECT * FROM loading_plan_warnings WHERE plan_id = :plan_id
            """)
            warnings = session.execute(warning_sql, {'plan_id': plan_id}).fetchall()
            
            # 積載不可取得
            unloaded_sql = text("""
                SELECT * FROM loading_plan_unloaded WHERE plan_id = :plan_id
            """)
            unloaded = session.execute(unloaded_sql, {'plan_id': plan_id}).fetchall()
            
            # ✅ daily_plansを再構築
            daily_plans = {}
            
            for detail in details:
                detail_dict = dict(detail._mapping)
                loading_date = detail_dict['loading_date']
                
                # 日付をstrに変換
                if hasattr(loading_date, 'strftime'):
                    date_str = loading_date.strftime('%Y-%m-%d')
                else:
                    date_str = str(loading_date)
                
                if date_str not in daily_plans:
                    daily_plans[date_str] = {
                        'trucks': [],
                        'total_trips': 0,
                        'warnings': []
                    }
                
                # トラックを検索または新規作成
                truck_id = detail_dict['truck_id']
                truck = next((t for t in daily_plans[date_str]['trucks'] 
                            if t['truck_id'] == truck_id), None)
                
                if not truck:
                    truck = {
                        'truck_id': truck_id,
                        'truck_name': detail_dict.get('truck_name', '不明'),
                        'loaded_items': [],
                        'utilization': {
                            'volume_rate': float(detail_dict.get('volume_utilization', 0)),
                            'weight_rate': 0
                        }
                    }
                    daily_plans[date_str]['trucks'].append(truck)
                    daily_plans[date_str]['total_trips'] += 1
                
                # アイテム追加
                delivery_date = detail_dict.get('delivery_date')
                if delivery_date:
                    if hasattr(delivery_date, 'date'):
                        delivery_date = delivery_date.date() if hasattr(delivery_date, 'date') else delivery_date
                
                truck['loaded_items'].append({
                    'product_id': detail_dict.get('product_id'),
                    'product_code': detail_dict.get('product_code', ''),
                    'product_name': detail_dict.get('product_name', ''),
                    'container_id': detail_dict.get('container_id'),
                    'num_containers': int(detail_dict.get('num_containers', 0)),
                    'total_quantity': int(detail_dict.get('total_quantity', 0)),
                    'delivery_date': delivery_date,
                    'is_advanced': bool(detail_dict.get('is_advanced', False))
                })
            
            # 警告を追加
            for warning in warnings:
                warning_dict = dict(warning._mapping)
                warning_date = warning_dict['warning_date']
                
                if hasattr(warning_date, 'strftime'):
                    date_str = warning_date.strftime('%Y-%m-%d')
                else:
                    date_str = str(warning_date)
                
                if date_str in daily_plans:
                    daily_plans[date_str]['warnings'].append(
                        warning_dict.get('warning_message', '')
                    )
            
            # 積載不可タスク
            unloaded_tasks = []
            for task in unloaded:
                task_dict = dict(task._mapping)
                
                delivery_date = task_dict.get('delivery_date')
                if delivery_date:
                    if hasattr(delivery_date, 'date'):
                        delivery_date = delivery_date.date() if hasattr(delivery_date, 'date') else delivery_date
                
                unloaded_tasks.append({
                    'product_id': task_dict.get('product_id'),
                    'product_code': task_dict.get('product_code', ''),
                    'product_name': task_dict.get('product_name', ''),
                    'container_id': task_dict.get('container_id'),
                    'num_containers': int(task_dict.get('num_containers', 0)),
                    'total_quantity': int(task_dict.get('total_quantity', 0)),
                    'delivery_date': delivery_date,
                    'reason': task_dict.get('reason', '')
                })
            
            # サマリー作成
            summary = {
                'total_days': int(header.get('total_days', 0)),
                'total_trips': int(header.get('total_trips', 0)),
                'status': header.get('status', '不明'),
                'total_warnings': len(warnings),
                'unloaded_count': len(unloaded_tasks)
            }
            
            print(f"✅ daily_plans作成: {len(daily_plans)}日分")
            print(f"✅ summary: {summary}")
            
            return {
                'id': plan_id,
                'plan_name': header.get('plan_name', ''),
                'header': header,
                'details': [dict(row._mapping) for row in details],
                'warnings': [dict(row._mapping) for row in warnings],
                'unloaded': [dict(row._mapping) for row in unloaded],
                'daily_plans': daily_plans,  # ✅ 追加
                'summary': summary,          # ✅ 追加
                'unloaded_tasks': unloaded_tasks,  # ✅ 追加
                'period': f"{header.get('start_date', '')} ~ {header.get('end_date', '')}"  # ✅ 追加
            }
            
        except SQLAlchemyError as e:
            print(f"❌ 積載計画取得エラー: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            session.close()    
    
    def get_all_plans(self) -> List[Dict]:
        """全積載計画のリスト取得"""
        session = self.db.get_session()
        
        try:
            sql = text("""
                SELECT 
                    id, plan_name, start_date, end_date, 
                    total_days, total_trips, status, created_at
                FROM loading_plan_header
                ORDER BY created_at DESC
            """)
            results = session.execute(sql).fetchall()
            
            plans = []
            for row in results:
                row_dict = dict(row._mapping)
                
                # ✅ summaryキーを追加
                row_dict['summary'] = {
                    'total_days': row_dict.get('total_days', 0),
                    'total_trips': row_dict.get('total_trips', 0),
                    'status': row_dict.get('status', '不明'),
                    'total_warnings': 0,  # ヘッダーにはないのでデフォルト値
                    'unloaded_count': 0   # ヘッダーにはないのでデフォルト値
                }
                
                plans.append(row_dict)
            
            return plans
            
        except SQLAlchemyError as e:
            print(f"積載計画リスト取得エラー: {e}")
            return []
        finally:
            session.close()

    def get_plan_details_by_date_and_truck(self, loading_date: date, truck_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """指定日の積載計画明細をトラック単位で取得"""
        session = self.db.get_session()

        try:
            latest_plan = session.execute(
                text("""
                    SELECT id
                    FROM loading_plan_header
                    ORDER BY id DESC
                    LIMIT 1
                """)
            ).fetchone()

            if not latest_plan:
                return []

            plan_id = latest_plan[0]
            params = {
                'plan_id': plan_id,
                'loading_date': loading_date.strftime('%Y-%m-%d')
            }

            detail_sql = """
                SELECT 
                    id,
                    plan_id,
                    loading_date,
                    truck_id,
                    truck_name,
                    trip_number,
                    product_id,
                    product_code,
                    product_name,
                    container_id,
                    num_containers,
                    total_quantity,
                    delivery_date,
                    original_date
                FROM loading_plan_detail
                WHERE plan_id = :plan_id
                  AND DATE(loading_date) = :loading_date
            """

            if truck_id:
                detail_sql += " AND truck_id = :truck_id"
                params['truck_id'] = truck_id

            detail_sql += " ORDER BY truck_id, trip_number, id"

            results = session.execute(text(detail_sql), params).fetchall()
            return [dict(row._mapping) for row in results]

        except SQLAlchemyError as e:
            print(f"積載計画明細取得エラー: {e}")
            return []
        finally:
            session.close()
    
    def delete_loading_plan(self, plan_id: int) -> bool:
        """積載計画を削除"""
        session = self.db.get_session()
        
        try:
            sql = text("DELETE FROM loading_plan_header WHERE id = :plan_id")
            session.execute(sql, {'plan_id': plan_id})
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            print(f"積載計画削除エラー: {e}")
            return False
        finally:
            session.close()
    def update_loading_plan_detail(self, detail_id: int, update_data: Dict[str, Any]) -> bool:
        """積載計画明細を更新"""
        session = self.db.get_session()
        
        try:
            set_clauses = []
            params = {'detail_id': detail_id}
            
            for key, value in update_data.items():
                set_clauses.append(f"{key} = :{key}")
                params[key] = value
            
            query = text(f"""
                UPDATE loading_plan_detail
                SET {', '.join(set_clauses)}
                WHERE id = :detail_id
            """)
            
            session.execute(query, params)
            session.commit()
            return True
            
        except SQLAlchemyError as e:
            session.rollback()
            print(f"計画明細更新エラー: {e}")
            return False
        finally:
            session.close()

    def save_edit_history(self, history_data: Dict[str, Any]) -> bool:
        """編集履歴を保存"""
        session = self.db.get_session()
        
        try:
            query = text("""
                INSERT INTO loading_plan_edit_history
                (plan_id, user_id, field_changed, old_value, new_value, detail_id)
                VALUES
                (:plan_id, :user_id, :field_changed, :old_value, :new_value, :detail_id)
            """)
            
            session.execute(query, history_data)
            session.commit()
            return True
            
        except SQLAlchemyError as e:
            session.rollback()
            print(f"編集履歴保存エラー: {e}")
            return False
        finally:
            session.close()

    def create_plan_version(self, version_data: Dict[str, Any]) -> int:
        """計画バージョンを作成"""
        session = self.db.get_session()
        
        try:
            # 現在の最大バージョン番号を取得
            max_version_query = text("""
                SELECT COALESCE(MAX(version_number), 0) 
                FROM loading_plan_versions 
                WHERE plan_id = :plan_id
            """)
            max_version = session.execute(max_version_query, {
                'plan_id': version_data['plan_id']
            }).scalar()
            
            version_data['version_number'] = max_version + 1
            
            query = text("""
                INSERT INTO loading_plan_versions
                (plan_id, version_number, version_name, created_by, snapshot_data, notes)
                VALUES
                (:plan_id, :version_number, :version_name, :created_by, :snapshot_data, :notes)
            """)
            
            result = session.execute(query, version_data)
            session.commit()
            return result.lastrowid
            
        except SQLAlchemyError as e:
            session.rollback()
            print(f"バージョン作成エラー: {e}")
            return 0
        finally:
            session.close()
