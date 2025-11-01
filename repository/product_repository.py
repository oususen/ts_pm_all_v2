# app/repository/product_repository.py

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import Column, Integer, String, Date, TIMESTAMP, Boolean, Text, text
from sqlalchemy.orm import declarative_base
import pandas as pd
from typing import Optional
from .database_manager import DatabaseManager

Base = declarative_base()

class ProductORM(Base):
    """製品テーブル - SQLAlchemy ORM（実テーブル構造に完全一致）"""
    __tablename__ = "products"

    # ✅ 実際のテーブルに存在するカラムのみ定義
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_code = Column(String(50))
    product_name = Column(String(200))
    model_name = Column(String(255))  # 機種名
    product_group_id = Column(Integer)  # 製品群ID
    display_id = Column(Integer)  # 表示順序
    delivery_location = Column(String(100))
    box_type = Column(String(20))
    capacity = Column(Integer)
    container_width = Column(Integer)
    container_depth = Column(Integer)
    container_height = Column(Integer)
    stackable = Column(Integer)  # tinyint(1)
    can_advance = Column(Integer)  # tinyint(1)
    lead_time_days = Column(Integer)  # リードタイム日数
    fixed_point_days = Column(Integer)  # 固定日数
    used_container_id = Column(Integer)
    used_truck_ids = Column(String(100))
    created_at = Column(TIMESTAMP)
    inspection_category = Column(String(10))


class ProductionConstraintORM(Base):
    """生産制約テーブル - SQLAlchemy ORM"""
    __tablename__ = "production_constraints"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, nullable=False, unique=True)
    daily_capacity = Column(Integer, nullable=False, default=1000)
    smoothing_level = Column(Integer, nullable=False)
    volume_per_unit = Column(Integer, nullable=False)
    is_transport_constrained = Column(Integer, nullable=False, default=0)
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)


class ProductGroupORM(Base):
    """Product group table represented via SQLAlchemy ORM."""
    __tablename__ = "product_groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_code = Column(String(50), unique=True, nullable=False)
    group_name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    enable_container_management = Column(Boolean, default=True)
    enable_transport_planning = Column(Boolean, default=True)
    enable_progress_tracking = Column(Boolean, default=True)
    enable_inventory_management = Column(Boolean, default=False)
    default_lead_time_days = Column(Integer, default=2)
    default_priority = Column(Integer, default=5)
    is_active = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)
    notes = Column(Text)
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)


