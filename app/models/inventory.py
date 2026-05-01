"""
models/inventory.py — Inventory CRUD and stock adjustment.
"""

from datetime import datetime
from app.database import get_connection
from app.auth import write_audit_log


def get_all_inventory(warehouse_id: int = None, search: str = None) -> list:
    conn = get_connection()
    sql = """
        SELECT i.*, w.name AS warehouse_name
        FROM Inventory i
        JOIN Warehouses w ON i.warehouse_id = w.id
    """
    params = []
    conditions = []
    if warehouse_id:
        conditions.append("i.warehouse_id = ?")
        params.append(warehouse_id)
    if search:
        conditions.append("(i.sku LIKE ? OR i.item_name LIKE ?)")
        params += [f"%{search}%", f"%{search}%"]
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY i.item_name"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows


def get_low_stock() -> list:
    conn = get_connection()
    rows = conn.execute("""
        SELECT i.*, w.name AS warehouse_name
        FROM Inventory i JOIN Warehouses w ON i.warehouse_id = w.id
        WHERE i.quantity <= i.reorder_level
        ORDER BY i.quantity ASC
    """).fetchall()
    conn.close()
    return rows


def add_item(data: dict, user_id: int) -> tuple[bool, str]:
    conn = get_connection()
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = conn.execute("""
            INSERT INTO Inventory(warehouse_id,sku,item_name,description,quantity,
            reorder_level,unit_weight_kg,location_code,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)
        """, (data["warehouse_id"], data["sku"], data["item_name"],
              data.get("description"), int(data.get("quantity", 0)),
              int(data.get("reorder_level", 10)),
              float(data.get("unit_weight_kg", 1.0)),
              data.get("location_code"), now, now))
        conn.commit()
        write_audit_log(user_id, "INSERT", "Inventory", cur.lastrowid,
                        f"Added inventory item: {data['item_name']}")
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def update_item(item_id: int, data: dict, user_id: int) -> tuple[bool, str]:
    conn = get_connection()
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("""
            UPDATE Inventory SET warehouse_id=?,sku=?,item_name=?,description=?,
            quantity=?,reorder_level=?,unit_weight_kg=?,location_code=?,updated_at=?
            WHERE id=?
        """, (data["warehouse_id"], data["sku"], data["item_name"],
              data.get("description"), int(data.get("quantity", 0)),
              int(data.get("reorder_level", 10)),
              float(data.get("unit_weight_kg", 1.0)),
              data.get("location_code"), now, item_id))
        conn.commit()
        write_audit_log(user_id, "UPDATE", "Inventory", item_id,
                        f"Updated item id={item_id}")
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def delete_item(item_id: int, user_id: int) -> tuple[bool, str]:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM Inventory WHERE id=?", (item_id,))
        conn.commit()
        write_audit_log(user_id, "DELETE", "Inventory", item_id,
                        f"Deleted inventory item id={item_id}")
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def adjust_stock(item_id: int, delta: int, reason: str, user_id: int) -> tuple[bool, str]:
    """Safely increment or decrement stock quantity."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT quantity FROM Inventory WHERE id=?", (item_id,)).fetchone()
        if not row:
            return False, "Item not found."
        new_qty = row["quantity"] + delta
        if new_qty < 0:
            return False, f"Cannot reduce below 0. Current stock: {row['quantity']}"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("UPDATE Inventory SET quantity=?, updated_at=? WHERE id=?",
                     (new_qty, now, item_id))
        conn.commit()
        write_audit_log(user_id, "STOCK_ADJUST", "Inventory", item_id,
                        f"Stock adjusted by {delta:+d}. Reason: {reason}")
        return True, str(new_qty)
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def get_warehouses_list() -> list:
    conn = get_connection()
    rows = conn.execute("SELECT id, name FROM Warehouses ORDER BY name").fetchall()
    conn.close()
    return rows
