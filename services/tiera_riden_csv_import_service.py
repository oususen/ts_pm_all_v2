# app/services/tiera_riden_csv_import_service.py
from typing import List, Dict, Tuple
from datetime import datetime
from services.tiera_csv_import_service import TieraCSVImportService
from sqlalchemy import text


class TieraRidenCSVImportService(TieraCSVImportService):
    """ティエラ様（リーデン注文書）専用CSVインポートサービス"""

    COL_DRAWING_NO = 5       # 品目コード
    COL_DELIVERY_DATE = 9    # 納期
    COL_QUANTITY = 10        # 発注数量
    COL_PRODUCT_NAME_JP = 7  # 品目
    COL_PRODUCT_NAME_EN = 7  # 品目（英名なしのため同列を使用）
    COL_MODEL_NO = 6         # 型番（品目コードが空の際のフォールバック）

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
                'quantity': quantity
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
                    'quantity': 0
                }
            aggregated[key]['quantity'] += item['quantity']

        result = list(aggregated.values())
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

                product_id = product_ids.get(drawing_no)
                if not product_id:
                    continue

                year_month = delivery_date.strftime('%Y%m')

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
                    'order_number': None,
                    'start_month': year_month,
                    'instruction_date': delivery_date,
                    'quantity': quantity,
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
        session = self.db.get_session()
        progress_count = 0

        try:
            for item in grouped_data:
                drawing_no = item['drawing_no']
                delivery_date = item['delivery_date']
                quantity = item['quantity']

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

                existing = session.execute(text("""
                    SELECT id FROM delivery_progress
                    WHERE order_id = :order_id
                """), {'order_id': order_id}).fetchone()

                if existing:
                    session.execute(text("""
                        UPDATE delivery_progress
                        SET order_quantity = :new_quantity,
                            order_type = :order_type,
                            order_number = :order_number,
                            priority = :priority,
                            notes = :notes
                        WHERE id = :progress_id
                    """), {
                        'progress_id': existing[0],
                        'new_quantity': quantity,
                        'order_type': '確定',
                        'order_number': None,
                        'priority': 3,
                        'notes': f'ティエラ様図番（リーデン確定）: {drawing_no} (更新)'
                    })
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
                    """), {
                        'order_id': order_id,
                        'product_id': product_id,
                        'order_date': delivery_date,
                        'delivery_date': delivery_date,
                        'order_quantity': quantity,
                        'customer_code': 'TIERA_R',
                        'customer_name': 'ティエラ様（リーデン確定）',
                        'order_type': '確定',
                        'order_number': None,
                        'priority': 3,
                        'notes': f'図番: {drawing_no} (リーデン確定CSV)'
                    })

                progress_count += 1

            session.commit()
            print(f"[リーデン] 納入進捗登録（確定）: {progress_count}件")
            return progress_count

        except Exception as e:
            session.rollback()
            print(f"[リーデン] 納入進捗登録エラー: {e}")
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

            session.execute(text("""
                INSERT INTO csv_import_history
                (filename, import_date, record_count, status, message)
                VALUES (:filename, :import_date, :record_count, :status, :message)
            """), {
                'filename': filename,
                'import_date': datetime.now(),
                'record_count': record_count,
                'status': '成功',
                'message': f"[ティエラ様・リーデン確定] {message}"
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
