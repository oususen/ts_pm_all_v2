# app/services/tiera_riden_csv_import_service.py
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from services.tiera_csv_import_service import TieraCSVImportService
from sqlalchemy import text
from repository.calendar_repository import CalendarRepository
import unicodedata
import traceback


class TieraRidenCSVImportService(TieraCSVImportService):
    """ティエラ様（リーデン注文書）専用CSVインポートサービス"""

    HISTORY_PREFIX = "[ティエラ様・リーデン確定]"
    DELIVERY_CODE_KEYWORDS = ("納入", "納入先")
    DELIVERY_CODE_POSTFIXES = ("コード", "ｺｰﾄﾞ", "code", "cd")
    LEAD_TIME_OVERRIDES = {
        "000010": 2,
        "000030": 2,
    }

    COL_ORDER_NUMBER = 0     # 発注番号
    COL_DRAWING_NO = 5       # 品目コード
    COL_DELIVERY_DATE = 9    # 納期
    COL_QUANTITY = 10        # 発注数量
    COL_PRODUCT_NAME_JP = 7  # 品目
    COL_PRODUCT_NAME_EN = 7  # 品目（英名なしのため同列を使用）
    COL_MODEL_NO = 6         # 型番（品目コードが空の際のフォールバック）

    def __init__(self, db_manager):
        super().__init__(db_manager)
        self.calendar_repo = CalendarRepository(db_manager)

    def import_csv_data(self, uploaded_file,
                        create_progress: bool = True) -> Tuple[bool, str]:
        """CSVを読み込み、基底クラスの処理を実行"""
        success, message = super().import_csv_data(uploaded_file, create_progress)
        if success:
            return success, f"【リーデン確定】{message}"
        return success, message

    def _group_by_product_and_date(self, df,
                                   drawing_col: str,
                                   delivery_col: str,
                                   quantity_col: str,
                                   product_name_jp_col: str,
                                   product_name_en_col: str) -> List[Dict]:
        """型番と納期単位でグルーピング（リーデン注文書フォーマット対応）"""
        grouped_data = []

        fallback_col = None
        columns = df.columns.tolist()
        delivery_code_col = self._find_delivery_code_column(columns)
        order_number_col = columns[self.COL_ORDER_NUMBER] if len(columns) > self.COL_ORDER_NUMBER else None
        if len(columns) > self.COL_MODEL_NO:
            fallback_col = columns[self.COL_MODEL_NO]

        for _, row in df.iterrows():
            drawing_no = str(row[drawing_col]).strip()
            if not drawing_no or drawing_no == 'nan':
                if fallback_col and fallback_col in row:
                    drawing_no = str(row[fallback_col]).strip()

            drawing_no = self._normalize_drawing_no(drawing_no)
            delivery_date_str = str(row[delivery_col]).strip()
            quantity_str = str(row[quantity_col]).strip()
            product_name_jp = str(row[product_name_jp_col]).strip()
            product_name_en = str(row[product_name_en_col]).strip()
            delivery_code = ''
            if delivery_code_col and delivery_code_col in row.index:
                delivery_code = self._normalize_delivery_code(str(row[delivery_code_col]).strip())

            order_number = ''
            if order_number_col and order_number_col in row.index:
                order_number = str(row[order_number_col]).strip()
                if order_number == 'nan':
                    order_number = ''

            if product_name_jp == 'nan':
                product_name_jp = ''
            if product_name_en == 'nan':
                product_name_en = ''

            if not drawing_no:
                continue

            if not delivery_date_str or delivery_date_str == 'nan':
                continue

            delivery_date = self._parse_date(delivery_date_str)
            if not delivery_date:
                continue

            try:
                quantity = int(float(quantity_str)) if quantity_str and quantity_str != 'nan' else 0
            except Exception:
                quantity = 0

            if quantity <= 0:
                continue

            grouped_data.append({
                'drawing_no': drawing_no,
                'product_name_jp': product_name_jp,
                'product_name_en': product_name_en or product_name_jp,
                'delivery_date': delivery_date,
                'quantity': quantity,
                'delivery_code': delivery_code,
                'order_number': order_number
            })

        aggregated = {}
        for item in grouped_data:
            key = (item['drawing_no'], item['delivery_date'])
            if key not in aggregated:
                aggregated[key] = {
                    'drawing_no': item['drawing_no'],
                    'product_name_jp': item['product_name_jp'],
                    'product_name_en': item['product_name_en'],
                    'delivery_date': item['delivery_date'],
                    'quantity': 0,
                    'delivery_code': item.get('delivery_code', ''),
                    'order_numbers': set(),
                    'order_details': {}
                }
            aggregated[key]['quantity'] += item['quantity']
            if not aggregated[key].get('delivery_code') and item.get('delivery_code'):
                aggregated[key]['delivery_code'] = item['delivery_code']

            # 発注番号を収集
            order_number = item.get('order_number', '')
            if order_number:
                aggregated[key]['order_numbers'].add(order_number)
                aggregated[key]['order_details'][order_number] = aggregated[key]['order_details'].get(order_number, 0) + item['quantity']

        # order_numbersをソート済みリストに変換
        result = []
        for item in aggregated.values():
            item['order_numbers'] = sorted(item['order_numbers'])
            result.append(item)
        print(f"[リーデン] グループ数: {len(result)}件")
        return result

    def _create_production_instructions(self, grouped_data: List[Dict],
                                        product_ids: Dict) -> int:
        """確定受注として生産指示を登録"""
        session = self.db.get_session()
        instruction_count = 0

        try:
            for item in grouped_data:
                drawing_no = item['drawing_no']
                delivery_date = item['delivery_date']
                quantity = item['quantity']
                order_details: Dict[str, int] = item.get('order_details', {})

                product_id = product_ids.get(drawing_no)
                if not product_id:
                    continue

                year_month = delivery_date.strftime('%Y%m')

                # 既存レコードから発注番号を取得
                existing_row = session.execute(text("""
                    SELECT instruction_quantity, order_number
                    FROM production_instructions_detail
                    WHERE product_id = :product_id
                      AND instruction_date = :instruction_date
                      AND inspection_category = :inspection_category
                """), {
                    'product_id': product_id,
                    'instruction_date': delivery_date,
                    'inspection_category': 'N'
                }).fetchone()

                base_quantity = int(existing_row[0]) if existing_row and existing_row[0] is not None else 0
                previous_order_numbers = set()
                if existing_row and existing_row[1]:
                    previous_order_numbers = set(existing_row[1].split('+'))

                current_order_numbers = set(order_details.keys())
                is_naiji_stub = existing_row is not None and not previous_order_numbers

                if not existing_row or is_naiji_stub:
                    addition_quantity = sum(order_details.values()) if order_details else quantity
                else:
                    new_order_numbers = current_order_numbers - previous_order_numbers
                    addition_quantity = sum(order_details[order_no] for order_no in new_order_numbers) if new_order_numbers else 0

                if not existing_row or is_naiji_stub:
                    new_total = addition_quantity if order_details else quantity
                else:
                    new_total = base_quantity + addition_quantity

                combined_order_numbers = sorted(previous_order_numbers.union(current_order_numbers)) if (previous_order_numbers or current_order_numbers) else []
                order_numbers_str = '+'.join(combined_order_numbers) if combined_order_numbers else None

                session.execute(text("""
                    REPLACE INTO production_instructions_detail
                    (product_id, record_type, order_type, order_number, start_month, instruction_date,
                    instruction_quantity, month_type, day_number, inspection_category)
                    VALUES (:product_id, :record_type, :order_type, :order_number, :start_month, :instruction_date,
                    :quantity, :month_type, :day_number, :inspection_category)
                """), {
                    'product_id': product_id,
                    'record_type': 'TIERA',
                    'order_type': '確定',
                    'order_number': order_numbers_str,
                    'start_month': year_month,
                    'instruction_date': delivery_date,
                    'quantity': new_total,
                    'month_type': 'first',
                    'day_number': delivery_date.day,
                    'inspection_category': 'N'
                })

                instruction_count += 1

            session.commit()
            print(f"[リーデン] 生産指示登録（確定）: {instruction_count}件")
            return instruction_count

        except Exception as e:
            session.rollback()
            print(f"[リーデン] 生産指示登録エラー: {e}")
            return 0
        finally:
            session.close()


    def _create_delivery_progress(self, grouped_data: List[Dict],
                                  product_ids: Dict) -> int:
        """確定受注として納入進捗を登録"""
        
        # 事前に出荷日を計算（カレンダーリポジトリのセッションがメイントランザクションに干渉しないように）
        for item in grouped_data:
            delivery_date = item['delivery_date']
            delivery_code = (item.get('delivery_code') or '').strip()
            item['shipping_date'] = self._calculate_shipping_date(delivery_date, delivery_code)
        
        session = self.db.get_session()
        progress_count = 0

        try:
            for item in grouped_data:
                drawing_no = item['drawing_no']
                delivery_date = item['delivery_date']
                quantity = item['quantity']
                delivery_code = (item.get('delivery_code') or '').strip()
                shipping_date = item['shipping_date']  # 事前計算済みの値を使用
                order_details: Dict[str, int] = item.get('order_details', {})

                product_id = product_ids.get(drawing_no)
                if not product_id:
                    continue

                order_id = f"TIERA-RIDEN-KAKUTEI-{delivery_date.strftime('%Y%m%d')}-{drawing_no}"
                naiji_order_id = f"TIERA-{delivery_date.strftime('%Y%m%d')}-{drawing_no}"

                deleted_rows = session.execute(text("""
                    DELETE FROM delivery_progress
                    WHERE product_id = :product_id
                      AND delivery_date = :delivery_date
                      AND order_id = :naiji_order_id
                """), {
                    'product_id': product_id,
                    'delivery_date': delivery_date,
                    'naiji_order_id': naiji_order_id
                }).rowcount
                if deleted_rows > 0:
                    print(f"[リーデン] 内示データ削除: {drawing_no} 納期={delivery_date}")

                # 既存レコードのチェック
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

                current_order_numbers = set(order_details.keys())
                new_order_numbers = current_order_numbers - existing_order_numbers
                addition_quantity = sum(order_details[order_no] for order_no in new_order_numbers) if new_order_numbers else 0

                if existing:
                    total_quantity = existing_qty_value + addition_quantity
                else:
                    total_quantity = addition_quantity if order_details else quantity

                combined_order_numbers = sorted(existing_order_numbers.union(current_order_numbers))
                order_numbers_str = '+'.join(combined_order_numbers) if combined_order_numbers else None

                notes_base = f'図番: {drawing_no} (リーデン確定CSV)'
                if order_numbers_str:
                    notes_base += f' / 発注番号: {order_numbers_str}'

                if existing:
                    session.execute(text("""
                        UPDATE delivery_progress
                        SET order_date = :order_date,
                            order_quantity = :new_quantity,
                            order_type = :order_type,
                            order_number = :order_number,
                            delivery_location = :delivery_location,
                            priority = :priority,
                            notes = :notes
                        WHERE id = :progress_id
                    """), {
                        'progress_id': existing[0],
                        'order_date': shipping_date,
                        'new_quantity': total_quantity,
                        'order_type': '確定',
                        'order_number': order_numbers_str,
                        'delivery_location': delivery_code or None,
                        'priority': 3,
                        'notes': notes_base + ' (更新)'
                    })
                else:
                    try:
                        session.execute(text("""
                            INSERT INTO delivery_progress
                            (order_id, product_id, order_date, delivery_date,
                            order_quantity, shipped_quantity, status,
                            customer_code, customer_name, order_type, order_number, delivery_location, priority, notes)
                            VALUES
                            (:order_id, :product_id, :order_date, :delivery_date,
                            :order_quantity, 0, '未出荷',
                            :customer_code, :customer_name, :order_type, :order_number, :delivery_location, :priority, :notes)
                        """), {
                            'order_id': order_id,
                            'product_id': product_id,
                            'order_date': shipping_date,
                            'delivery_date': delivery_date,
                            'order_quantity': total_quantity,
                            'customer_code': 'TIERA_R',
                            'customer_name': 'ティエラ様（リーデン確定）',
                            'order_type': '確定',
                            'order_number': order_numbers_str,
                            'delivery_location': delivery_code or None,
                            'priority': 3,
                            'notes': notes_base
                        })
                    except Exception:
                        import traceback
                        traceback.print_exc()
                        raise

                progress_count += 1

            session.commit()
            print(f"[リーデン] 納入進捗登録（確定）: {progress_count}件")
            return progress_count

        except Exception as e:
            session.rollback()
            print(f"[リーデン] 納入進捗登録エラー: {e}")
            import traceback
            traceback.print_exc()
            return 0
        finally:
            session.close()

    def log_import_history(self, filename: str, message: str):
        """CSV取り込み履歴を記録（リーデン向けメッセージ）"""
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

    @staticmethod
    def _normalize_drawing_no(value: str) -> str:
        """余分な空白を除去して図番を正規化"""
        if not value or value == 'nan':
            return ''
        return "".join(value.split())

    @staticmethod
    def _normalize_delivery_code(value: str) -> str:
        if not value or value == 'nan':
            return ''
        normalized = unicodedata.normalize('NFKC', value)
        normalized = normalized.replace('-', '').replace(' ', '').replace('　', '')
        if normalized.isdigit():
            normalized = normalized.zfill(6)
        return normalized

    def _find_delivery_code_column(self, columns: List[str]) -> Optional[str]:
        for col in columns:
            normalized = unicodedata.normalize('NFKC', str(col)).lower()
            if any(keyword in normalized for keyword in self.DELIVERY_CODE_KEYWORDS):
                if any(postfix in normalized for postfix in self.DELIVERY_CODE_POSTFIXES):
                    return col
            if 'delivery' in normalized and 'code' in normalized:
                return col
        return None

    def _calculate_shipping_date(self, delivery_date: datetime, delivery_code: str) -> datetime:
        normalized_code = self._normalize_delivery_code(delivery_code)
        lead_days = self.LEAD_TIME_OVERRIDES.get(normalized_code, 0)
        if lead_days <= 0:
            return delivery_date

        calendar_repo = getattr(self, 'calendar_repo', None)
        if not calendar_repo:
            return delivery_date - timedelta(days=lead_days)

        return self._subtract_working_days(delivery_date, lead_days)

    def _subtract_working_days(self, base_date: datetime, days: int) -> datetime:
        if days <= 0:
            return base_date

        calendar_repo = getattr(self, 'calendar_repo', None)
        if not calendar_repo:
            return base_date - timedelta(days=days)

        remaining = days
        current = base_date

        while remaining > 0:
            current -= timedelta(days=1)
            try:
                is_working = calendar_repo.is_working_day(current)
            except Exception:
                # カレンダー取得で予期せぬ失敗があった場合は週末判定にフォールバック
                is_working = current.weekday() < 5

            if is_working:
                remaining -= 1

        return current
