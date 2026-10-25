import os
import tkinter
import tkinter.font as tkfont
from tkinter import ttk

import customtkinter
from PIL import Image

R_CARD, R_CTRL = 12, 8      # one corner radius for panels, one for controls

COLOR_THEME_NAMIN = {
    "bg": ("#EDF0F5", "#0D1522"), "card": ("#FFFFFF", "#141E30"), "inset": ("#F3F5F9", "#1A2640"),
    "input": ("#FFFFFF", "#0F1A2C"), "border": ("#D8DEE8", "#243049"),
    "text": ("#14203A", "#E5EAF3"), "muted": ("#5A6781", "#8C99B3"),
    "accent": ("#0F766E", "#1F8F86"), "accent_hover": ("#0B5E58", "#26A79D"),
    "accent_soft": ("#DDF1EF", "#17383A"), "accent_text": ("#0B5E58", "#5FD0C6"), "on_accent": ("#FFFFFF", "#FFFFFF"),
    "neutral": ("#E6EAF1", "#212E49"), "neutral_hover": ("#D8DEE9", "#2B3A59"),
    "seg_bg": ("#E3E8F0", "#1A2640"), "seg_sel": ("#FFFFFF", "#2D4168"),
    "side": ("#0F1B2E", "#0A111D"), "side_text": ("#E6EBF4", "#E6EBF4"), "side_muted": ("#93A1BC", "#7F8DA8"),
    "side_hover": ("#1B2A44", "#152033"), "side_danger": ("#FF8A80", "#FF8A80"), "side_danger_bg": ("#2B1A22", "#2B1A22"), "side_accent": ("#5FD0C6", "#5FD0C6"), "side_active": ("#16433F", "#163C3C"), "side_border": ("#22324F", "#1A2640"),
    "danger": ("#B42318", "#F0766B"), "danger_bg": ("#FDECEA", "#2F1B21"),
    "danger_solid": ("#B42318", "#B93A31"), "danger_hover": ("#912018", "#9E2F27"),
    "warn": ("#B45309", "#E3A445"), "warn_bg": ("#FDF1DC", "#2C2315"),
    "orange": ("#C2410C", "#F08A4B"), "orange_bg": ("#FDEBDD", "#33200F"),
    "yellow": ("#A16207", "#F2D14B"), "yellow_bg": ("#FEF6CF", "#2E2A10"),
    "ok": ("#15803D", "#52C08A"), "ok_bg": ("#E3F4E9", "#14281F"),
    "info": ("#1D4ED8", "#7BA3F0"), "info_bg": ("#E6EDFC", "#17233C"),
}
TONES = {"danger": ("danger_bg", "danger"), "warn": ("warn_bg", "warn"), "ok": ("ok_bg", "ok"),
         "info": ("info_bg", "info"), "neutral": ("neutral", "muted"), "accent": ("accent_soft", "accent_text"),
         "orange": ("orange_bg", "orange"), "yellow": ("yellow_bg", "yellow")}

# Flood table rows: critical = red, warning = orange, alert = yellow, normal/safe = green
FLOOD_ROW_TAGS = {"critical": ("danger_bg", "danger"), "warning": ("orange_bg", "orange"),
                  "alert": ("yellow_bg", "yellow"), "normal": ("ok_bg", "ok")}
FLOOD_TONES = {"critical": "danger", "warning": "orange", "alert": "yellow", "normal": "ok"}


def flood_tag(alert_level):
    """'critical' / 'warning' / 'alert' / 'normal' for an alert-level string."""
    level = alert_level.lower()
    return next((key for key in FLOOD_TONES if key in level), "")

# name: (font role, base size, weight)
_FONT_SPECS = {
    "display": ("head", 26, "bold"), "metric": ("head", 28, "bold"), "title": ("head", 20, "bold"),
    "heading": ("head", 15, "bold"), "body": ("body", 13, "normal"), "bodybold": ("body", 13, "bold"),
    "label": ("body", 12, "bold"), "small": ("body", 11, "normal"), "smallbold": ("body", 11, "bold"),
    "mono": ("mono", 20, "bold"),
}
_FAMILIES = {"head": ["Bahnschrift SemiBold", "Segoe UI Semibold", "Segoe UI", "Helvetica"],
             "body": ["Segoe UI", "Helvetica", "Arial"],
             "mono": ["Cascadia Mono", "Consolas", "Courier New"]}

