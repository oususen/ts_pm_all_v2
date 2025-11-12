# -*- coding: utf-8 -*-
"""出荷指示書 PDF を生成するユーティリティ。"""

from __future__ import annotations

import os
import textwrap
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


JPN_WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]

COLOR_BLADE_BLUE = colors.HexColor("#bde3ff")
COLOR_BLADE_YELLOW = colors.HexColor("#fff59d")
COLOR_SEATBASE_GREEN = colors.HexColor("#a9d99a")
COLOR_TANK_BLUE = colors.HexColor("#8fd3ff")
COLOR_BOX_BORDER = colors.HexColor("#6b6b6b")
COLOR_BOX_EMPTY = colors.HexColor("#f5f5f5")
COLOR_RIDEN_PINK = colors.HexColor("#f7b7d2")

BOX_GAP = 2.5 * mm
BOX_ROW_HEIGHT = 26 * mm
BOX_ROW_SPACING = 4  # points


def register_japanese_fonts() -> None:
    """
    ReportLab で日本語を扱えるようにフォントを登録する。

    Windows環境ではMSゴシックまたはメイリオ、
    Linux環境ではNoto Sans JP、IPAゴシック、TakaoPゴシック、
    Mac環境ではヒラギノを使用する。
    既に登録済みの場合は何もしない。
    """
    if "MSGothic" in pdfmetrics.getRegisteredFontNames():
        return

    # Windowsフォント候補
    windows_fonts = [
        Path("C:/Windows/Fonts/msgothic.ttc"),
        Path("C:/Windows/Fonts/meiryo.ttc"),
        Path("C:/Windows/Fonts/msmincho.ttc"),
        Path("C:/Windows/Fonts/yugothic.ttf"),
    ]

    # Linuxフォント候補（Docker/Ubuntu用）
    # ReportLabはTrueTypeフォントのみサポート（PostScript outlinesは非サポート）
    linux_fonts = [
        # IPA ゴシック（TrueType - 推奨）
        Path("/usr/share/fonts/truetype/fonts-japanese-gothic.ttf"),
        Path("/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"),
        Path("/usr/share/fonts/truetype/ipafont/ipag.ttf"),
        Path("/usr/share/fonts/truetype/ipafont-gothic/ipag.ttf"),
        # Takao ゴシック（TrueType）
        Path("/usr/share/fonts/truetype/takao-gothic/TakaoPGothic.ttf"),
        # Noto Sans CJK JP（TrueType版があれば）
        Path("/usr/share/fonts/truetype/noto-cjk/NotoSansCJK-Regular.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSansCJK-jp-Regular.otf"),
    ]

    # Macフォント候補
    mac_fonts = [
        Path("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"),
        Path("/System/Library/Fonts/ヒラギノ角ゴシック ProN W3.otf"),
        Path("/Library/Fonts/ヒラギノ角ゴ ProN W3.otc"),
    ]

    # OSに応じて候補を選択
    if os.name == "nt":
        candidates: Sequence[Path] = windows_fonts
    elif os.uname().sysname == "Darwin":
        candidates = mac_fonts
    else:
        candidates = linux_fonts

    # 全候補を順番に試す（見つからない場合は全環境の候補も試す）
    all_candidates = list(candidates) + [p for p in (windows_fonts + linux_fonts + mac_fonts) if p not in candidates]

    # 各フォントを試して、最初に成功したものを使用
    font_registered = False
    last_error = None

    for font_path in all_candidates:
        if not font_path.exists():
            continue

        try:
            # フォント登録を試みる
            pdfmetrics.registerFont(TTFont("MSGothic", str(font_path)))
            pdfmetrics.registerFont(TTFont("MSGothic-Bold", str(font_path)))
            font_registered = True
            print(f"✅ 日本語フォントを登録しました: {font_path}")
            break
        except Exception as e:
            # このフォントは使えないので次を試す
            last_error = e
            print(f"⚠️ フォント読み込みエラー（次を試します）: {font_path} - {str(e)[:100]}")
            continue

    if not font_registered:
        error_msg = (
            "日本語フォントが見つからないか、読み込みに失敗しました。\n\n"
            "Dockerコンテナの場合は、以下のコマンドでフォントをインストールしてください:\n"
            "  apt-get update && apt-get install -y fonts-ipafont-gothic fonts-takao-gothic\n\n"
            "Windowsの場合は、システムフォントが正しくインストールされているか確認してください。\n"
            "Linuxの場合は、以下のいずれかをインストールしてください:\n"
            "  - fonts-ipafont-gothic (推奨)\n"
            "  - fonts-takao-gothic\n\n"
        )
        if last_error:
            error_msg += f"最後のエラー: {str(last_error)}"
        raise FileNotFoundError(error_msg)


