"""
ui/fleet_tab.py — Vehicles, Drivers, and Warehouses management via sub-tabs.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from app.ui.styles import C, F, scrolled_tree, populate_tree, status_badge
from app.models.fleet import (get_all_vehicles, add_vehicle, update_vehicle, delete_vehicle,
                               get_all_drivers, add_driver, update_driver,
                               get_all_warehouses, add_warehouse, update_warehouse,
                               delete_warehouse, get_managers_list, get_warehouses_list)

VEH_STATUSES = ["available", "in_use", "maintenance", "retired"]
DRV_STATUSES = ["available", "on_route", "off_duty", "suspended"]
VEH_TYPES    = ["Van", "Lorry", "Motorbike", "Car", "HGV"]


class FleetTab(ttk.Frame):
    def __init__(self, parent, session):
        super().__init__(parent)
        self.session = session
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        nb.add(VehiclesPanel(nb, session), text="🚗  Vehicles")
        nb.add(DriversPanel(nb, session),  text="👤  Drivers")
        nb.add(WarehousesPanel(nb, session),text="🏭  Warehouses")


# ── Vehicles ──────────────────────────────────────────────────────────────────

VEH_COLS = [
    ("registration",    "Reg",         100),
    ("vehicle_type",    "Type",         80),
    ("warehouse_name",  "Warehouse",   120),
    ("capacity_kg",     "Cap (kg)",     80),
    ("status",          "Status",       90),
    ("last_service_date","Last Service",110),
    ("next_service_date","Next Service",110),
]


class VehiclesPanel(ttk.Frame):
    def __init__(self, parent, session):
        super().__init__(parent)
        self.session = session
        self._build()
        self.refresh()

    def _build(self):
        tb = ttk.Frame(self); tb.pack(fill="x", padx=8, pady=6)
        self._wh_list = get_warehouses_list()
        wh_names = ["All"] + [w["name"] for w in self._wh_list]
        self._wh_map = {w["name"]: w["id"] for w in self._wh_list}
        self._wh_var = tk.StringVar(value="All")
        cb = ttk.Combobox(tb, textvariable=self._wh_var, values=wh_names,
                          state="readonly", width=18)
        cb.pack(side="left", padx=4)
        cb.bind("<<ComboboxSelected>>", lambda _: self.refresh())
        ttk.Button(tb, text="⟳ Refresh", command=self.refresh).pack(side="left", padx=4)

        if self.session.can("add_vehicle"):
            ttk.Button(tb, text="+ Add", style="Primary.TButton",
                       command=self._add).pack(side="right", padx=4)
        if self.session.can("edit_vehicle"):
            ttk.Button(tb, text="✎ Edit", command=self._edit).pack(side="right", padx=4)
        if self.session.can("delete_vehicle"):
            ttk.Button(tb, text="🗑 Delete", style="Danger.TButton",
                       command=self._delete).pack(side="right", padx=4)

        self.tree = scrolled_tree(self, VEH_COLS, height=16)
        self.tree.bind("<Double-1>", lambda _: self._edit())
        self._sv = tk.StringVar()
        tk.Label(self, textvariable=self._sv, font=F["small"],
                 bg=C["bg"], fg=C["text_muted"]).pack(anchor="w", padx=8, pady=2)

    def refresh(self):
        whn = self._wh_var.get()
        wid = self._wh_map.get(whn)
        rows = get_all_vehicles(wid)
        def vals(r): return (r["registration"], r["vehicle_type"], r["warehouse_name"],
                             r["capacity_kg"], status_badge(r["status"]),
                             r["last_service_date"] or "", r["next_service_date"] or "")
        populate_tree(self.tree, rows, vals)
        self._sv.set(f"{len(rows)} vehicle(s)")

    def _sel(self): sel = self.tree.selection(); return int(sel[0]) if sel else None
    def _add(self): VehicleForm(self, self.session, None, self.refresh)
    def _edit(self):
        v = self._sel()
        if not v: messagebox.showwarning("Select", "Select a vehicle first."); return
        VehicleForm(self, self.session, v, self.refresh)
    def _delete(self):
        v = self._sel()
        if not v: messagebox.showwarning("Select", "Select a vehicle first."); return
        if messagebox.askyesno("Delete", "Delete this vehicle?"):
            ok, err = delete_vehicle(v, self.session.user_id)
            if ok: self.refresh()
            else: messagebox.showerror("Error", err)


class VehicleForm(tk.Toplevel):
    def __init__(self, parent, session, vid, on_save):
        super().__init__(parent)
        self.session = session; self.vid = vid; self.on_save = on_save
        self.title("Edit Vehicle" if vid else "Add Vehicle")
        self.geometry("440x380"); self.resizable(False, False)
        self.configure(bg=C["bg"]); self.grab_set(); self.transient(parent)
        self._wh_list = get_warehouses_list()
        self._wh_map  = {w["name"]: w["id"] for w in self._wh_list}
        self._build()
        if vid: self._load()

    def _build(self):
        f = ttk.Frame(self, padding=16); f.pack(fill="both", expand=True)
        f.columnconfigure(1, weight=1)
        def lbl_entry(lbl, r):
            tk.Label(f, text=lbl, bg=C["bg"]).grid(row=r, column=0, sticky="w", padx=4, pady=3)
            v = tk.StringVar()
            ttk.Entry(f, textvariable=v).grid(row=r, column=1, sticky="ew", padx=4, pady=3)
            return v
        def lbl_combo(lbl, r, vals):
            tk.Label(f, text=lbl, bg=C["bg"]).grid(row=r, column=0, sticky="w", padx=4, pady=3)
            v = tk.StringVar()
            ttk.Combobox(f, textvariable=v, values=vals, state="readonly").grid(
                row=r, column=1, sticky="ew", padx=4, pady=3)
            return v
        self.v_wh   = lbl_combo("Warehouse *",   0, list(self._wh_map.keys()))
        self.v_reg  = lbl_entry("Registration *", 1)
        self.v_type = lbl_combo("Type *",         2, VEH_TYPES)
        self.v_cap  = lbl_entry("Capacity (kg) *",3)
        self.v_st   = lbl_combo("Status *",       4, VEH_STATUSES)
        self.v_ls   = lbl_entry("Last Service (YYYY-MM-DD)", 5)
        self.v_ns   = lbl_entry("Next Service (YYYY-MM-DD)", 6)
        self.v_notes= lbl_entry("Notes",           7)
        btn = ttk.Frame(f); btn.grid(row=8, column=0, columnspan=2, pady=10, sticky="e")
        ttk.Button(btn, text="Cancel", command=self.destroy).pack(side="right", padx=4)
        ttk.Button(btn, text="Save", style="Primary.TButton", command=self._save).pack(side="right", padx=4)
        self.v_st.set("available"); self.v_cap.set("1000")

    def _load(self):
        from app.database import get_connection
        conn = get_connection()
        r = conn.execute("SELECT * FROM Vehicles WHERE id=?", (self.vid,)).fetchone()
        conn.close()
        if not r: return
        whn = next((k for k, v in self._wh_map.items() if v == r["warehouse_id"]), "")
        self.v_wh.set(whn); self.v_reg.set(r["registration"]); self.v_type.set(r["vehicle_type"])
        self.v_cap.set(str(r["capacity_kg"])); self.v_st.set(r["status"])
        self.v_ls.set(r["last_service_date"] or ""); self.v_ns.set(r["next_service_date"] or "")
        self.v_notes.set(r["notes"] or "")

    def _save(self):
        try:
            data = {"warehouse_id": self._wh_map[self.v_wh.get()],
                    "registration": self.v_reg.get().strip(),
                    "vehicle_type": self.v_type.get(),
                    "capacity_kg":  float(self.v_cap.get()),
                    "status":       self.v_st.get(),
                    "last_service_date": self.v_ls.get().strip() or None,
                    "next_service_date": self.v_ns.get().strip() or None,
                    "notes":        self.v_notes.get().strip() or None}
            if not data["registration"]: raise ValueError("Registration required")
        except (KeyError, ValueError) as e:
            messagebox.showerror("Validation", str(e)); return
        fn = update_vehicle if self.vid else add_vehicle
        args = (self.vid, data, self.session.user_id) if self.vid else (data, self.session.user_id)
        ok, err = fn(*args)
        if ok: self.on_save(); self.destroy()
        else: messagebox.showerror("Error", err)


# ── Drivers ───────────────────────────────────────────────────────────────────

DRV_COLS = [
    ("full_name",      "Name",         130),
    ("username",       "Username",      100),
    ("licence_number", "Licence No",   110),
    ("licence_expiry", "Expiry",        90),
    ("status",         "Status",        90),
    ("shift_start",    "Shift Start",   90),
    ("shift_end",      "Shift End",     90),
    ("email",          "Email",        160),
]


class DriversPanel(ttk.Frame):
    def __init__(self, parent, session):
        super().__init__(parent)
        self.session = session
        self._build(); self.refresh()

    def _build(self):
        tb = ttk.Frame(self); tb.pack(fill="x", padx=8, pady=6)
        self._sv2 = tk.StringVar()
        ttk.Entry(tb, textvariable=self._sv2, width=22).pack(side="left", padx=2)
        ttk.Button(tb, text="🔍 Search", command=self.refresh).pack(side="left", padx=4)
        ttk.Button(tb, text="⟳ Refresh",  command=self.refresh).pack(side="left", padx=4)
        if self.session.can("add_driver"):
            ttk.Button(tb, text="+ Add Driver", style="Primary.TButton",
                       command=self._add).pack(side="right", padx=4)
        if self.session.can("edit_driver"):
            ttk.Button(tb, text="✎ Edit", command=self._edit).pack(side="right", padx=4)
        self.tree = scrolled_tree(self, DRV_COLS, height=16)
        self.tree.bind("<Double-1>", lambda _: self._edit())
        self._sv = tk.StringVar()
        tk.Label(self, textvariable=self._sv, font=F["small"],
                 bg=C["bg"], fg=C["text_muted"]).pack(anchor="w", padx=8, pady=2)

    def refresh(self):
        rows = get_all_drivers(self._sv2.get().strip() or None)
        def vals(r): return (r["full_name"], r["username"], r["licence_number"],
                             r["licence_expiry"], status_badge(r["status"]),
                             r["shift_start"] or "", r["shift_end"] or "", r["email"] or "")
        populate_tree(self.tree, rows, vals)
        self._sv.set(f"{len(rows)} driver(s)")

    def _sel(self): sel = self.tree.selection(); return int(sel[0]) if sel else None
    def _add(self): DriverForm(self, self.session, None, self.refresh)
    def _edit(self):
        d = self._sel()
        if not d: messagebox.showwarning("Select", "Select a driver first."); return
        DriverForm(self, self.session, d, self.refresh)


class DriverForm(tk.Toplevel):
    def __init__(self, parent, session, did, on_save):
        super().__init__(parent)
        self.session = session; self.did = did; self.on_save = on_save
        self.title("Edit Driver" if did else "Add Driver")
        self.geometry("440x420"); self.resizable(False, False)
        self.configure(bg=C["bg"]); self.grab_set(); self.transient(parent)
        self._build()
        if did: self._load()

    def _build(self):
        f = ttk.Frame(self, padding=16); f.pack(fill="both", expand=True)
        f.columnconfigure(1, weight=1)
        def row(lbl, r):
            tk.Label(f, text=lbl, bg=C["bg"]).grid(row=r, column=0, sticky="w", padx=4, pady=3)
            v = tk.StringVar()
            ttk.Entry(f, textvariable=v).grid(row=r, column=1, sticky="ew", padx=4, pady=3)
            return v
        def combo_row(lbl, r, vals):
            tk.Label(f, text=lbl, bg=C["bg"]).grid(row=r, column=0, sticky="w", padx=4, pady=3)
            v = tk.StringVar()
            ttk.Combobox(f, textvariable=v, values=vals, state="readonly").grid(
                row=r, column=1, sticky="ew", padx=4, pady=3); return v
        self.v_name    = row("Full Name *",       0)
        self.v_uname   = row("Username *",         1)
        self.v_email   = row("Email",              2)
        self.v_pw      = row("Password *",         3)
        self.v_lic     = row("Licence Number *",   4)
        self.v_exp     = row("Licence Expiry (YYYY-MM-DD) *", 5)
        self.v_st      = combo_row("Status *",     6, DRV_STATUSES)
        self.v_ss      = row("Shift Start (HH:MM)",7)
        self.v_se      = row("Shift End (HH:MM)",  8)
        self.v_notes   = row("Notes",              9)
        btn = ttk.Frame(f); btn.grid(row=10, column=0, columnspan=2, pady=10, sticky="e")
        ttk.Button(btn, text="Cancel", command=self.destroy).pack(side="right", padx=4)
        ttk.Button(btn, text="Save", style="Primary.TButton", command=self._save).pack(side="right", padx=4)
        self.v_st.set("available")
        if self.did:
            tk.Label(f, text="(Leave password blank to keep unchanged)",
                     font=F["small"], bg=C["bg"], fg=C["text_muted"]).grid(
                row=11, column=0, columnspan=2, sticky="w", padx=4)

    def _load(self):
        from app.database import get_connection
        conn = get_connection()
        r = conn.execute("""SELECT d.*, u.full_name, u.username, u.email
                            FROM Drivers d JOIN Users u ON d.user_id=u.id
                            WHERE d.id=?""", (self.did,)).fetchone()
        conn.close()
        if not r: return
        self.v_name.set(r["full_name"]); self.v_uname.set(r["username"])
        self.v_email.set(r["email"] or ""); self.v_lic.set(r["licence_number"])
        self.v_exp.set(r["licence_expiry"]); self.v_st.set(r["status"])
        self.v_ss.set(r["shift_start"] or ""); self.v_se.set(r["shift_end"] or "")
        self.v_notes.set(r["notes"] or "")

    def _save(self):
        data = {"full_name": self.v_name.get().strip(), "username": self.v_uname.get().strip(),
                "email": self.v_email.get().strip() or None, "password": self.v_pw.get(),
                "licence_number": self.v_lic.get().strip(), "licence_expiry": self.v_exp.get().strip(),
                "status": self.v_st.get(), "shift_start": self.v_ss.get().strip() or None,
                "shift_end": self.v_se.get().strip() or None, "notes": self.v_notes.get().strip() or None}
        if not data["full_name"] or not data["licence_number"] or not data["licence_expiry"]:
            messagebox.showerror("Validation", "Name, Licence, and Expiry are required."); return
        if not self.did and not data["password"]:
            messagebox.showerror("Validation", "Password required for new driver."); return
        fn = update_driver if self.did else add_driver
        args = (self.did, data, self.session.user_id) if self.did else (data, self.session.user_id)
        ok, err = fn(*args)
        if ok: self.on_save(); self.destroy()
        else: messagebox.showerror("Error", err)


# ── Warehouses ────────────────────────────────────────────────────────────────

WH_COLS = [
    ("name",         "Name",        160),
    ("city",         "City",         90),
    ("postcode",     "Postcode",     80),
    ("address",      "Address",     180),
    ("capacity",     "Capacity",     80),
    ("manager_name", "Manager",     120),
]


class WarehousesPanel(ttk.Frame):
    def __init__(self, parent, session):
        super().__init__(parent)
        self.session = session
        self._build(); self.refresh()

    def _build(self):
        tb = ttk.Frame(self); tb.pack(fill="x", padx=8, pady=6)
        ttk.Button(tb, text="⟳ Refresh", command=self.refresh).pack(side="left", padx=4)
        if self.session.can("add_warehouse"):
            ttk.Button(tb, text="+ Add Warehouse", style="Primary.TButton",
                       command=self._add).pack(side="right", padx=4)
        if self.session.can("edit_warehouse"):
            ttk.Button(tb, text="✎ Edit", command=self._edit).pack(side="right", padx=4)
        if self.session.can("delete_warehouse"):
            ttk.Button(tb, text="🗑 Delete", style="Danger.TButton",
                       command=self._delete).pack(side="right", padx=4)
        self.tree = scrolled_tree(self, WH_COLS, height=14)
        self.tree.bind("<Double-1>", lambda _: self._edit())
        self._sv = tk.StringVar()
        tk.Label(self, textvariable=self._sv, font=F["small"],
                 bg=C["bg"], fg=C["text_muted"]).pack(anchor="w", padx=8, pady=2)

    def refresh(self):
        rows = get_all_warehouses()
        def vals(r): return (r["name"], r["city"], r["postcode"], r["address"],
                             r["capacity"], r["manager_name"] or "")
        populate_tree(self.tree, rows, vals)
        self._sv.set(f"{len(rows)} warehouse(s)")

    def _sel(self): sel = self.tree.selection(); return int(sel[0]) if sel else None
    def _add(self): WarehouseForm(self, self.session, None, self.refresh)
    def _edit(self):
        w = self._sel()
        if not w: messagebox.showwarning("Select", "Select a warehouse first."); return
        WarehouseForm(self, self.session, w, self.refresh)
    def _delete(self):
        w = self._sel()
        if not w: messagebox.showwarning("Select", "Select a warehouse first."); return
        if messagebox.askyesno("Delete", "Delete this warehouse and all linked data?"):
            ok, err = delete_warehouse(w, self.session.user_id)
            if ok: self.refresh()
            else: messagebox.showerror("Error", err)


class WarehouseForm(tk.Toplevel):
    def __init__(self, parent, session, wid, on_save):
        super().__init__(parent)
        self.session = session; self.wid = wid; self.on_save = on_save
        self.title("Edit Warehouse" if wid else "Add Warehouse")
        self.geometry("440x340"); self.resizable(False, False)
        self.configure(bg=C["bg"]); self.grab_set(); self.transient(parent)
        self._mgr_list = get_managers_list()
        self._mgr_map  = {"(None)": None, **{m["full_name"]: m["id"] for m in self._mgr_list}}
        self._build()
        if wid: self._load()

    def _build(self):
        f = ttk.Frame(self, padding=16); f.pack(fill="both", expand=True)
        f.columnconfigure(1, weight=1)
        def row(lbl, r):
            tk.Label(f, text=lbl, bg=C["bg"]).grid(row=r, column=0, sticky="w", padx=4, pady=3)
            v = tk.StringVar()
            ttk.Entry(f, textvariable=v).grid(row=r, column=1, sticky="ew", padx=4, pady=3)
            return v
        self.v_name    = row("Name *",     0)
        self.v_addr    = row("Address *",  1)
        self.v_city    = row("City *",     2)
        self.v_post    = row("Postcode *", 3)
        self.v_cap     = row("Capacity",   4)
        tk.Label(f, text="Manager", bg=C["bg"]).grid(row=5, column=0, sticky="w", padx=4, pady=3)
        self.v_mgr = tk.StringVar(value="(None)")
        ttk.Combobox(f, textvariable=self.v_mgr, values=list(self._mgr_map.keys()),
                     state="readonly").grid(row=5, column=1, sticky="ew", padx=4, pady=3)
        btn = ttk.Frame(f); btn.grid(row=6, column=0, columnspan=2, pady=10, sticky="e")
        ttk.Button(btn, text="Cancel", command=self.destroy).pack(side="right", padx=4)
        ttk.Button(btn, text="Save", style="Primary.TButton", command=self._save).pack(side="right", padx=4)
        self.v_cap.set("1000")

    def _load(self):
        from app.database import get_connection
        conn = get_connection()
        r = conn.execute("SELECT * FROM Warehouses WHERE id=?", (self.wid,)).fetchone()
        conn.close()
        if not r: return
        mgr_name = next((k for k, v in self._mgr_map.items() if v == r["manager_id"]), "(None)")
        self.v_name.set(r["name"]); self.v_addr.set(r["address"]); self.v_city.set(r["city"])
        self.v_post.set(r["postcode"]); self.v_cap.set(str(r["capacity"])); self.v_mgr.set(mgr_name)

    def _save(self):
        try:
            data = {"name": self.v_name.get().strip(), "address": self.v_addr.get().strip(),
                    "city": self.v_city.get().strip(), "postcode": self.v_post.get().strip(),
                    "capacity": int(self.v_cap.get() or 1000),
                    "manager_id": self._mgr_map.get(self.v_mgr.get())}
            if not data["name"] or not data["city"]: raise ValueError("Name and City required")
        except (KeyError, ValueError) as e:
            messagebox.showerror("Validation", str(e)); return
        fn = update_warehouse if self.wid else add_warehouse
        args = (self.wid, data, self.session.user_id) if self.wid else (data, self.session.user_id)
        ok, err = fn(*args)
        if ok: self.on_save(); self.destroy()
        else: messagebox.showerror("Error", err)
