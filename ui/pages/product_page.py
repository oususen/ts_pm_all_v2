# app/ui/pages/product_page.py
import streamlit as st
import pandas as pd
from ui.components.forms import FormComponents

class ProductPage:
    """製品管理ページ - マトリックス編集対応"""
    
    def __init__(self, production_service, transport_service, auth_service=None):
        self.production_service = production_service
        self.transport_service = transport_service
        self.auth_service = auth_service

    def _can_edit_page(self) -> bool:
        """ページ編集権限チェック"""
        if not self.auth_service:
            return True
        user = st.session_state.get('user')
        if not user:
            return False
        return self.auth_service.can_edit_page(user['id'], "製品管理")
    
    def show(self):
        """ページ表示"""
        st.title("📦 製品管理")
        st.write("製品の登録・編集・削除、および容器との紐付けを管理します。")

        # 権限チェック
        can_edit = self._can_edit_page()
        if not can_edit:
            st.warning("⚠️ この画面の編集権限がありません。閲覧のみ可能です。")

        tab1, tab2, tab3, tab4 = st.tabs(["📊 製品一覧（マトリックス）", "➕ 製品登録", "🏷️ 製品群管理", "🔗 製品×容器紐付け"])

        with tab1:
            self._show_product_matrix(can_edit)
        with tab2:
            self._show_product_registration(can_edit)
        with tab3:
            self._show_product_group_management(can_edit)
        with tab4:
            self._show_product_container_mapping()
    
    def _show_product_matrix(self, can_edit):
        """製品一覧 - マトリックス編集"""
        st.header("📊 製品一覧（編集可能）")
        
        try:
            products = self.production_service.get_all_products()
            containers = self.transport_service.get_containers()
            trucks_df = self.transport_service.get_trucks()
            # すべての製品群を取得（非アクティブも含む）
            product_groups_df = self.production_service.get_all_product_groups(include_inactive=True)

            if not products:
                st.info("登録されている製品がありません")
                return

            # 容器マップ作成
            container_map = {c.id: c.name for c in containers} if containers else {}
            container_name_to_id = {c.name: c.id for c in containers} if containers else {}

            # トラックマップ作成
            truck_map = dict(zip(trucks_df['id'], trucks_df['name'])) if not trucks_df.empty else {}
            truck_name_to_id = dict(zip(trucks_df['name'], trucks_df['id'])) if not trucks_df.empty else {}

            # 製品群マップ作成
            product_group_map = {}
            product_group_name_to_id = {}

            if product_groups_df is not None and not product_groups_df.empty:
                product_group_map = dict(zip(product_groups_df['id'], product_groups_df['group_name']))
                product_group_name_to_id = dict(zip(product_groups_df['group_name'], product_groups_df['id']))
            else:
                st.warning("⚠️ 製品群データが取得できませんでした。「🏷️ 製品群管理」タブで製品群を登録してください。")
            
            # DataFrame作成 - デフォルト値の設定を強化
            products_data = []
            for p in products:
                # 容器IDの取得（様々な属性名に対応）
                used_container_id = getattr(p, 'used_container_id', None) or getattr(p, 'container_id', None)

                # トラックIDの取得（様々な属性名に対応）
                used_truck_ids = getattr(p, 'used_truck_ids', None) or getattr(p, 'truck_ids', None)

                # 製品群IDの取得
                product_group_id = getattr(p, 'product_group_id', None)

                # 製品群の表示名を取得（マップになくてもIDを表示）
                if product_group_id:
                    product_group_display = product_group_map.get(product_group_id, f'ID:{product_group_id}')
                else:
                    product_group_display = '未設定'

                # その他の属性も同様に取得
                product_data = {
                    'ID': p.id,
                    '製品コード': getattr(p, 'product_code', '') or '',
                    '製品名': getattr(p, 'product_name', '') or '',
                    '機種名': getattr(p, 'model_name', '') or '',
                    '製品群': product_group_display,
                    '使用容器': container_map.get(used_container_id, '未設定') if used_container_id else '未設定',
                    '入り数': int(getattr(p, 'capacity', 0) or 0),
                    '検査区分': getattr(p, 'inspection_category', 'N') or 'N',
                    'リードタイム': int(getattr(p, 'lead_time_days', 0) or 0),
                    '固定日数': int(getattr(p, 'fixed_point_days', 0) or 0),
                    '前倒可': bool(getattr(p, 'can_advance', False)),
                    '使用トラック': ', '.join(self._get_truck_names_by_ids(used_truck_ids)) or '未設定'
                }
                products_data.append(product_data)
            
            products_df = pd.DataFrame(products_data)
            
            # サマリー
            st.subheader("📋 製品統計")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("登録製品数", len(products_df))
            with col2:
                can_advance_count = len(products_df[products_df['前倒可'] == True])
                st.metric("前倒可能製品", can_advance_count)
            with col3:
                n_count = len(products_df[products_df['検査区分'] == 'N'])
                st.metric("検査区分N", n_count)
            with col4:
                avg_capacity = products_df['入り数'].mean() if len(products_df) > 0 else 0
                st.metric("平均入り数", f"{avg_capacity:.0f}")
            
            st.markdown("---")
            st.subheader("✏️ 製品情報編集（セルをダブルクリックで編集）")

            # ソート機能
            col_sort1, col_sort2, _ = st.columns([2, 1, 3])
            with col_sort1:
                sort_column = st.selectbox(
                    "ソート列",
                    options=['ID', '製品コード', '製品名', '機種名', '製品群', '使用容器', '入り数', '検査区分', 'リードタイム', '固定日数', '前倒可', '使用トラック'],
                    index=0,
                    key="product_sort_column"
                )
            with col_sort2:
                sort_ascending = st.selectbox(
                    "ソート方向",
                    options=['昇順', '降順'],
                    index=0,
                    key="product_sort_direction"
                )

            # ソート適用
            if sort_column and sort_column in products_df.columns:
                products_df = products_df.sort_values(
                    by=sort_column,
                    ascending=(sort_ascending == '昇順')
                ).reset_index(drop=True)

            st.info("""
            **編集方法:**
            1. セルをダブルクリックして値を変更
            2. 変更が完了したら「💾 変更を保存」をクリック
            3. 削除する場合は「🗑️ 選択製品を削除」をクリック
            """)

            # 編集可能なデータエディタ
            edited_df = st.data_editor(
                products_df,
                use_container_width=True,
                hide_index=True,
                num_rows="dynamic",
                disabled=['ID', '使用トラック'],  # ID・使用トラックは編集不可（個別編集で設定）
                column_config={
                    "ID": st.column_config.NumberColumn("ID", disabled=True),
                    "製品コード": st.column_config.TextColumn("製品コード", width="medium", required=True),
                    "製品名": st.column_config.TextColumn("製品名", width="medium", required=True),
                    "機種名": st.column_config.TextColumn("機種名", width="medium"),
                    "製品群": st.column_config.SelectboxColumn(
                        "製品群",
                        options=['未設定'] + list(product_group_name_to_id.keys()),
                        width="medium",
                        help="この製品が属する製品群を選択"
                    ),
                    "使用容器": st.column_config.SelectboxColumn(
                        "使用容器",
                        options=['未設定'] + list(container_name_to_id.keys()),
                        width="medium"
                    ),
                    "入り数": st.column_config.NumberColumn("入り数", min_value=0, step=1),
                    "検査区分": st.column_config.SelectboxColumn(
                        "検査区分",
                        options=['N', 'NS', 'F', 'FS', '$S', ''],
                        width="small"
                    ),
                    "リードタイム": st.column_config.NumberColumn(
                        "リードタイム(日)",
                        min_value=0,
                        step=1,
                        help="納品日の何日前に積載するか（0=納品日当日、2=2日前など）"
                    ),
                    "固定日数": st.column_config.NumberColumn("固定日数(日)", min_value=0, step=1),
                    "前倒可": st.column_config.CheckboxColumn("前倒可"),
                    "使用トラック": st.column_config.TextColumn("使用トラック", width="medium", disabled=True, help="個別編集で設定してください")
                },
                key="product_matrix_editor"
            )
            
            # 保存・削除ボタン
            st.markdown("---")
            col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 4])
            
            with col_btn1:
                if st.button("💾 変更を保存", type="primary", use_container_width=True, disabled=not can_edit):
                    changes_saved = self._save_product_changes(
                        original_df=products_df,
                        edited_df=edited_df,
                        container_name_to_id=container_name_to_id,
                        truck_name_to_id=truck_name_to_id,
                        product_group_name_to_id=product_group_name_to_id
                    )
                    
                    if changes_saved:
                        st.success("✅ 変更を保存しました")
                        st.rerun()
                    else:
                        st.info("変更はありませんでした")
            
            with col_btn2:
                if st.button("🗑️ 選択製品を削除", type="secondary", use_container_width=True, disabled=not can_edit):
                    st.warning("削除機能は個別製品選択後に実行してください")
            
            # 詳細編集エリア（トラック選択対応）
            st.markdown("---")
            st.subheader("🔍 個別製品の詳細編集・削除（トラック選択可）")
            
            st.info("💡 **使用トラックの設定**は、こちらの個別編集で行ってください（複数選択可能）")
            
            product_options = {f"{row['製品コード']} - {row['製品名']}": row['ID'] for _, row in products_df.iterrows()}
            selected_product_key = st.selectbox(
                "編集・削除する製品を選択",
                options=list(product_options.keys()),
                key="product_detail_selector"
            )
            
            if selected_product_key:
                product_id = product_options[selected_product_key]
                product = next((p for p in products if p.id == product_id), None)
                
                if product:
                    self._show_product_detail_editor_with_truck_select(product, containers, trucks_df, container_map, can_edit)
        
        except Exception as e:
            st.error(f"製品一覧エラー: {e}")
            import traceback
            st.code(traceback.format_exc())
    
    def _save_product_changes(self, original_df, edited_df, container_name_to_id, truck_name_to_id, product_group_name_to_id=None):
        """マトリックスの変更をデータベースに保存"""

        changes_made = False

        for idx, edited_row in edited_df.iterrows():
            if idx >= len(original_df):
                # 新規行の場合（スキップまたは新規登録処理）
                continue

            original_row = original_df.iloc[idx]
            product_id = int(edited_row['ID'])

            # 変更があったか確認
            update_data = {}

            # 製品コード
            if edited_row['製品コード'] != original_row['製品コード']:
                update_data['product_code'] = edited_row['製品コード']

            # 製品名
            if edited_row['製品名'] != original_row['製品名']:
                update_data['product_name'] = edited_row['製品名']

            # 機種名
            if edited_row['機種名'] != original_row['機種名']:
                update_data['model_name'] = edited_row['機種名']

            # 製品群
            if product_group_name_to_id and '製品群' in edited_row:
                new_group_name = edited_row['製品群']
                original_group_name = original_row['製品群']
                if new_group_name != original_group_name:
                    if new_group_name == '未設定':
                        update_data['product_group_id'] = None
                    else:
                        update_data['product_group_id'] = product_group_name_to_id.get(new_group_name)

            # 使用容器
            new_container_name = edited_row['使用容器']
            original_container_name = original_row['使用容器']
            if new_container_name != original_container_name:
                if new_container_name == '未設定':
                    update_data['used_container_id'] = None
                else:
                    update_data['used_container_id'] = container_name_to_id.get(new_container_name)
            
            # 入り数
            if int(edited_row['入り数']) != int(original_row['入り数']):
                update_data['capacity'] = int(edited_row['入り数'])
            
            # 検査区分
            if edited_row['検査区分'] != original_row['検査区分']:
                update_data['inspection_category'] = edited_row['検査区分']
            
            # リードタイム
            if int(edited_row['リードタイム']) != int(original_row['リードタイム']):
                update_data['lead_time_days'] = int(edited_row['リードタイム'])
            
            # 固定日数
            if int(edited_row['固定日数']) != int(original_row['固定日数']):
                update_data['fixed_point_days'] = int(edited_row['固定日数'])
            
            # 前倒可
            if bool(edited_row['前倒可']) != bool(original_row['前倒可']):
                update_data['can_advance'] = bool(edited_row['前倒可'])
            
            # 変更があれば保存
            if update_data:
                success = self.production_service.update_product(product_id, update_data)
                if success:
                    changes_made = True
                    st.toast(f"✅ 製品ID={product_id} を更新しました")
                else:
                    st.toast(f"❌ 製品ID={product_id} の更新に失敗")
        
        return changes_made
    
    def _show_product_detail_editor_with_truck_select(self, product, containers, trucks_df, container_map, can_edit):
        """個別製品の詳細編集・削除（トラック複数選択対応）"""
        
        with st.container(border=True):
            st.write(f"**製品詳細編集: {getattr(product, 'product_code', 'N/A')}**")
            
            # 現在の情報表示
            col_info1, col_info2, col_info3 = st.columns(3)
            
            with col_info1:
                st.write("**基本情報**")
                st.write(f"ID: {product.id}")
                st.write(f"製品コード: {getattr(product, 'product_code', '-')}")
                st.write(f"製品名: {getattr(product, 'product_name', '-')}")
                st.write(f"機種名: {getattr(product, 'model_name', '-') or '-'}")
                st.write(f"入り数: {getattr(product, 'capacity', 0)}")
            
            with col_info2:
                st.write("**容器情報**")
                used_container_id = getattr(product, 'used_container_id', None) or getattr(product, 'container_id', None)
                st.write(f"使用容器: {container_map.get(used_container_id, '未設定') if used_container_id else '未設定'}")
                st.write(f"検査区分: {getattr(product, 'inspection_category', 'N')}")
            
            with col_info3:
                st.write("**納期・制約**")
                st.write(f"リードタイム: {getattr(product, 'lead_time_days', 0)} 日")
                st.write(f"固定日数: {getattr(product, 'fixed_point_days', 0)} 日")
                st.write(f"前倒可: {'✅' if getattr(product, 'can_advance', False) else '❌'}")
            
            st.markdown("---")

            # 基本情報編集フォーム
            with st.form(f"edit_basic_info_form_{product.id}"):
                st.write("**✏️ 基本情報編集**")

                col_edit1, col_edit2 = st.columns(2)

                with col_edit1:
                    new_product_code = st.text_input(
                        "製品コード",
                        value=getattr(product, 'product_code', ''),
                        key=f"product_code_{product.id}"
                    )
                    new_product_name = st.text_input(
                        "製品名",
                        value=getattr(product, 'product_name', ''),
                        key=f"product_name_{product.id}"
                    )
                    new_model_name = st.text_input(
                        "機種名",
                        value=getattr(product, 'model_name', '') or '',
                        key=f"model_name_{product.id}"
                    )

                with col_edit2:
                    new_capacity = st.number_input(
                        "入り数",
                        value=int(getattr(product, 'capacity', 0)),
                        min_value=0,
                        step=1,
                        key=f"capacity_{product.id}"
                    )
                    new_lead_time = st.number_input(
                        "リードタイム(日)",
                        value=int(getattr(product, 'lead_time_days', 0)),
                        min_value=0,
                        step=1,
                        key=f"lead_time_{product.id}"
                    )
                    new_can_advance = st.checkbox(
                        "前倒可",
                        value=bool(getattr(product, 'can_advance', False)),
                        key=f"can_advance_{product.id}"
                    )

                submitted_basic = st.form_submit_button("💾 基本情報を保存", type="primary", disabled=not can_edit)

                if submitted_basic:
                    update_data = {
                        "product_code": new_product_code,
                        "product_name": new_product_name,
                        "model_name": new_model_name if new_model_name else None,
                        "capacity": new_capacity,
                        "lead_time_days": new_lead_time,
                        "can_advance": new_can_advance
                    }

                    success = self.production_service.update_product(product.id, update_data)
                    if success:
                        st.success(f"✅ 製品 '{new_product_code}' の基本情報を更新しました")
                        st.rerun()
                    else:
                        st.error("❌ 基本情報の更新に失敗しました")

            st.markdown("---")

            # トラック複数選択編集フォーム
            with st.form(f"edit_truck_form_{product.id}"):
                st.write("**🚛 使用トラック設定（優先順位付き）**")
                
                # 使用トラック選択（複数選択）
                if not trucks_df.empty:
                    truck_options = dict(zip(trucks_df['name'], trucks_df['id']))
                    
                    # 現在のトラックIDを取得（様々な属性名に対応）
                    current_truck_ids = []
                    used_truck_ids = getattr(product, 'used_truck_ids', None) or getattr(product, 'truck_ids', None)
                    
                    if used_truck_ids:
                        try:
                            current_truck_ids = [int(tid.strip()) for tid in str(used_truck_ids).split(',')]
                        except:
                            current_truck_ids = []
                    
                    # 現在選択中のトラック名を取得
                    truck_name_map = dict(zip(trucks_df['id'], trucks_df['name']))
                    current_truck_names = [truck_name_map.get(tid) for tid in current_truck_ids if tid in truck_name_map]
                    
                    st.info("💡 **優先順位**: 上から順に優先度が高くなります（ドラッグ&ドロップで並び替え可能）")
                    
                    new_used_trucks = st.multiselect(
                        "使用トラック（複数選択可・上から優先）",
                        options=list(truck_options.keys()),
                        default=current_truck_names,
                        key=f"trucks_{product.id}",
                        help="上にあるトラックほど優先的に使用されます"
                    )
                    
                    # 優先順位の説明
                    if new_used_trucks:
                        st.success(f"**設定される優先順位:** 1位: {new_used_trucks[0]}" + 
                                 (f" → 2位: {new_used_trucks[1]}" if len(new_used_trucks) > 1 else "") +
                                 (f" → 3位: {new_used_trucks[2]}" if len(new_used_trucks) > 2 else ""))
                else:
                    new_used_trucks = []
                    st.info("トラックが登録されていません")
                
                # 現在の設定を表示
                if current_truck_names:
                    st.info(f"現在の設定（優先順）: {' → '.join(current_truck_names)}")
                else:
                    st.warning("トラックが未設定です")
                
                submitted = st.form_submit_button("💾 トラック設定を保存", type="primary", disabled=not can_edit)
                
                if submitted:
                    # ✅ 選択された順番でトラックIDを保存（優先順位）
                    selected_truck_ids = [truck_options[name] for name in new_used_trucks] if new_used_trucks else []
                    used_truck_ids_str = ','.join(map(str, selected_truck_ids)) if selected_truck_ids else None
                    
                    update_data = {
                        "used_truck_ids": used_truck_ids_str
                    }
                    
                    success = self.production_service.update_product(product.id, update_data)
                    if success:
                        st.success(f"✅ 製品 '{getattr(product, 'product_code', 'N/A')}' のトラック設定を更新しました")
                        st.rerun()
                    else:
                        st.error("❌ トラック設定の更新に失敗しました")
            
            # 削除ボタン
            st.markdown("---")
            col_del1, col_del2 = st.columns([1, 5])
            
            with col_del1:
                if st.button("🗑️ この製品を削除", key=f"delete_product_{product.id}", type="secondary", use_container_width=True, disabled=not can_edit):
                    if st.session_state.get(f"confirm_delete_{product.id}", False):
                        success = self.production_service.delete_product(product.id)
                        if success:
                            st.success(f"製品 '{getattr(product, 'product_code', 'N/A')}' を削除しました")
                            # 確認フラグをリセット
                            st.session_state[f"confirm_delete_{product.id}"] = False
                            st.rerun()
                        else:
                            st.error("製品削除に失敗しました")
                    else:
                        st.session_state[f"confirm_delete_{product.id}"] = True
                        st.warning("⚠️ もう一度クリックすると削除されます")
            
            with col_del2:
                if st.session_state.get(f"confirm_delete_{product.id}", False):
                    st.error("⚠️ 削除確認中 - もう一度「削除」ボタンをクリックしてください")
    
    def _get_truck_names_by_ids(self, truck_ids_str):
        """トラックIDの文字列からトラック名のリストを取得"""
        if not truck_ids_str:
            return []
        try:
            trucks_df = self.transport_service.get_trucks()
            if trucks_df.empty:
                return []
            truck_map = dict(zip(trucks_df['id'], trucks_df['name']))
            truck_ids = [int(tid.strip()) for tid in str(truck_ids_str).split(',')]
            return [truck_map.get(tid, f"ID:{tid}") for tid in truck_ids]
        except:
            return []
    
    def _show_product_registration(self, can_edit):
        """新規製品登録"""
        st.header("➕ 新規製品登録")

        if not can_edit:
            st.info("編集権限がないため、新規登録はできません")
            return

        try:
            containers = self.transport_service.get_containers()
            trucks_df = self.transport_service.get_trucks()
            product_data = FormComponents.product_form(containers, trucks_df)

            if product_data:
                success = self.production_service.create_product(product_data)
                if success:
                    st.success(f"製品 '{product_data['product_name']}' を登録しました")
                    st.rerun()
                else:
                    st.error("製品登録に失敗しました")
        
        except Exception as e:
            st.error(f"製品登録エラー: {e}")
    
    def _show_product_group_management(self, can_edit):
        """製品群管理"""
        st.header("🏷️ 製品群管理")
        st.write("製品群（kubota、tieraなど）の登録・編集・削除を行います。")

        if not can_edit:
            st.warning("⚠️ この画面の編集権限がありません。閲覧のみ可能です。")

        try:
            # 製品群データを取得（すべて、非アクティブも含む）
            product_groups_df = self.production_service.get_all_product_groups(include_inactive=True)

            # 新規登録フォーム
            st.subheader("➕ 新規製品群登録")
            with st.form("new_product_group_form", clear_on_submit=True):
                st.write("**📋 基本情報**")
                col1, col2, col3 = st.columns(3)

                with col1:
                    new_group_code = st.text_input(
                        "GROUP_CODE",
                        placeholder="例: KB, TR",
                        help="製品群コードを入力してください"
                    )

                with col2:
                    new_group_name = st.text_input(
                        "製品群名",
                        placeholder="例: kubota, tiera",
                        help="製品群の名前を入力してください"
                    )

                with col3:
                    new_description = st.text_input(
                        "説明（任意）",
                        placeholder="製品群の説明を入力",
                        help="製品群の説明（省略可）"
                    )

                st.markdown("---")

                # 機能有効化設定
                st.write("**⚙️ 機能設定**")
                col_func1, col_func2, col_func3, col_func4 = st.columns(4)

                with col_func1:
                    new_enable_container = st.checkbox(
                        "容器管理",
                        value=True,
                        help="容器管理機能を有効化"
                    )

                with col_func2:
                    new_enable_transport = st.checkbox(
                        "輸送計画",
                        value=True,
                        help="輸送計画機能を有効化"
                    )

                with col_func3:
                    new_enable_progress = st.checkbox(
                        "進捗管理",
                        value=True,
                        help="進捗管理機能を有効化"
                    )

                with col_func4:
                    new_enable_inventory = st.checkbox(
                        "在庫管理",
                        value=False,
                        help="在庫管理機能を有効化"
                    )

                st.markdown("---")

                # デフォルト値設定
                st.write("**🎯 デフォルト設定**")
                col_def1, col_def2, col_def3, col_def4 = st.columns(4)

                with col_def1:
                    new_default_lead_time = st.number_input(
                        "デフォルトリードタイム(日)",
                        value=2,
                        min_value=0,
                        max_value=30,
                        step=1,
                        help="この製品群のデフォルトリードタイム"
                    )

                with col_def2:
                    new_default_priority = st.number_input(
                        "デフォルト優先度",
                        value=5,
                        min_value=1,
                        max_value=10,
                        step=1,
                        help="優先度（1:最高 〜 10:最低）"
                    )

                with col_def3:
                    new_display_order = st.number_input(
                        "表示順序",
                        value=0,
                        min_value=0,
                        max_value=999,
                        step=1,
                        help="小さいほど上に表示されます"
                    )

                with col_def4:
                    new_is_active = st.checkbox(
                        "有効",
                        value=True,
                        help="無効にすると一覧に表示されなくなります"
                    )

                st.markdown("---")

                submitted = st.form_submit_button("💾 登録", type="primary", use_container_width=True, disabled=not can_edit)

                if submitted:
                    if not new_group_code or not new_group_code.strip():
                        st.error("❌ GROUP_CODEを入力してください")
                    elif not new_group_name or not new_group_name.strip():
                        st.error("❌ 製品群名を入力してください")
                    else:
                        # 製品群を登録
                        success = self.production_service.create_product_group({
                            'group_code': new_group_code.strip(),
                            'group_name': new_group_name.strip(),
                            'description': new_description.strip() if new_description else None,
                            'enable_container_management': new_enable_container,
                            'enable_transport_planning': new_enable_transport,
                            'enable_progress_tracking': new_enable_progress,
                            'enable_inventory_management': new_enable_inventory,
                            'default_lead_time_days': new_default_lead_time,
                            'default_priority': new_default_priority,
                            'display_order': new_display_order,
                            'is_active': new_is_active
                        })

                        if success:
                            st.success(f"✅ 製品群 '{new_group_name}' を登録しました")
                            st.rerun()
                        else:
                            st.error("❌ 製品群の登録に失敗しました（同じ名前が既に存在する可能性があります）")

            st.markdown("---")

            # 登録済み製品群一覧
            st.subheader("📋 登録済み製品群")

            if product_groups_df is None or product_groups_df.empty:
                st.info("登録されている製品群がありません")
            else:
                # 製品群ごとに表示・編集
                for _, group in product_groups_df.iterrows():
                    group_id = group['id']
                    group_code = group.get('group_code', '') or ''
                    group_name = group['group_name']
                    description = group.get('description', '') or ''

                    # アクティブ状態を取得
                    is_active = bool(group.get('is_active', True))
                    display_order = int(group.get('display_order', 0))

                    # ステータスマークを追加
                    status_mark = "✅" if is_active else "❌"

                    with st.expander(f"{status_mark} {group_name} (CODE: {group_code}, ID: {group_id})"):
                        # 基本情報表示
                        col_info1, col_info2, col_info3 = st.columns(3)
                        with col_info1:
                            st.write(f"**GROUP_CODE:** {group_code if group_code else '（なし）'}")
                            st.write(f"**説明:** {description if description else '（なし）'}")
                        with col_info2:
                            st.write(f"**有効/無効:** {'✅ 有効' if is_active else '❌ 無効'}")
                            st.write(f"**表示順序:** {display_order}")
                            st.write(f"**製品数:** {group.get('product_count', 0)}件")
                        with col_info3:
                            st.write(f"**デフォルトリードタイム:** {group.get('default_lead_time_days', 2)}日")
                            st.write(f"**デフォルト優先度:** {group.get('default_priority', 5)}")

                        # 編集フォーム
                        with st.form(f"edit_group_form_{group_id}"):
                            st.write("**✏️ 製品群情報を編集**")

                            # 基本情報
                            st.write("**📋 基本情報**")
                            col_edit1, col_edit2, col_edit3 = st.columns(3)

                            with col_edit1:
                                updated_code = st.text_input(
                                    "GROUP_CODE",
                                    value=group_code,
                                    key=f"code_{group_id}"
                                )

                            with col_edit2:
                                updated_name = st.text_input(
                                    "製品群名",
                                    value=group_name,
                                    key=f"name_{group_id}"
                                )

                            with col_edit3:
                                updated_description = st.text_input(
                                    "説明",
                                    value=description,
                                    key=f"desc_{group_id}"
                                )

                            st.markdown("---")

                            # 機能有効化設定
                            st.write("**⚙️ 機能設定**")
                            col_func1, col_func2, col_func3, col_func4 = st.columns(4)

                            with col_func1:
                                enable_container = st.checkbox(
                                    "容器管理",
                                    value=bool(group.get('enable_container_management', True)),
                                    key=f"container_{group_id}",
                                    help="容器管理機能を有効化"
                                )

                            with col_func2:
                                enable_transport = st.checkbox(
                                    "輸送計画",
                                    value=bool(group.get('enable_transport_planning', True)),
                                    key=f"transport_{group_id}",
                                    help="輸送計画機能を有効化"
                                )

                            with col_func3:
                                enable_progress = st.checkbox(
                                    "進捗管理",
                                    value=bool(group.get('enable_progress_tracking', True)),
                                    key=f"progress_{group_id}",
                                    help="進捗管理機能を有効化"
                                )

                            with col_func4:
                                enable_inventory = st.checkbox(
                                    "在庫管理",
                                    value=bool(group.get('enable_inventory_management', False)),
                                    key=f"inventory_{group_id}",
                                    help="在庫管理機能を有効化"
                                )

                            st.markdown("---")

                            # デフォルト値設定
                            st.write("**🎯 デフォルト設定**")
                            col_def1, col_def2, col_def3, col_def4 = st.columns(4)

                            with col_def1:
                                default_lead_time = st.number_input(
                                    "デフォルトリードタイム(日)",
                                    value=int(group.get('default_lead_time_days', 2)),
                                    min_value=0,
                                    max_value=30,
                                    step=1,
                                    key=f"lead_{group_id}",
                                    help="この製品群のデフォルトリードタイム"
                                )

                            with col_def2:
                                default_priority = st.number_input(
                                    "デフォルト優先度",
                                    value=int(group.get('default_priority', 5)),
                                    min_value=1,
                                    max_value=10,
                                    step=1,
                                    key=f"priority_{group_id}",
                                    help="優先度（1:最高 〜 10:最低）"
                                )

                            with col_def3:
                                updated_display_order = st.number_input(
                                    "表示順序",
                                    value=display_order,
                                    min_value=0,
                                    max_value=999,
                                    step=1,
                                    key=f"order_{group_id}",
                                    help="小さいほど上に表示されます"
                                )

                            with col_def4:
                                updated_is_active = st.checkbox(
                                    "有効",
                                    value=is_active,
                                    key=f"active_{group_id}",
                                    help="無効にすると一覧に表示されなくなります"
                                )

                            st.markdown("---")

                            update_submitted = st.form_submit_button("💾 更新", type="primary", disabled=not can_edit)

                            if update_submitted:
                                if not updated_code or not updated_code.strip():
                                    st.error("❌ GROUP_CODEを入力してください")
                                elif not updated_name or not updated_name.strip():
                                    st.error("❌ 製品群名を入力してください")
                                else:
                                    update_data = {
                                        'group_code': updated_code.strip(),
                                        'group_name': updated_name.strip(),
                                        'description': updated_description.strip() if updated_description else None,
                                        'enable_container_management': enable_container,
                                        'enable_transport_planning': enable_transport,
                                        'enable_progress_tracking': enable_progress,
                                        'enable_inventory_management': enable_inventory,
                                        'default_lead_time_days': default_lead_time,
                                        'default_priority': default_priority,
                                        'display_order': updated_display_order,
                                        'is_active': updated_is_active
                                    }

                                    success = self.production_service.update_product_group(group_id, update_data)

                                    if success:
                                        st.success(f"✅ 製品群 '{updated_name}' を更新しました")
                                        st.rerun()
                                    else:
                                        st.error("❌ 製品群の更新に失敗しました")

                        # 削除ボタン
                        st.markdown("---")
                        col_del1, col_del2 = st.columns([1, 5])

                        with col_del1:
                            if st.button(
                                "🗑️ 削除",
                                key=f"delete_group_{group_id}",
                                type="secondary",
                                use_container_width=True,
                                disabled=not can_edit
                            ):
                                # 確認フラグをチェック
                                confirm_key = f"confirm_delete_group_{group_id}"
                                if st.session_state.get(confirm_key, False):
                                    # 実際に削除
                                    success = self.production_service.delete_product_group(group_id)
                                    if success:
                                        st.success(f"✅ 製品群 '{group_name}' を削除しました")
                                        st.session_state[confirm_key] = False
                                        st.rerun()
                                    else:
                                        st.error("❌ 製品群の削除に失敗しました（この製品群を使用している製品がある可能性があります）")
                                else:
                                    # 確認フラグを設定
                                    st.session_state[confirm_key] = True
                                    st.warning("⚠️ もう一度クリックすると削除されます")

                        with col_del2:
                            if st.session_state.get(f"confirm_delete_group_{group_id}", False):
                                st.error("⚠️ 削除確認中 - もう一度「削除」ボタンをクリックしてください")

        except Exception as e:
            st.error(f"製品群管理エラー: {e}")
            import traceback
            st.code(traceback.format_exc())

    def _show_product_container_mapping(self):
        """製品×容器紐付け管理"""
        st.header("🔗 製品×容器紐付け設定")

        st.warning("""
        **この機能は product_container_mapping テーブルが必要です**

        以下のSQLを実行してテーブルを作成してください:
        """)

        st.code("""
CREATE TABLE product_container_mapping (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    container_id INT NOT NULL,
    max_quantity INT DEFAULT 100 COMMENT '容器あたりの最大積載数',
    is_primary TINYINT(1) DEFAULT 0 COMMENT '主要容器フラグ',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (container_id) REFERENCES container_capacity(id) ON DELETE CASCADE,
    UNIQUE KEY unique_product_container (product_id, container_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='製品と容器の紐付けマスタ';
        """, language="sql")

        st.info("テーブル作成後、この機能を実装します。")