"""
ui/reports_tab.py — Pandas reports, export, and audit log viewer.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from app.ui.styles import C, F, scrolled_tree
from app.models.reports import (report_shipment_status, report_vehicle_utilisation,
                                  report_warehouse_activity, report_driver_performance,
                                  export_report_csv, get_audit_logs)


class ReportsTab(ttk.Frame):
    def __init__(self, parent, session):
        super().__init__(parent)
        self.session = session
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        nb.add(ReportPanel(nb, session, "Shipment Status",    report_shipment_status,    "shipment_status"),    text="📦 Shipments")
        nb.add(ReportPanel(nb, session, "Vehicle Utilisation",report_vehicle_utilisation,"vehicle_utilisation"),text="🚗 Vehicles")
        nb.add(ReportPanel(nb, session, "Warehouse Activity", report_warehouse_activity, "warehouse_activity"), text="🏭 Warehouses")
        nb.add(ReportPanel(nb, session, "Driver Performance", report_driver_performance, "driver_performance"), text="👤 Drivers")
        if session.can("view_audit_logs"):
            nb.add(AuditLogPanel(nb, session), text="🔍 Audit Log")


class ReportPanel(ttk.Frame):
    def __init__(self, parent, session, title, data_fn, export_name):
        super().__init__(parent)
        self.session = session
        self.data_fn = data_fn
        self.export_name = export_name
        self._df = None
        self._build(title)

    def _build(self, title):
        tb = ttk.Frame(self); tb.pack(fill="x", padx=8, pady=6)
        tk.Label(tb, text=title, font=F["heading"], bg=C["bg"], fg=C["primary"]).pack(side="left")
        ttk.Button(tb, text="⟳ Load", style="Primary.TButton",
                   command=self._load).pack(side="right", padx=4)
        if self.session.can("export_reports"):
            ttk.Button(tb, text="📥 Export CSV",
                       command=self._export).pack(side="right", padx=4)

        # Frame for the tree — built dynamically after first load
        self._tree_frame = ttk.Frame(self)
        self._tree_frame.pack(fill="both", expand=True)

        self._sv = tk.StringVar(value="Click ⟳ Load to generate report.")
        tk.Label(self, textvariable=self._sv, font=F["small"],
                 bg=C["bg"], fg=C["text_muted"]).pack(anchor="w", padx=8, pady=2)

    def _load(self):
        for w in self._tree_frame.winfo_children():
            w.destroy()
        try:
            self._df = self.data_fn()
        except Exception as e:
            messagebox.showerror("Report Error", str(e)); return

        cols = list(self._df.columns)
        col_defs = [(c, c, max(80, min(200, len(c)*10))) for c in cols]

        # Build treeview directly (columns are dynamic)
        frame = self._tree_frame
        col_ids = [c[0] for c in col_defs]
        tree = ttk.Treeview(frame, columns=col_ids, show="headings", height=16)
        vsb = ttk.Scrollbar(frame, orient="vertical",   command=tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        for cid, label, width in col_defs:
            tree.heading(cid, text=label)
            tree.column(cid, width=width, minwidth=50)
        tree.tag_configure("alt", background=C["row_alt"])
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        tree.pack(fill="both", expand=True)

        for i, row in self._df.iterrows():
            vals = [str(v) if v is not None else "" for v in row]
            tree.insert("", "end", values=vals, tags=("alt",) if i % 2 else ())

        self._sv.set(f"{len(self._df)} row(s) loaded.")

    def _export(self):
        if self._df is None:
            messagebox.showwarning("No Data", "Load the report first.")
            return
        path = export_report_csv(self._df, self.export_name)
        messagebox.showinfo("Exported", f"Saved to:\n{path}")


class AuditLogPanel(ttk.Frame):
    def __init__(self, parent, session):
        super().__init__(parent)
        self.session = session
        self._build()
        self.refresh()

    def _build(self):
        tb = ttk.Frame(self); tb.pack(fill="x", padx=8, pady=6)
        self._sv_search = tk.StringVar()
        ttk.Entry(tb, textvariable=self._sv_search, width=24).pack(side="left", padx=2)
        ttk.Button(tb, text="🔍 Search", command=self.refresh).pack(side="left", padx=4)
        ttk.Button(tb, text="⟳ Refresh", command=self.refresh).pack(side="left", padx=4)

        COLS = [
            ("timestamp",   "Timestamp",  130),
            ("username",    "User",        90),
            ("action",      "Action",      90),
            ("table_name",  "Table",       90),
            ("record_id",   "Record ID",   80),
            ("description", "Description",320),
        ]
        self.tree = scrolled_tree(self, COLS, height=18)
        self._sv = tk.StringVar()
        tk.Label(self, textvariable=self._sv, font=F["small"],
                 bg=C["bg"], fg=C["text_muted"]).pack(anchor="w", padx=8, pady=2)

    def refresh(self):
        search = self._sv_search.get().strip() or None
        rows = get_audit_logs(200, search)
        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(rows):
            vals = ((r["timestamp"] or "")[:16], r["username"] or "system",
                    r["action"], r["table_name"] or "", r["record_id"] or "",
                    r["description"] or "")
            tag = "alt" if i % 2 else ""
            self.tree.insert("", "end", values=vals, tags=(tag,))
        self._sv.set(f"{len(rows)} audit entries shown")
