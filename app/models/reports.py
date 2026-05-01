"""
models/reports.py — Dashboard stats, pandas reports, incidents, user management, audit log.
"""

import os
from datetime import datetime

import pandas as pd

from app.database import get_connection, hash_password
from app.auth import write_audit_log

REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


# ── Dashboard ────────────────────────────────────────────────────────────────

def get_dashboard_stats() -> dict:
    conn = get_connection()
    s = {}
    s["total_shipments"]   = conn.execute("SELECT COUNT(*) FROM Shipments").fetchone()[0]
    s["pending"]           = conn.execute("SELECT COUNT(*) FROM Shipments WHERE status='pending'").fetchone()[0]
    s["in_transit"]        = conn.execute("SELECT COUNT(*) FROM Shipments WHERE status='in_transit'").fetchone()[0]
    s["delivered"]         = conn.execute("SELECT COUNT(*) FROM Shipments WHERE status='delivered'").fetchone()[0]
    s["delayed"]           = conn.execute("SELECT COUNT(*) FROM Shipments WHERE status='delayed'").fetchone()[0]
    s["low_stock_items"]   = conn.execute("SELECT COUNT(*) FROM Inventory WHERE quantity <= reorder_level").fetchone()[0]
    s["available_vehicles"]= conn.execute("SELECT COUNT(*) FROM Vehicles WHERE status='available'").fetchone()[0]
    s["available_drivers"] = conn.execute("SELECT COUNT(*) FROM Drivers WHERE status='available'").fetchone()[0]
    row = conn.execute("SELECT SUM(transport_cost + surcharge) FROM Shipments WHERE payment_status='pending'").fetchone()
    s["revenue_pending"]   = row[0] or 0.0
    row2 = conn.execute("SELECT SUM(transport_cost + surcharge) FROM Shipments WHERE payment_status='paid'").fetchone()
    s["revenue_paid"]      = row2[0] or 0.0
    s["open_incidents"]    = conn.execute("SELECT COUNT(*) FROM Incidents WHERE is_resolved=0").fetchone()[0]
    s["total_warehouses"]  = conn.execute("SELECT COUNT(*) FROM Warehouses").fetchone()[0]
    conn.close()
    return s


# ── Pandas Reports ───────────────────────────────────────────────────────────

def report_shipment_status() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT s.shipment_ref AS "Ref", s.order_number AS "Order",
               s.sender_name AS "Sender", s.receiver_name AS "Receiver",
               w.name AS "Warehouse", u.full_name AS "Driver",
               s.weight_kg AS "Weight (kg)",
               s.transport_cost + s.surcharge AS "Total Cost (£)",
               s.payment_status AS "Payment", s.status AS "Status",
               s.created_at AS "Created"
        FROM Shipments s
        LEFT JOIN Warehouses w ON s.warehouse_id = w.id
        LEFT JOIN Drivers d ON s.driver_id = d.id
        LEFT JOIN Users u ON d.user_id = u.id
        ORDER BY s.created_at DESC
    """, conn)
    conn.close()
    return df


def report_vehicle_utilisation() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT v.registration AS "Registration", v.vehicle_type AS "Type",
               w.name AS "Warehouse", v.capacity_kg AS "Capacity (kg)",
               v.status AS "Status",
               COUNT(s.id) AS "Total Shipments",
               COALESCE(SUM(s.weight_kg), 0) AS "Total Weight (kg)",
               v.next_service_date AS "Next Service"
        FROM Vehicles v
        LEFT JOIN Warehouses w ON v.warehouse_id = w.id
        LEFT JOIN Shipments s ON s.vehicle_id = v.id
        GROUP BY v.id
        ORDER BY COUNT(s.id) DESC
    """, conn)
    conn.close()
    return df


def report_warehouse_activity() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT w.name AS "Warehouse", w.city AS "City",
               COUNT(DISTINCT s.id) AS "Shipments",
               COUNT(DISTINCT i.id) AS "Inventory Lines",
               COALESCE(SUM(i.quantity), 0) AS "Total Stock",
               COUNT(DISTINCT v.id) AS "Vehicles"
        FROM Warehouses w
        LEFT JOIN Shipments s ON s.warehouse_id = w.id
        LEFT JOIN Inventory i ON i.warehouse_id = w.id
        LEFT JOIN Vehicles v ON v.warehouse_id = w.id
        GROUP BY w.id
        ORDER BY w.name
    """, conn)
    conn.close()
    return df


def report_driver_performance() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT u.full_name AS "Driver", d.licence_number AS "Licence",
               d.status AS "Current Status",
               SUM(CASE WHEN s.status='delivered' THEN 1 ELSE 0 END) AS "Delivered",
               SUM(CASE WHEN s.status='delayed'   THEN 1 ELSE 0 END) AS "Delayed",
               SUM(CASE WHEN s.status='returned'  THEN 1 ELSE 0 END) AS "Returned",
               COUNT(s.id) AS "Total Assigned"
        FROM Drivers d
        JOIN Users u ON d.user_id = u.id
        LEFT JOIN Shipments s ON s.driver_id = d.id
        GROUP BY d.id
        ORDER BY u.full_name
    """, conn)
    conn.close()
    return df


