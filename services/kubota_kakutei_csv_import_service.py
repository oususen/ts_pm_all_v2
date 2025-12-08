# app/services/kubota_kakutei_csv_import_service.py
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Tuple, List, Dict, Optional
from sqlalchemy import text


class KubotaKakuteiCSVImportService:
    """クボタ向け確定受注CSVインポートサービス（JVAN形式）"""

    HISTORY_PREFIX = "[クボタ様・確定CSV]"

    def __init__(self, db_manager):
        self.db = db_manager
        self.latest_quantity_changes: List[Dict] = []
        self.latest_quantity_change_window: Tuple[Optional[date], Optional[date]] = (None, None)

    # Public API -----------------------------------------------------------------

    def import_csv_data(self, uploaded_file,
                        create_progress: bool = True) -> Tuple[bool, str]:
        """確定受注CSVを読み込み、指示・配送情報へ反映"""
        try:
            self.latest_quantity_changes = []
            window_start = date.today()
            window_end = window_start + timedelta(days=10)
            self.latest_quantity_change_window = (window_start, window_end)

            df = pd.read_csv(uploaded_file, encoding='cp932', dtype=str)
            df = df.fillna('')

            grouped_data = self._group_by_product_and_date(df)
            if not grouped_data:
                return False, "[確定CSV] 有効なレコードが見つかりませんでした。"

            product_ids = self._import_products(grouped_data)
            if not product_ids:
                return False, "[確定CSV] 製品マスタ登録に失敗しました。"

            instruction_count = self._create_production_instructions(grouped_data, product_ids)

            progress_count = 0
            if create_progress:
                progress_count = self._create_delivery_progress(grouped_data, product_ids)

            if create_progress:
                return True, f"[確定CSV] {instruction_count}件の受注指示と{progress_count}件の配送進捗を登録しました。"
            return True, f"[確定CSV] {instruction_count}件の受注指示を登録しました。"

        except Exception as e:
            error_msg = f"[確定CSV] インポートエラー: {str(e)}"
            import traceback
            traceback.print_exc()
            return False, error_msg

    def get_import_history(self) -> List[Dict]:
        """インポート履歴を取得"""
        session = self.db.get_session()
        try:
            result = session.execute(text("""
                SELECT id, filename, import_date, record_count, status, message
                FROM csv_import_history
                ORDER BY import_date DESC
                LIMIT 50
            """)).fetchall()

            return [{
                'ID': r[0],
                'ファイル名': r[1],
                'インポート日時': r[2],
                '登録件数': r[3],
                'ステータス': r[4],
                'メッセージ': r[5]
            } for r in result]
        except Exception:
            return []
        finally:
            session.close()

    def log_import_history(self, filename: str, message: str):
        """インポート履歴を記録"""
        session = self.db.get_session()
        try:
            import re
            match = re.search(r'(\d+)件', message)
            record_count = int(match.group(1)) if match else 0

            history_message = message
            if not history_message.startswith(self.HISTORY_PREFIX):
                history_message = f"{self.HISTORY_PREFIX} {message}"

            session.execute(text("""
                INSERT INTO csv_import_history
                (filename, import_date, record_count, status, message)
                VALUES (:filename, :import_date, :record_count, :status, :message)
            """), {
                'filename': filename,
                'import_date': datetime.now(),
                'record_count': record_count,
                'status': '成功',
                'message': history_message
            })
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()

    # Internal helpers -----------------------------------------------------------

    def _group_by_product_and_date(self, df: pd.DataFrame) -> List[Dict]:
        """品番×納期×検区単位で数量を集計"""
        aggregated: Dict[Tuple, Dict] = {}

        for _, row in df.iterrows():
            product_code = str(row.get('品番', '')).strip()
            if not product_code or product_code.lower() == 'nan':
                continue

            product_name = str(row.get('品名', '')).strip()
            delivery_place = str(row.get('納場所名', '') or row.get('納場所', '')).strip()
            inspection_category = str(row.get('検区', '') or 'N').strip() or 'N'

            quantity = self._safe_int(row.get('発注数', 0))
            if quantity <= 0:
                continue

            issue_date = self._parse_issue_date(str(row.get('発行日', '')).strip())
            delivery_date = self._parse_delivery_date(str(row.get('納期', '')).strip(), issue_date)
            if not delivery_date:
                continue
            customer_code = 'KUBOTA_K'
            customer_name = 'クボタ様(確定)'
            order_number = str(row.get('発注番号', '')).strip()

            box_type = str(row.get('箱種', '')).strip()
            capacity = self._safe_int(row.get('収容数', 0))

            key = (product_code, delivery_date, inspection_category, customer_code, customer_name, delivery_place or '', box_type)
            entry = aggregated.setdefault(key, {
                'product_code': product_code,
                'product_name': product_name,
                'delivery_date': delivery_date,
                'issue_date': issue_date or delivery_date,
                'inspection_category': inspection_category,
                'customer_code': customer_code,
                'customer_name': customer_name,
                'delivery_place': delivery_place,
                'box_type': box_type,
                'capacity': capacity if capacity > 0 else 1,
                'quantity': 0,
                'order_numbers': set(),
                'order_details': {}
            })
            entry['quantity'] += quantity
            if order_number:
                entry['order_numbers'].add(order_number)
                entry['order_details'][order_number] = entry['order_details'].get(order_number, 0) + quantity

        results = []
        for item in aggregated.values():
            item['order_numbers'] = sorted(item['order_numbers'])
            results.append(item)
        return results

    def _import_products(self, grouped_data: List[Dict]) -> Dict[str, int]:
        """必要な品番をproductsへ登録"""
        product_ids: Dict[str, int] = {}
        session = self.db.get_session()

        try:
            for item in grouped_data:
                product_code = item['product_code']

                result = session.execute(text("""
                    SELECT id FROM products WHERE product_code = :product_code
                """), {'product_code': product_code}).fetchone()

                if result:
                    product_id = result[0]
                else:
                    result = session.execute(text("""
                        INSERT INTO products
                        (product_code, product_name, delivery_location, box_type, capacity)
                        VALUES (:product_code, :product_name, :delivery_location, :box_type, :capacity)
                    """), {
                        'product_code': product_code,
                        'product_name': item['product_name'] or product_code,
                        'delivery_location': item['delivery_place'],
                        'box_type': item['box_type'],
                        'capacity': item['capacity'] if item['capacity'] > 0 else 1
                    })
                    product_id = result.lastrowid

                product_ids[product_code] = product_id

            session.commit()
            return product_ids
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def _create_production_instructions(self, grouped_data: List[Dict],
                                        product_ids: Dict[str, int]) -> int:
        session = self.db.get_session()
        instruction_count = 0
        change_window_start, change_window_end = self.latest_quantity_change_window

        try:
            for item in grouped_data:
                product_code = item['product_code']
                product_id = product_ids.get(product_code)
                if not product_id:
                    continue

                delivery_date = item['delivery_date']
                inspection_category = item['inspection_category']
                start_month = delivery_date.strftime('%Y%m')
                order_details: Dict[str, int] = item.get('order_details', {})

                within_window = (
                    change_window_start is not None
                    and change_window_end is not None
                    and change_window_start <= delivery_date <= change_window_end
                )

                existing_row = session.execute(text("""
                    SELECT instruction_quantity, order_number
                    FROM production_instructions_detail
                    WHERE product_id = :product_id
                      AND instruction_date = :instruction_date
                      AND inspection_category = :inspection_category
                """), {
                    'product_id': product_id,
                    'instruction_date': delivery_date,
                    'inspection_category': inspection_category
                }).fetchone()

                base_quantity = int(existing_row[0]) if existing_row and existing_row[0] is not None else 0
                previous_order_numbers = set()
                if existing_row and existing_row[1]:
                    previous_order_numbers = set(existing_row[1].split('+'))

                current_order_numbers = set(order_details.keys())
                is_naiji_stub = existing_row is not None and not previous_order_numbers

                if not existing_row or is_naiji_stub:
                    addition_quantity = sum(order_details.values())
                else:
                    new_order_numbers = current_order_numbers - previous_order_numbers
                    addition_quantity = sum(order_details[order_no] for order_no in new_order_numbers)

                if not existing_row or is_naiji_stub:
                    new_total = addition_quantity
                else:
                    new_total = base_quantity + addition_quantity

                combined_order_numbers = sorted(previous_order_numbers.union(current_order_numbers)) if (previous_order_numbers or current_order_numbers) else []
                order_numbers_str = '+'.join(combined_order_numbers) if combined_order_numbers else None
                difference = new_total - base_quantity

                session.execute(text("""
                    REPLACE INTO production_instructions_detail
                    (product_id, record_type, order_type, order_number, start_month, instruction_date,
                    instruction_quantity, month_type, day_number, inspection_category)
                    VALUES
                    (:product_id, :record_type, :order_type, :order_number, :start_month, :instruction_date,
                     :instruction_quantity, :month_type, :day_number, :inspection_category)
                """), {
                    'product_id': product_id,
                    'record_type': 'V3',
                    'order_type': '確定',
                    'order_number': order_numbers_str,
                    'start_month': start_month,
                    'instruction_date': delivery_date,
                    'instruction_quantity': new_total,
                    'month_type': 'first',
                    'day_number': delivery_date.day,
                    'inspection_category': inspection_category
                })

                if within_window and difference != 0:
                    self.latest_quantity_changes.append({
                        'product_code': product_code,
                        'product_name': item['product_name'] or product_code,
                        'inspection_category': inspection_category,
                        'instruction_date': delivery_date,
                        'previous_quantity': base_quantity,
                        'new_quantity': new_total,
                        'difference': difference,
                        'order_type': '確定',
                        'order_numbers': sorted(current_order_numbers) if current_order_numbers else []
                    })

                instruction_count += 1

            session.commit()
            return instruction_count
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()


    def _create_delivery_progress(self, grouped_data: List[Dict],
                                  product_ids: Dict[str, int]) -> int:
        """delivery_progress へ登録"""
        session = self.db.get_session()
        progress_count = 0

        try:
            for item in grouped_data:
                product_code = item['product_code']
                product_id = product_ids.get(product_code)
                if not product_id:
                    continue

                delivery_date = item['delivery_date']
                inspection_category = item['inspection_category']
                order_details: Dict[str, int] = item.get('order_details', {})

                # 内示の集約レコードを削除（同じ製品コードの内示を納期までまとめて削除）
                deleted_rows = session.execute(text("""
                    DELETE FROM delivery_progress
                    WHERE product_id = :product_id
                      AND order_type = '内示'
                      AND delivery_date <= :delivery_date
                """), {
                    'product_id': product_id,
                    'delivery_date': delivery_date
                }).rowcount
                if deleted_rows > 0:
                    print(f"  内示削除: {product_code} 納期<={delivery_date} 件数={deleted_rows}")

                due_date = delivery_date
                issue_date = item.get('issue_date')
                delivery_date_value = due_date

                order_id = f"KUBOTA-KAKUTEI-{delivery_date.strftime('%Y%m%d')}-{product_code}-{inspection_category}"
                total_quantity = sum(order_details.values())
                current_order_numbers = set(order_details.keys())

                existing = session.execute(text("""
                    SELECT id, order_quantity, order_number
                    FROM delivery_progress
                    WHERE order_id = :order_id
                """), {'order_id': order_id}).fetchone()

                existing_qty_value = 0
                existing_order_numbers = set()
                if existing:
                    if existing[1] is not None:
                        existing_qty_value = int(existing[1])
                    if existing[2]:
                        existing_order_numbers = set(existing[2].split('+'))

                new_order_numbers = current_order_numbers - existing_order_numbers
                addition_quantity = sum(order_details[order_no] for order_no in new_order_numbers)

                if existing:
                    # 再インポートで新規の発注番号がある場合のみ数量を加算
                    total_quantity = existing_qty_value + addition_quantity
                else:
                    total_quantity = addition_quantity

                combined_order_numbers = sorted(existing_order_numbers.union(current_order_numbers))
                order_numbers_str = '+'.join(combined_order_numbers) if combined_order_numbers else None

                notes_base = f'品番: {product_code} / 検区: {inspection_category} (確定受注CSV)'
                if issue_date:
                    notes_base += f' / 受注日: {issue_date}'
                if order_numbers_str:
                    notes_base += f' / 発注番号: {order_numbers_str}'

                params = {
                    'order_id': order_id,
                    'product_id': product_id,
                    'order_date': due_date,
                    'delivery_date': delivery_date_value,
                    'order_quantity': total_quantity,
                    'customer_code': item['customer_code'] or 'KUBOTA_K',
                    'customer_name': 'クボタ様(確定)',
                    'order_type': '確定',
                    'order_number': order_numbers_str,
                    'notes': notes_base,
                    'priority': 3
                }

                if existing:
                    session.execute(text("""
                        UPDATE delivery_progress
                        SET order_quantity = :order_quantity,
                            order_date = :order_date,
                            delivery_date = :delivery_date,
                            customer_name = :customer_name,
                            order_type = :order_type,
                            order_number = :order_number,
                            notes = :notes
                        WHERE order_id = :order_id
                    """), params)
                else:
                    session.execute(text("""
                        INSERT INTO delivery_progress
                        (order_id, product_id, order_date, delivery_date,
                         order_quantity, shipped_quantity, status,
                         customer_code, customer_name, order_type, order_number, priority, notes)
                        VALUES
                        (:order_id, :product_id, :order_date, :delivery_date,
                         :order_quantity, 0, '未出荷',
                         :customer_code, :customer_name, :order_type, :order_number, :priority, :notes)
                    """), params)

                progress_count += 1

            session.commit()
            return progress_count
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()


    @staticmethod
    def _parse_issue_date(issue_str: str) -> Optional[date]:
        """発行日（YYMMDD形式想定）をdate化"""
        if not issue_str or issue_str.lower() == 'nan':
            return None
        issue_str = issue_str.strip()
        if len(issue_str) != 6 or not issue_str.isdigit():
            return None
        year = 2000 + int(issue_str[:2])
        month = int(issue_str[2:4])
        day = int(issue_str[4:6])
        try:
            return date(year, month, day)
        except ValueError:
            return None

    @staticmethod
    def _parse_delivery_date(delivery_str: str, issue_date: Optional[date]) -> Optional[date]:
        """納期（MMDD形式想定）をdate化。発行日から年度を補完"""
        if not delivery_str or delivery_str.lower() == 'nan':
            return None
        delivery_str = delivery_str.strip()
        if len(delivery_str) != 4 or not delivery_str.isdigit():
            return None

        month = int(delivery_str[:2])
        day = int(delivery_str[2:])

        base_year = issue_date.year if issue_date else date.today().year
        if issue_date and (month, day) < (issue_date.month, issue_date.day):
            base_year += 1

        try:
            return date(base_year, month, day)
        except ValueError:
            return None

    @staticmethod
    def _safe_int(value) -> int:
        """文字列/数値を安全にintへ変換"""
        try:
            if value is None:
                return 0
            if isinstance(value, (int, float)):
                return int(float(value))
            value_str = str(value).strip()
            if not value_str or value_str.lower() == 'nan':
                return 0
            value_str = value_str.replace(',', '')
            return int(float(value_str))
        except Exception:
            return 0
