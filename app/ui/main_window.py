"""
ui/main_window.py — Main application window, tab container, status bar.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from app.ui.styles import C, F
import app.auth as auth


class MainWindow(tk.Tk):
    def __init__(self, session):
        super().__init__()
        self.session = session
        self.title(f"Northshore Logistics DMS — {session.full_name} ({session.role.title()})")
        self.geometry("1280x780")
        self.minsize(1024, 600)
        self.configure(bg=C["bg"])
        self._build()
        self._center()

    def _center(self):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        x, y = (sw - 1280) // 2, (sh - 780) // 2
        self.geometry(f"1280x780+{x}+{y}")

    def _build(self):
        # Top bar
        top = tk.Frame(self, bg=C["sidebar"], pady=8)
        top.pack(fill="x")
        tk.Label(top, text="  🚚  Northshore Logistics DMS",
                 font=F["title"], bg=C["sidebar"], fg=C["white"]).pack(side="left")
        logout_btn = tk.Button(top, text="Log Out", font=F["small"],
                               bg=C["danger"], fg=C["white"], relief="flat",
                               activebackground="#922B21", activeforeground=C["white"],
                               cursor="hand2", padx=10, command=self._logout)
        logout_btn.pack(side="right", padx=12, pady=2)
        tk.Label(top, text=f"{self.session.full_name}  |  {self.session.role.title()}",
                 font=F["small"], bg=C["sidebar"], fg="#AABDD4").pack(side="right", padx=8)

        # Notebook
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=0, pady=0)
        self._load_tabs()

        # Status bar
        sb = tk.Frame(self, bg=C["border"], height=22)
        sb.pack(fill="x", side="bottom")
        tk.Label(sb, text="Ready", font=F["small"],
                 bg=C["border"], fg=C["text_muted"]).pack(side="left", padx=8)

    def _load_tabs(self):
        from app.ui.dashboard_tab  import DashboardTab
        from app.ui.shipments_tab  import ShipmentsTab
        from app.ui.inventory_tab  import InventoryTab
        from app.ui.fleet_tab      import FleetTab
        from app.ui.incidents_tab  import IncidentsTab
        from app.ui.reports_tab    import ReportsTab
        from app.ui.admin_tab      import AdminTab

        s = self.session
        self.nb.add(DashboardTab(self.nb, s), text="📊  Dashboard")
        if s.can("view_shipments"):
            self.nb.add(ShipmentsTab(self.nb, s),  text="📦  Shipments")
        if s.can("view_inventory"):
            self.nb.add(InventoryTab(self.nb, s),  text="📋  Inventory")
        if s.can("view_vehicles"):
            self.nb.add(FleetTab(self.nb, s),      text="🚗  Fleet")
        if s.can("view_incidents"):
            self.nb.add(IncidentsTab(self.nb, s),  text="🚨  Incidents")
        if s.can("view_reports"):
            self.nb.add(ReportsTab(self.nb, s),    text="📈  Reports")
        if s.can("view_users"):
            self.nb.add(AdminTab(self.nb, s),      text="⚙  Admin")

    def _logout(self):
        if messagebox.askyesno("Log Out", "Are you sure you want to log out?"):
            auth.logout()
            self.destroy()
