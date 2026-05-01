# Northshore Logistics Ltd — Database Management System

**CPS4004 Database Systems | St Mary's University Twickenham**

---

## Quick Start

```bash
# 1. Navigate into the project folder
cd northshore_logistics

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 3. Install the only external dependency
pip install -r requirements.txt

# 4. Launch the application
python app/main.py
```

The database (`data/northshore.db`) and audit log (`logs/audit.log`) are
created automatically on first run and seeded with demonstration data.

---

## Demo Login Credentials

| Username  | Password      | Role    |
|-----------|---------------|---------|
| admin     | Admin2024!    | Admin   |
| manager1  | Manager2024!  | Manager |
| staff1    | Staff2024!    | Staff   |
| driver1   | Driver2024!   | Driver  |

---

## Tech Stack

| Component        | Technology                          |
|------------------|-------------------------------------|
| Language         | Python 3.11+                        |
| Database         | SQLite3 (WAL mode, FK enforcement)  |
| GUI              | Tkinter + ttk                       |
| Data processing  | pandas                              |
| Password hashing | hashlib (SHA-256) + secrets         |
| Audit logging    | logging (standard library)          |
| Date handling    | datetime (standard library)         |

---

## Project Structure

```
northshore_logistics/
├── app/
│   ├── main.py              Entry point
│   ├── database.py          Schema, connection factory, seed data
│   ├── auth.py              Authentication, sessions, RBAC
│   ├── models/
│   │   ├── shipments.py     Shipment & delivery CRUD
│   │   ├── inventory.py     Inventory CRUD & stock adjustment
│   │   ├── fleet.py         Vehicles, drivers, warehouses CRUD
│   │   └── reports.py       Pandas reports, incidents, audit log, users
│   └── ui/
│       ├── styles.py        Design system: colours, fonts, widgets
│       ├── login_window.py  Login screen
│       ├── main_window.py   Main window & tab container
│       ├── dashboard_tab.py KPI summary cards
│       ├── shipments_tab.py Shipments management
│       ├── inventory_tab.py Inventory management
│       ├── fleet_tab.py     Fleet, drivers, warehouses
│       ├── incidents_tab.py Incident reporting & resolution
│       ├── reports_tab.py   Pandas reports & audit log
│       └── admin_tab.py     User management (admin only)
├── data/
│   └── northshore.db        SQLite database (auto-created)
├── logs/
│   └── audit.log            Audit trail (auto-created)
├── reports/                 CSV exports saved here
├── requirements.txt
└── README.md
```

---

## macOS Note

If Tkinter is missing on Apple Silicon, install via Homebrew:

```bash
brew install python-tk
```

This is not needed if Python was installed from python.org.
