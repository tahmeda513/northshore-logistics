"""
ui/shipments_tab.py — Full CRUD shipment management.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from app.ui.styles import C, F, scrolled_tree, populate_tree, form_dialog, status_badge
from app.models.shipments import (get_all_shipments, add_shipment, update_shipment,
                                   delete_shipment, get_warehouses_list,
                                   get_drivers_list, get_vehicles_list)

STATUSES      = ["pending", "in_transit", "delivered", "delayed", "returned"]
PAY_STATUSES  = ["paid", "pending", "overdue"]
COLS = [
    ("shipment_ref",  "Reference",   110),
    ("order_number",  "Order #",      90),
    ("sender_name",   "Sender",      140),
    ("receiver_name", "Receiver",    140),
    ("warehouse_name","Warehouse",   120),
    ("driver_name",   "Driver",      110),
    ("weight_kg",     "Weight (kg)",  90),
    ("total_cost",    "Cost (£)",     90),
    ("payment_status","Payment",      90),
    ("status",        "Status",       95),
    ("created_at",    "Created",     130),
]


class ShipmentsTab(ttk.Frame):
    def __init__(self, parent, session):
        super().__init__(parent)
        self.session = session
        self._build()
        self.refresh()

    def _build(self):
        # Toolbar
        tb = ttk.Frame(self)
        tb.pack(fill="x", padx=8, pady=6)

        tk.Label(tb, text="Filter:", font=F["normal"],
                 bg=C["bg"], fg=C["text"]).pack(side="left")
        self._filter_var = tk.StringVar(value="All")
        opts = ["All"] + [s.replace("_", " ").title() for s in STATUSES]
        cb = ttk.Combobox(tb, textvariable=self._filter_var, values=opts,
                          state="readonly", width=14)
        cb.pack(side="left", padx=(2, 12))
        cb.bind("<<ComboboxSelected>>", lambda _: self.refresh())

        self._search_var = tk.StringVar()
        ttk.Entry(tb, textvariable=self._search_var, width=22).pack(side="left", padx=2)
        ttk.Button(tb, text="🔍 Search", command=self.refresh).pack(side="left", padx=4)
        ttk.Button(tb, text="⟳ Refresh", command=self.refresh).pack(side="left", padx=4)

        if self.session.can("add_shipment"):
            ttk.Button(tb, text="+ Add Shipment", style="Primary.TButton",
                       command=self._add).pack(side="right", padx=4)
        if self.session.can("edit_shipment"):
            ttk.Button(tb, text="✎ Edit", command=self._edit).pack(side="right", padx=4)
        if self.session.can("delete_shipment"):
            ttk.Button(tb, text="🗑 Delete", style="Danger.TButton",
                       command=self._delete).pack(side="right", padx=4)

        # Tree
        self.tree = scrolled_tree(self, COLS, height=18)
        self.tree.bind("<Double-1>", lambda _: self._edit())

        # Status bar
        self._status_var = tk.StringVar()
        tk.Label(self, textvariable=self._status_var, font=F["small"],
                 bg=C["bg"], fg=C["text_muted"]).pack(anchor="w", padx=8, pady=2)

    def refresh(self):
        raw = self._filter_var.get()
        sf = None if raw == "All" else raw.lower().replace(" ", "_")
        search = self._search_var.get().strip() or None
        rows = get_all_shipments(sf, search)

        def vals(r):
            total = (r["transport_cost"] or 0) + (r["surcharge"] or 0)
            return (r["shipment_ref"], r["order_number"] or "",
                    r["sender_name"], r["receiver_name"],
                    r["warehouse_name"] or "", r["driver_name"] or "Unassigned",
                    f"{r['weight_kg']:.1f}", f"£{total:.2f}",
                    status_badge(r["payment_status"]),
                    status_badge(r["status"]),
                    (r["created_at"] or "")[:16])

        populate_tree(self.tree, rows, vals)
        self._status_var.set(f"{len(rows)} shipment(s) shown")

    def _selected_id(self) -> int | None:
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def _add(self):
        ShipmentForm(self, self.session, None, self.refresh)

    def _edit(self):
        sid = self._selected_id()
        if not sid:
            messagebox.showwarning("Select", "Please select a shipment first.")
            return
        ShipmentForm(self, self.session, sid, self.refresh)

    def _delete(self):
        sid = self._selected_id()
        if not sid:
            messagebox.showwarning("Select", "Please select a shipment first.")
            return
        if messagebox.askyesno("Confirm Delete",
                               "Delete this shipment and all linked records?"):
            ok, err = delete_shipment(sid, self.session.user_id)
            if ok:
                self.refresh()
            else:
                messagebox.showerror("Error", err)


class ShipmentForm(tk.Toplevel):
    def __init__(self, parent, session, shipment_id, on_save):
        super().__init__(parent)
        self.session = session
        self.shipment_id = shipment_id
        self.on_save = on_save
        self.title("Edit Shipment" if shipment_id else "Add Shipment")
        self.geometry("560x640")
        self.resizable(False, True)
        self.configure(bg=C["bg"])
        self.grab_set()
        self.transient(parent)

        self._wh_map    = {r["name"]: r["id"] for r in get_warehouses_list()}
        self._drv_map   = {"(None)": None, **{r["full_name"]: r["id"] for r in get_drivers_list()}}
        self._veh_map   = {"(None)": None, **{f"{r['registration']} ({r['vehicle_type']})": r["id"]
                                               for r in get_vehicles_list()}}
        self._build()
        if shipment_id:
            self._load()

    def _build(self):
        canvas = tk.Canvas(self, bg=C["bg"], highlightthickness=0)
        sb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        self.form = ttk.Frame(canvas)
        win = canvas.create_window((0, 0), window=self.form, anchor="nw")
        self.form.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))

        f = self.form
        f.columnconfigure(1, weight=1)

        def lbl(text, r):
            tk.Label(f, text=text, font=F["heading"], bg=C["bg"],
                     fg=C["primary"]).grid(row=r, column=0, columnspan=2,
                                           sticky="w", padx=8, pady=(10, 2))

        def entry(label, r):
            tk.Label(f, text=label, bg=C["bg"]).grid(row=r, column=0, sticky="w", padx=8, pady=2)
            v = tk.StringVar()
            ttk.Entry(f, textvariable=v).grid(row=r, column=1, sticky="ew", padx=8, pady=2)
            return v

        def combo(label, r, values):
            tk.Label(f, text=label, bg=C["bg"]).grid(row=r, column=0, sticky="w", padx=8, pady=2)
            v = tk.StringVar()
            ttk.Combobox(f, textvariable=v, values=values, state="readonly").grid(
                row=r, column=1, sticky="ew", padx=8, pady=2)
            return v

        lbl("Shipment Details", 0)
        self.v_order    = entry("Order Number",    1)
        self.v_wh       = combo("Warehouse *",     2, list(self._wh_map.keys()))
        self.v_status   = combo("Status *",        3, STATUSES)
        self.v_weight   = entry("Weight (kg) *",   4)

        lbl("Sender", 5)
        self.v_sname    = entry("Sender Name *",   6)
        self.v_saddr    = entry("Sender Address *",7)

        lbl("Receiver", 8)
        self.v_rname    = entry("Receiver Name *", 9)
        self.v_raddr    = entry("Receiver Address *",10)
        self.v_rphone   = entry("Receiver Phone",  11)
        self.v_item     = entry("Item Description *",12)

        lbl("Assignment", 13)
        self.v_driver   = combo("Driver",          14, list(self._drv_map.keys()))
        self.v_vehicle  = combo("Vehicle",         15, list(self._veh_map.keys()))
        self.v_sched    = entry("Scheduled Date (YYYY-MM-DD)", 16)

        lbl("Financials", 17)
        self.v_cost     = entry("Transport Cost (£) *", 18)
        self.v_surch    = entry("Surcharge (£)",   19)
        self.v_pay      = combo("Payment Status *",20, PAY_STATUSES)

        lbl("Notes", 21)
        self.v_notes    = entry("Notes",           22)

        # Buttons
        btn_row = ttk.Frame(f)
        btn_row.grid(row=23, column=0, columnspan=2, pady=12, padx=8, sticky="ew")
        ttk.Button(btn_row, text="Cancel", command=self.destroy).pack(side="right", padx=4)
        ttk.Button(btn_row, text="Save", style="Primary.TButton",
                   command=self._save).pack(side="right", padx=4)

        # Defaults
        self.v_status.set("pending")
        self.v_pay.set("pending")
        self.v_driver.set("(None)")
        self.v_vehicle.set("(None)")
        self.v_cost.set("0.00")
        self.v_surch.set("0.00")

    def _load(self):
        from app.models.shipments import get_shipment_by_id
        r = get_shipment_by_id(self.shipment_id)
        if not r:
            return
        wh_name = next((k for k, v in self._wh_map.items() if v == r["warehouse_id"]), "")
        drv_name = next((k for k, v in self._drv_map.items() if v == r["driver_id"]), "(None)")
        veh_name = next((k for k, v in self._veh_map.items() if v == r["vehicle_id"]), "(None)")
        self.v_order.set(r["order_number"] or "")
        self.v_wh.set(wh_name)
        self.v_status.set(r["status"])
        self.v_weight.set(str(r["weight_kg"]))
        self.v_sname.set(r["sender_name"])
        self.v_saddr.set(r["sender_address"])
        self.v_rname.set(r["receiver_name"])
        self.v_raddr.set(r["receiver_address"])
        self.v_rphone.set(r["receiver_phone"] or "")
        self.v_item.set(r["item_description"])
        self.v_driver.set(drv_name)
        self.v_vehicle.set(veh_name)
        self.v_cost.set(str(r["transport_cost"]))
        self.v_surch.set(str(r["surcharge"]))
        self.v_pay.set(r["payment_status"])
        self.v_notes.set(r["notes"] or "")

    def _save(self):
        try:
            data = {
                "order_number":    self.v_order.get().strip() or None,
                "warehouse_id":    self._wh_map[self.v_wh.get()],
                "driver_id":       self._drv_map.get(self.v_driver.get()),
                "vehicle_id":      self._veh_map.get(self.v_vehicle.get()),
                "sender_name":     self.v_sname.get().strip(),
                "sender_address":  self.v_saddr.get().strip(),
                "receiver_name":   self.v_rname.get().strip(),
                "receiver_address":self.v_raddr.get().strip(),
                "receiver_phone":  self.v_rphone.get().strip() or None,
                "item_description":self.v_item.get().strip(),
                "weight_kg":       self.v_weight.get().strip() or "0",
                "status":          self.v_status.get(),
                "transport_cost":  self.v_cost.get().strip() or "0",
                "surcharge":       self.v_surch.get().strip() or "0",
                "payment_status":  self.v_pay.get(),
                "notes":           self.v_notes.get().strip() or None,
                "scheduled_date":  self.v_sched.get().strip() or None,
            }
            required = ["warehouse_id", "sender_name", "sender_address",
                        "receiver_name", "receiver_address", "item_description"]
            for k in required:
                if not data.get(k):
                    messagebox.showerror("Validation", f"Field '{k}' is required.")
                    return
            float(data["weight_kg"])
            float(data["transport_cost"])
            float(data["surcharge"])
        except (KeyError, ValueError) as e:
            messagebox.showerror("Validation", f"Invalid input: {e}")
            return

        if self.shipment_id:
            ok, err = update_shipment(self.shipment_id, data, self.session.user_id)
        else:
            ok, err = add_shipment(data, self.session.user_id)

        if ok:
            self.on_save()
            self.destroy()
        else:
            messagebox.showerror("Save Error", err)
