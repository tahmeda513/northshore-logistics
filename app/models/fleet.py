"""
models/fleet.py — Vehicles, Drivers, and Warehouses CRUD.
"""

from datetime import datetime
from app.database import get_connection, hash_password
from app.auth import write_audit_log


# ── Vehicles ─────────────────────────────────────────────────────────────────

def get_all_vehicles(warehouse_id: int = None, search: str = None) -> list:
    conn = get_connection()
    sql = """
        SELECT v.*, w.name AS warehouse_name
        FROM Vehicles v JOIN Warehouses w ON v.warehouse_id = w.id
    """
    params = []
    conditions = []
    if warehouse_id:
        conditions.append("v.warehouse_id = ?")
        params.append(warehouse_id)
    if search:
        conditions.append("(v.registration LIKE ? OR v.vehicle_type LIKE ?)")
        params += [f"%{search}%", f"%{search}%"]
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY v.registration"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows


def add_vehicle(data: dict, user_id: int) -> tuple[bool, str]:
    conn = get_connection()
    try:
        cur = conn.execute("""
            INSERT INTO Vehicles(warehouse_id,registration,vehicle_type,capacity_kg,
            status,last_service_date,next_service_date,notes)
            VALUES(?,?,?,?,?,?,?,?)
        """, (data["warehouse_id"], data["registration"], data["vehicle_type"],
              float(data.get("capacity_kg", 0)),
              data.get("status", "available"),
              data.get("last_service_date") or None,
              data.get("next_service_date") or None,
              data.get("notes")))
        conn.commit()
        write_audit_log(user_id, "INSERT", "Vehicles", cur.lastrowid,
                        f"Added vehicle: {data['registration']}")
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def update_vehicle(vehicle_id: int, data: dict, user_id: int) -> tuple[bool, str]:
    conn = get_connection()
    try:
        conn.execute("""
            UPDATE Vehicles SET warehouse_id=?,registration=?,vehicle_type=?,
            capacity_kg=?,status=?,last_service_date=?,next_service_date=?,notes=?
            WHERE id=?
        """, (data["warehouse_id"], data["registration"], data["vehicle_type"],
              float(data.get("capacity_kg", 0)),
              data.get("status", "available"),
              data.get("last_service_date") or None,
              data.get("next_service_date") or None,
              data.get("notes"), vehicle_id))
        conn.commit()
        write_audit_log(user_id, "UPDATE", "Vehicles", vehicle_id,
                        f"Updated vehicle id={vehicle_id}")
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def delete_vehicle(vehicle_id: int, user_id: int) -> tuple[bool, str]:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM Vehicles WHERE id=?", (vehicle_id,))
        conn.commit()
        write_audit_log(user_id, "DELETE", "Vehicles", vehicle_id,
                        f"Deleted vehicle id={vehicle_id}")
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


# ── Drivers ──────────────────────────────────────────────────────────────────

def get_all_drivers(search: str = None) -> list:
    conn = get_connection()
    sql = """
        SELECT d.*, u.full_name, u.username, u.email, u.is_active
        FROM Drivers d JOIN Users u ON d.user_id = u.id
    """
    params = []
    if search:
        sql += " WHERE (u.full_name LIKE ? OR d.licence_number LIKE ?)"
        params = [f"%{search}%", f"%{search}%"]
    sql += " ORDER BY u.full_name"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows


