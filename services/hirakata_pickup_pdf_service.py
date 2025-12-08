# app/services/hirakata_pickup_pdf_service.py
"""枚方集荷依頼書PDF生成サービス"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Table, TableStyle
from datetime import date, timedelta
from typing import List, Dict, Tuple
from sqlalchemy import text
from io import BytesIO
import os
import math


class HirakataPickupPDFService:
    """枚方集荷依頼書PDF生成サービス"""

    # 固定情報
    COMPANY_NAME = "ダイソウ工業株式会社"
    CONTACT_PERSON = "辻岡(ツジオカ)"
    PICKUP_LOCATION = "ダイソウ工業（株）三重県津市芸濃町北神山１４７０－３"
    DELIVERY_LOCATION = "ロジスクエア枚方"
    TRANSPORT_COMPANY = "大友ﾛｼﾞｽﾃｨｸｽｻｰﾋﾞｽ(株)京都営業所 配車担当者 御中"
    EMAIL = "kyouto03@otomo-logi.co.jp"
    DESTINATION = "枚方製造所行き"

    def __init__(self, db_manager):
        self.db = db_manager
        self._register_font()

    def _register_font(self):
        """日本語フォントを登録"""
        # 既に登録済みの場合はスキップ
        if 'JapaneseFont' in pdfmetrics.getRegisteredFontNames():
            return

        # 日本語フォントパス（優先順位順）
        font_paths = [
            # Windows標準フォント
            ('C:/Windows/Fonts/msgothic.ttc', 'MS Gothic'),
            ('C:/Windows/Fonts/GOTHIC.TTF', 'MS Gothic'),
            ('C:/Windows/Fonts/BIZ-UDGothicR.ttc', 'BIZ UD Gothic'),
            # IPAフォント
            ('C:/Windows/Fonts/ipaexg.ttf', 'IPAex Gothic'),
            ('/usr/share/fonts/opentype/ipaexfont-gothic/ipaexg.ttf', 'IPAex Gothic'),
            # プロジェクト内のフォント
            (os.path.join(os.path.dirname(__file__), '..', 'fonts', 'ipaexg.ttf'), 'IPAex Gothic')
        ]

        for font_path, font_name in font_paths:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont('JapaneseFont', font_path))
                    print(f"✅ フォント登録成功: {font_name} ({font_path})")
                    return
                except Exception as e:
                    print(f"⚠️ フォント登録失敗 ({font_name}): {e}")
                    continue

        # フォントが見つからない場合はエラー
        raise FileNotFoundError(
            "日本語フォントが見つかりません。\n"
            "MS Gothic、BIZ UD Gothic、またはJapaneseFontフォントをインストールしてください。"
        )

    def generate_pickup_request_pdf(self, start_date: date, end_date: date) -> BytesIO:
        """
        枚方集荷依頼書PDFを生成

        Args:
            start_date: 開始日
            end_date: 終了日

        Returns:
            BytesIO: PDF データ
        """
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        self._canvas = c

        # 依頼日（今日）
        request_date = date.today()

        # ヘッダー
        self._draw_header(c, width, height, request_date)

        # 固定情報
        self._draw_fixed_info(c, width, height)

        # 納品日ごとのデータを取得して描画
        y_position = height - 300

        # 稼働日リスト（納品日）を取得
        working_dates, working_set = self._get_working_dates(start_date, end_date)

        for delivery_date in working_dates:
            container_data, max_lead_time = self._get_container_data_for_date(delivery_date)

            # 製品の設定リードタイム（日数）を考慮して集荷日を算出
            lead_days = max(int(max_lead_time or 1), 1)
            pickup_date = self._subtract_working_days(delivery_date, lead_days, working_set)

            y_position = self._draw_date_section(
                c, width, y_position,
                pickup_date, delivery_date,
                container_data
            )

            # ページ下部に余白が無ければ改ページ
            if y_position < 150:
                c.showPage()
                y_position = height - 100

        # フッター
        self._draw_footer(c, width, 100)

        c.save()
        buffer.seek(0)
        return buffer

    def _draw_header(self, c: canvas.Canvas, width: float, height: float, request_date: date):
        """ヘッダー描画"""
        c.setFont("JapaneseFont", 20)
        c.drawString(100, height - 80, "集荷依頼書")

        # 依頼日
        c.setFont("JapaneseFont", 10)
        date_x = width - 250
        c.drawString(date_x, height - 50, f"ご依頼日: {request_date.year} 年")
        c.drawString(date_x + 100, height - 50, f"{request_date.month} 月")
        c.drawString(date_x + 150, height - 50, f"{request_date.day} 日")

        # 宛先
        c.setFont("JapaneseFont", 10)
        c.drawString(100, height - 100, self.TRANSPORT_COMPANY)

        # 赤文字で「枚方製造所行き」
        c.setFillColor(colors.red)
        c.setFont("JapaneseFont", 12)
        c.drawString(100, height - 120, self.DESTINATION)
        c.setFillColor(colors.black)

    def _draw_fixed_info(self, c: canvas.Canvas, width: float, height: float):
        """固定情報描画"""
        c.setFont("JapaneseFont", 10)

        # 発信者
        c.drawString(250, height - 120, f"発信者: {self.COMPANY_NAME}　{self.CONTACT_PERSON}")

        # テーブル形式で集荷場所と納入先を描画
        table_data = [
            ["集荷場所:", self.PICKUP_LOCATION],
            ["納入先:", self.DELIVERY_LOCATION]
        ]

        table = Table(table_data, colWidths=[80, 400])
        table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), 'JapaneseFont', 10),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))

        table.wrapOn(c, width, height)
        table.drawOn(c, 100, height - 200)

    def _draw_date_section(self, c: canvas.Canvas, width: float, y_position: float,
                           pickup_date: date, delivery_date: date,
                           container_data: List[Dict]) -> float:
        """
        日付ごとの集荷依頼セクションを描画
        """

        rows = []
        # 行の列数をテーブル全体で統一（6列）
        rows.append([
            "集 荷 日:",
            f"{pickup_date.year}", "年",
            f"{pickup_date.month}", "月",
            f"{pickup_date.day} 日"
        ])

        # 当日の出荷製品に紐づく容器コードを動的に抽出（重複除去）
        container_types: List[str] = []
        for container_item in container_data:
            code = container_item.get('container_code') or 'UNKNOWN'
            if code not in container_types:
                container_types.append(code)
        # 該当が無い場合のみ従来のデフォルトを表示
        if not container_types:
            container_types = ["アミ", "グレー（小）", "グレー", "青"]

        handled_codes = set()
        row_index = 1
        for container_code in container_types:
            container_info = next((c for c in container_data if c.get('container_code') == container_code), None)
            handled_codes.add(container_code)

            if container_info:
                container_name = container_info.get('container_name') or container_code
                container_color = container_info.get('color', '')
                quantity = int(container_info.get('total_containers', 0) or 0)
                # アミ容器の場合は常に単位を「アミ」に設定（出荷なしでも）
                if 'アミ' in container_name or container_code == 'AMI':
                    unit = 'アミ'
                else:
                    unit = container_info.get('unit', 'ポリ')
            else:
                container_name = container_code
                container_color = ''
                quantity = 0
                # アミ容器の場合は常に単位を「アミ」に設定
                if 'アミ' in container_code or container_code == 'AMI':
                    unit = 'アミ'
                else:
                    unit = 'ポリ'

            rows.append([
                f"容    器{row_index}:",
                container_name,
                container_color,
                str(quantity),
                unit,
                "kg"
            ])
            row_index += 1

        rows.append([
            "納 品 日:",
            f"{delivery_date.year}", "年",
            f"{delivery_date.month}", "月",
            f"{delivery_date.day} 日"
        ])

        table = Table(rows, colWidths=[80, 90, 25, 60, 25, 60])
        styles = [
            ('FONT', (0, 0), (-1, -1), 'JapaneseFont', 10),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BACKGROUND', (0, 0), (0, 0), colors.white),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]
        container_start = 1
        container_end = max(container_start, len(rows) - 2)  # コンテナ行の最終インデックス
        if container_end >= container_start:
            styles.append(('ALIGN', (3, container_start), (3, container_end), 'RIGHT'))
        table.setStyle(TableStyle(styles))

        table.wrapOn(c, width, 800)
        table.drawOn(c, 100, y_position - 120)

        return y_position - 140

    def _draw_footer(self, c: canvas.Canvas, width: float, y_position: float):
        """フッター描画"""
        c.setFont("JapaneseFont", 9)
        c.drawString(100, y_position, "集荷前日の17時までに下記アドレスにメールにてご依頼ください")
        c.drawString(100, y_position - 15, f"E-MAIL  {self.EMAIL}")

    def _get_container_data_for_date(self, target_date: date) -> Tuple[List[Dict], int]:
        """
        指定日の容器別集計データを取得

        Args:
            target_date: 対象日

        Returns:
            Tuple[List[Dict], int]: 容器コード、容器名、必要容器数の集計、リードタイム最大値
        """
        session = self.db.get_session()

        try:
            query = text("""
                SELECT
                    cc.container_code,
                    cc.name AS container_name,
                    COALESCE(p.capacity, 0) AS capacity_per_container,
                    COALESCE(p.lead_time_days, 1) AS lead_time_days,
                    COALESCE(
                        NULLIF(dp.planned_quantity, 0),
                        NULLIF(dp.manual_planning_quantity, 0),
                        dp.order_quantity,
                        0
                    ) AS effective_quantity
                FROM delivery_progress dp
                INNER JOIN products p ON dp.product_id = p.id
                LEFT JOIN container_capacity cc ON p.used_container_id = cc.id
                WHERE DATE(dp.delivery_date) = :target_date
                  AND dp.customer_code = 'HIRAKATA_K'
                  AND COALESCE(
                        NULLIF(dp.planned_quantity, 0),
                        NULLIF(dp.manual_planning_quantity, 0),
                        dp.order_quantity,
                        0
                  ) > 0
            """)

            rows = session.execute(query, {'target_date': target_date}).fetchall()

            container_totals: Dict[str, Dict] = {}
            max_lead_time = 1
            for row in rows:
                container_code = getattr(row, 'container_code', None) or 'UNKNOWN'
                container_name = getattr(row, 'container_name', None) or '不明容器'
                capacity = int(getattr(row, 'capacity_per_container', 0) or 0)
                lead_time_days = int(getattr(row, 'lead_time_days', 1) or 1)
                max_lead_time = max(max_lead_time, lead_time_days)
                quantity = int(getattr(row, 'effective_quantity', 0) or 0)

                effective_capacity = capacity if capacity > 0 else 1
                containers_needed = math.ceil(quantity / effective_capacity) if quantity > 0 else 0

                if containers_needed <= 0:
                    continue

                if container_code not in container_totals:
                    container_totals[container_code] = {
                        'container_code': container_code,
                        'container_name': container_name,
                        'total_containers': 0
                    }
                container_totals[container_code]['total_containers'] += containers_needed

            return sorted(container_totals.values(), key=lambda x: x['container_code']), max_lead_time

        except Exception as e:
            print(f"容器データ取得エラー: {e}")
            import traceback
            traceback.print_exc()
            return [], 1
        finally:
            session.close()

    def _get_working_dates(self, start_date: date, end_date: date) -> Tuple[List[date], set]:
        """
        company_calendar の稼働日のみ取得（is_working_day=1）。該当なしなら空リストを返す。
        """
        session = self.db.get_session()
        try:
            buffer_days = 14  # リードタイムさかのぼり用に少し前から取得
            query = text("""
                SELECT calendar_date
                FROM company_calendar
                WHERE calendar_date BETWEEN :start_buf AND :end_date
                  AND is_working_day = 1
                ORDER BY calendar_date
            """)
            start_buf = start_date - timedelta(days=buffer_days)
            rows = session.execute(query, {
                'start_buf': start_buf,
                'end_date': end_date
            }).fetchall()

            if not rows:
                return [], set()

            working_set = {r[0] for r in rows}
            dates = [d for d in (r[0] for r in rows) if start_date <= d <= end_date]
            return dates, working_set
        finally:
            session.close()

    def _subtract_working_days(self, base_date: date, days: int, working_set: set) -> date:
        """
        稼働日ベースで日数をさかのぼる（working_set が空なら暦日で計算）。
        """
        if days <= 0:
            return base_date

        current = base_date
        remaining = days
        while remaining > 0:
            current -= timedelta(days=1)
            if not working_set or current in working_set:
                remaining -= 1
        return current

    def get_daily_product_list(self, start_date: date, end_date: date) -> Dict[date, List[Dict]]:
        """
        指定期間の日別製品リストを取得

        Args:
            start_date: 開始日
            end_date: 終了日

        Returns:
            Dict[date, List[Dict]]: 日付ごとの製品リスト
        """
        session = self.db.get_session()

        try:
            query = text("""
                SELECT
                    DATE(dp.delivery_date) AS delivery_date,
                    p.product_code,
                    p.product_name,
                    p.capacity,
                    cc.container_code,
                    cc.name AS container_name,
                    COALESCE(
                        NULLIF(dp.planned_quantity, 0),
                        NULLIF(dp.manual_planning_quantity, 0),
                        dp.order_quantity,
                        0
                    ) AS effective_quantity
                FROM delivery_progress dp
                INNER JOIN products p ON dp.product_id = p.id
                LEFT JOIN container_capacity cc ON p.used_container_id = cc.id
                WHERE DATE(dp.delivery_date) BETWEEN :start_date AND :end_date
                  AND dp.customer_code = 'HIRAKATA_K'
                  AND COALESCE(
                        NULLIF(dp.planned_quantity, 0),
                        NULLIF(dp.manual_planning_quantity, 0),
                        dp.order_quantity,
                        0
                  ) > 0
                ORDER BY delivery_date, p.product_code
            """)

            rows = session.execute(query, {
                'start_date': start_date,
                'end_date': end_date
            }).fetchall()

            # 日付ごとにグループ化
            daily_products: Dict[date, List[Dict]] = {}
            for row in rows:
                delivery_date = getattr(row, 'delivery_date')
                product_code = getattr(row, 'product_code', '')
                product_name = getattr(row, 'product_name', '')
                capacity = int(getattr(row, 'capacity', 0) or 0)
                container_code = getattr(row, 'container_code', None) or '不明'
                container_name = getattr(row, 'container_name', None) or '不明容器'
                quantity = int(getattr(row, 'effective_quantity', 0) or 0)

                effective_capacity = capacity if capacity > 0 else 1
                containers_needed = math.ceil(quantity / effective_capacity) if quantity > 0 else 0

                if delivery_date not in daily_products:
                    daily_products[delivery_date] = []

                daily_products[delivery_date].append({
                    'product_code': product_code,
                    'product_name': product_name,
                    'quantity': quantity,
                    'container_code': container_code,
                    'container_name': container_name,
                    'containers_needed': containers_needed
                })

            return daily_products

        except Exception as e:
            print(f"日別製品リスト取得エラー: {e}")
            import traceback
            traceback.print_exc()
            return {}
        finally:
            session.close()
