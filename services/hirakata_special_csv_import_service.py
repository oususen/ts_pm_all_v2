# app/services/hirakata_special_csv_import_service.py
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Tuple, List, Dict, Optional
from sqlalchemy import text


class HirakataSpecialCSVImportService:
    """枚方向け特殊確定受注CSVインポートサービス（RCV_NVAN-2-特殊形式）"""

    HISTORY_PREFIX = "[枚方様・特殊CSV]"

    def __init__(self, db_manager):
        self.db = db_manager
        self.latest_quantity_changes: List[Dict] = []
        self.latest_quantity_change_window: Tuple[Optional[date], Optional[date]] = (None, None)

    # Public API -----------------------------------------------------------------

    def import_csv_data(self, uploaded_file,
                        create_progress: bool = True) -> Tuple[bool, str]:
        """特殊確定受注CSVを読み込み、指示・配送情報へ反映"""
        try:
            self.latest_quantity_changes = []
            window_start = date.today()
            window_end = window_start + timedelta(days=10)
            self.latest_quantity_change_window = (window_start, window_end)

            df = pd.read_csv(uploaded_file, encoding='cp932', dtype=str, header=None)
            df = df.fillna('')

            # NO列（列1、インデックス0）が47の行のみを抽出
            df_filtered = df[df[0].astype(str).str.strip() == '47'].copy()

            if df_filtered.empty:
                return False, "[特殊CSV] NOが47のレコードが見つかりませんでした。"

            grouped_data = self._group_by_product_and_date(df_filtered)
            if not grouped_data:
                return False, "[特殊CSV] 有効なレコードが見つかりませんでした。"

            product_ids = self._import_products(grouped_data)
            if not product_ids:
                return False, "[特殊CSV] 製品マスタ登録に失敗しました。"

            instruction_count = self._create_production_instructions(grouped_data, product_ids)

            progress_count = 0
            if create_progress:
                progress_count = self._create_delivery_progress(grouped_data, product_ids)

            if create_progress:
                return True, f"[特殊CSV] {instruction_count}件の受注指示と{progress_count}件の配送進捗を登録しました。"
            return True, f"[特殊CSV] {instruction_count}件の受注指示を登録しました。"

        except Exception as e:
            error_msg = f"[特殊CSV] インポートエラー: {str(e)}"
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
        """品番×納期単位で数量を集計"""
        aggregated: Dict[Tuple, Dict] = {}

        for _, row in df.iterrows():
            # 列6（インデックス5）: 製品コード
            product_code = str(row[5]).strip() if len(row) > 5 else ''
            if not product_code or product_code.lower() == 'nan':
                continue

            # 列11（インデックス10）: 品名
            product_name = str(row[10]).strip() if len(row) > 10 else ''

            # 列25（インデックス24）: 数量
            quantity = self._safe_int(row[24]) if len(row) > 24 else 0
            if quantity <= 0:
                continue

            # 列4（インデックス3）: 発注番号
            order_number = str(row[3]).strip() if len(row) > 3 else ''

            # 列24（インデックス23）: 納期（MMDD形式）
            delivery_date_str = str(row[23]).strip() if len(row) > 23 else ''

            delivery_date = self._parse_delivery_date(delivery_date_str)
            if not delivery_date:
                continue

            # 検査区分はデフォルトで'N'（特殊CSVには検査区分の列がない）
            inspection_category = 'N'

            customer_code = 'HIRAKATA_S'
            customer_name = '枚方様(特殊)'

            key = (product_code, delivery_date, inspection_category, customer_code, customer_name)
            entry = aggregated.setdefault(key, {
                'product_code': product_code,
                'product_name': product_name,
                'delivery_date': delivery_date,
                'inspection_category': inspection_category,
                'customer_code': customer_code,
                'customer_name': customer_name,
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
                        (product_code, product_name)
                        VALUES (:product_code, :product_name)
                    """), {
                        'product_code': product_code,
                        'product_name': item['product_name'] or product_code
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

                # 内示の集約レコードを削除（同じ製品コード×指示日の内示は確定優先）
                naiji_order_id = f"ORD-{delivery_date.strftime('%Y%m%d')}-{product_code}"
                session.execute(text("""
                    DELETE FROM delivery_progress
                    WHERE order_id = :order_id AND order_type = '内示'
                """), {'order_id': naiji_order_id})

                order_id = f"HIRAKATA-SPECIAL-{delivery_date.strftime('%Y%m%d')}-{product_code}-{inspection_category}"
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

                notes_base = f'品番: {product_code} / 検区: {inspection_category} (特殊確定受注CSV)'
                if order_numbers_str:
                    notes_base += f' / 発注番号: {order_numbers_str}'

                params = {
                    'order_id': order_id,
                    'product_id': product_id,
                    'order_date': delivery_date,
                    'delivery_date': delivery_date,
                    'order_quantity': total_quantity,
                    'customer_code': item['customer_code'] or 'HIRAKATA_S',
                    'customer_name': '枚方様(特殊)',
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
    def _parse_delivery_date(delivery_str: str) -> Optional[date]:
        """納期（MMDD形式想定）をdate化"""
        if not delivery_str or delivery_str.lower() == 'nan':
            return None
        delivery_str = delivery_str.strip()

        # MMDD形式（4桁）
        if len(delivery_str) == 4 and delivery_str.isdigit():
            month = int(delivery_str[:2])
            day = int(delivery_str[2:4])
            year = date.today().year

            # 月が過去の場合は翌年とする
            if month < date.today().month:
                year += 1

            try:
                return date(year, month, day)
            except ValueError:
                return None

        # MDD形式（3桁、例: 106 = 1月6日）
        if len(delivery_str) == 3 and delivery_str.isdigit():
            month = int(delivery_str[0])
            day = int(delivery_str[1:3])
            year = date.today().year

            # 月が過去の場合は翌年とする
            if month < date.today().month:
                year += 1

            try:
                return date(year, month, day)
            except ValueError:
                return None

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
