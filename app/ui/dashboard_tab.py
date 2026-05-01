"""
ui/dashboard_tab.py — KPI summary cards shown to all roles.
"""

import tkinter as tk
from tkinter import ttk
from app.ui.styles import C, F
from app.models.reports import get_dashboard_stats


class DashboardTab(ttk.Frame):
    def __init__(self, parent, session):
        super().__init__(parent)
        self.session = session
        self.configure(style="TFrame")
        self._build()

    def _build(self):
        # Title bar
        hdr = tk.Frame(self, bg=C["primary"], pady=12)
        hdr.pack(fill="x")
        tk.Label(hdr, text="  📊  Operations Dashboard",
                 font=F["title"], bg=C["primary"], fg=C["white"]).pack(side="left")
        tk.Label(hdr, text=f"Logged in as: {self.session.full_name}  ({self.session.role.title()})",
                 font=F["small"], bg=C["primary"], fg="#D6EAF8").pack(side="right", padx=12)

        # Refresh button
        btn_bar = ttk.Frame(self)
        btn_bar.pack(fill="x", padx=16, pady=(8, 0))
        ttk.Button(btn_bar, text="⟳  Refresh", style="Primary.TButton",
                   command=self.refresh).pack(side="right")

        # KPI scroll area
        self._cards_frame = ttk.Frame(self)
        self._cards_frame.pack(fill="both", expand=True, padx=16, pady=8)
        self.refresh()

    def refresh(self):
        for w in self._cards_frame.winfo_children():
            w.destroy()
        stats = get_dashboard_stats()

        kpis = [
            ("📦", "Total Shipments",    str(stats["total_shipments"]),   C["primary"]),
            ("🕐", "Pending",            str(stats["pending"]),           C["text_muted"]),
            ("🚚", "In Transit",         str(stats["in_transit"]),        C["primary"]),
            ("✅", "Delivered",          str(stats["delivered"]),         C["success"]),
            ("⚠️", "Delayed",            str(stats["delayed"]),           C["warning"]),
            ("🔴", "Low Stock Items",    str(stats["low_stock_items"]),   C["danger"]),
            ("🚗", "Vehicles Available", str(stats["available_vehicles"]),C["accent"]),
            ("👤", "Drivers Available",  str(stats["available_drivers"]), C["accent"]),
            ("💰", "Revenue Paid",       f"£{stats['revenue_paid']:,.2f}", C["success"]),
            ("⏳", "Revenue Pending",    f"£{stats['revenue_pending']:,.2f}", C["warning"]),
            ("🚨", "Open Incidents",     str(stats["open_incidents"]),    C["danger"]),
            ("🏭", "Warehouses",         str(stats["total_warehouses"]),  C["primary"]),
        ]

        cols = 4
        for i, (icon, label, value, colour) in enumerate(kpis):
            r, c = divmod(i, cols)
            card = tk.Frame(self._cards_frame, bg=C["white"],
                            relief="solid", bd=1, padx=16, pady=14)
            card.grid(row=r, column=c, padx=8, pady=8, sticky="nsew")
            self._cards_frame.columnconfigure(c, weight=1)
            tk.Label(card, text=icon, font=("Segoe UI", 28),
                     bg=C["white"]).pack(anchor="w")
            tk.Label(card, text=value, font=F["kpi"],
                     bg=C["white"], fg=colour).pack(anchor="w")
            tk.Label(card, text=label, font=F["small"],
                     bg=C["white"], fg=C["text_muted"]).pack(anchor="w")
