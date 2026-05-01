"""
models/shipments.py — Shipment and Delivery CRUD operations.
All writes go through here; no UI module touches SQL directly.
"""

from datetime import datetime
from app.database import get_connection
from app.auth import write_audit_log


def _next_ref() -> str:
    """Generate the next sequential shipment reference SHP-YYYY-NNNN."""
    year = datetime.now().year
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(*) FROM Shipments WHERE shipment_ref LIKE ?", (f"SHP-{year}-%",)
    ).fetchone()
    conn.close()
    return f"SHP-{year}-{row[0]+1:04d}"


def get_all_shipments(status_filter: str = None, search: str = None) -> list:
    conn = get_connection()
    sql = """
        SELECT s.*, w.name AS warehouse_name,
               u.full_name AS driver_name, v.registration AS vehicle_reg,
               cu.full_name AS created_by_name
        FROM Shipments s
        LEFT JOIN Warehouses w ON s.warehouse_id = w.id
        LEFT JOIN Drivers d ON s.driver_id = d.id
        LEFT JOIN Users u ON d.user_id = u.id
        LEFT JOIN Vehicles v ON s.vehicle_id = v.id
        LEFT JOIN Users cu ON s.created_by = cu.id
    """
    params = []
    conditions = []
    if status_filter and status_filter != "All":
        conditions.append("s.status = ?")
        params.append(status_filter)
    if search:
        conditions.append("(s.shipment_ref LIKE ? OR s.receiver_name LIKE ? OR s.sender_name LIKE ?)")
        params += [f"%{search}%", f"%{search}%", f"%{search}%"]
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY s.created_at DESC"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows


def get_shipment_by_id(shipment_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM Shipments WHERE id=?", (shipment_id,)).fetchone()
    conn.close()
    return row


def add_shipment(data: dict, user_id: int) -> tuple[bool, str]:
    conn = get_connection()
    try:
        ref = _next_ref()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = conn.execute("""
            INSERT INTO Shipments(shipment_ref,order_number,warehouse_id,driver_id,vehicle_id,
            created_by,sender_name,sender_address,receiver_name,receiver_address,receiver_phone,
            item_description,weight_kg,status,transport_cost,surcharge,payment_status,notes,
            created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            ref, data.get("order_number"), data["warehouse_id"],
            data.get("driver_id") or None, data.get("vehicle_id") or None,
            user_id, data["sender_name"], data["sender_address"],
            data["receiver_name"], data["receiver_address"],
            data.get("receiver_phone"), data["item_description"],
            float(data.get("weight_kg", 0)),
            data.get("status", "pending"),
            float(data.get("transport_cost", 0)),
            float(data.get("surcharge", 0)),
            data.get("payment_status", "pending"),
            data.get("notes"), now, now
        ))
        shp_id = cur.lastrowid
        # Auto-create linked Delivery row
        conn.execute("""
            INSERT INTO Deliveries(shipment_id,driver_id,vehicle_id,scheduled_date,status)
            VALUES(?,?,?,?,?)
        """, (shp_id, data.get("driver_id") or None, data.get("vehicle_id") or None,
              data.get("scheduled_date"), data.get("status", "pending")))
        conn.commit()
        write_audit_log(user_id, "INSERT", "Shipments", shp_id, f"Added shipment {ref}")
        return True, ref
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def update_shipment(shipment_id: int, data: dict, user_id: int) -> tuple[bool, str]:
    conn = get_connection()
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("""
            UPDATE Shipments SET
                order_number=?, warehouse_id=?, driver_id=?, vehicle_id=?,
                sender_name=?, sender_address=?, receiver_name=?, receiver_address=?,
                receiver_phone=?, item_description=?, weight_kg=?, status=?,
                transport_cost=?, surcharge=?, payment_status=?, notes=?, updated_at=?
            WHERE id=?
        """, (
            data.get("order_number"), data["warehouse_id"],
            data.get("driver_id") or None, data.get("vehicle_id") or None,
            data["sender_name"], data["sender_address"],
            data["receiver_name"], data["receiver_address"],
            data.get("receiver_phone"), data["item_description"],
            float(data.get("weight_kg", 0)),
            data.get("status", "pending"),
            float(data.get("transport_cost", 0)),
            float(data.get("surcharge", 0)),
            data.get("payment_status", "pending"),
            data.get("notes"), now, shipment_id
        ))
        # Sync delivery status
        conn.execute("""
            UPDATE Deliveries SET driver_id=?, vehicle_id=?, status=?,
            scheduled_date=?, updated_at=?
            WHERE shipment_id=?
        """, (data.get("driver_id") or None, data.get("vehicle_id") or None,
              data.get("status","pending"), data.get("scheduled_date"), now, shipment_id))
        conn.commit()
        write_audit_log(user_id, "UPDATE", "Shipments", shipment_id,
                        f"Updated shipment id={shipment_id}")
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def delete_shipment(shipment_id: int, user_id: int) -> tuple[bool, str]:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM Shipments WHERE id=?", (shipment_id,))
        conn.commit()
        write_audit_log(user_id, "DELETE", "Shipments", shipment_id,
                        f"Deleted shipment id={shipment_id}")
        return True, ""
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


def get_drivers_list() -> list:
    conn = get_connection()
    rows = conn.execute("""
        SELECT d.id, u.full_name FROM Drivers d
        JOIN Users u ON d.user_id = u.id
        WHERE d.status IN ('available','on_route')
        ORDER BY u.full_name
    """).fetchall()
    conn.close()
    return rows


def get_vehicles_list() -> list:
    conn = get_connection()
    rows = conn.execute("""
        SELECT id, registration, vehicle_type FROM Vehicles
        WHERE status IN ('available','in_use')
        ORDER BY registration
    """).fetchall()
    conn.close()
    return rows
