"""
ui/admin_tab.py — User management (admin role only).
"""

import tkinter as tk
from tkinter import ttk, messagebox
from app.ui.styles import C, F, scrolled_tree, populate_tree
from app.models.reports import get_all_users, add_user, update_user, toggle_user_active

ROLES = ["admin", "manager", "staff", "driver"]

USR_COLS = [
    ("username",   "Username",   110),
    ("full_name",  "Full Name",  150),
    ("email",      "Email",      180),
    ("role",       "Role",        80),
    ("is_active",  "Active",      60),
    ("created_at", "Created",    120),
]


class AdminTab(ttk.Frame):
    def __init__(self, parent, session):
        super().__init__(parent)
        self.session = session
        self._build()
        self.refresh()

    def _build(self):
        tb = ttk.Frame(self); tb.pack(fill="x", padx=8, pady=6)
        tk.Label(tb, text="User Management", font=F["heading"],
                 bg=C["bg"], fg=C["primary"]).pack(side="left")
        ttk.Button(tb, text="⟳ Refresh", command=self.refresh).pack(side="left", padx=8)
        ttk.Button(tb, text="+ Add User", style="Primary.TButton",
                   command=self._add).pack(side="right", padx=4)
        ttk.Button(tb, text="✎ Edit", command=self._edit).pack(side="right", padx=4)
        ttk.Button(tb, text="⏸ Toggle Active", command=self._toggle).pack(side="right", padx=4)

        self.tree = scrolled_tree(self, USR_COLS, height=16)
        self.tree.bind("<Double-1>", lambda _: self._edit())

        # System info
        info = ttk.LabelFrame(self, text="System Information", padding=8)
        info.pack(fill="x", padx=8, pady=6)
        from app.database import DB_PATH
        import os
        size_kb = os.path.getsize(DB_PATH) // 1024 if os.path.exists(DB_PATH) else 0
        tk.Label(info, text=f"Database: {DB_PATH}   |   Size: {size_kb} KB",
                 font=F["small"], bg=C["bg"], fg=C["text_muted"]).pack(anchor="w")

        self._sv = tk.StringVar()
        tk.Label(self, textvariable=self._sv, font=F["small"],
                 bg=C["bg"], fg=C["text_muted"]).pack(anchor="w", padx=8, pady=2)

    def refresh(self):
        rows = get_all_users()
        def vals(r): return (r["username"], r["full_name"], r["email"] or "",
                             r["role"].title(), "Yes" if r["is_active"] else "No",
                             (r["created_at"] or "")[:10])
        populate_tree(self.tree, rows, vals)
        self._sv.set(f"{len(rows)} user(s)")

    def _sel(self): sel = self.tree.selection(); return int(sel[0]) if sel else None

    def _add(self): UserForm(self, self.session, None, self.refresh)
    def _edit(self):
        uid = self._sel()
        if not uid: messagebox.showwarning("Select", "Select a user first."); return
        UserForm(self, self.session, uid, self.refresh)
    def _toggle(self):
        uid = self._sel()
        if not uid: messagebox.showwarning("Select", "Select a user first."); return
        if uid == self.session.user_id:
            messagebox.showwarning("Warning", "You cannot deactivate your own account.")
            return
        ok, state = toggle_user_active(uid, self.session.user_id)
        if ok: messagebox.showinfo("Done", f"Account {state}."); self.refresh()
        else:  messagebox.showerror("Error", state)


class UserForm(tk.Toplevel):
    def __init__(self, parent, session, user_id, on_save):
        super().__init__(parent)
        self.session = session; self.user_id = user_id; self.on_save = on_save
        self.title("Edit User" if user_id else "Add User")
        self.geometry("420x340"); self.resizable(False, False)
        self.configure(bg=C["bg"]); self.grab_set(); self.transient(parent)
        self._build()
        if user_id: self._load()

    def _build(self):
        f = ttk.Frame(self, padding=16); f.pack(fill="both", expand=True)
        f.columnconfigure(1, weight=1)
        def row(lbl, r):
            tk.Label(f, text=lbl, bg=C["bg"]).grid(row=r, column=0, sticky="w", padx=4, pady=3)
            v = tk.StringVar()
            ttk.Entry(f, textvariable=v).grid(row=r, column=1, sticky="ew", padx=4, pady=3)
            return v
        self.v_uname = row("Username *",  0)
        self.v_name  = row("Full Name *", 1)
        self.v_email = row("Email",       2)
        self.v_pw    = row("Password *",  3)
        tk.Label(f, text="Role *", bg=C["bg"]).grid(row=4, column=0, sticky="w", padx=4, pady=3)
        self.v_role = tk.StringVar(value="staff")
        ttk.Combobox(f, textvariable=self.v_role, values=ROLES, state="readonly").grid(
            row=4, column=1, sticky="ew", padx=4, pady=3)
        if self.user_id:
            tk.Label(f, text="Active", bg=C["bg"]).grid(row=5, column=0, sticky="w", padx=4, pady=3)
            self.v_active = tk.BooleanVar(value=True)
            ttk.Checkbutton(f, variable=self.v_active).grid(row=5, column=1, sticky="w", padx=4)
            tk.Label(f, text="(Leave password blank to keep unchanged)",
                     font=F["small"], bg=C["bg"], fg=C["text_muted"]).grid(
                row=6, column=0, columnspan=2, sticky="w", padx=4)
        btn = ttk.Frame(f); btn.grid(row=7, column=0, columnspan=2, pady=10, sticky="e")
        ttk.Button(btn, text="Cancel", command=self.destroy).pack(side="right", padx=4)
        ttk.Button(btn, text="Save", style="Primary.TButton", command=self._save).pack(side="right", padx=4)

    def _load(self):
        from app.database import get_connection
        conn = get_connection()
        r = conn.execute("SELECT * FROM Users WHERE id=?", (self.user_id,)).fetchone()
        conn.close()
        if not r: return
        self.v_uname.set(r["username"]); self.v_name.set(r["full_name"])
        self.v_email.set(r["email"] or ""); self.v_role.set(r["role"])
        if hasattr(self, "v_active"): self.v_active.set(bool(r["is_active"]))

    def _save(self):
        data = {"username": self.v_uname.get().strip(), "full_name": self.v_name.get().strip(),
                "email": self.v_email.get().strip() or None,
                "password": self.v_pw.get(), "role": self.v_role.get(),
                "is_active": getattr(self, "v_active", tk.BooleanVar(value=True)).get()}
        if not data["full_name"] or not data["username"]:
            messagebox.showerror("Validation", "Username and Full Name are required."); return
        if not self.user_id and not data["password"]:
            messagebox.showerror("Validation", "Password required for new user."); return
        if self.user_id:
            ok, err = update_user(self.user_id, data, self.session.user_id)
        else:
            ok, err = add_user(data, self.session.user_id)
        if ok: self.on_save(); self.destroy()
        else:  messagebox.showerror("Error", err)
