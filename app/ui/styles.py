"""
ui/styles.py — Design system: colours, fonts, and shared widget factories.
"""

import tkinter as tk
from tkinter import ttk

# ── Colour Palette ────────────────────────────────────────────────────────────
C = {
    "bg":          "#F4F6F9",
    "sidebar":     "#1B2A4A",
    "primary":     "#1B6CA8",
    "primary_dk":  "#144F7A",
    "accent":      "#17A589",
    "danger":      "#C0392B",
    "warning":     "#D4880A",
    "success":     "#1E8449",
    "white":       "#FFFFFF",
    "border":      "#D5D8DC",
    "text":        "#212529",
    "text_muted":  "#6C757D",
    "row_alt":     "#EBF5FB",
    "row_sel":     "#AED6F1",
}

# ── Fonts ─────────────────────────────────────────────────────────────────────
F = {
    "title":   ("Segoe UI", 16, "bold"),
    "heading": ("Segoe UI", 11, "bold"),
    "normal":  ("Segoe UI", 10),
    "small":   ("Segoe UI",  9),
    "mono":    ("Consolas",  9),
    "kpi":     ("Segoe UI", 22, "bold"),
}


def apply_theme(root: tk.Tk):
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure("TFrame",       background=C["bg"])
    style.configure("TLabel",       background=C["bg"], foreground=C["text"], font=F["normal"])
    style.configure("TButton",      font=F["normal"], padding=6)
    style.configure("TEntry",       padding=4, font=F["normal"])
    style.configure("TCombobox",    padding=4, font=F["normal"])
    style.configure("TLabelframe",  background=C["bg"], foreground=C["text"])
    style.configure("TLabelframe.Label", font=F["heading"], foreground=C["primary"])

    # Notebook (tabs)
    style.configure("TNotebook",           background=C["bg"], borderwidth=0)
    style.configure("TNotebook.Tab",       font=F["normal"], padding=(12, 6))
    style.map("TNotebook.Tab",
              background=[("selected", C["primary"]), ("!selected", C["sidebar"])],
              foreground=[("selected", C["white"]),   ("!selected", "#AABDD4")])

    # Treeview
    style.configure("Treeview",
                    background=C["white"], foreground=C["text"],
                    rowheight=26, font=F["normal"], fieldbackground=C["white"])
    style.configure("Treeview.Heading",
                    background=C["sidebar"], foreground=C["white"],
                    font=F["heading"], relief="flat")
    style.map("Treeview",
              background=[("selected", C["row_sel"])],
              foreground=[("selected", C["text"])])

    # Named button styles
    style.configure("Primary.TButton",
                    background=C["primary"], foreground=C["white"],
                    font=F["normal"], relief="flat")
    style.map("Primary.TButton",
              background=[("active", C["primary_dk"])])

    style.configure("Danger.TButton",
                    background=C["danger"], foreground=C["white"],
                    font=F["normal"], relief="flat")
    style.map("Danger.TButton",
              background=[("active", "#922B21")])

    style.configure("Success.TButton",
                    background=C["success"], foreground=C["white"],
                    font=F["normal"], relief="flat")
    style.map("Success.TButton",
              background=[("active", "#145A32")])

    style.configure("Sidebar.TFrame", background=C["sidebar"])
    style.configure("Card.TFrame",    background=C["white"],
                    relief="solid", borderwidth=1)


# ── Shared Widget Factories ───────────────────────────────────────────────────

def scrolled_tree(parent, columns: list[tuple], height: int = 14) -> ttk.Treeview:
    """Return a Treeview + scrollbars packed into parent."""
    frame = ttk.Frame(parent)
    frame.pack(fill="both", expand=True)

    col_ids = [c[0] for c in columns]
    tree = ttk.Treeview(frame, columns=col_ids, show="headings", height=height)

    vsb = ttk.Scrollbar(frame, orient="vertical",   command=tree.yview)
    hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    for cid, label, width in columns:
        tree.heading(cid, text=label)
        tree.column(cid, width=width, minwidth=50)

    tree.tag_configure("alt", background=C["row_alt"])

    vsb.pack(side="right",  fill="y")
    hsb.pack(side="bottom", fill="x")
    tree.pack(fill="both", expand=True)
    return tree


def populate_tree(tree: ttk.Treeview, rows, key_fn=None):
    """Clear and repopulate a Treeview. key_fn maps row → tuple of display values."""
    tree.delete(*tree.get_children())
    for i, row in enumerate(rows):
        vals = key_fn(row) if key_fn else tuple(row)
        tag = "alt" if i % 2 else ""
        tree.insert("", "end", iid=str(row["id"]), values=vals, tags=(tag,))


def labeled_entry(parent, label: str, row: int, col: int = 0,
                  width: int = 28, default: str = "") -> tk.StringVar:
    var = tk.StringVar(value=default)
    ttk.Label(parent, text=label).grid(row=row, column=col,   sticky="w",  padx=4, pady=3)
    ttk.Entry(parent, textvariable=var, width=width).grid(
        row=row, column=col+1, sticky="ew", padx=4, pady=3)
    return var


def labeled_combo(parent, label: str, row: int, values: list,
                  col: int = 0, default: str = "") -> tk.StringVar:
    var = tk.StringVar(value=default)
    ttk.Label(parent, text=label).grid(row=row, column=col,   sticky="w",  padx=4, pady=3)
    cb = ttk.Combobox(parent, textvariable=var, values=values, state="readonly", width=26)
    cb.grid(row=row, column=col+1, sticky="ew", padx=4, pady=3)
    return var


def form_dialog(parent, title: str, width: int = 480, height: int = 520) -> tk.Toplevel:
    dlg = tk.Toplevel(parent)
    dlg.title(title)
    dlg.geometry(f"{width}x{height}")
    dlg.resizable(False, False)
    dlg.configure(bg=C["bg"])
    dlg.grab_set()
    dlg.transient(parent)
    return dlg


def status_badge(text: str) -> str:
    badges = {
        "delivered":  "✓ Delivered",
        "in_transit": "→ In Transit",
        "pending":    "○ Pending",
        "delayed":    "⚠ Delayed",
        "returned":   "↩ Returned",
        "available":  "● Available",
        "in_use":     "▶ In Use",
        "maintenance":"⚙ Maintenance",
        "retired":    "✗ Retired",
        "on_route":   "▶ On Route",
        "off_duty":   "○ Off Duty",
        "suspended":  "✗ Suspended",
        "paid":       "✓ Paid",
        "overdue":    "⚠ Overdue",
    }
    return badges.get(text, text.title())