def format_japanese_date(target_date: Union[date, datetime]) -> str:
    """
    日付を日本語形式 'M月D日(曜)' に変換して返す。

    Args:
        target_date: 変換する日付（dateまたはdatetimeオブジェクト）

    Returns:
        日本語形式の日付文字列（例：「11月4日(月)」）
    """
    if isinstance(target_date, datetime):
        target_date = target_date.date()
    if isinstance(target_date, date):
        weekday = JPN_WEEKDAYS[target_date.weekday()]
        return f"{target_date.month}月{target_date.day}日({weekday})"
    return str(target_date)


def draw_title_band(
    canv: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    width: float,
    height: float,
) -> None:
    """
    ページ上部に黒帯のタイトルを描画する。

    Args:
        canv: ReportLabのCanvasオブジェクト
        text: タイトルに表示するテキスト
        x: 描画開始位置のX座標
        y: 描画開始位置のY座標
        width: タイトル帯の幅
        height: タイトル帯の高さ
    """
    canv.saveState()
    canv.setFillColor(colors.black)
    canv.rect(x, y - height, width, height, stroke=0, fill=1)
    canv.setFillColor(colors.white)
    canv.setFont("MSGothic-Bold", 20)
    canv.drawCentredString(x + width / 2, y - height + (height - 16) / 2, text)
    canv.restoreState()


def draw_labeled_box(
    canv: canvas.Canvas,
    label: str,
    value: str,
    x: float,
    y: float,
    label_size=(18 * mm, 10 * mm),
    value_width: float = 55 * mm,
) -> None:
    """
    ラベルと値で構成される2列ボックスを描画する。

    Args:
        canv: ReportLabのCanvasオブジェクト
        label: ラベルテキスト（例：「出荷日」）
        value: 値テキスト（例：「11月4日(月)」）
        x: 描画開始位置のX座標
        y: 描画開始位置のY座標
        label_size: ラベル部分のサイズ（幅, 高さ）
        value_width: 値部分の幅
    """
    canv.saveState()
    label_w, label_h = label_size
    canv.setLineWidth(1)
    canv.rect(x, y - label_h, label_w, label_h, stroke=1, fill=0)
    canv.setFont("MSGothic-Bold", 12)
    canv.drawCentredString(x + label_w / 2, y - label_h + 2.5, label)

    canv.rect(x + label_w, y - label_h, value_width, label_h, stroke=1, fill=0)
    canv.setFont("MSGothic-Bold", 14)
    canv.drawCentredString(x + label_w + value_width / 2, y - label_h + 2.5, value)
    canv.restoreState()


def draw_confirmation_box(
    canv: canvas.Canvas,
    x: float,
    y: float,
    width: float,
    height: float,
    creator_text: str,
) -> None:
    """
    ヘッダー右側の確認／作成者枠を描画する。

    Args:
        canv: ReportLabのCanvasオブジェクト
        x: 描画開始位置のX座標
        y: 描画開始位置のY座標
        width: ボックスの幅
        height: ボックスの高さ
        creator_text: 作成者名
    """
    canv.saveState()
    canv.setLineWidth(1)
    canv.rect(x, y - height, width, height, stroke=1, fill=0)
    header_height = height * 0.45
    canv.line(x, y - header_height, x + width, y - header_height)
    canv.line(x + width / 2, y, x + width / 2, y - height)

    canv.setFont("MSGothic-Bold", 11)
    canv.drawCentredString(x + width / 4, y - header_height + 3, "確認")
    canv.drawCentredString(x + 3 * width / 4, y - header_height + 3, "作成")

    canv.setFont("MSGothic-Bold", 14)
    canv.drawCentredString(
        x + 3 * width / 4,
        y - header_height - (height - header_height) / 2 + 1.5,
        creator_text,
    )
    canv.restoreState()