FONTS = {}
_state = {"dark": True, "scale": 1.0}     # survives logout/login, so the user's choices stay
_listeners = []


def is_dark():
    return _state["dark"]


def text_scale():
    return _state["scale"]


def pick(pair):
    """Light or dark member of a colour pair (for ttk widgets that cannot take pairs)."""
    return pair[1] if _state["dark"] else pair[0]


# ── Theme, fonts, ttk styling ──────────────────────────────────────────────
def scaled_size(base):
    return max(10, round(base * _state["scale"]))


def setup(root):
    """Call once right after creating a CTk window."""
    _listeners.clear()
    customtkinter.set_appearance_mode("dark" if _state["dark"] else "light")
    available = set(tkfont.families(root))
    FONTS.clear()
    for name, (role, size, weight) in _FONT_SPECS.items():
        family = next((f for f in _FAMILIES[role] if f in available), _FAMILIES[role][-1])
        FONTS[name] = customtkinter.CTkFont(family=family, size=scaled_size(size), weight=weight)
    ttk.Style().theme_use("clam")
    style_ttk()
    root.configure(fg_color=COLOR_THEME_NAMIN["bg"])


def style_ttk():
    s, p = ttk.Style(), pick
    s.configure("W.Treeview", background=p(COLOR_THEME_NAMIN["card"]), fieldbackground=p(COLOR_THEME_NAMIN["card"]), foreground=p(COLOR_THEME_NAMIN["text"]),
                borderwidth=0, rowheight=max(30, round(34 * _state["scale"])), font=FONTS["body"])
    s.layout("W.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    s.map("W.Treeview", background=[("selected", p(COLOR_THEME_NAMIN["accent_soft"]))], foreground=[("selected", p(COLOR_THEME_NAMIN["text"]))])
    s.configure("W.Treeview.Heading", background=p(COLOR_THEME_NAMIN["inset"]), foreground=p(COLOR_THEME_NAMIN["muted"]), font=FONTS["smallbold"],
                relief="flat", borderwidth=0, padding=(10, 8))
    s.map("W.Treeview.Heading", background=[("active", p(COLOR_THEME_NAMIN["neutral"]))])
    s.configure("Vertical.TScrollbar", background=p(COLOR_THEME_NAMIN["neutral"]), troughcolor=p(COLOR_THEME_NAMIN["card"]), bordercolor=p(COLOR_THEME_NAMIN["card"]),
                arrowcolor=p(COLOR_THEME_NAMIN["muted"]), relief="flat", arrowsize=12)
    s.map("Vertical.TScrollbar", background=[("active", p(COLOR_THEME_NAMIN["neutral_hover"]))])


def notify():
    for fn in list(_listeners):
        fn()


def set_dark(flag):
    _state["dark"] = flag
    customtkinter.set_appearance_mode("dark" if flag else "light")
    style_ttk()
    notify()


def toggle_dark():
    set_dark(not _state["dark"])


def set_text_scale(value):
    _state["scale"] = value
    for name, (_, size, _w) in _FONT_SPECS.items():
        FONTS[name].configure(size=scaled_size(size))
    style_ttk()
    notify()


def on_theme_change(fn):
    _listeners.append(fn)


# ── Widget factories ───────────────────────────────────────────────────────
def card(parent, **kw):
    kw.setdefault("fg_color", COLOR_THEME_NAMIN["card"])
    return customtkinter.CTkFrame(parent, border_width=1, border_color=COLOR_THEME_NAMIN["border"], corner_radius=R_CARD, **kw)


def inset(parent, **kw):
    kw.setdefault("fg_color", COLOR_THEME_NAMIN["inset"])
    return customtkinter.CTkFrame(parent, corner_radius=R_CTRL, **kw)


def row(parent, **kw):
    return customtkinter.CTkFrame(parent, fg_color="transparent", **kw)


def divider(parent, color="border"):
    return customtkinter.CTkFrame(parent, fg_color=COLOR_THEME_NAMIN[color], width=1, height=1, corner_radius=0)


def label(parent, text="", font="body", color="text", **kw):
    return customtkinter.CTkLabel(parent, text=text, font=FONTS[font], text_color=COLOR_THEME_NAMIN[color], **kw)


_BUTTONS = {
    "primary": dict(fg_color=COLOR_THEME_NAMIN["accent"], hover_color=COLOR_THEME_NAMIN["accent_hover"], text_color=COLOR_THEME_NAMIN["on_accent"]),
    "secondary": dict(fg_color=COLOR_THEME_NAMIN["neutral"], hover_color=COLOR_THEME_NAMIN["neutral_hover"], text_color=COLOR_THEME_NAMIN["text"]),
    "danger": dict(fg_color=COLOR_THEME_NAMIN["danger_solid"], hover_color=COLOR_THEME_NAMIN["danger_hover"], text_color="#FFFFFF"),
    "ghost": dict(fg_color="transparent", hover_color=COLOR_THEME_NAMIN["neutral"], text_color=COLOR_THEME_NAMIN["text"], border_width=1,
                  border_color=COLOR_THEME_NAMIN["border"]),
    "link": dict(fg_color="transparent", hover_color=COLOR_THEME_NAMIN["accent_soft"], text_color=COLOR_THEME_NAMIN["accent_text"]),
    "nav": dict(fg_color="transparent", hover_color=COLOR_THEME_NAMIN["side_hover"], text_color="#FFFFFF"),
    "nav_active": dict(fg_color=COLOR_THEME_NAMIN["side_active"], hover_color=COLOR_THEME_NAMIN["side_active"], text_color="#FFFFFF"),
}


def button(parent, text, command=None, kind="primary", font="bodybold", height=38, **kw):
    return customtkinter.CTkButton(parent, text=text, command=command, font=FONTS[font], height=height,
                                   corner_radius=R_CTRL, **{**_BUTTONS[kind], **kw})


def restyle(button_widget, kind):
    """Switch an existing button to another kind (e.g. nav <-> nav_active)."""
    button_widget.configure(**_BUTTONS[kind])


def entry(parent, placeholder="", height=38, **kw):
    opts = dict(placeholder_text=placeholder, font=FONTS["body"], height=height, fg_color=COLOR_THEME_NAMIN["input"],
                border_color=COLOR_THEME_NAMIN["border"], border_width=1, text_color=COLOR_THEME_NAMIN["text"], placeholder_text_color=COLOR_THEME_NAMIN["muted"],
                corner_radius=R_CTRL)
    return customtkinter.CTkEntry(parent, **{**opts, **kw})


def combo(parent, values, default=None, height=38, **kw):
    box = customtkinter.CTkComboBox(
        parent, values=list(values), font=FONTS["body"], dropdown_font=FONTS["body"], height=height, state="readonly",
        fg_color=COLOR_THEME_NAMIN["input"], border_color=COLOR_THEME_NAMIN["border"], border_width=1, text_color=COLOR_THEME_NAMIN["text"],
        button_color=COLOR_THEME_NAMIN["neutral"], button_hover_color=COLOR_THEME_NAMIN["neutral_hover"], dropdown_fg_color=COLOR_THEME_NAMIN["card"],
        dropdown_text_color=COLOR_THEME_NAMIN["text"], dropdown_hover_color=COLOR_THEME_NAMIN["neutral"], corner_radius=R_CTRL, **kw)
    box.set(default if default is not None else (list(values)[0] if values else ""))
    return box


def field(parent, text, kind="entry", values=None, default=None, placeholder="", show=None, pady=(0, 10), height=38, command=None, **kw):
    """Label above an entry or dropdown; returns the input widget."""
    label(parent, text, "label", "muted", anchor="w").pack(fill="x", pady=(0, 4))
    if kind == "combo":
        combo_kw = dict(kw)
        if command:
            combo_kw["command"] = command
        widget = combo(parent, values, default, height=height, **combo_kw)
    else:
        entry_kw = dict(kw)
        if show:
            entry_kw["show"] = show
        widget = entry(parent, placeholder, height=height, **entry_kw)
    widget.pack(fill="x", pady=pady)
    return widget


def segmented(parent, values, command, current, **kw):
    seg = customtkinter.CTkSegmentedButton(
        parent, values=list(values), command=command, font=FONTS["smallbold"], fg_color=COLOR_THEME_NAMIN["seg_bg"],
        selected_color=COLOR_THEME_NAMIN["seg_sel"], selected_hover_color=COLOR_THEME_NAMIN["seg_sel"], unselected_color=COLOR_THEME_NAMIN["seg_bg"],
        unselected_hover_color=COLOR_THEME_NAMIN["neutral_hover"], text_color=COLOR_THEME_NAMIN["text"], corner_radius=R_CTRL, **kw)
    seg.set(current)
    return seg


def pill(parent, text, tone="neutral", font="smallbold"):
    bg, fg = TONES[tone]
    return customtkinter.CTkLabel(parent, text=f"  {text}  ", font=FONTS[font], fg_color=COLOR_THEME_NAMIN[bg], text_color=COLOR_THEME_NAMIN[fg],
                                  corner_radius=6, height=24)


def metric(parent, title, value="0", tone="text"):
    """Compact KPI tile. Returns the value label so callers can update it."""
    tile = inset(parent)
    label(tile, title, "small", "muted", anchor="w").pack(fill="x", padx=14, pady=(10, 0))
    value_label = label(tile, value, "metric", tone, anchor="w")
    value_label.pack(fill="x", padx=14, pady=(0, 10))
    return tile, value_label


def set_text(widget, value):
    widget.delete(0, "end")
    widget.insert(0, str(value))


# ── Treeview ───────────────────────────────────────────────────────────────
def make_tree(parent, columns):
    """columns: [(key, heading, width, anchor)]. Packs a themed Treeview plus scrollbar into parent."""
    tree = ttk.Treeview(parent, columns=[c[0] for c in columns], show="headings", style="W.Treeview", selectmode="browse")
    widest = max(columns, key=lambda c: c[2])[0]      # only the widest column absorbs extra space
    for key, heading, width, anchor in columns:
        tree.heading(key, text=heading, anchor=anchor)
        tree.column(key, width=width, minwidth=40, anchor=anchor, stretch=(key == widest))
    bar = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=bar.set)
    bar.pack(side="right", fill="y", padx=(0, 2), pady=2)
    tree.pack(side="left", fill="both", expand=True, padx=2, pady=2)
    return tree


