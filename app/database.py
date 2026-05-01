"""
database.py — Schema definition, connection factory, password utilities, and seed data.
All database access in the application goes through get_connection().
"""

import sqlite3
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "northshore.db")

SCHEMA = """
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS Users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT NOT NULL UNIQUE,
    pw_hash     TEXT NOT NULL,
    salt        TEXT NOT NULL,
    full_name   TEXT NOT NULL,
    email       TEXT,
    role        TEXT NOT NULL CHECK(role IN ('admin','manager','staff','driver')),
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS Warehouses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    address     TEXT NOT NULL,
    city        TEXT NOT NULL,
    postcode    TEXT NOT NULL,
    capacity    INTEGER NOT NULL DEFAULT 1000,
    manager_id  INTEGER REFERENCES Users(id) ON DELETE SET NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS Inventory (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    warehouse_id    INTEGER NOT NULL REFERENCES Warehouses(id) ON DELETE CASCADE,
    sku             TEXT NOT NULL,
    item_name       TEXT NOT NULL,
    description     TEXT,
    quantity        INTEGER NOT NULL DEFAULT 0,
    reorder_level   INTEGER NOT NULL DEFAULT 10,
    unit_weight_kg  REAL NOT NULL DEFAULT 1.0,
    location_code   TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS Vehicles (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    warehouse_id        INTEGER NOT NULL REFERENCES Warehouses(id) ON DELETE CASCADE,
    registration        TEXT NOT NULL UNIQUE,
    vehicle_type        TEXT NOT NULL,
    capacity_kg         REAL NOT NULL,
    status              TEXT NOT NULL DEFAULT 'available'
                            CHECK(status IN ('available','in_use','maintenance','retired')),
    last_service_date   TEXT,
    next_service_date   TEXT,
    notes               TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS Drivers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL UNIQUE REFERENCES Users(id) ON DELETE CASCADE,
    licence_number  TEXT NOT NULL UNIQUE,
    licence_expiry  TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'available'
                        CHECK(status IN ('available','on_route','off_duty','suspended')),
    shift_start     TEXT,
    shift_end       TEXT,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS Shipments (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    shipment_ref        TEXT NOT NULL UNIQUE,
    order_number        TEXT,
    warehouse_id        INTEGER NOT NULL REFERENCES Warehouses(id),
    driver_id           INTEGER REFERENCES Drivers(id) ON DELETE SET NULL,
    vehicle_id          INTEGER REFERENCES Vehicles(id) ON DELETE SET NULL,
    created_by          INTEGER REFERENCES Users(id) ON DELETE SET NULL,
    sender_name         TEXT NOT NULL,
    sender_address      TEXT NOT NULL,
    receiver_name       TEXT NOT NULL,
    receiver_address    TEXT NOT NULL,
    receiver_phone      TEXT,
    item_description    TEXT NOT NULL,
    weight_kg           REAL NOT NULL DEFAULT 0.0,
    status              TEXT NOT NULL DEFAULT 'pending'
                            CHECK(status IN ('pending','in_transit','delivered','delayed','returned')),
    transport_cost      REAL NOT NULL DEFAULT 0.0,
    surcharge           REAL NOT NULL DEFAULT 0.0,
    payment_status      TEXT NOT NULL DEFAULT 'pending'
                            CHECK(payment_status IN ('paid','pending','overdue')),
    notes               TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS Deliveries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    shipment_id     INTEGER NOT NULL UNIQUE REFERENCES Shipments(id) ON DELETE CASCADE,
    driver_id       INTEGER REFERENCES Drivers(id) ON DELETE SET NULL,
    vehicle_id      INTEGER REFERENCES Vehicles(id) ON DELETE SET NULL,
    route_details   TEXT,
    scheduled_date  TEXT,
    delivered_date  TEXT,
    status          TEXT NOT NULL DEFAULT 'pending'
                        CHECK(status IN ('pending','in_transit','delivered','delayed','returned')),
    notes           TEXT,
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS Incidents (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    shipment_id     INTEGER NOT NULL REFERENCES Shipments(id) ON DELETE CASCADE,
    reported_by     INTEGER REFERENCES Users(id) ON DELETE SET NULL,
    incident_type   TEXT NOT NULL
                        CHECK(incident_type IN ('delay','route_change','damaged_goods','failed_delivery','other')),
    description     TEXT NOT NULL,
    resolution      TEXT,
    is_resolved     INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    resolved_at     TEXT
);

CREATE TABLE IF NOT EXISTS AuditLogs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER REFERENCES Users(id) ON DELETE SET NULL,
    action      TEXT NOT NULL,
    table_name  TEXT,
    record_id   INTEGER,
    description TEXT,
    timestamp   TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

INDEXES = """
CREATE INDEX IF NOT EXISTS idx_inventory_warehouse   ON Inventory(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_inventory_sku         ON Inventory(sku);
CREATE INDEX IF NOT EXISTS idx_vehicles_warehouse    ON Vehicles(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_vehicles_status       ON Vehicles(status);
CREATE INDEX IF NOT EXISTS idx_drivers_status        ON Drivers(status);
CREATE INDEX IF NOT EXISTS idx_shipments_warehouse   ON Shipments(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_shipments_driver      ON Shipments(driver_id);
CREATE INDEX IF NOT EXISTS idx_shipments_status      ON Shipments(status);
CREATE INDEX IF NOT EXISTS idx_shipments_created_at  ON Shipments(created_at);
CREATE INDEX IF NOT EXISTS idx_shipments_ref         ON Shipments(shipment_ref);
CREATE INDEX IF NOT EXISTS idx_deliveries_shipment   ON Deliveries(shipment_id);
CREATE INDEX IF NOT EXISTS idx_deliveries_driver     ON Deliveries(driver_id);
CREATE INDEX IF NOT EXISTS idx_incidents_shipment    ON Incidents(shipment_id);
CREATE INDEX IF NOT EXISTS idx_auditlogs_user        ON AuditLogs(user_id);
CREATE INDEX IF NOT EXISTS idx_auditlogs_timestamp   ON AuditLogs(timestamp);
"""


def get_connection() -> sqlite3.Connection:
    """Return a configured connection with row_factory and FK enforcement."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def hash_password(password: str) -> tuple[str, str]:
    """Return (pw_hash, salt) using SHA-256 with a random salt."""
    salt = secrets.token_hex(16)
    pw_hash = hashlib.sha256((salt + password).encode()).hexdigest()
    return pw_hash, salt


def verify_password(password: str, pw_hash: str, salt: str) -> bool:
    """Return True if the password matches the stored hash."""
    check = hashlib.sha256((salt + password).encode()).hexdigest()
    return check == pw_hash


def initialise_database():
    """Create tables, indexes, and seed data if the DB is fresh."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_connection()
    conn.executescript(SCHEMA)
    conn.executescript(INDEXES)
    conn.commit()

    cur = conn.execute("SELECT COUNT(*) FROM Users")
    if cur.fetchone()[0] == 0:
        _seed(conn)
    conn.close()


def _seed(conn: sqlite3.Connection):
    """Insert realistic demonstration data on first run."""
    # --- Users ---
    users = [
        ("admin",    "Admin2024!",    "Alice Admin",    "alice@northshore.co.uk",  "admin"),
        ("manager1", "Manager2024!",  "Bob Manager",    "bob@northshore.co.uk",    "manager"),
        ("staff1",   "Staff2024!",    "Carol Staff",    "carol@northshore.co.uk",  "staff"),
        ("staff2",   "Staff2024!",    "Dan Staff",      "dan@northshore.co.uk",    "staff"),
        ("driver1",  "Driver2024!",   "Eve Driver",     "eve@northshore.co.uk",    "driver"),
        ("driver2",  "Driver2024!",   "Frank Driver",   "frank@northshore.co.uk",  "driver"),
        ("driver3",  "Driver2024!",   "Grace Driver",   "grace@northshore.co.uk",  "driver"),
    ]
    user_ids = {}
    for uname, pw, name, email, role in users:
        h, s = hash_password(pw)
        cur = conn.execute(
            "INSERT INTO Users(username,pw_hash,salt,full_name,email,role) VALUES(?,?,?,?,?,?)",
            (uname, h, s, name, email, role)
        )
        user_ids[uname] = cur.lastrowid

    # --- Warehouses ---
    wh_data = [
        ("London Central Hub",    "12 Dock Road",         "London",     "E1 8AA",  5000, user_ids["manager1"]),
        ("Manchester North",      "45 Industrial Park",   "Manchester", "M9 2BH",  3000, user_ids["manager1"]),
        ("Birmingham Midlands",   "7 Freight Lane",       "Birmingham", "B6 7TT",  2500, user_ids["manager1"]),
    ]
    wh_ids = []
    for row in wh_data:
        cur = conn.execute(
            "INSERT INTO Warehouses(name,address,city,postcode,capacity,manager_id) VALUES(?,?,?,?,?,?)", row)
        wh_ids.append(cur.lastrowid)

    # --- Inventory ---
    inv_data = [
        (wh_ids[0], "SKU-001", "Cardboard Boxes (Large)",   "Heavy-duty shipping boxes",  250, 50, 0.8, "A1-01"),
        (wh_ids[0], "SKU-002", "Bubble Wrap Roll",          "Protective packaging",        80, 20, 0.5, "A1-02"),
        (wh_ids[0], "SKU-003", "Packing Tape (48mm)",       "Brown sealing tape",           8,  15, 0.1, "A1-03"),  # low stock
        (wh_ids[1], "SKU-004", "Pallets (Wooden)",          "Standard euro pallets",       40, 10, 20.0, "B2-01"),
        (wh_ids[1], "SKU-005", "Stretch Film",              "Pallet wrap film",             5, 12, 0.3, "B2-02"),   # low stock
        (wh_ids[2], "SKU-006", "Fragile Stickers",         "Handle with care labels",     500, 100, 0.01,"C3-01"),
        (wh_ids[2], "SKU-007", "Thermal Labels (100x150)", "Shipping labels for printer", 300,  50, 0.02,"C3-02"),
    ]
    for row in inv_data:
        conn.execute(
            "INSERT INTO Inventory(warehouse_id,sku,item_name,description,quantity,reorder_level,unit_weight_kg,location_code) VALUES(?,?,?,?,?,?,?,?)", row)

    # --- Vehicles ---
    veh_data = [
        (wh_ids[0], "LN21 ABC", "Van",   1500, "available", "2024-11-01", "2025-11-01"),
        (wh_ids[0], "LN70 XYZ", "Lorry", 8000, "in_use",    "2024-09-15", "2025-09-15"),
        (wh_ids[1], "MN19 DEF", "Van",   1200, "available", "2025-01-10", "2026-01-10"),
        (wh_ids[1], "MN22 GHI", "Lorry", 7500, "maintenance","2023-06-01","2024-06-01"),
        (wh_ids[2], "BM20 JKL", "Van",   1000, "available", "2024-12-20", "2025-12-20"),
    ]
    veh_ids = []
    for row in veh_data:
        cur = conn.execute(
            "INSERT INTO Vehicles(warehouse_id,registration,vehicle_type,capacity_kg,status,last_service_date,next_service_date) VALUES(?,?,?,?,?,?,?)", row)
        veh_ids.append(cur.lastrowid)

    # --- Drivers ---
    drv_data = [
        (user_ids["driver1"], "DL-001-2019", "2027-06-30", "available",  "08:00", "18:00"),
        (user_ids["driver2"], "DL-002-2020", "2026-12-31", "on_route",   "07:00", "17:00"),
        (user_ids["driver3"], "DL-003-2021", "2028-03-15", "available",  "09:00", "19:00"),
    ]
    drv_ids = []
    for row in drv_data:
        cur = conn.execute(
            "INSERT INTO Drivers(user_id,licence_number,licence_expiry,status,shift_start,shift_end) VALUES(?,?,?,?,?,?)", row)
        drv_ids.append(cur.lastrowid)

    # --- Shipments ---
    today = datetime.now()
    ship_data = [
        ("SHP-2026-0001", "ORD-100", wh_ids[0], drv_ids[0], veh_ids[0], user_ids["staff1"],
         "Global Imports Ltd",    "10 Trade St, London",
         "John Smith",            "22 Oak Ave, Bristol",       "07700900001",
         "Electronics (10 units)", 45.0, "delivered", 120.00, 5.00, "paid",    (today - timedelta(days=5)).strftime("%Y-%m-%d")),
        ("SHP-2026-0002", "ORD-101", wh_ids[0], drv_ids[1], veh_ids[1], user_ids["staff1"],
         "Tech Suppliers UK",     "5 Park Lane, London",
         "Sarah Jones",           "8 High St, Birmingham",     "07700900002",
         "Server Hardware",        320.0, "in_transit", 450.00, 20.00, "pending", (today + timedelta(days=1)).strftime("%Y-%m-%d")),
        ("SHP-2026-0003", "ORD-102", wh_ids[1], drv_ids[2], veh_ids[2], user_ids["staff2"],
         "Home Goods Co",         "3 Retail Park, Manchester",
         "Mike Brown",            "15 Elm Rd, Leeds",          "07700900003",
         "Kitchen Appliances",    85.0, "delayed",    200.00, 10.00, "overdue",  (today - timedelta(days=2)).strftime("%Y-%m-%d")),
        ("SHP-2026-0004", "ORD-103", wh_ids[2], None,        None,        user_ids["staff2"],
         "Fashion House",         "20 Fashion Row, Birmingham",
         "Lucy Green",            "47 New St, Coventry",       "07700900004",
         "Clothing (Seasonal)",   12.0, "pending",     75.00,  0.00, "pending",  (today + timedelta(days=3)).strftime("%Y-%m-%d")),
        ("SHP-2026-0005", "ORD-104", wh_ids[0], drv_ids[0], veh_ids[0], user_ids["staff1"],
         "Office Depot",          "1 Business Quarter, London",
         "Tom White",             "9 Park St, Brighton",       "07700900005",
         "Office Furniture",      200.0, "delivered",  350.00, 15.00, "paid",    (today - timedelta(days=10)).strftime("%Y-%m-%d")),
        ("SHP-2026-0006", "ORD-105", wh_ids[1], drv_ids[1], veh_ids[1], user_ids["staff2"],
         "Auto Parts Ltd",        "6 Motor Way, Manchester",
         "Diana Black",           "33 West Ave, Sheffield",    "07700900006",
         "Car Components",        420.0, "returned",   280.00, 25.00, "overdue", (today - timedelta(days=7)).strftime("%Y-%m-%d")),
    ]
    shp_ids = []
    for row in ship_data:
        ref,ord_,wid,did,vid,uid,sn,sa,rn,ra,rp,itm,wt,st,tc,sc,ps,dd = row
        cur = conn.execute("""
            INSERT INTO Shipments(shipment_ref,order_number,warehouse_id,driver_id,vehicle_id,
            created_by,sender_name,sender_address,receiver_name,receiver_address,receiver_phone,
            item_description,weight_kg,status,transport_cost,surcharge,payment_status)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (ref,ord_,wid,did,vid,uid,sn,sa,rn,ra,rp,itm,wt,st,tc,sc,ps))
        shp_ids.append(cur.lastrowid)
        # Linked delivery row
        conn.execute("""
            INSERT INTO Deliveries(shipment_id,driver_id,vehicle_id,scheduled_date,status)
            VALUES(?,?,?,?,?)""",
            (cur.lastrowid, did, vid, dd, st))

    # --- Incidents ---
    inc_data = [
        (shp_ids[2], user_ids["driver3"], "delay",         "Road works on M62 caused 3-hour delay.", None, 0),
        (shp_ids[5], user_ids["driver2"], "failed_delivery","Recipient not at address. Left card.", "Rescheduled for next day.", 1),
    ]
    for row in inc_data:
        sid, uid, itype, desc, res, resolved = row
        conn.execute("""
            INSERT INTO Incidents(shipment_id,reported_by,incident_type,description,resolution,is_resolved)
            VALUES(?,?,?,?,?,?)""",
            (sid, uid, itype, desc, res, resolved))

    conn.commit()
    logging.info("Database seeded with demonstration data.")