def export_report_csv(df: pd.DataFrame, name: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(REPORTS_DIR, f"{name}_{ts}.csv")
    df.to_csv(path, index=False)
    return path


# ── Incidents ────────────────────────────────────────────────────────────────

def get_all_incidents(show_resolved: bool = False) -> list:
    conn = get_connection()
    sql = """
        SELECT inc.*, s.shipment_ref, u.full_name AS reporter_name
        FROM Incidents inc
        JOIN Shipments s ON inc.shipment_id = s.id
        LEFT JOIN Users u ON inc.reported_by = u.id
    """
    if not show_resolved:
        sql += " WHERE inc.is_resolved = 0"
    sql += " ORDER BY inc.created_at DESC"
    rows = conn.execute(sql).fetchall()
    conn.close()
    return rows


def add_incident(data: dict, user_id: int) -> tuple[bool, str]:
    conn = get_connection()
    try:
        cur = conn.execute("""
            INSERT INTO Incidents(shipment_id,reported_by,incident_type,description)
            VALUES(?,?,?,?)
        """, (data["shipment_id"], user_id,
              data["incident_type"], data["description"]))
        conn.commit()
        write_audit_log(user_id, "INSERT", "Incidents", cur.lastrowid,
                        f"Incident reported on shipment id={data['shipment_id']}")
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def resolve_incident(incident_id: int, resolution: str, user_id: int) -> tuple[bool, str]:
    conn = get_connection()
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("""
            UPDATE Incidents SET is_resolved=1, resolution=?, resolved_at=?
            WHERE id=?
        """, (resolution, now, incident_id))
        conn.commit()
        write_audit_log(user_id, "UPDATE", "Incidents", incident_id,
                        f"Incident id={incident_id} resolved.")
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


# ── Audit Log ────────────────────────────────────────────────────────────────

def get_audit_logs(limit: int = 200, search: str = None) -> list:
    conn = get_connection()
    sql = """
        SELECT a.*, u.username
        FROM AuditLogs a LEFT JOIN Users u ON a.user_id = u.id
    """
    params = []
    if search:
        sql += " WHERE (a.action LIKE ? OR a.description LIKE ? OR u.username LIKE ?)"
        params = [f"%{search}%", f"%{search}%", f"%{search}%"]
    sql += " ORDER BY a.timestamp DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows


# ── User Management ──────────────────────────────────────────────────────────

def get_all_users() -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT id,username,full_name,email,role,is_active,created_at FROM Users ORDER BY full_name"
    ).fetchall()
    conn.close()
    return rows


def add_user(data: dict, admin_user_id: int) -> tuple[bool, str]:
    conn = get_connection()
    try:
        pw_hash, salt = hash_password(data["password"])
        cur = conn.execute("""
            INSERT INTO Users(username,pw_hash,salt,full_name,email,role)
            VALUES(?,?,?,?,?,?)
        """, (data["username"], pw_hash, salt,
              data["full_name"], data.get("email"), data["role"]))
        conn.commit()
        write_audit_log(admin_user_id, "INSERT", "Users", cur.lastrowid,
                        f"Created user: {data['username']}")
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def update_user(user_id: int, data: dict, admin_user_id: int) -> tuple[bool, str]:
    conn = get_connection()
    try:
        conn.execute("""
            UPDATE Users SET full_name=?,email=?,role=?,is_active=? WHERE id=?
        """, (data["full_name"], data.get("email"),
              data["role"], int(data.get("is_active", 1)), user_id))
        if data.get("password"):
            pw_hash, salt = hash_password(data["password"])
            conn.execute("UPDATE Users SET pw_hash=?,salt=? WHERE id=?",
                         (pw_hash, salt, user_id))
        conn.commit()
        write_audit_log(admin_user_id, "UPDATE", "Users", user_id,
                        f"Updated user id={user_id}")
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def toggle_user_active(user_id: int, admin_user_id: int) -> tuple[bool, str]:
    conn = get_connection()
    try:
        row = conn.execute("SELECT is_active FROM Users WHERE id=?", (user_id,)).fetchone()
        if not row:
            return False, "User not found."
        new_state = 0 if row["is_active"] else 1
        conn.execute("UPDATE Users SET is_active=? WHERE id=?", (new_state, user_id))
        conn.commit()
        state_str = "enabled" if new_state else "disabled"
        write_audit_log(admin_user_id, "UPDATE", "Users", user_id,
                        f"Account {state_str} for user id={user_id}")
        return True, state_str
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()
