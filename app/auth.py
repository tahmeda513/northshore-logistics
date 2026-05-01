"""
auth.py — Authentication, session management, and Role-Based Access Control.
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from app.database import get_connection, verify_password

# File-based audit log
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "audit.log"),
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# ── Permission sets per role ─────────────────────────────────────────────────
ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {
        "view_shipments", "add_shipment", "edit_shipment", "delete_shipment",
        "view_inventory", "add_inventory", "edit_inventory", "delete_inventory",
        "view_vehicles", "add_vehicle", "edit_vehicle", "delete_vehicle",
        "view_drivers", "add_driver", "edit_driver",
        "view_warehouses", "add_warehouse", "edit_warehouse", "delete_warehouse",
        "view_incidents", "add_incident", "resolve_incident",
        "view_reports", "export_reports",
        "view_audit_logs",
        "view_users", "add_user", "edit_user", "delete_user",
    },
    "manager": {
        "view_shipments", "add_shipment", "edit_shipment",
        "view_inventory", "add_inventory", "edit_inventory", "delete_inventory",
        "view_vehicles", "add_vehicle", "edit_vehicle",
        "view_drivers", "add_driver", "edit_driver",
        "view_warehouses", "add_warehouse", "edit_warehouse",
        "view_incidents", "add_incident", "resolve_incident",
        "view_reports", "export_reports",
        "view_audit_logs",
        "view_users",
    },
    "staff": {
        "view_shipments", "add_shipment", "edit_shipment",
        "view_inventory", "add_inventory", "edit_inventory",
        "view_vehicles",
        "view_drivers",
        "view_warehouses",
        "view_incidents", "add_incident",
        "view_reports",
    },
    "driver": {
        "view_shipments",
        "view_incidents", "add_incident",
    },
}


@dataclass
class Session:
    user_id: int
    username: str
    full_name: str
    role: str
    permissions: set[str] = field(default_factory=set)

    def can(self, permission: str) -> bool:
        return permission in self.permissions


# Module-level active session
_session: Optional[Session] = None


def get_session() -> Optional[Session]:
    return _session


def login(username: str, password: str) -> tuple[bool, str]:
    """Validate credentials, create session, write audit entry."""
    global _session
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, pw_hash, salt, full_name, role, is_active FROM Users WHERE username=?",
            (username,)
        ).fetchone()

        if row is None:
            _log_audit(conn, None, "LOGIN_FAIL", None, None, f"Unknown user: {username}")
            conn.commit()
            return False, "Invalid username or password."

        if not row["is_active"]:
            _log_audit(conn, row["id"], "LOGIN_FAIL", None, None, "Account disabled.")
            conn.commit()
            return False, "Account is disabled. Contact an administrator."

        if not verify_password(password, row["pw_hash"], row["salt"]):
            _log_audit(conn, row["id"], "LOGIN_FAIL", None, None, "Bad password.")
            conn.commit()
            return False, "Invalid username or password."

        _session = Session(
            user_id=row["id"],
            username=username,
            full_name=row["full_name"],
            role=row["role"],
            permissions=ROLE_PERMISSIONS.get(row["role"], set()),
        )
        _log_audit(conn, row["id"], "LOGIN_SUCCESS", "Users", row["id"],
                   f"User '{username}' logged in.")
        conn.commit()
        return True, ""
    finally:
        conn.close()


def logout():
    global _session
    if _session:
        conn = get_connection()
        _log_audit(conn, _session.user_id, "LOGOUT", "Users", _session.user_id,
                   f"User '{_session.username}' logged out.")
        conn.commit()
        conn.close()
    _session = None


def write_audit_log(user_id: Optional[int], action: str, table_name: Optional[str],
                    record_id: Optional[int], description: str):
    """Public helper — called by model functions after every data mutation."""
    conn = get_connection()
    try:
        _log_audit(conn, user_id, action, table_name, record_id, description)
        conn.commit()
    finally:
        conn.close()


def _log_audit(conn, user_id, action, table_name, record_id, description):
    conn.execute(
        "INSERT INTO AuditLogs(user_id,action,table_name,record_id,description) VALUES(?,?,?,?,?)",
        (user_id, action, table_name, record_id, description)
    )
    logging.info(f"uid={user_id} | {action} | {table_name}:{record_id} | {description}")