def draw_section_header(
    canv: canvas.Canvas,
    x: float,
    y: float,
    trip_no: str,
    time_text: str,
    label_text: str,
    width: float,
) -> float:
    """
    便の見出しを描画し、次の描画開始位置を返す。

    Args:
        canv: ReportLabのCanvasオブジェクト
        x: 描画開始位置のX座標
        y: 描画開始位置のY座標
        trip_no: 便番号（例：「1」「2」「3」「4」）
        time_text: 出荷時刻（例：「AM 06:00」）
        label_text: ラベルテキスト（例：「4t／5tブレード（1）」）
        width: セクションの幅

    Returns:
        次の描画開始Y座標
    """
    trip_box_size = 10 * mm
    canv.saveState()

    canv.rect(x, y - trip_box_size, trip_box_size, trip_box_size, stroke=1, fill=0)
    canv.setFont("MSGothic-Bold", 18)
    canv.drawCentredString(x + trip_box_size / 2, y - trip_box_size + 4, trip_no)

    canv.setFont("MSGothic-Bold", 11)
    canv.drawString(x + trip_box_size + 5, y - 8, "便目")

    canv.setFont("MSGothic-Bold", 16)
    canv.drawString(x + trip_box_size + 30, y - 8, time_text)

    if label_text:
        label_width = 70 * mm
        canv.rect(
            x + width - label_width,
            y - trip_box_size,
            label_width,
            trip_box_size,
            stroke=1,
            fill=0,
        )
        canv.setFont("MSGothic-Bold", 14)
        canv.drawCentredString(
            x + width - label_width / 2,
            y - trip_box_size + 3,
            label_text,
        )

    canv.restoreState()
    return y - trip_box_size - 2


def _normalize_quantity_value(value: Any) -> Union[int, float, None]:
    """
    数量を int または float に正規化し、計算しやすい形にする。

    Args:
        value: 正規化する値（Decimal、int、float、str など）

    Returns:
        正規化された数値（int または float）、変換できない場合は None
    """
    if value is None:
        return None
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return int(value)
        return float(value)
    if isinstance(value, (int, float)):
        if isinstance(value, float) and value.is_integer():
            return int(value)
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = Decimal(value.strip())
            if parsed == parsed.to_integral_value():
                return int(parsed)
            return float(parsed)
        except Exception:
            return None
    return None


def _is_positive_quantity(value: Any) -> bool:
    """
    数量が 0 より大きい場合に True を返す。

    Args:
        value: チェックする値

    Returns:
        値が正の数の場合 True、それ以外は False
    """
    normalized = _normalize_quantity_value(value)
    if normalized is None:
        return False
    if isinstance(normalized, (int, float)):
        return normalized > 0
    return False


