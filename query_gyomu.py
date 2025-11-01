# -*- coding: utf-8 -*-
import sys
sys.path.append('.')
from repository.database_manager import DatabaseManager
from sqlalchemy import text
import json

try:
    db = DatabaseManager()
    session = db.get_session()
    
    # gyomuロール（配送管理者）のID取得
    query = text("SELECT id FROM roles WHERE role_name = '配送管理者'")
    role_id_result = session.execute(query).scalar()
    
    result = {}
    result['role_id'] = role_id_result
    result['role_name'] = '配送管理者'
    
    # ページ権限を取得
    query = text("""
        SELECT page_name, can_view, can_edit 
        FROM page_permissions 
        WHERE role_id = :role_id
        ORDER BY page_name
    """)
    page_perms = session.execute(query, {'role_id': role_id_result}).fetchall()
    
    pages = []
    for row in page_perms:
        pages.append({
            'page_name': row[0],
            'can_view': bool(row[1]),
            'can_edit': bool(row[2])
        })
    result['page_permissions'] = pages
    
    # タブ権限を取得
    query = text("""
        SELECT page_name, tab_name, can_view, can_edit 
        FROM tab_permissions 
        WHERE role_id = :role_id
        ORDER BY page_name, tab_name
    """)
    tab_perms = session.execute(query, {'role_id': role_id_result}).fetchall()
    
    tabs = []
    for row in tab_perms:
        tabs.append({
            'page_name': row[0],
            'tab_name': row[1],
            'can_view': bool(row[2]),
            'can_edit': bool(row[3])
        })
    result['tab_permissions'] = tabs
    
    # JSON形式でファイルに出力
    with open('gyomu_permissions.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print("gyomu_permissions.json に出力しました")
    
    session.close()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
