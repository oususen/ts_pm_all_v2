# app/ui/pages/dashboard_page.py
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from ui.components.charts import ChartComponents

class DashboardPage:
    """ダッシュボードページ - メインの分析画面"""

    def __init__(self, production_service, transport_service=None, db_manager=None):
        self.service = production_service
        self.transport_service = transport_service
        self.db_manager = db_manager
        self.charts = ChartComponents()
    
    def show(self):
        """ページ表示"""
        st.title("🏭 生産計画管理ダッシュボード")

        # 基本情報表示
        self._show_basic_metrics()

        # 製品マトリックス表（フィルタ含む）
        filter_params = self._show_product_matrix()

        st.markdown("---")

        # 需要トレンドグラフ（マトリックスフィルタを適用）
        if filter_params:
            self._show_demand_trend(filter_params)
        else:
            self._show_demand_trend()
    
    def _show_basic_metrics(self):
        """基本メトリクス表示"""
        try:
            products = self.service.get_all_products()
            instructions = self.service.get_production_instructions()
            constraints = self.service.get_product_constraints()
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("登録製品数", len(products))
            
            with col2:
                st.metric("制約対象製品", len(constraints))
            
            with col3:
                total_demand = sum(inst.instruction_quantity for inst in instructions) if instructions else 0
                st.metric("総需要量", f"{total_demand:,.0f}")
            
            with col4:
                if instructions:
                    date_range = f"{min(inst.instruction_date for inst in instructions).strftime('%m/%d')} - {max(inst.instruction_date for inst in instructions).strftime('%m/%d')}"
                    st.metric("計画期間", date_range)
                else:
                    st.metric("計画期間", "データなし")
                    
        except Exception as e:
            st.error(f"データ取得エラー: {e}")
    
    def _show_demand_trend(self, filter_params=None):
        """需要トレンド表示（稼働日のみ、マトリックスフィルタ適用）"""
        st.subheader("📈 需要トレンド分析")

        try:
            # フィルタパラメータの取得
            if filter_params:
                start_date = filter_params.get('start_date')
                end_date = filter_params.get('end_date')
                selected_products = filter_params.get('selected_products')
                selected_groups = filter_params.get('selected_groups')
                selected_inspections = filter_params.get('selected_inspections')
                products_df = filter_params.get('products_df')

                st.caption(f"📅 期間: {start_date.strftime('%Y/%m/%d')} ～ {end_date.strftime('%Y/%m/%d')} のデータを表示（マトリックスフィルタ適用）")

                # 期間でフィルタした生産指示を取得
                instructions = self.service.get_production_instructions(start_date, end_date)
            else:
                instructions = self.service.get_production_instructions()

            if instructions:
                # DataFrameに変換
                instructions_df = pd.DataFrame([{
                    'instruction_date': inst.instruction_date,
                    'instruction_quantity': inst.instruction_quantity,
                    'product_code': inst.product_code,
                    'product_name': inst.product_name
                } for inst in instructions])

                # フィルタパラメータがある場合、追加のフィルタリングを適用
                if filter_params and not instructions_df.empty:
                    # 製品コードでフィルタ
                    if selected_products:
                        instructions_df = instructions_df[
                            instructions_df['product_code'].isin(selected_products)
                        ]

                    # 製品群でフィルタ（products_dfと結合が必要）
                    if selected_groups and products_df is not None:
                        # 製品群マップを作成
                        product_groups_df = self.service.get_all_product_groups(include_inactive=True)
                        if product_groups_df is not None and not product_groups_df.empty:
                            product_group_map = dict(zip(product_groups_df['id'], product_groups_df['group_name']))
                            products_df['製品群'] = products_df['product_group_id'].apply(
                                lambda x: product_group_map.get(x, '未設定') if pd.notna(x) else '未設定'
                            )

                            # 選択された製品群に属する製品コードを取得
                            filtered_products = products_df[
                                products_df['製品群'].isin(selected_groups)
                            ]['product_code'].unique()

                            instructions_df = instructions_df[
                                instructions_df['product_code'].isin(filtered_products)
                            ]

                    # 検査区分でフィルタ（products_dfと結合が必要）
                    if selected_inspections and products_df is not None:
                        filtered_products = products_df[
                            products_df['inspection_category'].isin(selected_inspections)
                        ]['product_code'].unique()

                        instructions_df = instructions_df[
                            instructions_df['product_code'].isin(filtered_products)
                        ]

                # 稼働日のみにフィルタ
                if not instructions_df.empty and self.db_manager:
                    min_date = instructions_df['instruction_date'].min()
                    max_date = instructions_df['instruction_date'].max()

                    # 稼働日リストを取得
                    working_days = self._get_working_days_list(min_date, max_date)

                    # 稼働日のみにフィルタ
                    instructions_df = instructions_df[
                        instructions_df['instruction_date'].isin(working_days)
                    ]

                    if not instructions_df.empty:
                        st.caption(f"📅 稼働日のみ表示（土日祝日除外）")

                # トレンドグラフ表示
                fig = self.charts.create_demand_trend_chart(instructions_df)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                
                # 製品別需要
                st.subheader("製品別需要分析")
                product_demand = instructions_df.groupby(['product_code', 'product_name'])['instruction_quantity'].sum().reset_index()
                product_demand = product_demand.sort_values('instruction_quantity', ascending=False)
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.dataframe(
                        product_demand,
                        column_config={
                            "product_code": "製品コード",
                            "product_name": "製品名", 
                            "instruction_quantity": st.column_config.NumberColumn(
                                "需要数量",
                                format="%d"
                            )
                        },
                        use_container_width=True
                    )
                
                with col2:
                    st.write("**需要トップ5**")
                    top_products = product_demand.head()
                    for _, product in top_products.iterrows():
                        st.write(f"• {product['product_name']}: {product['instruction_quantity']:,.0f}")
                        
            else:
                st.warning("生産指示データがありません")
                
        except Exception as e:
            st.error(f"グラフ表示エラー: {e}")

    def _show_product_matrix(self):
        """製品マトリックス表（フィルタ機能付き）"""
        st.subheader("📊 製品マトリックス")

        try:
            # 製品データ取得
            products_df = self.service.get_all_products_df()
            if products_df is None or products_df.empty:
                st.warning("製品データがありません")
                return None

            # 製品群データ取得
            product_groups_df = self.service.get_all_product_groups(include_inactive=True)
            product_group_map = {}
            if product_groups_df is not None and not product_groups_df.empty:
                product_group_map = dict(zip(product_groups_df['id'], product_groups_df['group_name']))

            # 製品群名を追加
            products_df['製品群'] = products_df['product_group_id'].apply(
                lambda x: product_group_map.get(x, '未設定') if pd.notna(x) else '未設定'
            )

            # フィルタUI
            st.markdown("**フィルタ条件**")
            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:
                # 開始日
                default_start = date.today()
                start_date = st.date_input(
                    "開始日",
                    value=default_start,
                    key="dashboard_start_date"
                )

            with col2:
                # 終了日
                default_end = date.today() + timedelta(days=7)
                end_date = st.date_input(
                    "終了日",
                    value=default_end,
                    key="dashboard_end_date"
                )

            with col3:
                # 製品コードフィルタ（複数選択）
                product_codes = ['すべて'] + sorted(products_df['product_code'].unique().tolist())
                selected_products = st.multiselect(
                    "製品コード",
                    options=product_codes,
                    default=['すべて'],
                    key="dashboard_product_filter"
                )

            with col4:
                # 製品群フィルタ（複数選択）
                product_groups = ['すべて'] + sorted(products_df['製品群'].unique().tolist())
                selected_groups = st.multiselect(
                    "製品群",
                    options=product_groups,
                    default=['すべて'],
                    key="dashboard_group_filter"
                )

            with col5:
                # 検査区分フィルタ（複数選択）
                inspection_categories = ['すべて'] + sorted(products_df['inspection_category'].dropna().unique().tolist())
                selected_inspections = st.multiselect(
                    "検査区分",
                    options=inspection_categories,
                    default=['すべて'],
                    key="dashboard_inspection_filter"
                )

            # フィルタリング適用
            filtered_df = products_df.copy()

            # 製品コードでフィルタ
            if 'すべて' not in selected_products and selected_products:
                filtered_df = filtered_df[filtered_df['product_code'].isin(selected_products)]

            # 製品群でフィルタ
            if 'すべて' not in selected_groups and selected_groups:
                filtered_df = filtered_df[filtered_df['製品群'].isin(selected_groups)]

            # 検査区分でフィルタ
            if 'すべて' not in selected_inspections and selected_inspections:
                filtered_df = filtered_df[filtered_df['inspection_category'].isin(selected_inspections)]

            # 納入進度データを取得（期間フィルタ用）
            delivery_df = None
            if self.transport_service:
                try:
                    from sqlalchemy import text
                    session = self.transport_service.db.get_session()

                    query = text("""
                        SELECT
                            p.product_code,
                            p.product_name,
                            dp.delivery_date,
                            dp.order_quantity,
                            dp.planned_quantity,
                            dp.shipped_quantity,
                            dp.status
                        FROM delivery_progress dp
                        LEFT JOIN products p ON dp.product_id = p.id
                        WHERE dp.delivery_date BETWEEN :start_date AND :end_date
                            AND dp.status != 'キャンセル'
                        ORDER BY dp.delivery_date, p.product_code
                    """)

                    result = session.execute(query, {
                        'start_date': start_date.strftime('%Y-%m-%d'),
                        'end_date': end_date.strftime('%Y-%m-%d')
                    })

                    delivery_rows = result.fetchall()
                    session.close()

                    if delivery_rows:
                        delivery_df = pd.DataFrame(delivery_rows, columns=result.keys())
                        delivery_df['delivery_date'] = pd.to_datetime(delivery_df['delivery_date']).dt.date
                except Exception as e:
                    st.warning(f"納入進度データ取得エラー: {e}")

            # 表示形式選択
            view_mode = st.radio(
                "表示形式",
                options=["日付マトリックス", "一覧形式"],
                horizontal=True,
                key="dashboard_view_mode"
            )

            if view_mode == "日付マトリックス":
                # ピボット形式で表示
                self._show_pivot_matrix(filtered_df, delivery_df, start_date, end_date, products_df)
            else:
                # 従来の一覧形式
                self._show_list_format(filtered_df, delivery_df, products_df)

            # フィルタパラメータを返す
            return {
                'start_date': start_date,
                'end_date': end_date,
                'selected_products': selected_products if 'すべて' not in selected_products else None,
                'selected_groups': selected_groups if 'すべて' not in selected_groups else None,
                'selected_inspections': selected_inspections if 'すべて' not in selected_inspections else None,
                'products_df': products_df
            }

        except Exception as e:
            st.error(f"製品マトリックス表示エラー: {e}")
            import traceback
            st.code(traceback.format_exc())
            return None

    def _get_working_days_count(self, start_date, end_date):
        """稼働日数を取得（会社カレンダーから非稼働日を除外）"""
        if not self.db_manager:
            # カレンダーがない場合は期間の日数を返す
            return (end_date - start_date).days + 1

        try:
            from sqlalchemy import text
            session = self.db_manager.get_session()

            query = text("""
                SELECT calendar_date, is_working_day
                FROM company_calendar
                WHERE calendar_date BETWEEN :start_date AND :end_date
            """)

            result = session.execute(query, {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d')
            })

            calendar_rows = result.fetchall()
            session.close()

            if calendar_rows:
                # カレンダーデータがある場合は稼働日を数える
                working_days = sum(1 for row in calendar_rows if row[1])
                return working_days if working_days > 0 else 1  # 0の場合は1を返す
            else:
                # カレンダーデータがない場合は全日数を返す
                return (end_date - start_date).days + 1

        except Exception as e:
            # エラーの場合は全日数を返す
            print(f"稼働日取得エラー: {e}")
            return (end_date - start_date).days + 1

    def _get_working_days_list(self, start_date, end_date):
        """稼働日のリストを取得（会社カレンダーから非稼働日を除外）"""
        if not self.db_manager:
            # カレンダーがない場合は全日を返す
            return pd.date_range(start=start_date, end=end_date).date.tolist()

        try:
            from sqlalchemy import text
            session = self.db_manager.get_session()

            query = text("""
                SELECT calendar_date
                FROM company_calendar
                WHERE calendar_date BETWEEN :start_date AND :end_date
                    AND is_working_day = 1
                ORDER BY calendar_date
            """)

            result = session.execute(query, {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d')
            })

            working_days = [row[0] for row in result.fetchall()]
            session.close()

            if working_days:
                return working_days
            else:
                # カレンダーデータがない場合は全日を返す
                return pd.date_range(start=start_date, end=end_date).date.tolist()

        except Exception as e:
            # エラーの場合は全日を返す
            print(f"稼働日リスト取得エラー: {e}")
            return pd.date_range(start=start_date, end=end_date).date.tolist()

    def _show_pivot_matrix(self, filtered_df, delivery_df, start_date, end_date, products_df):
        """日付×製品のピボットマトリックス表示"""
        st.info(f"📋 表示件数: {len(filtered_df)}件 / 全{len(products_df)}件")

        if filtered_df.empty:
            st.warning("フィルタ条件に一致する製品がありません")
            return

        if delivery_df is None or delivery_df.empty:
            st.warning("指定期間の納入進度データがありません")
            return

        # 稼働日数を取得
        working_days_count = self._get_working_days_count(start_date, end_date)
        st.caption(f"📅 期間: {start_date.strftime('%Y/%m/%d')} ～ {end_date.strftime('%Y/%m/%d')} ({working_days_count}稼働日)")

        # 期間内の日付リストを作成
        date_range = pd.date_range(start=start_date, end=end_date).date.tolist()

        # フィルタされた製品のみに絞る
        delivery_filtered = delivery_df[
            delivery_df['product_code'].isin(filtered_df['product_code'])
        ].copy()

        # 表示する数値の選択
        data_type = st.radio(
            "表示データ",
            options=["受注数", "計画数", "出荷済"],
            horizontal=True,
            key="dashboard_data_type"
        )

        # データタイプに応じた列名
        column_map = {
            "受注数": "order_quantity",
            "計画数": "planned_quantity",
            "出荷済": "shipped_quantity"
        }
        value_column = column_map[data_type]

        # ピボットテーブル作成
        pivot_data = delivery_filtered.pivot_table(
            index='product_code',
            columns='delivery_date',
            values=value_column,
            aggfunc='sum',
            fill_value=0
        )

        # 製品名を追加
        product_info = filtered_df[['product_code', 'product_name']].drop_duplicates()
        pivot_data = pivot_data.merge(
            product_info.set_index('product_code'),
            left_index=True,
            right_index=True,
            how='left'
        )

        # カラムを再配置（製品コード、製品名を左側に固定）
        # インデックスをリセット
        pivot_data = pivot_data.reset_index()

        # カラム順序を調整（製品コード、製品名、日付列）
        date_columns = [col for col in pivot_data.columns if isinstance(col, date)]
        fixed_columns = ['product_code', 'product_name']
        pivot_data = pivot_data[fixed_columns + date_columns]

        # 日平均を計算（稼働日で割る）
        pivot_data['日平均'] = pivot_data[date_columns].sum(axis=1) / working_days_count

        # 列名を日本語に変更
        date_column_names = [d.strftime('%m/%d') for d in date_columns]

        # 列を並び替え：製品コード、製品名、日平均、日付列
        pivot_data = pivot_data[['product_code', 'product_name', '日平均'] + date_columns]
        pivot_data.columns = ['製品コード', '製品名', '日平均'] + date_column_names

        # 合計行を追加
        # 日平均の合計
        avg_total = pivot_data['日平均'].sum()
        # 日付列の合計
        date_totals = pivot_data[date_column_names].sum()

        total_row = pd.DataFrame([['合計', '', avg_total] + date_totals.tolist()],
                                 columns=pivot_data.columns)
        pivot_data = pd.concat([pivot_data, total_row], ignore_index=True)

        # column_configを作成（日平均列に小数点表示を追加）
        column_config = {
            "日平均": st.column_config.NumberColumn(
                "日平均",
                format="%.1f",
                help="期間合計 ÷ 稼働日数"
            )
        }

        # データフレーム表示
        st.dataframe(
            pivot_data,
            use_container_width=True,
            hide_index=True,
            height=min(600, (len(pivot_data) + 1) * 35),
            column_config=column_config
        )

        # サマリー情報
        total_quantity = delivery_filtered[value_column].sum()
        st.metric(f"期間合計（{data_type}）", f"{total_quantity:,.0f}")

    def _show_list_format(self, filtered_df, delivery_df, products_df):
        """従来の一覧形式表示"""
        if delivery_df is not None and not delivery_df.empty:
            # 製品別に集計
            product_summary = delivery_df.groupby('product_code').agg({
                'order_quantity': 'sum',
                'planned_quantity': 'sum',
                'shipped_quantity': 'sum'
            }).reset_index()

            # filtered_dfとマージ
            filtered_df = filtered_df.merge(
                product_summary,
                on='product_code',
                how='left'
            )
            filtered_df['order_quantity'] = filtered_df['order_quantity'].fillna(0).astype(int)
            filtered_df['planned_quantity'] = filtered_df['planned_quantity'].fillna(0).astype(int)
            filtered_df['shipped_quantity'] = filtered_df['shipped_quantity'].fillna(0).astype(int)
        else:
            filtered_df['order_quantity'] = 0
            filtered_df['planned_quantity'] = 0
            filtered_df['shipped_quantity'] = 0

        # 表示用にカラムを整理
        display_df = filtered_df[[
            'product_code',
            'product_name',
            '製品群',
            'capacity',
            'inspection_category',
            'lead_time_days',
            'can_advance',
            'order_quantity',
            'planned_quantity',
            'shipped_quantity'
        ]].copy()

        display_df.columns = [
            '製品コード',
            '製品名',
            '製品群',
            '入り数',
            '検査区分',
            'リードタイム',
            '前倒可',
            '受注数',
            '計画数',
            '出荷済'
        ]

        # 結果表示
        st.info(f"📋 表示件数: {len(display_df)}件 / 全{len(products_df)}件")

        if display_df.empty:
            st.warning("フィルタ条件に一致する製品がありません")
        else:
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "製品コード": st.column_config.TextColumn("製品コード", width="medium"),
                    "製品名": st.column_config.TextColumn("製品名", width="large"),
                    "製品群": st.column_config.TextColumn("製品群", width="medium"),
                    "入り数": st.column_config.NumberColumn("入り数", format="%d"),
                    "検査区分": st.column_config.TextColumn("検査区分", width="small"),
                    "リードタイム": st.column_config.NumberColumn("リードタイム", format="%d日"),
                    "前倒可": st.column_config.CheckboxColumn("前倒可"),
                    "受注数": st.column_config.NumberColumn("受注数", format="%d"),
                    "計画数": st.column_config.NumberColumn("計画数", format="%d"),
                    "出荷済": st.column_config.NumberColumn("出荷済", format="%d")
                }
            )

            # サマリー情報
            col_sum1, col_sum2, col_sum3, col_sum4 = st.columns(4)
            with col_sum1:
                st.metric("総受注数", f"{display_df['受注数'].sum():,.0f}")
            with col_sum2:
                st.metric("総計画数", f"{display_df['計画数'].sum():,.0f}")
            with col_sum3:
                st.metric("総出荷済", f"{display_df['出荷済'].sum():,.0f}")
            with col_sum4:
                remaining = display_df['受注数'].sum() - display_df['出荷済'].sum()
                st.metric("未出荷数", f"{remaining:,.0f}")