def _filter_positive_products(products: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    数量が正の製品だけを抽出したリストを返す。

    Args:
        products: 製品情報の辞書のリスト

    Returns:
        order_quantity が正の値の製品のみを含むリスト
    """
    return [prod for prod in products if _is_positive_quantity(prod.get("order_quantity"))]


def determine_box_color(trip_no: str, product: Dict[str, Any]) -> colors.Color:
    """
    便番号とグループに応じてボックス背景色を決定する。

    Args:
        trip_no: 便番号（「1」「2」「3」「4」）
        product: 製品情報（group_codeを含む）

    Returns:
        適用する背景色（ReportLab の Color オブジェクト）

    ルール:
        - 1便目、4便目: ブレード青色
        - 2便目: ブレード黄色
        - 3便目: グループコードに応じて
            - SEATBASE: シートベース緑色
            - TANK: タンク青色
    """
    group_code = str(product.get("group_code", "") or "").upper()
    if trip_no in ("1", "4"):
        return COLOR_BLADE_BLUE
    if trip_no == "2":
        return COLOR_BLADE_YELLOW
    if trip_no == "3":
        if group_code == "SEATBASE":
            return COLOR_SEATBASE_GREEN
        if group_code == "TANK":
            return COLOR_TANK_BLUE
    return COLOR_BOX_EMPTY


def _format_unit_label_single_line(prod: Dict[str, Any]) -> str:
    """
    単体ボックス内に表示するラベルを1行形式で生成する（1便目・4便目用）。

    Args:
        prod: 製品情報（model_name、product_name、product_code を含む）

    Returns:
        「機種名 (製品コード)」形式の文字列
    """
    model_name = str(prod.get("model_name", "") or "")
    product_name = str(prod.get("product_name", "") or "")
    product_code = str(prod.get("product_code", "") or "")

    if model_name and product_code:
        return f"{model_name} ({product_code})"
    if product_name and product_code:
        return f"{product_name} ({product_code})"
    return model_name or product_name or product_code


def _format_unit_label(prod: Dict[str, Any]) -> List[str]:
    """
    単体ボックス内に表示するラベルを3行形式で生成する（2便目・3便目用）。

    Args:
        prod: 製品情報（model_name、product_name、product_code を含む）

    Returns:
        ラベル行のリスト：
            - 1行目: 機種名または製品名
            - 2行目: 製品コード
        （台数は別途 draw_product_box で追加される）
    """
    model_name = str(prod.get("model_name", "") or "")
    product_name = str(prod.get("product_name", "") or "")
    product_code = str(prod.get("product_code", "") or "")

    lines: List[str] = []
    # 1行目：機種名または製品名
    if model_name:
        lines.append(model_name)
    elif product_name:
        lines.append(product_name)

    # 2行目：製品コード
    if product_code:
        lines.append(product_code)

    return lines


def chunked(items: Sequence[Any], size: int) -> List[List[Any]]:
    """
    シーケンスを指定サイズごとのリストに分割する。

    Args:
        items: 分割する要素のシーケンス
        size: 1つのチャンクに含める要素数

    Returns:
        size 個ずつに分割されたリストのリスト
    """
    return [list(items[i : i + size]) for i in range(0, len(items), size)]


def prepare_box_items(trip_no: str, products: List[Dict[str, Any]], db_manager=None) -> List[Dict[str, Any]]:
    """
    便ごとの製品リストを PDF ボックス描画用データへ変換する。

    Args:
        trip_no: 便番号（「1」「2」「3」「4」）
        products: 製品情報のリスト
        db_manager: データベースマネージャー（SUB_BLADE製品の容器情報取得用）

    Returns:
        描画用ボックスデータのリスト

    処理内容:
        - 1便目・4便目: 3台ずつカートにまとめて表示
        - 2便目・3便目: 容器単位（capacity）で分割して表示
        - SUB_BLADE製品: MAIN機種名の容器情報を参照
        - その他: 製品ごとに1マス表示
    """
    filtered = _filter_positive_products(products)
    if not filtered:
        return []

    if trip_no in ("1", "4"):
        # 以下のコードは削除しないでください（コメントアウトして保持）
        # units: List[Dict[str, Any]] = []
        # for prod in filtered:
        #     qty = int(_normalize_quantity_value(prod.get("order_quantity")) or 0)
        #     for _ in range(qty):
        #         units.append(
        #             {
        #                 "text_lines": [_format_unit_label_single_line(prod)],
        #                 "color": determine_box_color(trip_no, prod),
        #             }
        #         )

        # carts: List[Dict[str, Any]] = []
        # for chunk in chunked(units, 3):
        #     lines: List[str] = []
        #     for entry in chunk:
        #         lines.extend(entry.get("text_lines", []))
        #     carts.append(
        #         {
        #             "text_lines": lines,
        #             "quantity": len(chunk),
        #             "color": COLOR_BLADE_BLUE,
        #         }
        #     )
        # return carts

        # 「別紙参照」を容器数分のカードとして表示
        # 全機種の注文数を合計し、3で割って容器数を計算（1容器3台）
        total_qty = 0
        for prod in filtered:
            order_qty = int(_normalize_quantity_value(prod.get("order_quantity")) or 0)
            total_qty += order_qty

        # 容器数を計算（切り上げ）
        num_containers = (total_qty + 2) // 3  # 3で割って切り上げ

        # 各容器ごとに「別紙参照」カードを作成
        cards: List[Dict[str, Any]] = []
        for _ in range(num_containers):
            cards.append(
                {
                    "text_lines": ["別紙参照"],
                    "color": COLOR_BLADE_BLUE,
                }
            )
        return cards

    if trip_no in ("2", "3"):
        # MAINとSUBを機種名でグループ化して処理
        from services.shipping_order_service import ShippingOrderService

        # MAINとSUBを分離
        main_products: List[Dict[str, Any]] = []
        sub_products: List[Dict[str, Any]] = []

        for prod in filtered:
            group_code = str(prod.get("group_code", "") or "").strip().upper()
            if group_code == "SUB_BLADE":
                sub_products.append(prod)
            else:
                main_products.append(prod)

        # SUBを機種名でグループ化（MAIN機種名に変換）
        sub_by_main_model: Dict[str, List[Dict[str, Any]]] = {}
        if db_manager:
            try:
                service = ShippingOrderService(db_manager)
                for sub_prod in sub_products:
                    model_name = str(sub_prod.get("model_name", "") or "").strip()
                    if model_name:
                        main_model = service._extract_main_model_name(model_name)
                        if main_model:
                            # 空白を完全に除去して正規化
                            main_model_key = main_model.replace(" ", "").replace("　", "")
                            if main_model_key not in sub_by_main_model:
                                sub_by_main_model[main_model_key] = []
                            sub_by_main_model[main_model_key].append(sub_prod)
            except Exception as e:
                import traceback
                print(f"Error in SUB grouping: {e}")
                traceback.print_exc()

        # デバッグ情報
        print(f"DEBUG: trip_no={trip_no}, main_products={len(main_products)}, sub_products={len(sub_products)}")
        print(f"DEBUG: sub_by_main_model keys={list(sub_by_main_model.keys())}")
        for key, subs in sub_by_main_model.items():
            print(f"DEBUG:   {key}: {len(subs)} SUB products")

        containers: List[Dict[str, Any]] = []

        # MAIN製品を処理
        for main_prod in main_products:
            order_qty = int(_normalize_quantity_value(main_prod.get("order_quantity")) or 0)
            capacity = int(_normalize_quantity_value(main_prod.get("capacity")) or 1)

            if capacity <= 0:
                capacity = 1

            # MAIN製品の機種名を取得（空白を完全に除去して正規化）
            main_model_name = str(main_prod.get("model_name", "") or "").strip().upper()
            main_model_name_key = main_model_name.replace(" ", "").replace("　", "")

            # デバッグ：MAIN製品情報
            print(f"DEBUG: MAIN product: model_name='{main_model_name}' -> key='{main_model_name_key}'")

            # 対応するSUB製品の総数量を取得
            sub_total_qty = 0
            sub_prods_for_this_main = sub_by_main_model.get(main_model_name_key, [])
            print(f"DEBUG:   Found {len(sub_prods_for_this_main)} SUB products for key '{main_model_name_key}'")
            for sub_prod in sub_prods_for_this_main:
                sub_qty = int(_normalize_quantity_value(sub_prod.get("order_quantity")) or 0)
                print(f"DEBUG:     SUB product: model_name='{sub_prod.get('model_name')}', quantity={sub_qty}")
                sub_total_qty += sub_qty
            print(f"DEBUG:   Total SUB quantity for '{main_model_name_key}': {sub_total_qty}")

            # MAINの容器数を計算（SUBは含めない、MAINのみで容器数を決定）
            num_containers = (order_qty + capacity - 1) // capacity
            print(f"DEBUG:   MAIN containers: {num_containers}, total_sub_qty: {sub_total_qty}")

            # MAIN製品のみで容器を作成（通常の表示）
            remaining_main = order_qty
            for i in range(num_containers):
                # この容器のMAIN数量
                main_in_container = min(capacity, remaining_main)
                remaining_main -= main_in_container

                # 表示テキストを作成（通常の表示、「MAIN」接頭辞なし）
                text_lines = _format_unit_label(main_prod)
                text_lines.append(f"{main_in_container}個")

                # 最後の容器の場合、SUB情報を追加
                if i == num_containers - 1 and sub_total_qty > 0:
                    # SUB製品の詳細を追加
                    for sub_prod in sub_prods_for_this_main:
                        sub_qty = int(_normalize_quantity_value(sub_prod.get("order_quantity")) or 0)
                        sub_model = str(sub_prod.get("model_name", "") or "").strip()
                        if sub_qty > 0:
                            text_lines.append(f"{sub_model} {sub_qty}個")
                            print(f"DEBUG:   Added SUB line: '{sub_model} {sub_qty}個'")

                containers.append(
                    {
                        "text_lines": text_lines,
                        "color": determine_box_color(trip_no, main_prod),
                    }
                )

        # SUBでMAINが存在しない場合の処理
        for main_model, sub_prods in sub_by_main_model.items():
            # このMAINモデルが既に処理されているかチェック
            main_exists = any(
                str(p.get("model_name", "") or "").strip().upper().replace(" ", "").replace("　", "") == main_model
                for p in main_products
            )

            if not main_exists:
                # L/Rをチェック
                has_L = False
                has_R = False

                for sub_prod in sub_prods:
                    model_name = str(sub_prod.get("model_name", "") or "").strip().upper()
                    # -L または末尾がLの場合
                    if "-L" in model_name or (model_name.endswith("L") and not model_name.endswith("BL")):
                        has_L = True
                    # -R または末尾がRの場合
                    elif "-R" in model_name or model_name.endswith("R"):
                        has_R = True

                # L/R両方ある場合は1つの容器にまとめる
                if has_L and has_R:
                    print(f"DEBUG: Merging L/R for main_model '{main_model}' into one container")
                    # 全SUBをまとめて1つの容器に
                    text_lines = []
                    for sub_prod in sub_prods:
                        order_qty = int(_normalize_quantity_value(sub_prod.get("order_quantity")) or 0)
                        if order_qty > 0:
                            model_name = str(sub_prod.get("model_name", "") or "").strip()
                            product_code = str(sub_prod.get("product_code", "") or "")
                            text_lines.append(model_name)
                            if product_code:
                                text_lines.append(product_code)
                            text_lines.append(f"{order_qty}個")

                    containers.append(
                        {
                            "text_lines": text_lines,
                            "color": determine_box_color(trip_no, sub_prods[0]),
                        }
                    )
                else:
                    # L/Rの片方しかない場合は従来通り個別に容器を作成
                    print(f"DEBUG: Creating separate containers for main_model '{main_model}' (has_L={has_L}, has_R={has_R})")
                    for sub_prod in sub_prods:
                        order_qty = int(_normalize_quantity_value(sub_prod.get("order_quantity")) or 0)
                        capacity = 1  # デフォルト

                        # MAIN容器情報を取得
                        if db_manager:
                            try:
                                service = ShippingOrderService(db_manager)
                                product_id = sub_prod.get("product_id")
                                if product_id:
                                    main_container_info = service.get_main_container_info(product_id)
                                    if main_container_info and main_container_info.get("capacity"):
                                        capacity = int(main_container_info["capacity"])
                            except Exception:
                                pass

                        if capacity <= 0:
                            capacity = 1

                        num_containers = (order_qty + capacity - 1) // capacity

                        for i in range(num_containers):
                            if i == num_containers - 1:
                                container_qty = order_qty - (i * capacity)
                            else:
                                container_qty = capacity

                            # text_linesに個数を追加
                            text_lines = _format_unit_label(sub_prod)
                            text_lines.append(f"{container_qty}個")

                            containers.append(
                                {
                                    "text_lines": text_lines,
                                    "color": determine_box_color(trip_no, sub_prod),
                                }
                            )

        return containers

    items: List[Dict[str, Any]] = []
    for prod in filtered:
        items.append(
            {
                "title": str(prod.get("model_name", "") or prod.get("product_name", "") or prod.get("product_code", "")),
                "subtitle": str(prod.get("product_code", "") or ""),
                "quantity": _normalize_quantity_value(prod.get("order_quantity")),
                "color": determine_box_color(trip_no, prod),
            }
        )
    return items


def draw_product_box(
    canv: canvas.Canvas,
    x: float,
    y: float,
    width: float,
    height: float,
    item: Dict[str, Any],
) -> None:
    """
    製品ボックスを描画する。

    Args:
        canv: ReportLabのCanvasオブジェクト
        x: 描画開始位置のX座標
        y: 描画開始位置のY座標
        width: ボックスの幅
        height: ボックスの高さ
        item: ボックスデータ（text_lines, quantity, color を含む）

    処理内容:
        - 背景色を設定してボックスを描画
        - text_lines の各行を表示
        - quantity がある場合は「〇台」を最終行に追加
    """
    canv.saveState()
    canv.setStrokeColor(COLOR_BOX_BORDER)
    canv.setFillColor(item.get("color", COLOR_BOX_EMPTY))
    canv.rect(x, y - height, width, height, stroke=1, fill=1)

    lines: List[str] = []
    if "text_lines" in item:
        lines.extend(item.get("text_lines") or [])
    else:
        title = item.get("title", "") or ""
        subtitle = item.get("subtitle", "") or ""
        if title:
            lines.extend(textwrap.wrap(title, width=8)[:2])
        if subtitle:
            for line in textwrap.wrap(subtitle, width=10):
                if len(lines) >= 3:
                    break
                lines.append(line)

    quantity = _normalize_quantity_value(item.get("quantity"))
    if quantity not in (None, 0, ""):
        if isinstance(quantity, (int, float)):
            lines.append(f"{quantity}台")
        else:
            lines.append(str(quantity))

    if not lines:
        canv.restoreState()
        return

    line_height = 13
    total_height = line_height * len(lines)
    text_y = y - (height - total_height) / 2 - 3

    for idx, line in enumerate(lines):
        if idx == 0:
            # 1行目：機種名
            canv.setFont("MSGothic-Bold", 11)
        elif idx == len(lines) - 1 and quantity not in (None, 0, ""):
            # 最終行：台数
            canv.setFont("MSGothic-Bold", 12)
        else:
            # 2行目：製品コード
            canv.setFont("MSGothic", 9)
        canv.setFillColor(colors.black)
        canv.drawCentredString(x + width / 2, text_y, line)
        text_y -= line_height

    canv.restoreState()


def draw_product_boxes(
    canv: canvas.Canvas,
    items: List[Dict[str, Any]],
    x: float,
    y: float,
    width: float,
    columns: int,
    show_empty_message: bool = True,
) -> float:
    """
    製品ボックスの配列を描画する。

    Args:
        canv: ReportLabのCanvasオブジェクト
        items: 描画するボックスデータのリスト
        x: 描画開始位置のX座標
        y: 描画開始位置のY座標
        width: 全体の幅
        columns: 1行あたりの列数

    Returns:
        次の描画開始Y座標
    """
    if not items:
        if show_empty_message:
            canv.saveState()
            canv.setFont("MSGothic", 11)
            canv.drawString(x + 10, y - 18, "該当する製品がありません")
            canv.restoreState()
        return y - 24

    gap = BOX_GAP
    row_height = BOX_ROW_HEIGHT
    current_y = y

    for row_items in chunked(items, columns):
        col_count = len(row_items)
        if col_count == 0:
            continue
        box_width = (width - gap * (col_count - 1)) / col_count
        row_top = current_y
        for idx, item in enumerate(row_items):
            box_x = x + idx * (box_width + gap)
            draw_product_box(
                canv,
                x=box_x,
                y=row_top,
                width=box_width,
                height=row_height,
                item=item,
            )
        current_y -= row_height + BOX_ROW_SPACING

    return current_y + BOX_ROW_SPACING


def draw_trip2_special_box(
    canv: canvas.Canvas,
    annotations: List[Dict[str, Any]],
    x: float,
    width: float,
    row_top: float,
    columns: int,
    has_main_row: bool,
) -> float:
    """
    2便目特記事項（SIGA/KANTATSU）を所定位置に描画
    """
    if not annotations:
        return

    gap = BOX_GAP
    row_height = BOX_ROW_HEIGHT
    box_width = (width - gap * (columns - 1)) / columns

    display_locations = {
        "SIGA": "滋賀",
        "KANTATSU": "神立",
    }

    order = {"SIGA": 0, "KANTATSU": 1}
    sorted_annotations = sorted(
        annotations,
        key=lambda ann: order.get((ann.get("group_code") or "").upper(), 99),
    )

    col_idx = columns - 1
    row_idx = 1 if has_main_row else 0
    rows_used = 0
    for ann in sorted_annotations:
        group_code = ann.get("group_code", "")
        containers = ann.get("containers") or 0
        try:
            containers = int(containers)
        except Exception:
            containers = 1
        containers = max(1, containers)

        location = display_locations.get(group_code, group_code or "")
        text_lines = ["リーデン"]
        second_line = location or group_code or ""
        if second_line:
            text_lines.append(second_line)
        text_lines.append(f"{containers}容器")

        if col_idx < 0:
            col_idx = columns - 1
            row_idx += 1

        box_x = x + col_idx * (box_width + gap)
        row_top_position = row_top - row_idx * (row_height + BOX_ROW_SPACING)

        draw_product_box(
            canv=canv,
            x=box_x,
            y=row_top_position,
            width=box_width,
            height=row_height,
            item={
                "text_lines": text_lines,
                "quantity": None,
                "color": COLOR_RIDEN_PINK,
            },
        )

        rows_used = max(rows_used, row_idx + 1)
        col_idx -= 1

    extra_rows = rows_used - (1 if has_main_row else 0)
    extra_rows = max(0, extra_rows)
    return extra_rows * (row_height + BOX_ROW_SPACING)


def draw_trip_section(
    canv: canvas.Canvas,
    trip_no: str,
    time_text: str,
    label_text: str,
    products: List[Dict[str, Any]],
    x: float,
    y: float,
    width: float,
    special_annotations: Optional[List[Dict[str, Any]]] = None,
    db_manager=None,
) -> float:
    """
    出荷便ごとのセクションを描画する。

    Args:
        canv: ReportLabのCanvasオブジェクト
        trip_no: 便番号（「1」「2」「3」「4」）
        time_text: 出荷時刻（例：「AM 06:00」）
        label_text: ラベルテキスト（例：「4t／5tブレード（1）」）
        products: この便の製品リスト
        x: 描画開始位置のX座標
        y: 描画開始位置のY座標
        width: セクションの幅

    Returns:
        次の描画開始Y座標
    """
    current_y = draw_section_header(
        canv,
        x=x,
        y=y,
        trip_no=trip_no,
        time_text=time_text,
        label_text=label_text,
        width=width,
    )

    columns = 5 if trip_no in ("1", "4") else 7
    filtered = _filter_positive_products(products)
    special_annotations = special_annotations or []
    special_groups = set()
    if trip_no == "2" and special_annotations:
        for ann in special_annotations:
            code = str(ann.get("group_code", "") or "").strip().upper()
            if code:
                special_groups.add(code)
        if special_groups:
            filtered = [
                prod
                for prod in filtered
                if str(prod.get("group_code", "") or "").strip().upper() not in special_groups
            ]

    products_sorted = sorted(filtered, key=lambda p: str(p.get("product_code", "")))
    box_items = prepare_box_items(trip_no, products_sorted, db_manager) if products_sorted else []
    has_main_row = bool(box_items)
    box_area_top = current_y

    current_y = draw_product_boxes(
        canv,
        box_items,
        x,
        current_y,
        width,
        columns=columns,
        show_empty_message=not (trip_no == "2" and special_annotations and not box_items),
    )

    extra_height = 0
    if trip_no == "2" and special_annotations:
        extra_height = draw_trip2_special_box(
            canv=canv,
            annotations=special_annotations,
            x=x,
            width=width,
            row_top=box_area_top,
            columns=columns,
            has_main_row=has_main_row,
        )

    return current_y - extra_height - 2


def generate_shipping_order_pdf(
    shipping_data: Dict[str, Any],
    output_path: str,
    creator_name: str = "システム",
    db_manager=None,
) -> str:
    """
    出荷指示書 PDF を生成してファイルに書き出す。

    Args:
        shipping_data: 出荷データ（date, trip1, trip2, trip3, trip4 を含む辞書）
        output_path: 出力先PDFファイルのパス
        creator_name: 作成者名（デフォルト: 「システム」）
        db_manager: データベースマネージャー（SUB_BLADE製品の容器情報取得用）

    Returns:
        出力したPDFファイルのパス

    処理内容:
        - A4サイズのPDFを作成
        - タイトルバンド、出荷日、確認欄を描画
        - 4つの便（1便目〜4便目）のセクションを描画
        - 1便目・4便目: 3台ずつカート形式、5列
        - 2便目・3便目: 容器単位、7列
        - ページが足りない場合は自動で改ページ
    """
    register_japanese_fonts()

    page_width, page_height = A4
    margin_x = 13 * mm
    margin_top = 12 * mm
    content_width = page_width - margin_x * 2

    canv = canvas.Canvas(output_path, pagesize=A4)
    canv.setAuthor("Shipping Planner")
    canv.setTitle("出荷指示書")

    current_y = page_height - margin_top

    draw_title_band(
        canv,
        text="株式会社日立建機ティエラ様向け　出荷指示書",
        x=margin_x,
        y=current_y,
        width=content_width,
        height=11 * mm,
    )
    current_y -= 12 * mm

    target_date = shipping_data.get("date")
    date_text = format_japanese_date(target_date) if target_date else "未設定"
    draw_labeled_box(
        canv,
        label="出荷日",
        value=date_text,
        x=margin_x,
        y=current_y,
    )

    confirm_box_width = 36 * mm
    draw_confirmation_box(
        canv,
        x=margin_x + content_width - confirm_box_width,
        y=current_y + 4,
        width=confirm_box_width,
        height=22 * mm,
        creator_text=creator_name,
    )

    current_y -= 24 * mm

    trips = [
        ("1", "AM 06:00", "4t／5tブレード(1)", shipping_data.get("trip1", []), None),
        ("2", "AM 06:30", "ブレード", shipping_data.get("trip2", []), shipping_data.get("trip2_special_annotations")),
        ("3", "AM 10:00", "オイルタンク・シートベース", shipping_data.get("trip3", []), None),
        ("4", "PM 13:00", "4t／5tブレード(2)", shipping_data.get("trip4", []), None),
    ]

    for trip_no, time_text, label_text, products, special in trips:
        current_y = draw_trip_section(
            canv,
            trip_no=trip_no,
            time_text=time_text,
            label_text=label_text,
            products=products or [],
            x=margin_x,
            y=current_y,
            width=content_width,
            special_annotations=special or [],
            db_manager=db_manager,
        )
        current_y -= 2 * mm
        if current_y < 20 * mm:
            canv.showPage()
            current_y = page_height - margin_top

    canv.save()

    return output_path

