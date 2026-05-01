"""
ui/incidents_tab.py — Incident reporting and resolution.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from app.ui.styles import C, F, scrolled_tree, populate_tree
from app.models.reports import get_all_incidents, add_incident, resolve_incident
from app.models.shipments import get_all_shipments

INCIDENT_TYPES = ["delay", "route_change", "damaged_goods", "failed_delivery", "other"]

INC_COLS = [
    ("shipment_ref",   "Shipment Ref",  110),
    ("incident_type",  "Type",          110),
    ("reporter_name",  "Reported By",   120),
    ("description",    "Description",   220),
    ("is_resolved",    "Resolved",       80),
    ("resolution",     "Resolution",    180),
    ("created_at",     "Reported At",   120),
    ("resolved_at",    "Resolved At",   120),
]


class IncidentsTab(ttk.Frame):
    def __init__(self, parent, session):
        super().__init__(parent)
        self.session = session
        self._build()
        self.refresh()

    def _build(self):
        tb = ttk.Frame(self); tb.pack(fill="x", padx=8, pady=6)
        self._show_all_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(tb, text="Show Resolved", variable=self._show_all_var,
                        command=self.refresh).pack(side="left", padx=4)
        ttk.Button(tb, text="⟳ Refresh", command=self.refresh).pack(side="left", padx=4)

        if self.session.can("add_incident"):
            ttk.Button(tb, text="+ Report Incident", style="Primary.TButton",
                       command=self._add).pack(side="right", padx=4)
        if self.session.can("resolve_incident"):
            ttk.Button(tb, text="✓ Resolve", style="Success.TButton",
                       command=self._resolve).pack(side="right", padx=4)

        self.tree = scrolled_tree(self, INC_COLS, height=18)
        self._sv = tk.StringVar()
        tk.Label(self, textvariable=self._sv, font=F["small"],
                 bg=C["bg"], fg=C["text_muted"]).pack(anchor="w", padx=8, pady=2)

    def refresh(self):
        rows = get_all_incidents(show_resolved=self._show_all_var.get())
        def vals(r): return (r["shipment_ref"],
                             r["incident_type"].replace("_", " ").title(),
                             r["reporter_name"] or "Unknown",
                             r["description"],
                             "Yes" if r["is_resolved"] else "No",
                             r["resolution"] or "",
                             (r["created_at"] or "")[:16],
                             (r["resolved_at"] or "")[:16])
        populate_tree(self.tree, rows, vals)
        self._sv.set(f"{len(rows)} incident(s) shown")

    def _sel(self): sel = self.tree.selection(); return int(sel[0]) if sel else None

    def _add(self):
        IncidentForm(self, self.session, self.refresh)

    def _resolve(self):
        iid = self._sel()
        if not iid:
            messagebox.showwarning("Select", "Select an incident first.")
            return
        ResolveDialog(self, self.session, iid, self.refresh)


class IncidentForm(tk.Toplevel):
    def __init__(self, parent, session, on_save):
        super().__init__(parent)
        self.session = session; self.on_save = on_save
        self.title("Report Incident")
        self.geometry("480x300"); self.resizable(False, False)
        self.configure(bg=C["bg"]); self.grab_set(); self.transient(parent)
        # Build shipment lookup
        self._shp_rows = get_all_shipments()
        self._shp_map  = {r["shipment_ref"]: r["id"] for r in self._shp_rows}
        self._build()

    def _build(self):
        f = ttk.Frame(self, padding=16); f.pack(fill="both", expand=True)
        f.columnconfigure(1, weight=1)

        tk.Label(f, text="Shipment *", bg=C["bg"]).grid(row=0, column=0, sticky="w", padx=4, pady=3)
        self.v_shp = tk.StringVar()
        ttk.Combobox(f, textvariable=self.v_shp, values=list(self._shp_map.keys()),
                     state="readonly").grid(row=0, column=1, sticky="ew", padx=4, pady=3)

        tk.Label(f, text="Type *", bg=C["bg"]).grid(row=1, column=0, sticky="w", padx=4, pady=3)
        self.v_type = tk.StringVar(value=INCIDENT_TYPES[0])
        ttk.Combobox(f, textvariable=self.v_type, values=INCIDENT_TYPES,
                     state="readonly").grid(row=1, column=1, sticky="ew", padx=4, pady=3)

        tk.Label(f, text="Description *", bg=C["bg"]).grid(row=2, column=0, sticky="nw", padx=4, pady=3)
        self.txt_desc = tk.Text(f, height=5, width=38, font=F["normal"])
        self.txt_desc.grid(row=2, column=1, sticky="ew", padx=4, pady=3)

        btn = ttk.Frame(f); btn.grid(row=3, column=0, columnspan=2, pady=10, sticky="e")
        ttk.Button(btn, text="Cancel", command=self.destroy).pack(side="right", padx=4)
        ttk.Button(btn, text="Submit", style="Primary.TButton",
                   command=self._submit).pack(side="right", padx=4)

    def _submit(self):
        shp_ref = self.v_shp.get()
        desc    = self.txt_desc.get("1.0", "end").strip()
        if not shp_ref or not desc:
            messagebox.showerror("Validation", "Shipment and Description are required.")
            return
        data = {"shipment_id": self._shp_map[shp_ref],
                "incident_type": self.v_type.get(),
                "description":   desc}
        ok, err = add_incident(data, self.session.user_id)
        if ok: self.on_save(); self.destroy()
        else:  messagebox.showerror("Error", err)


class ResolveDialog(tk.Toplevel):
    def __init__(self, parent, session, incident_id, on_save):
        super().__init__(parent)
        self.session = session; self.incident_id = incident_id; self.on_save = on_save
        self.title("Resolve Incident")
        self.geometry("420x200"); self.resizable(False, False)
        self.configure(bg=C["bg"]); self.grab_set(); self.transient(parent)
        self._build()

    def _build(self):
        f = ttk.Frame(self, padding=16); f.pack(fill="both", expand=True)
        tk.Label(f, text="Resolution notes:", font=F["heading"], bg=C["bg"]).pack(anchor="w")
        self.txt = tk.Text(f, height=5, width=50, font=F["normal"])
        self.txt.pack(fill="x", pady=(4, 10))
        btn = ttk.Frame(f); btn.pack(anchor="e")
        ttk.Button(btn, text="Cancel", command=self.destroy).pack(side="right", padx=4)
        ttk.Button(btn, text="Mark Resolved", style="Success.TButton",
                   command=self._apply).pack(side="right", padx=4)

    def _apply(self):
        resolution = self.txt.get("1.0", "end").strip() or "Resolved."
        ok, err = resolve_incident(self.incident_id, resolution, self.session.user_id)
        if ok: self.on_save(); self.destroy()
        else:  messagebox.showerror("Error", err)
