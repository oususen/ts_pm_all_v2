# -*- coding: utf-8 -*-
from repository.database_manager import DatabaseManager
from sqlalchemy import text

db = DatabaseManager()
session = db.get_session()

# Get recent dates with 4-5T products
query = text('''
    SELECT DISTINCT DATE(dp.order_date) as order_date
    FROM delivery_progress dp
    INNER JOIN products p ON dp.product_id = p.id
    LEFT JOIN container_capacity cc ON p.used_container_id = cc.id
    WHERE cc.name LIKE :pattern
        AND dp.order_quantity > 0
    ORDER BY order_date DESC
    LIMIT 10
''')

result = session.execute(query, {'pattern': '%4-5T%'})
rows = result.fetchall()

print('Recent dates with 4-5T products:')
for row in rows:
    print(f'  {row.order_date}')

session.close()
