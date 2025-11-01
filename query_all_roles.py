# -*- coding: utf-8 -*-
import sys
sys.path.append('.')
from repository.database_manager import DatabaseManager
from sqlalchemy import text
import json

try:
    db = DatabaseManager()
    session = db.get_session()
    
    # 全ロール取得
    query = text("SELECT id, role_name, description FROM roles ORDER BY id")
    roles = session.execute(query).fetchall()
    
    all_roles = {}
    
    for role_id, role_name, description in roles:
        role_info = {
            'role_id': role_id,
            'role_name': role_name,
            'description': description,
            'page_permissions': [],
            'tab_permissions': []
        }
        
        # ページ権限
        query = text("""
            SELECT page_name, can_view, can_edit 
            FROM page_permissions 
            WHERE role_id = :role_id
            ORDER BY page_name
        """)
        pages = session.execute(query, {'role_id': role_id}).fetchall()
        
        for page_name, can_view, can_edit in pages:
            role_info['page_permissions'].append({
                'page_name': page_name,
                'can_view': bool(can_view),
                'can_edit': bool(can_edit)
            })
        
        # タブ権限
        query = text("""
            SELECT page_name, tab_name, can_view, can_edit 
            FROM tab_permissions 
            WHERE role_id = :role_id
            ORDER BY page_name, tab_name
        """)
        tabs = session.execute(query, {'role_id': role_id}).fetchall()
        
        for page_name, tab_name, can_view, can_edit in tabs:
            role_info['tab_permissions'].append({
                'page_name': page_name,
                'tab_name': tab_name,
                'can_view': bool(can_view),
                'can_edit': bool(can_edit)
            })
        
        all_roles[role_name] = role_info
    
    # JSON形式でファイルに出力
    with open('all_roles_permissions.json', 'w', encoding='utf-8') as f:
        json.dump(all_roles, f, ensure_ascii=False, indent=2)
    
    print("all_roles_permissions.json に出力しました")
    
    session.close()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