class ProductRepository:
    """製品関連データアクセス"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def get_all_products(self):
        """全製品を取得（製品グループ情報を含む）"""
        try:
            query = """
            SELECT
                p.id, p.product_code, p.product_name, p.model_name,
                p.display_id, p.product_group_id,
                p.used_container_id, p.used_truck_ids,
                p.capacity, p.inspection_category, p.can_advance,
                p.stackable,
                p.lead_time_days, p.fixed_point_days,
                pg.group_code
            FROM products p
            LEFT JOIN product_groups pg ON p.product_group_id = pg.id
            ORDER BY COALESCE(p.display_id, 0), p.product_code
            """

            result = self.db.execute_query(query)

            print(f"[DEBUG] 製品データ取得 - {len(result)}件")

            if result.empty:
                print("[WARN] 製品データが0件")

            return result

        except Exception as e:
            print(f"[ERROR] 製品データ取得エラー: {e}")
            return pd.DataFrame()
    
    def get_product_constraints(self) -> pd.DataFrame:
        """製品制約取得"""
        session = self.db.get_session()
        try:
            query = """
                SELECT 
                    pc.id,
                    pc.product_id,
                    pc.daily_capacity,
                    pc.smoothing_level,
                    pc.volume_per_unit,
                    pc.is_transport_constrained,
                    p.product_code,
                    p.product_name,
                    p.inspection_category
                FROM production_constraints pc
                LEFT JOIN products p ON pc.product_id = p.id
                ORDER BY p.product_code
            """
            result = session.execute(text(query))
            rows = result.fetchall()
            
            return pd.DataFrame([{
                "id": row[0],
                "product_id": row[1],
                "daily_capacity": row[2] or 0,
                "smoothing_level": float(row[3]) if row[3] else 0.0,
                "volume_per_unit": float(row[4]) if row[4] else 0.0,
                "is_transport_constrained": bool(row[5]) if row[5] is not None else False,
                "product_code": row[6] or "",
                "product_name": row[7] or "",
                "inspection_category": row[8] or ""
            } for row in rows])
        except SQLAlchemyError as e:
            print(f"製品制約取得エラー: {e}")
            return pd.DataFrame()
        finally:
            session.close()

    def save_product_constraints(self, constraints_df: pd.DataFrame) -> bool:
        """製品制約保存（全削除 → 一括挿入）"""
        session = self.db.get_session()
        try:
            session.query(ProductionConstraintORM).delete()
            for _, row in constraints_df.iterrows():
                constraint = ProductionConstraintORM(
                    product_id=int(row.get("product_id", 0)),
                    daily_capacity=int(row.get("daily_capacity", 0)),
                    smoothing_level=float(row.get("smoothing_level", 0.0)),
                    volume_per_unit=float(row.get("volume_per_unit", 0.0)),
                    is_transport_constrained=int(bool(row.get("is_transport_constrained", False)))
                )
                session.add(constraint)
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            print(f"製品制約保存エラー: {e}")
            return False
        finally:
            session.close()   

    def create_product(self, product_data: dict) -> bool:
        """製品を新規登録"""
        VALID_CATEGORIES = {'F', 'N', 'NS', 'FS', '$S'}
        
        category = product_data.get("inspection_category")

        if category not in VALID_CATEGORIES:
            print(f"⚠️ 警告: 不正な inspection_category の値 '{category}' が指定されました。登録を中止します。")
            return False
        
        session = self.db.get_session()
        try:
            product = ProductORM(
                product_code=product_data.get("product_code"),
                product_name=product_data.get("product_name"),
                product_group_id=product_data.get("product_group_id"),
                inspection_category=category,
                capacity=product_data.get("capacity", 0),
                container_width=product_data.get("container_width", 0),
                container_depth=product_data.get("container_depth", 0),
                container_height=product_data.get("container_height", 0),
                stackable=int(product_data.get("stackable", False)),
                used_container_id=product_data.get("used_container_id"),
                used_truck_ids=product_data.get("used_truck_ids"),
                can_advance=int(product_data.get("can_advance", False)),
                lead_time_days=product_data.get("lead_time_days", 0),
                fixed_point_days=product_data.get("fixed_point_days", 0),
                delivery_location=product_data.get("delivery_location"),
                box_type=product_data.get("box_type")
            )
            session.add(product)
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            print(f"製品登録エラー: {e}")
            return False
        finally:
            session.close()

    def update_product(self, product_id: int, update_data: dict) -> bool:
        """製品を更新 - 修正版"""
        session = self.db.get_session()
        try:
            print(f"[DEBUG] update_product: ID={product_id}, data={update_data}")

            product = session.get(ProductORM, product_id)

            if product:
                print(f"[INFO] 製品見つかりました: {product.product_code}")

                for key, value in update_data.items():
                    if hasattr(product, key):
                        # bool値をintに変換
                        if key in ['stackable', 'can_advance'] and isinstance(value, bool):
                            value = int(value)

                        old_value = getattr(product, key, None)
                        print(f"[UPDATE] {key}: {old_value} -> {value}")

                        setattr(product, key, value)
                    else:
                        print(f"[WARN] カラム '{key}' は ProductORM に存在しません")

                print(f"[INFO] コミット実行中...")
                session.commit()
                print(f"[INFO] コミット成功")

                # コミット後の値を確認
                session.refresh(product)
                print(f"[DEBUG] コミット後の used_container_id: {product.used_container_id}")

                return True
            else:
                print(f"[ERROR] product_id={product_id} が見つかりません")
                return False

        except SQLAlchemyError as e:
            session.rollback()
            print(f"[ERROR] update_product エラー: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            session.close()

    def delete_product(self, product_id: int) -> bool:
        """製品を削除"""
        session = self.db.get_session()
        try:
            product = session.get(ProductORM, product_id)
            if product:
                session.delete(product)
                session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            session.rollback()
            print(f"製品削除エラー: {e}")
            return False
        finally:
            session.close()

    def get_product_by_id(self, product_id: int) -> Optional[ProductORM]:
        """IDで製品を取得"""
        session = self.db.get_session()
        try:
            return session.get(ProductORM, product_id)
        except SQLAlchemyError as e:
            print(f"製品取得エラー: {e}")
            return None
        finally:
            session.close()

    def get_all_product_groups(self, include_inactive: bool = True) -> pd.DataFrame:
        """Return product groups; include inactive rows when requested."""
        try:
            where_clause = "" if include_inactive else "WHERE pg.is_active = TRUE"
            query = f"""
            SELECT
                pg.id,
                pg.group_code,
                pg.group_name,
                pg.description,
                pg.enable_container_management,
                pg.enable_transport_planning,
                pg.enable_progress_tracking,
                pg.enable_inventory_management,
                pg.default_lead_time_days,
                pg.default_priority,
                pg.is_active,
                pg.display_order,
                pg.notes,
                pg.created_at,
                pg.updated_at,
                COALESCE(prod_stats.product_count, 0) AS product_count
            FROM product_groups pg
            LEFT JOIN (
                SELECT
                    product_group_id,
                    COUNT(*) AS product_count
                FROM products
                WHERE product_group_id IS NOT NULL
                GROUP BY product_group_id
            ) prod_stats ON prod_stats.product_group_id = pg.id
            {where_clause}
            ORDER BY pg.display_order, pg.group_code
            """
            result = self.db.execute_query(query)
            return result
        except Exception as e:
            print(f"Failed to fetch product group data: {e}")
            return pd.DataFrame()

    def create_product_group(self, group_data: dict) -> Optional[int]:
        """Persist a newly created product group."""
        session = self.db.get_session()
        try:
            default_lead_time = group_data.get("default_lead_time_days")
            default_priority = group_data.get("default_priority")
            display_order = group_data.get("display_order")

            group = ProductGroupORM(
                group_code=group_data.get("group_code"),
                group_name=group_data.get("group_name"),
                description=group_data.get("description") or None,
                enable_container_management=bool(group_data.get("enable_container_management", True)),
                enable_transport_planning=bool(group_data.get("enable_transport_planning", True)),
                enable_progress_tracking=bool(group_data.get("enable_progress_tracking", True)),
                enable_inventory_management=bool(group_data.get("enable_inventory_management", False)),
                default_lead_time_days=int(default_lead_time) if default_lead_time not in (None, "") else None,
                default_priority=int(default_priority) if default_priority not in (None, "") else None,
                is_active=bool(group_data.get("is_active", True)),
                display_order=int(display_order) if display_order not in (None, "") else None,
                notes=group_data.get("notes") or None
            )

            session.add(group)
            session.commit()
            return group.id
        except SQLAlchemyError as e:
            session.rollback()
            print(f"Failed to create product group: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            session.close()

    def update_product_group(self, group_id: int, update_data: dict) -> bool:
        """Update an existing product group."""
        session = self.db.get_session()
        try:
            group = session.get(ProductGroupORM, group_id)
            if not group:
                print(f"[WARN] Product group not found: ID={group_id}")
                return False

            bool_fields = {
                "enable_container_management",
                "enable_transport_planning",
                "enable_progress_tracking",
                "enable_inventory_management",
                "is_active"
            }
            int_fields = {
                "default_lead_time_days",
                "default_priority",
                "display_order"
            }

            for key, value in update_data.items():
                if not hasattr(group, key):
                    print(f"[WARN] Unknown attribute '{key}' on ProductGroupORM; skipping.")
                    continue

                if value == "":
                    value = None

                if key in bool_fields and value is not None:
                    value = bool(value)

                if key in int_fields and value is not None:
                    try:
                        value = int(value)
                    except (TypeError, ValueError):
                        print(f"[WARN] Invalid integer value for '{key}': {value}")
                        continue

                setattr(group, key, value)

            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            print(f"Failed to update product group: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            session.close()

    def delete_product_group(self, group_id: int) -> bool:
        """Delete a product group."""
        session = self.db.get_session()
        try:
            group = session.get(ProductGroupORM, group_id)
            if not group:
                print(f"[WARN] Product group not found: ID={group_id}")
                return False

            session.delete(group)
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            print(f"Failed to delete product group: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            session.close()

    def get_product_groups(self) -> pd.DataFrame:
        """Return only active product groups."""
        return self.get_all_product_groups(include_inactive=False)
