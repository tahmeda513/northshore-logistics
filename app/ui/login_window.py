"""
ui/login_window.py — Login screen.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from app.ui.styles import C, F, apply_theme
import app.auth as auth


class LoginWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Northshore Logistics — Login")
        self.geometry("420x480")
        self.resizable(False, False)
        self.configure(bg=C["sidebar"])
        apply_theme(self)
        self._build()
        self._center()

    def _center(self):
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - 420) // 2
        y = (sh - 480) // 2
        self.geometry(f"420x480+{x}+{y}")

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=C["sidebar"])
        hdr.pack(fill="x", pady=(40, 10))
        tk.Label(hdr, text="🚚", font=("Segoe UI", 48),
                 bg=C["sidebar"], fg=C["white"]).pack()
        tk.Label(hdr, text="Northshore Logistics",
                 font=("Segoe UI", 18, "bold"),
                 bg=C["sidebar"], fg=C["white"]).pack()
        tk.Label(hdr, text="Database Management System",
                 font=F["small"], bg=C["sidebar"], fg="#AABDD4").pack()

        # Card
        card = tk.Frame(self, bg=C["white"], bd=0, relief="flat")
        card.pack(fill="both", expand=True, padx=30, pady=20)

        tk.Label(card, text="Sign In", font=F["title"],
                 bg=C["white"], fg=C["text"]).pack(pady=(20, 4))
        tk.Label(card, text="Enter your credentials to continue",
                 font=F["small"], bg=C["white"], fg=C["text_muted"]).pack(pady=(0, 16))

        form = tk.Frame(card, bg=C["white"])
        form.pack(fill="x", padx=24)

        tk.Label(form, text="Username", font=F["heading"],
                 bg=C["white"], fg=C["text"]).pack(anchor="w")
        self._user_var = tk.StringVar()
        user_e = ttk.Entry(form, textvariable=self._user_var, width=32, font=F["normal"])
        user_e.pack(fill="x", pady=(2, 10))
        user_e.focus_set()

        tk.Label(form, text="Password", font=F["heading"],
                 bg=C["white"], fg=C["text"]).pack(anchor="w")
        self._pass_var = tk.StringVar()
        pass_e = ttk.Entry(form, textvariable=self._pass_var, show="●",
                           width=32, font=F["normal"])
        pass_e.pack(fill="x", pady=(2, 4))
        pass_e.bind("<Return>", lambda _: self._do_login())

        self._err_var = tk.StringVar()
        tk.Label(form, textvariable=self._err_var, font=F["small"],
                 bg=C["white"], fg=C["danger"]).pack(pady=(0, 10))

        btn = tk.Button(form, text="Sign In", font=F["heading"],
                        bg=C["primary"], fg=C["white"], relief="flat",
                        activebackground=C["primary_dk"], activeforeground=C["white"],
                        cursor="hand2", pady=8, command=self._do_login)
        btn.pack(fill="x")

        tk.Label(card, text="Default logins: admin / Admin2024!",
                 font=F["small"], bg=C["white"], fg=C["text_muted"]).pack(pady=(12, 0))

    def _do_login(self):
        username = self._user_var.get().strip()
        password = self._pass_var.get()
        if not username or not password:
            self._err_var.set("Please enter username and password.")
            return
        ok, msg = auth.login(username, password)
        if ok:
            self.destroy()
        else:
            self._err_var.set(msg)
            self._pass_var.set("")