def style_tags(tree, tags):
    """tags: {tag: (background key, foreground key)}; colours follow light/dark automatically."""
    def apply():
        try:
            for name, (bg, fg) in tags.items():
                tree.tag_configure(name, background=pick(COLOR_THEME_NAMIN[bg]), foreground=pick(COLOR_THEME_NAMIN[fg]))
        except tkinter.TclError:
            pass
    apply()
    _listeners.append(apply)


# ── Windows & images ───────────────────────────────────────────────────────
def asset(filename):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)


def logo_image(filename, size):
    """Transparent PNG as CTkImage, or None when the file is missing."""
    try:
        img = Image.open(asset(filename)).convert("RGBA")
        return customtkinter.CTkImage(light_image=img, dark_image=img, size=size)
    except Exception:
        return None


def set_app_icon(window):
    try:
        ico, png = asset("wildcare_logo.ico"), asset("wildcare_logo.png")
        if not os.path.exists(ico) and os.path.exists(png):
            Image.open(png).save(ico, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128)])
        if os.path.exists(ico):
            window.iconbitmap(ico)
    except Exception:
        pass


def place_window(window, width, height, min_size=None):
    """Size, centre on screen and set the icon (after CustomTkinter's own icon is applied)."""
    window.geometry(f"{width}x{height}")
    if min_size:
        window.minsize(*min_size)
    window.update_idletasks()
    x = max(0, (window.winfo_screenwidth() - window.winfo_width()) // 2)
    y = max(0, (window.winfo_screenheight() - window.winfo_height()) // 3)
    window.geometry(f"+{x}+{y}")
    window.after(300, lambda: set_app_icon(window))


def modal(root, title, width, height):
    """Dialog centred over `root`; returns the CTkToplevel."""
    top = customtkinter.CTkToplevel(root)
    top.title(title)
    top.configure(fg_color=COLOR_THEME_NAMIN["bg"])
    top.geometry(f"{width}x{height}")
    top.resizable(False, False)
    top.transient(root)
    top.update_idletasks()
    x = root.winfo_rootx() + (root.winfo_width() - top.winfo_width()) // 2
    y = root.winfo_rooty() + (root.winfo_height() - top.winfo_height()) // 3
    top.geometry(f"+{max(0, x)}+{max(0, y)}")

    def focus():
        try:
            top.lift()
            top.focus_force()
            top.grab_set()
        except tkinter.TclError:
            pass
    top.after(150, focus)
    top.after(300, lambda: set_app_icon(top))
    return top


def text_size_control(parent, on_change=None):
    """'A A A' selector shared by every window."""
    labels = {"A-": 0.9, "A": 1.10, "A+": 2.00}
    current = min(labels, key=lambda k: abs(labels[k] - _state["scale"]))

    def changed(choice):
        set_text_scale(labels[choice])
        if on_change:
            on_change()
    return segmented(parent, list(labels), changed, current, width=120)