from __future__ import annotations

from datetime import date
from typing import Optional
import re

import streamlit as st

_FULLWIDTH_DIGIT_MAP = {ord("０") + i: str(i) for i in range(10)}


class QuickDateParseError(ValueError):
    """クイック入力文字列が解釈できない場合に送出される例外。"""


def _normalize_to_digits(raw: str) -> str:
    """全角数字を半角に変換し、数字のみを抽出して返す。"""
    normalized = raw.strip().translate(_FULLWIDTH_DIGIT_MAP)
    return "".join(ch for ch in normalized if ch.isdigit())


def _split_numeric_tokens(raw: str) -> list[str]:
    """区切り文字を維持しつつ、数字トークンのみを抽出する。"""
    normalized = raw.strip().translate(_FULLWIDTH_DIGIT_MAP)
    return re.findall(r"\d+", normalized)


def parse_quick_date(raw: str, *, reference: Optional[date] = None) -> date:
    """
    クイック入力用の日付文字列を解析して `date` を返す。

    対応フォーマット（全角数字・区切り文字も許容）:
      - ``6``             → 参照月の6日
      - ``116``           → 当年1月6日
      - ``0116`` / ``1 16`` / ``1-16`` → 当年1月16日
      - ``20251106``      → 2025-11-06
      - ``2025/11/06``    → 2025-11-06
      - ``250106``        → 2025-01-06（二桁年は最も近い世紀を補完）
    """

    reference_date = reference or date.today()
    if not raw or not raw.strip():
        raise QuickDateParseError("日付の入力が空です。")

    normalized = raw.strip().translate(_FULLWIDTH_DIGIT_MAP)
    has_separator = bool(re.search(r"\D", normalized))
    tokens = _split_numeric_tokens(raw)

    def _from_year_month_day(year_value: int, month_value: int, day_value: int) -> date:
        try:
            return date(year_value, month_value, day_value)
        except ValueError as exc:
            raise QuickDateParseError(f"存在しない日付です: {exc}") from exc

    if has_separator and tokens:
        if len(tokens) >= 3:
            year_part = tokens[-3]
            month_part = tokens[-2]
            day_part = tokens[-1]

            year_value = int(year_part)
            if len(year_part) == 2:
                century = reference_date.year - (reference_date.year % 100)
                year_value = century + year_value
                if year_value - reference_date.year > 50:
                    year_value -= 100
                elif reference_date.year - year_value > 50:
                    year_value += 100

            month_value = int(month_part)
            day_value = int(day_part)
            return _from_year_month_day(year_value, month_value, day_value)

        if len(tokens) == 2:
            month_value = int(tokens[0])
            day_value = int(tokens[1])
            return _from_year_month_day(reference_date.year, month_value, day_value)

        if len(tokens) == 1:
            digits = tokens[0]
        else:
            raise QuickDateParseError("日付の形式を解釈できません。")
    else:
        digits = _normalize_to_digits(raw)

    if not digits:
        raise QuickDateParseError("数字を含む形式で入力してください。")

    length = len(digits)

    try:
        if length <= 2:
            day_value = int(digits)
            return _from_year_month_day(reference_date.year, reference_date.month, day_value)

        if length == 3:
            month_value = int(digits[0])
            if not 1 <= month_value <= 12:
                raise QuickDateParseError("月は1から12の範囲で入力してください。")

            last_two = int(digits[1:])
            if digits[1] == "0":
                day_value = int(digits[2])
            elif digits[1] == str(month_value):
                day_value = int(digits[2])
            else:
                day_value = last_two

            return _from_year_month_day(reference_date.year, month_value, day_value)

        if length == 4:
            month_value = int(digits[:2])
            day_value = int(digits[2:])
            return _from_year_month_day(reference_date.year, month_value, day_value)

        if length == 6:
            year_value = int(digits[:2])
            month_value = int(digits[2:4])
            day_value = int(digits[4:])

            base_century = reference_date.year - (reference_date.year % 100)
            year_full = base_century + year_value
            if year_full - reference_date.year > 50:
                year_full -= 100
            elif reference_date.year - year_full > 50:
                year_full += 100

            return _from_year_month_day(year_full, month_value, day_value)

        if length == 8:
            year_value = int(digits[:4])
            month_value = int(digits[4:6])
            day_value = int(digits[6:])
            return _from_year_month_day(year_value, month_value, day_value)
    except ValueError as exc:
        raise QuickDateParseError(f"日付の読み取りに失敗しました: {exc}") from exc

    raise QuickDateParseError("サポートされていない日付形式です。")


def quick_date_input(
    label: str,
    *,
    key: str,
    value: Optional[date] = None,
    min_value: Optional[date] = None,
    max_value: Optional[date] = None,
    help: Optional[str] = None,
    quick_label: str = "クイック入力",
    quick_placeholder: str = "例: 6 → 今月6日 / 116 → 1月6日 / 20251106 → 2025-11-06",
) -> date:
    """
    日付ピッカーに加えて数値クイック入力欄を提供し、選択日付を返す。
    """

    quick_key = f"{key}__quick"
    error_key = f"{key}__quick_error"

    default_value = st.session_state.get(key, value)
    if default_value is None:
        default_value = date.today()

    effective_min = min_value
    effective_max = max_value

    if effective_min and default_value < effective_min:
        effective_min = None

    if effective_max and default_value > effective_max:
        effective_max = None

    col_date, col_quick = st.columns([3, 2])

    with col_date:
        date_value = st.date_input(
            label,
            value=default_value,
            key=key,
            min_value=effective_min,
            max_value=effective_max,
            help=help,
        )

    def _handle_quick_change() -> None:
        raw = st.session_state.get(quick_key, "")
        if not raw.strip():
            st.session_state.pop(error_key, None)
            return

        reference_date = st.session_state.get(key, date_value)
        try:
            parsed = parse_quick_date(raw, reference=reference_date)
        except QuickDateParseError as exc:
            st.session_state[error_key] = str(exc)
            return

        st.session_state[key] = parsed
        st.session_state[quick_key] = ""
        st.session_state.pop(error_key, None)

    with col_quick:
        st.text_input(
            quick_label,
            key=quick_key,
            placeholder=quick_placeholder,
            on_change=_handle_quick_change,
        )

        if error_key in st.session_state:
            st.warning(st.session_state[error_key])

    return st.session_state.get(key, date_value)
