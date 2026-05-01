"""
ui/inventory_tab.py — Inventory management with stock adjustment.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from app.ui.styles import C, F, scrolled_tree, populate_tree
from app.models.inventory import (get_all_inventory, get_low_stock,
                                   add_item, update_item, delete_item,
                                   adjust_stock, get_warehouses_list)

COLS = [
    ("sku",            "SKU",         90),
    ("item_name",      "Item Name",  160),
    ("warehouse_name", "Warehouse",  120),
    ("location_code",  "Location",    80),
    ("quantity",       "Qty",         60),
    ("reorder_level",  "Reorder",     70),
    ("unit_weight_kg", "Unit Wt(kg)", 90),
    ("description",    "Description",180),
    ("updated_at",     "Updated",    120),
]


class InventoryTab(ttk.Frame):
    def __init__(self, parent, session):
        super().__init__(parent)
        self.session = session
        self._build()
        self.refresh()

    def _build(self):
        tb = ttk.Frame(self)
        tb.pack(fill="x", padx=8, pady=6)

        self._wh_list    = get_warehouses_list()
        wh_names         = ["All Warehouses"] + [w["name"] for w in self._wh_list]
        self._wh_map     = {w["name"]: w["id"] for w in self._wh_list}
        self._wh_var     = tk.StringVar(value="All Warehouses")
        cb = ttk.Combobox(tb, textvariable=self._wh_var, values=wh_names,
                          state="readonly", width=20)
        cb.pack(side="left", padx=(0, 8))
        cb.bind("<<ComboboxSelected>>", lambda _: self.refresh())

        self._search_var = tk.StringVar()
        ttk.Entry(tb, textvariable=self._search_var, width=20).pack(side="left", padx=2)
        ttk.Button(tb, text="🔍 Search", command=self.refresh).pack(side="left", padx=4)
        ttk.Button(tb, text="⚠ Low Stock", command=self._show_low).pack(side="left", padx=4)
        ttk.Button(tb, text="⟳ Refresh",  command=self.refresh).pack(side="left", padx=4)

        if self.session.can("add_inventory"):
            ttk.Button(tb, text="+ Add Item", style="Primary.TButton",
                       command=self._add).pack(side="right", padx=4)
        if self.session.can("edit_inventory"):
            ttk.Button(tb, text="✎ Edit",     command=self._edit).pack(side="right", padx=4)
            ttk.Button(tb, text="± Adjust Stock", style="Success.TButton",
                       command=self._adjust).pack(side="right", padx=4)
        if self.session.can("delete_inventory"):
            ttk.Button(tb, text="🗑 Delete", style="Danger.TButton",
                       command=self._delete).pack(side="right", padx=4)

        self.tree = scrolled_tree(self, COLS, height=18)
        self.tree.bind("<Double-1>", lambda _: self._edit())

        self._status_var = tk.StringVar()
        tk.Label(self, textvariable=self._status_var, font=F["small"],
                 bg=C["bg"], fg=C["text_muted"]).pack(anchor="w", padx=8, pady=2)

    def refresh(self):
        whn = self._wh_var.get()
        wid = self._wh_map.get(whn) if whn != "All Warehouses" else None
        search = self._search_var.get().strip() or None
        rows = get_all_inventory(wid, search)
        self._populate(rows)

    def _show_low(self):
        rows = get_low_stock()
        self._populate(rows)
        self._status_var.set(f"⚠ {len(rows)} low-stock item(s)")

    def _populate(self, rows):
        def vals(r):
            qty = r["quantity"]
            flag = " ⚠" if qty <= r["reorder_level"] else ""
            return (r["sku"], r["item_name"], r["warehouse_name"],
                    r["location_code"] or "", f"{qty}{flag}",
                    r["reorder_level"], r["unit_weight_kg"],
                    r["description"] or "", (r["updated_at"] or "")[:16])
        populate_tree(self.tree, rows, vals)
        self._status_var.set(f"{len(rows)} item(s) shown")

    def _selected_id(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def _add(self):
        InventoryForm(self, self.session, None, self.refresh)

    def _edit(self):
        iid = self._selected_id()
        if not iid:
            messagebox.showwarning("Select", "Please select an item.")
            return
        InventoryForm(self, self.session, iid, self.refresh)

    def _delete(self):
        iid = self._selected_id()
        if not iid:
            messagebox.showwarning("Select", "Please select an item.")
            return
        if messagebox.askyesno("Confirm Delete", "Delete this inventory item?"):
            ok, err = delete_item(iid, self.session.user_id)
            if ok:
                self.refresh()
            else:
                messagebox.showerror("Error", err)

    def _adjust(self):
        iid = self._selected_id()
        if not iid:
            messagebox.showwarning("Select", "Please select an item.")
            return
        AdjustDialog(self, self.session, iid, self.refresh)


class InventoryForm(tk.Toplevel):
    def __init__(self, parent, session, item_id, on_save):
        super().__init__(parent)
        self.session = session
        self.item_id = item_id
        self.on_save = on_save
        self.title("Edit Item" if item_id else "Add Item")
        self.geometry("460x420")
        self.resizable(False, False)
        self.configure(bg=C["bg"])
        self.grab_set()
        self.transient(parent)
        self._wh_list = get_warehouses_list()
        self._wh_map  = {w["name"]: w["id"] for w in self._wh_list}
        self._build()
        if item_id:
            self._load()

    def _build(self):
        f = ttk.Frame(self, padding=16)
        f.pack(fill="both", expand=True)
        f.columnconfigure(1, weight=1)

        def row(label, r):
            tk.Label(f, text=label, bg=C["bg"]).grid(row=r, column=0, sticky="w", padx=4, pady=3)
            v = tk.StringVar()
            ttk.Entry(f, textvariable=v).grid(row=r, column=1, sticky="ew", padx=4, pady=3)
            return v

        self.v_wh    = tk.StringVar()
        tk.Label(f, text="Warehouse *", bg=C["bg"]).grid(row=0, column=0, sticky="w", padx=4, pady=3)
        ttk.Combobox(f, textvariable=self.v_wh, values=list(self._wh_map.keys()),
                     state="readonly").grid(row=0, column=1, sticky="ew", padx=4, pady=3)

        self.v_sku   = row("SKU *",            1)
        self.v_name  = row("Item Name *",       2)
        self.v_desc  = row("Description",       3)
        self.v_qty   = row("Quantity *",        4)
        self.v_reord = row("Reorder Level *",   5)
        self.v_wt    = row("Unit Weight (kg) *",6)
        self.v_loc   = row("Location Code",     7)

        btn = ttk.Frame(f)
        btn.grid(row=8, column=0, columnspan=2, pady=12, sticky="e")
        ttk.Button(btn, text="Cancel", command=self.destroy).pack(side="right", padx=4)
        ttk.Button(btn, text="Save", style="Primary.TButton",
                   command=self._save).pack(side="right", padx=4)

        self.v_qty.set("0")
        self.v_reord.set("10")
        self.v_wt.set("1.0")

    def _load(self):
        from app.database import get_connection
        conn = get_connection()
        r = conn.execute("SELECT * FROM Inventory WHERE id=?", (self.item_id,)).fetchone()
        conn.close()
        if not r:
            return
        wh_name = next((k for k, v in self._wh_map.items() if v == r["warehouse_id"]), "")
        self.v_wh.set(wh_name)
        self.v_sku.set(r["sku"])
        self.v_name.set(r["item_name"])
        self.v_desc.set(r["description"] or "")
        self.v_qty.set(str(r["quantity"]))
        self.v_reord.set(str(r["reorder_level"]))
        self.v_wt.set(str(r["unit_weight_kg"]))
        self.v_loc.set(r["location_code"] or "")

    def _save(self):
        try:
            data = {
                "warehouse_id":    self._wh_map[self.v_wh.get()],
                "sku":             self.v_sku.get().strip(),
                "item_name":       self.v_name.get().strip(),
                "description":     self.v_desc.get().strip() or None,
                "quantity":        int(self.v_qty.get()),
                "reorder_level":   int(self.v_reord.get()),
                "unit_weight_kg":  float(self.v_wt.get()),
                "location_code":   self.v_loc.get().strip() or None,
            }
            if not data["sku"] or not data["item_name"]:
                messagebox.showerror("Validation", "SKU and Item Name are required.")
                return
        except (KeyError, ValueError) as e:
            messagebox.showerror("Validation", f"Invalid input: {e}")
            return

        if self.item_id:
            ok, err = update_item(self.item_id, data, self.session.user_id)
        else:
            ok, err = add_item(data, self.session.user_id)

        if ok:
            self.on_save()
            self.destroy()
        else:
            messagebox.showerror("Save Error", err)


class AdjustDialog(tk.Toplevel):
    def __init__(self, parent, session, item_id, on_save):
        super().__init__(parent)
        self.session = session
        self.item_id = item_id
        self.on_save = on_save
        self.title("Adjust Stock")
        self.geometry("360x220")
        self.resizable(False, False)
        self.configure(bg=C["bg"])
        self.grab_set()
        self.transient(parent)
        self._build()

    def _build(self):
        f = ttk.Frame(self, padding=16)
        f.pack(fill="both", expand=True)
        tk.Label(f, text="Adjustment (use + or - integer):",
                 font=F["heading"], bg=C["bg"]).pack(anchor="w", pady=(0, 4))
        self.v_delta = tk.StringVar()
        ttk.Entry(f, textvariable=self.v_delta, width=20).pack(anchor="w", pady=(0, 8))
        tk.Label(f, text="Reason:", font=F["heading"], bg=C["bg"]).pack(anchor="w")
        self.v_reason = tk.StringVar()
        ttk.Entry(f, textvariable=self.v_reason, width=40).pack(anchor="w", pady=(0, 12))
        btn = ttk.Frame(f)
        btn.pack(anchor="e")
        ttk.Button(btn, text="Cancel", command=self.destroy).pack(side="right", padx=4)
        ttk.Button(btn, text="Apply", style="Primary.TButton",
                   command=self._apply).pack(side="right", padx=4)

    def _apply(self):
        try:
            delta = int(self.v_delta.get())
        except ValueError:
            messagebox.showerror("Validation", "Enter a valid integer.")
            return
        reason = self.v_reason.get().strip() or "Manual adjustment"
        ok, msg = adjust_stock(self.item_id, delta, reason, self.session.user_id)
        if ok:
            messagebox.showinfo("Done", f"New quantity: {msg}")
            self.on_save()
            self.destroy()
        else:
            messagebox.showerror("Error", msg)