def add_driver(data: dict, user_id: int) -> tuple[bool, str]:
    """Creates a Users row + Drivers row in a single transaction."""
    conn = get_connection()
    try:
        pw_hash, salt = hash_password(data["password"])
        cur = conn.execute("""
            INSERT INTO Users(username,pw_hash,salt,full_name,email,role)
            VALUES(?,?,?,?,?,'driver')
        """, (data["username"], pw_hash, salt,
              data["full_name"], data.get("email")))
        new_user_id = cur.lastrowid
        conn.execute("""
            INSERT INTO Drivers(user_id,licence_number,licence_expiry,
            status,shift_start,shift_end,notes)
            VALUES(?,?,?,?,?,?,?)
        """, (new_user_id, data["licence_number"], data["licence_expiry"],
              data.get("status", "available"),
              data.get("shift_start"), data.get("shift_end"),
              data.get("notes")))
        conn.commit()
        write_audit_log(user_id, "INSERT", "Drivers", new_user_id,
                        f"Added driver: {data['full_name']}")
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def update_driver(driver_id: int, data: dict, user_id: int) -> tuple[bool, str]:
    conn = get_connection()
    try:
        row = conn.execute("SELECT user_id FROM Drivers WHERE id=?", (driver_id,)).fetchone()
        if not row:
            return False, "Driver not found."
        conn.execute("""
            UPDATE Users SET full_name=?, email=? WHERE id=?
        """, (data["full_name"], data.get("email"), row["user_id"]))
        conn.execute("""
            UPDATE Drivers SET licence_number=?,licence_expiry=?,
            status=?,shift_start=?,shift_end=?,notes=?
            WHERE id=?
        """, (data["licence_number"], data["licence_expiry"],
              data.get("status", "available"),
              data.get("shift_start"), data.get("shift_end"),
              data.get("notes"), driver_id))
        conn.commit()
        write_audit_log(user_id, "UPDATE", "Drivers", driver_id,
                        f"Updated driver id={driver_id}")
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def update_driver_status(driver_id: int, status: str, user_id: int):
    conn = get_connection()
    conn.execute("UPDATE Drivers SET status=? WHERE id=?", (status, driver_id))
    conn.commit()
    conn.close()
    write_audit_log(user_id, "UPDATE", "Drivers", driver_id,
                    f"Status changed to {status}")


# ── Warehouses ───────────────────────────────────────────────────────────────

def get_all_warehouses() -> list:
    conn = get_connection()
    rows = conn.execute("""
        SELECT w.*, u.full_name AS manager_name
        FROM Warehouses w LEFT JOIN Users u ON w.manager_id = u.id
        ORDER BY w.name
    """).fetchall()
    conn.close()
    return rows


def add_warehouse(data: dict, user_id: int) -> tuple[bool, str]:
    conn = get_connection()
    try:
        cur = conn.execute("""
            INSERT INTO Warehouses(name,address,city,postcode,capacity,manager_id)
            VALUES(?,?,?,?,?,?)
        """, (data["name"], data["address"], data["city"], data["postcode"],
              int(data.get("capacity", 1000)),
              data.get("manager_id") or None))
        conn.commit()
        write_audit_log(user_id, "INSERT", "Warehouses", cur.lastrowid,
                        f"Added warehouse: {data['name']}")
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def update_warehouse(wh_id: int, data: dict, user_id: int) -> tuple[bool, str]:
    conn = get_connection()
    try:
        conn.execute("""
            UPDATE Warehouses SET name=?,address=?,city=?,postcode=?,
            capacity=?,manager_id=? WHERE id=?
        """, (data["name"], data["address"], data["city"], data["postcode"],
              int(data.get("capacity", 1000)),
              data.get("manager_id") or None, wh_id))
        conn.commit()
        write_audit_log(user_id, "UPDATE", "Warehouses", wh_id,
                        f"Updated warehouse id={wh_id}")
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def delete_warehouse(wh_id: int, user_id: int) -> tuple[bool, str]:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM Warehouses WHERE id=?", (wh_id,))
        conn.commit()
        write_audit_log(user_id, "DELETE", "Warehouses", wh_id,
                        f"Deleted warehouse id={wh_id}")
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def get_managers_list() -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, full_name FROM Users WHERE role IN ('admin','manager') AND is_active=1 ORDER BY full_name"
    ).fetchall()
    conn.close()
    return rows


def get_warehouses_list() -> list:
    conn = get_connection()
    rows = conn.execute("SELECT id, name FROM Warehouses ORDER BY name").fetchall()
    conn.close()
    return rows
