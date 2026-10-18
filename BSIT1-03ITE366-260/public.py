import os
import sys
import csv
from datetime import date, datetime
import customtkinter
from tkinter import ttk, messagebox, filedialog
from PIL import Image
import group4database

# ── Logo helpers (images must sit in the same folder as this file) ──────────
def _logo_image(filename, size):
    """Loads a transparent PNG logo as a CTkImage. Returns None if missing."""
    try:
        folder = os.path.dirname(os.path.abspath(__file__))
        img = Image.open(os.path.join(folder, filename)).convert("RGBA")
        return customtkinter.CTkImage(light_image=img, dark_image=img, size=size)
    except Exception:
        return None

def _set_app_icon(window):
    """Sets the window title-bar icon using wildcare_logo.png."""
    try:
        folder = os.path.dirname(os.path.abspath(__file__))
        ico_path = os.path.join(folder, "wildcare_logo.ico")
        png_path = os.path.join(folder, "wildcare_logo.png")
        if not os.path.exists(ico_path) and os.path.exists(png_path):
            try:
                img = Image.open(png_path)
                img.save(ico_path, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128)])
            except Exception:
                pass
        if os.path.exists(ico_path):
            window.iconbitmap(ico_path)
        elif os.path.exists(png_path):
            from PIL import ImageTk
            photo = ImageTk.PhotoImage(file=png_path)
            window.iconphoto(False, photo)
    except Exception:
        pass


LT_BG       = "#F3F4F6"
LT_CARD     = "#FFFFFF"
LT_SIDEBAR  = "#E5E7EB"
LT_TEXT     = "#111827"
LT_MUTED    = "#4B5563"
LT_ENTRY    = "#F9FAFB"
LT_BORDER   = "#D1D5DB"
LT_BTN_PRI  = "#1F2937"
LT_BTN_HVR  = "#374151"
LT_BTN_PRI_T= "#FFFFFF"
LT_BTN_SEC  = "#E5E7EB"
LT_BTN_SECH = "#D1D5DB"
LT_TREE_BG  = "#FFFFFF"
LT_TREE_FG  = "#111827"
LT_TREE_SEL = "#E5E7EB"
LT_HEADER   = "#F3F4F6"

DK_BG       = "#111827"
DK_CARD     = "#1F2937"
DK_SIDEBAR  = "#182234"
DK_TEXT     = "#F9FAFB"
DK_MUTED    = "#9CA3AF"
DK_ENTRY    = "#111827"
DK_BORDER   = "#374151"
DK_BTN_PRI  = "#F9FAFB"
DK_BTN_HVR  = "#E5E7EB"
DK_BTN_PRI_T= "#111827"
DK_BTN_SEC  = "#374151"
DK_BTN_SECH = "#4B5563"
DK_TREE_BG  = "#1F2937"
DK_TREE_FG  = "#F9FAFB"
DK_TREE_SEL = "#374151"
DK_HEADER   = "#182234"

# Status colors with icons and words
COLOR_DANGER  = "#DC2626"  
COLOR_WARNING = "#EA580C"  
COLOR_ALERT   = "#CA8A04"  
COLOR_SUCCESS = "#16A34A"  
COLOR_INFO    = "#2563EB"  


class PatientPortalWindow:
    def __init__(self, user_info, on_logout_callback):
        self.user_info = user_info
        self.on_logout_callback = on_logout_callback
        self.current_page = "flood"  # "flood", "report", "watch"
        self.selected_flood_record = None
        self._is_dark = True
        self._font_scale = 1.0  # Scaler: 0.9 = Small, 1.0 = Normal, 1.15 = Large
        self._search_timer = None
        self._refresh_timer = None

        # Selected symptom chips for report form
        self.selected_symptoms = set(["Fever", "Muscle pain"])

        # Main window setup (1100 px wide)
        self.root = customtkinter.CTk()
        self.root.title("W.I.L.D. CARE — Resident Portal")
        self.root.after(300, lambda: _set_app_icon(self.root))
        
        window_w = 1100
        window_h = 740
        self.root.geometry(f"{window_w}x{window_h}")
        self.root.minsize(1050, 680)
        self.root.configure(fg_color=DK_BG if self._is_dark else LT_BG)

        # Center on screen
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = max(0, (sw - window_w) // 2)
        y = max(0, (sh - window_h) // 2)
        self.root.geometry(f"{window_w}x{window_h}+{x}+{y}")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self._apply_mode()
    
        self._configure_treeview_styles()

        # Build main layout: Permanent Sidebar on Left + Dynamic Content on Right
        self._build_sidebar()
        self._build_content_area()

        # Load initial data
        self.navigate_to("flood")
        self._schedule_auto_refresh()

    def _apply_mode(self):
        mode = "dark" if self._is_dark else "light"
        customtkinter.set_appearance_mode(mode)
        self.root.configure(fg_color=DK_BG if self._is_dark else LT_BG)

    def _t(self, dark_val, light_val):
        return dark_val if self._is_dark else light_val

    def _f(self, base_size, weight="normal"):
        scaled = max(11, int(round(base_size * self._font_scale)))
        return ("Segoe UI", scaled, weight)

    def _set_font_scale(self, scale_val):
        self._font_scale = scale_val
        self._configure_treeview_styles()
        self._rebuild_sidebar()
        self._render_current_page()

    def _toggle_theme(self):
        self._is_dark = not self._is_dark
        self._apply_mode()
        self._configure_treeview_styles()
        self._rebuild_sidebar()
        self._render_current_page()

    def _configure_treeview_styles(self):
        tree_bg  = self._t(DK_TREE_BG, LT_TREE_BG)
        tree_fg  = self._t(DK_TREE_FG, LT_TREE_FG)
        tree_sel = self._t(DK_TREE_SEL, LT_TREE_SEL)
        hdr_bg   = self._t(DK_HEADER, LT_HEADER)
        hdr_fg   = self._t(DK_TEXT, LT_TEXT)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Resident.Treeview",
            background=tree_bg, foreground=tree_fg, fieldbackground=tree_bg,
            font=self._f(13), rowheight=36, borderwidth=0
        )
        style.configure(
            "Resident.Treeview.Heading",
            background=hdr_bg, foreground=hdr_fg,
            font=self._f(13, "bold"), borderwidth=0, relief="flat"
        )
        style.map("Resident.Treeview", background=[("selected", tree_sel)], foreground=[("selected", hdr_fg)])

    def _schedule_auto_refresh(self):
        if self._refresh_timer:
            try:
                self.root.after_cancel(self._refresh_timer)
            except Exception:
                pass
        self._refresh_timer = self.root.after(30000, self._on_auto_refresh_tick)

    def _on_auto_refresh_tick(self):
        if self.current_page == "flood":
            self.load_flood_records()
        elif self.current_page == "report":
            self.load_my_cases()
        elif self.current_page == "watch":
            self.load_disease_watch()
        self._schedule_auto_refresh()

    def on_close(self):
        if self._search_timer:
            try:
                self.root.after_cancel(self._search_timer)
            except Exception:
                pass
        if self._refresh_timer:
            try:
                self.root.after_cancel(self._refresh_timer)
            except Exception:
                pass
        try:
            self.root.destroy()
        except Exception:
            pass
        sys.exit(0)

    # FIXED UNIFIED SIDEBAR 

    def _build_sidebar(self):
        self.sidebar_frame = customtkinter.CTkFrame(
            self.root,
            fg_color=self._t(DK_SIDEBAR, LT_SIDEBAR),
            corner_radius=16,
            border_width=1,
            border_color=self._t(DK_BORDER, LT_BORDER),
            width=270
        )
        self.sidebar_frame.place(x=12, y=12, relheight=0.965)
        self._populate_sidebar()

    def _rebuild_sidebar(self):
        for w in self.sidebar_frame.winfo_children():
            try:
                w.destroy()
            except Exception:
                pass
        self.sidebar_frame.configure(
            fg_color=self._t(DK_SIDEBAR, LT_SIDEBAR),
            border_color=self._t(DK_BORDER, LT_BORDER)
        )
        self._populate_sidebar()

    def _populate_sidebar(self):
        t_col  = self._t(DK_TEXT, LT_TEXT)
        muted  = self._t(DK_MUTED, LT_MUTED)
        pri    = self._t(DK_BTN_PRI, LT_BTN_PRI)
        pri_h  = self._t(DK_BTN_HVR, LT_BTN_HVR)
        pri_tc = self._t(DK_BTN_PRI_T, LT_BTN_PRI_T)
        sec    = self._t(DK_BTN_SEC, LT_BTN_SEC)
        sec_h  = self._t(DK_BTN_SECH, LT_BTN_SECH)

        # 1. Branding Header
        brand_box = customtkinter.CTkFrame(self.sidebar_frame, fg_color="transparent")
        brand_box.pack(fill="x", padx=14, pady=(18, 10))
        self.logo_img = _logo_image("wildcare_logo_shield.png", (40, 45))
        if self.logo_img:
            logo_tile = customtkinter.CTkFrame(brand_box, fg_color="#FFFFFF", corner_radius=12)
            logo_tile.pack(anchor="w", pady=(0, 8))
            customtkinter.CTkLabel(logo_tile, text="", image=self.logo_img).pack(padx=8, pady=6)
        customtkinter.CTkLabel(
            brand_box, text="W.I.L.D. CARE" if self.logo_img else "🌊 W.I.L.D. CARE",
            font=self._f(20, "bold"), text_color=t_col, anchor="w"
        ).pack(anchor="w")
        customtkinter.CTkLabel(
            brand_box, text="Resident Health & Flood Portal",
            font=self._f(12), text_color=muted, anchor="w"
        ).pack(anchor="w")

        # 2. Personalized Greeting Box
        full_name = self.user_info.get("full_name", "Resident")
        greet_box = customtkinter.CTkFrame(
            self.sidebar_frame,
            fg_color=self._t("#212D40", "#F0F2F5"),
            corner_radius=12
        )
        greet_box.pack(fill="x", padx=12, pady=(0, 16))
        customtkinter.CTkLabel(
            greet_box, text="Good day,",
            font=self._f(12), text_color=muted, anchor="w"
        ).pack(padx=12, pady=(10, 0), anchor="w")
        customtkinter.CTkLabel(
            greet_box, text=f"{full_name}",
            font=self._f(15, "bold"), text_color=t_col, anchor="w", wraplength=230, justify="left"
        ).pack(padx=12, pady=(0, 10), anchor="w")

        # 3. Main Navigation Menu (Big buttons 52 px)
        nav_box = customtkinter.CTkFrame(self.sidebar_frame, fg_color="transparent")
        nav_box.pack(fill="x", padx=12, pady=(0, 10))

        self.nav_buttons = {}
        pages = [
            ("flood", "🌊  Flood monitor"),
            ("report", "📝  Report illness"),
            ("watch", "📊  Disease Watch")
        ]
        for key, label in pages:
            is_active = (self.current_page == key)
            btn = customtkinter.CTkButton(
                nav_box, text=label,
                font=self._f(15, "bold" if is_active else "normal"),
                fg_color=pri if is_active else "transparent",
                hover_color=pri_h if is_active else sec_h,
                text_color=pri_tc if is_active else t_col,
                height=52, corner_radius=12, anchor="w",
                command=lambda k=key: self.navigate_to(k)
            )
            btn.pack(fill="x", pady=4)
            self.nav_buttons[key] = btn

        # 4. Emergency & Quick Help Banner
        help_card = customtkinter.CTkFrame(
            self.sidebar_frame,
            fg_color=self._t("#2A1E1E", "#FEF2F2"),
            border_width=1,
            border_color="#FCA5A5",
            corner_radius=10
        )
        help_card.pack(fill="x", padx=12, pady=(10, 0))
        customtkinter.CTkLabel(
            help_card, text="🛡 Need Urgent Help?",
            font=self._f(13, "bold"), text_color=COLOR_DANGER, anchor="w"
        ).pack(padx=10, pady=(8, 2), anchor="w")
        customtkinter.CTkLabel(
            help_card,
            text="Call Barangay Health Station or 911 immediately if fever or vomiting is severe.",
            font=self._f(11), text_color=t_col, wraplength=220, justify="left"
        ).pack(padx=10, pady=(0, 6), anchor="w")
        customtkinter.CTkButton(
            help_card, text="View Emergency Numbers",
            font=self._f(11, "bold"),
            fg_color="transparent", hover_color=self._t("#3B2323", "#FEE2E2"),
            text_color=COLOR_DANGER, height=26,
            command=self.show_emergency_hotlines
        ).pack(padx=10, pady=(0, 8), anchor="w")

        # 5. Bottom Controls (Text Size Scaler, Theme, Logout)
        btm_box = customtkinter.CTkFrame(self.sidebar_frame, fg_color="transparent")
        btm_box.pack(side="bottom", fill="x", padx=12, pady=14)

        # Text size row: Text size: A A A
        ts_row = customtkinter.CTkFrame(btm_box, fg_color="transparent")
        ts_row.pack(fill="x", pady=(0, 10))
        customtkinter.CTkLabel(
            ts_row, text="Text size:", font=self._f(12, "bold"), text_color=muted
        ).pack(side="left")

        for lbl, scale in [("A", 0.9), ("A", 1.0), ("A", 1.18)]:
            is_active = (abs(self._font_scale - scale) < 0.05)
            customtkinter.CTkButton(
                ts_row, text=lbl,
                font=("Segoe UI", 11 if scale == 0.9 else (13 if scale == 1.0 else 16), "bold"),
                fg_color=pri if is_active else sec,
                hover_color=pri_h if is_active else sec_h,
                text_color=pri_tc if is_active else t_col,
                width=32, height=28, corner_radius=6,
                command=lambda s=scale: self._set_font_scale(s)
            ).pack(side="left", padx=2)

        # Theme toggle
        theme_txt = "☀ Light Mode" if self._is_dark else "🌙 Dark Mode"
        customtkinter.CTkButton(
            btm_box, text=theme_txt,
            font=self._f(12),
            fg_color=sec, hover_color=sec_h, text_color=t_col,
            height=34, corner_radius=10,
            command=self._toggle_theme
        ).pack(fill="x", pady=(0, 8))

        # Logout Button (Big and distinct)
        customtkinter.CTkButton(
            btm_box, text="Log out",
            font=self._f(14, "bold"),
            fg_color=COLOR_DANGER, hover_color="#B91C1C", text_color="#FFFFFF",
            height=46, corner_radius=10,
            command=self.handle_logout
        ).pack(fill="x")

    def _build_content_area(self):
        self.content_frame = customtkinter.CTkFrame(
            self.root,
            fg_color=self._t(DK_CARD, LT_CARD),
            corner_radius=16,
            border_width=1,
            border_color=self._t(DK_BORDER, LT_BORDER)
        )
        self.content_frame.place(x=294, y=12, relwidth=0.718, relheight=0.965)

    def navigate_to(self, page_name):
        self.current_page = page_name
        self._rebuild_sidebar()
        self._render_current_page()

    def _render_current_page(self):
        for w in self.content_frame.winfo_children():
            try:
                w.destroy()
            except Exception:
                pass

        if self.current_page == "flood":
            self._build_flood_monitor_view()
        elif self.current_page == "report":
            self._build_report_illness_view()
        elif self.current_page == "watch":
            self._build_disease_watch_view()

    # WINDOW 2: RESIDENT PORTAL — FLOOD MONITOR & GAUGE

    def _build_flood_monitor_view(self):
        t_col  = self._t(DK_TEXT, LT_TEXT)
        muted  = self._t(DK_MUTED, LT_MUTED)
        border = self._t(DK_BORDER, LT_BORDER)

        pad_box = customtkinter.CTkFrame(self.content_frame, fg_color="transparent")
        pad_box.pack(fill="both", expand=True, padx=20, pady=16)

        # Header Title
        customtkinter.CTkLabel(
            pad_box, text="Live flood levels for Pangasinan",
            font=self._f(22, "bold"), text_color=t_col, anchor="w"
        ).pack(fill="x", pady=(0, 6))

        # Advisory Alert Banner (Color + icon + plain words)
        self.banner_frame = customtkinter.CTkFrame(
            pad_box, fg_color=self._t("#382314", "#FEF3C7"),
            border_width=1, border_color=COLOR_WARNING, corner_radius=10
        )
        self.banner_frame.pack(fill="x", pady=(0, 14))

        b_inner = customtkinter.CTkFrame(self.banner_frame, fg_color="transparent")
        b_inner.pack(fill="x", padx=14, pady=10)

        customtkinter.CTkLabel(
            b_inner, text="⚠️", font=("Segoe UI", 24)
        ).pack(side="left", padx=(0, 10))

        b_txt = customtkinter.CTkFrame(b_inner, fg_color="transparent")
        b_txt.pack(side="left", fill="both", expand=True)

        customtkinter.CTkLabel(
            b_txt, text="Heavy rain: be careful. Do not walk in floodwater.",
            font=self._f(14, "bold"), text_color=self._t("#FDBA74", "#92400E"), anchor="w"
        ).pack(anchor="w")
        customtkinter.CTkLabel(
            b_txt, text="Leptospirosis bacteria spread rapidly in dirty water. Keep children away from puddles.",
            font=self._f(12), text_color=t_col, anchor="w"
        ).pack(anchor="w")

        # Two-Column Sub-Layout: Left Table / Right Selected Card & Gauge
        cols_frame = customtkinter.CTkFrame(pad_box, fg_color="transparent")
        cols_frame.pack(fill="both", expand=True)
        cols_frame.columnconfigure(0, weight=3)
        cols_frame.columnconfigure(1, weight=2)
        cols_frame.rowconfigure(0, weight=1)

        # ── LEFT SUB-COLUMN: "Pick your barangay" Table ──────────────────────
        left_sub = customtkinter.CTkFrame(cols_frame, fg_color="transparent")
        left_sub.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        sub_hdr = customtkinter.CTkFrame(left_sub, fg_color="transparent")
        sub_hdr.pack(fill="x", pady=(0, 6))
        customtkinter.CTkLabel(
            sub_hdr, text="Pick your barangay",
            font=self._f(16, "bold"), text_color=t_col, anchor="w"
        ).pack(side="left")

        # Search bar
        self.entry_flood_search = customtkinter.CTkEntry(
            sub_hdr, placeholder_text="🔍 Filter barangay...",
            font=self._f(12), height=34, width=160,
            fg_color=self._t(DK_ENTRY, LT_ENTRY),
            border_color=border, text_color=t_col, corner_radius=8
        )
        self.entry_flood_search.pack(side="right")
        self.entry_flood_search.bind("<KeyRelease>", self._on_flood_search_change)

        # Flood Table (Barangay | Water | Alert)
        tbl_container = customtkinter.CTkFrame(left_sub, fg_color="transparent")
        tbl_container.pack(fill="both", expand=True)

        columns = ("barangay", "water", "alert")
        self.flood_tree = ttk.Treeview(
            tbl_container,
            columns=columns,
            show="headings",
            style="Resident.Treeview",
            selectmode="browse"
        )
        self.flood_tree.heading("barangay", text="Barangay", anchor="w")
        self.flood_tree.heading("water", text="Water", anchor="center")
        self.flood_tree.heading("alert", text="Alert", anchor="center")

        self.flood_tree.column("barangay", width=180, anchor="w")
        self.flood_tree.column("water", width=90, anchor="center")
        self.flood_tree.column("alert", width=110, anchor="center")

        v_scroll = ttk.Scrollbar(tbl_container, orient="vertical", command=self.flood_tree.yview)
        self.flood_tree.configure(yscrollcommand=v_scroll.set)

        self.flood_tree.pack(side="left", fill="both", expand=True)
        v_scroll.pack(side="right", fill="y")
        self.flood_tree.bind("<<TreeviewSelect>>", self._on_flood_row_selected)

        # ── RIGHT SUB-COLUMN: Card + Physical Depth Gauge ────────────────────
        right_sub = customtkinter.CTkFrame(
            cols_frame,
            fg_color=self._t("#182234", "#F9FAFB"),
            corner_radius=14,
            border_width=1,
            border_color=border
        )
        right_sub.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        self.right_sub_container = customtkinter.CTkFrame(right_sub, fg_color="transparent")
        self.right_sub_container.pack(fill="both", expand=True, padx=16, pady=16)

        # Selected Barangay Card Content
        self.lbl_card_brgy = customtkinter.CTkLabel(
            self.right_sub_container, text="Pantal, Dagupan",
            font=self._f(20, "bold"), text_color=t_col, anchor="w"
        )
        self.lbl_card_brgy.pack(fill="x", pady=(0, 2))

        self.lbl_card_depth = customtkinter.CTkLabel(
            self.right_sub_container, text="0.70 m",
            font=("Segoe UI", 34, "bold"), text_color=COLOR_WARNING, anchor="w"
        )
        self.lbl_card_depth.pack(fill="x", pady=(0, 2))

        self.lbl_card_cond = customtkinter.CTkLabel(
            self.right_sub_container, text="Knee deep · rising · heavy rain",
            font=self._f(14, "bold"), text_color=t_col, anchor="w"
        )
        self.lbl_card_cond.pack(fill="x", pady=(0, 14))

        # 4-Step Gauge: Safe | Knee | Waist | Chest
        customtkinter.CTkLabel(
            self.right_sub_container, text="Water Level Gauge",
            font=self._f(12, "bold"), text_color=muted, anchor="w"
        ).pack(fill="x", pady=(0, 6))

        self.gauge_frame = customtkinter.CTkFrame(self.right_sub_container, fg_color="transparent")
        self.gauge_frame.pack(fill="x", pady=(0, 16))
        self.gauge_steps = {}

        steps = [
            ("Safe",  "0.1m", COLOR_SUCCESS),
            ("Knee",  "0.7m", COLOR_WARNING),
            ("Waist", "1.1m", "#EA580C"),
            ("Chest", "1.5m+", COLOR_DANGER)
        ]
        for name, h_str, col in steps:
            col_box = customtkinter.CTkFrame(self.gauge_frame, fg_color="transparent")
            col_box.pack(side="left", fill="both", expand=True, padx=2)
            
            p_bar = customtkinter.CTkFrame(
                col_box,
                fg_color=col,
                height=14,
                corner_radius=4
            )
            p_bar.pack(fill="x", pady=(0, 4))

            lbl_n = customtkinter.CTkLabel(
                col_box, text=name, font=self._f(12, "bold"), text_color=t_col
            )
            lbl_n.pack()
            self.gauge_steps[name] = (p_bar, lbl_n, col)

        # Health & Safety Advisory Note
        safety_card = customtkinter.CTkFrame(
            self.right_sub_container,
            fg_color=self._t("#212D40", "#EFF6FF"),
            corner_radius=10,
            border_width=1,
            border_color=COLOR_INFO
        )
        safety_card.pack(fill="x", pady=(0, 10))

        customtkinter.CTkLabel(
            safety_card, text="🛡 Health Advisory",
            font=self._f(13, "bold"), text_color=COLOR_INFO, anchor="w"
        ).pack(padx=12, pady=(10, 2), anchor="w")

        self.lbl_card_tip = customtkinter.CTkLabel(
            safety_card,
            text="Do not wade barefoot. If you got wet, visit your Barangay Health Station for preventive medicine (Doxycycline).",
            font=self._f(12), text_color=t_col, wraplength=220, justify="left"
        )
        self.lbl_card_tip.pack(padx=12, pady=(0, 12), anchor="w")

        # Load flood data into table
        self.load_flood_records()

    def _on_flood_search_change(self, event=None):
        if self._search_timer:
            try:
                self.root.after_cancel(self._search_timer)
            except Exception:
                pass
        self._search_timer = self.root.after(250, self.load_flood_records)

    def load_flood_records(self):
        search_txt = ""
        try:
            search_txt = self.entry_flood_search.get().strip()
        except Exception:
            pass

        records = group4database.get_all_flood_records()
        for r in self.flood_tree.get_children():
            self.flood_tree.delete(r)

        matched_pantal_id = None
        for row in records:
            # row: (id, city, barangay, water_level_m, water_depth_desc, rainfall_rate_mm, rainfall_desc, alert_level, status, early_warning, last_updated)
            rec_id, city, brgy, w_m, depth_desc, rain_rate, rain_desc, alert, status, warning, updated = row
            display_brgy = brgy if city in brgy else f"{brgy}, {city}"

            if search_txt and (search_txt.lower() not in display_brgy.lower()):
                continue

            # Format Alert Level into Color + Icon + Word
            alert_clean = alert.lower()
            if "critical" in alert_clean:
                alert_badge = "⛔ Red"
            elif "warning" in alert_clean:
                alert_badge = "⚠ Orange"
            elif "alert" in alert_clean:
                alert_badge = "⚠ Yellow"
            else:
                alert_badge = "✔ Green"

            item_id = self.flood_tree.insert(
                "", "end",
                values=(display_brgy, f"{w_m:.2f} m", alert_badge)
            )

            # Keep reference to Pantal or first row
            if "pantal" in display_brgy.lower() and not matched_pantal_id:
                matched_pantal_id = item_id

        # Auto-select Pantal or first row
        children = self.flood_tree.get_children()
        if matched_pantal_id:
            self.flood_tree.selection_set(matched_pantal_id)
            self._update_selected_flood_card("Pantal, Dagupan", 0.70, "Knee Deep (0.70m)", "Rising", "Heavy Rain", "Warning (Moderate)", "Do not wade barefoot. Visit health station if you got wet.")
        elif children:
            self.flood_tree.selection_set(children[0])
            first_vals = self.flood_tree.item(children[0]).get("values", [])
            if first_vals:
                self._update_selected_flood_card(first_vals[0], 0.70, "Knee Deep", "Rising", "Heavy Rain", "Warning", "Avoid contaminated water.")

    def _on_flood_row_selected(self, event=None):
        sel = self.flood_tree.selection()
        if not sel:
            return
        vals = self.flood_tree.item(sel[0]).get("values", [])
        if not vals:
            return
        brgy_name = vals[0]
        # Query full record from database
        try:
            records = group4database.get_all_flood_records()
            for r in records:
                display_brgy = r[2] if r[1] in r[2] else f"{r[2]}, {r[1]}"
                if display_brgy == brgy_name:
                    self._update_selected_flood_card(
                        display_brgy, r[3], r[4], r[8], r[6], r[7], r[9]
                    )
                    break
        except Exception:
            pass

    def _update_selected_flood_card(self, brgy, w_m, depth_desc, status, rain_desc, alert, tip):
        self.lbl_card_brgy.configure(text=brgy)
        self.lbl_card_depth.configure(text=f"{w_m:.2f} m")

        # Color based on depth
        if w_m >= 1.5:
            d_col = COLOR_DANGER
            stage = "Chest"
        elif w_m >= 1.0:
            d_col = "#EA580C"
            stage = "Waist"
        elif w_m >= 0.5:
            d_col = COLOR_WARNING
            stage = "Knee"
        else:
            d_col = COLOR_SUCCESS
            stage = "Safe"

        self.lbl_card_depth.configure(text_color=d_col)
        self.lbl_card_cond.configure(text=f"{stage} deep · {status.lower()} · {rain_desc.lower()}")
        if tip:
            self.lbl_card_tip.configure(text=tip)

        # Highlight gauge step
        for name, (bar, lbl, orig_col) in self.gauge_steps.items():
            if name == stage:
                bar.configure(height=18, fg_color=orig_col)
                lbl.configure(font=self._f(13, "bold"), text_color=d_col)
            else:
                bar.configure(height=8, fg_color=self._t("#374151", "#D1D5DB"))
                lbl.configure(font=self._f(11), text_color=self._t(DK_MUTED, LT_MUTED))


    # WINDOW 3: RESIDENT PORTAL — REPORT ILLNESS & MY CASES 

    def _build_report_illness_view(self):
        t_col  = self._t(DK_TEXT, LT_TEXT)
        muted  = self._t(DK_MUTED, LT_MUTED)
        border = self._t(DK_BORDER, LT_BORDER)
        e_bg   = self._t(DK_ENTRY, LT_ENTRY)
        pri    = self._t(DK_BTN_PRI, LT_BTN_PRI)
        pri_h  = self._t(DK_BTN_HVR, LT_BTN_HVR)
        pri_tc = self._t(DK_BTN_PRI_T, LT_BTN_PRI_T)

        pad_box = customtkinter.CTkFrame(self.content_frame, fg_color="transparent")
        pad_box.pack(fill="both", expand=True, padx=20, pady=16)

        # Two-Column Layout: Left = Report Form / Right = "My cases"
        grid_frame = customtkinter.CTkFrame(pad_box, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True)
        grid_frame.columnconfigure(0, weight=1)
        grid_frame.columnconfigure(1, weight=1)
        grid_frame.rowconfigure(0, weight=1)

        # ── LEFT COLUMN: Report Form ─────────────────────────────────────────
        left_col = customtkinter.CTkFrame(
            grid_frame, fg_color=self._t("#182234", "#F9FAFB"),
            corner_radius=14, border_width=1, border_color=border
        )
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        form_pad = customtkinter.CTkFrame(left_col, fg_color="transparent")
        form_pad.pack(fill="both", expand=True, padx=18, pady=16)

        customtkinter.CTkLabel(
            form_pad, text="Report an illness",
            font=self._f(22, "bold"), text_color=t_col, anchor="w"
        ).pack(fill="x", pady=(0, 2))

        customtkinter.CTkLabel(
            form_pad, text="A health worker is told right away",
            font=self._f(13), text_color=COLOR_SUCCESS, anchor="w"
        ).pack(fill="x", pady=(0, 16))

        # Location Field
        customtkinter.CTkLabel(
            form_pad, text="Where are you? (Barangay)",
            font=self._f(14, "bold"), text_color=t_col, anchor="w"
        ).pack(fill="x", pady=(0, 4))

        self.entry_report_brgy = customtkinter.CTkEntry(
            form_pad, placeholder_text="e.g. Pantal, Dagupan",
            font=self._f(14), height=44,
            fg_color=e_bg, border_color=border, text_color=t_col, corner_radius=10
        )
        self.entry_report_brgy.pack(fill="x", pady=(0, 16))
        # Pre-fill
        user_brgy = self.user_info.get("station_barangay", "") or "Pantal, Dagupan"
        self.entry_report_brgy.insert(0, user_brgy)

        # Symptom Chips (Clickable toggles for elders)
        customtkinter.CTkLabel(
            form_pad, text="What do you feel?",
            font=self._f(14, "bold"), text_color=t_col, anchor="w"
        ).pack(fill="x", pady=(0, 6))

        chips_grid = customtkinter.CTkFrame(form_pad, fg_color="transparent")
        chips_grid.pack(fill="x", pady=(0, 16))
        chips_grid.columnconfigure(0, weight=1)
        chips_grid.columnconfigure(1, weight=1)

        symptoms_list = [
            ("Fever", 0, 0),
            ("Muscle pain", 0, 1),
            ("Diarrhea", 1, 0),
            ("Cough", 1, 1),
            ("Skin rash", 2, 0),
            ("Other", 2, 1)
        ]
        self.chip_buttons = {}
        for symp, r, c in symptoms_list:
            btn = customtkinter.CTkButton(
                chips_grid,
                text=f"✔ {symp}" if symp in self.selected_symptoms else symp,
                font=self._f(13, "bold"),
                fg_color=pri if symp in self.selected_symptoms else self._t(DK_BTN_SEC, LT_BTN_SEC),
                hover_color=pri_h if symp in self.selected_symptoms else self._t(DK_BTN_SECH, LT_BTN_SECH),
                text_color=pri_tc if symp in self.selected_symptoms else t_col,
                height=42, corner_radius=10,
                command=lambda s=symp: self._toggle_symptom_chip(s)
            )
            btn.grid(row=r, column=c, padx=4, pady=4, sticky="ew")
            self.chip_buttons[symp] = btn

        # Optional other notes
        customtkinter.CTkLabel(
            form_pad, text="Additional details (optional)",
            font=self._f(12), text_color=muted, anchor="w"
        ).pack(fill="x", pady=(0, 2))

        self.entry_other_notes = customtkinter.CTkEntry(
            form_pad, placeholder_text="e.g. Waded in flood yesterday, high fever",
            font=self._f(13), height=38,
            fg_color=e_bg, border_color=border, text_color=t_col, corner_radius=8
        )
        self.entry_other_notes.pack(fill="x", pady=(0, 18))

        # Big Submit Button (56 px high!)
        customtkinter.CTkButton(
            form_pad, text="Send Report to Health Worker",
            font=self._f(16, "bold"),
            fg_color=pri, hover_color=pri_h, text_color=pri_tc,
            height=56, corner_radius=12,
            command=self.submit_illness_report
        ).pack(fill="x", pady=(4, 0))

        # ── RIGHT COLUMN: "My cases" (Your Logged Cases & 3-Step Tracker) ───
        right_col = customtkinter.CTkFrame(
            grid_frame, fg_color=self._t("#182234", "#F9FAFB"),
            corner_radius=14, border_width=1, border_color=border
        )
        right_col.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        right_pad = customtkinter.CTkFrame(right_col, fg_color="transparent")
        right_pad.pack(fill="both", expand=True, padx=18, pady=16)

        hdr_row = customtkinter.CTkFrame(right_pad, fg_color="transparent")
        hdr_row.pack(fill="x", pady=(0, 8))

        customtkinter.CTkLabel(
            hdr_row, text="My cases",
            font=self._f(22, "bold"), text_color=t_col, anchor="w"
        ).pack(side="left")

        customtkinter.CTkButton(
            hdr_row, text="📥 Export CSV",
            font=self._f(11, "bold"),
            fg_color=self._t(DK_BTN_SEC, LT_BTN_SEC),
            hover_color=self._t(DK_BTN_SECH, LT_BTN_SECH),
            text_color=t_col, height=30, corner_radius=8,
            command=self.export_my_cases_csv
        ).pack(side="right")

        customtkinter.CTkLabel(
            right_pad, text="Track medical assessment and recovery progress.",
            font=self._f(12), text_color=muted, anchor="w"
        ).pack(fill="x", pady=(0, 10))

        # Scrollable container for personal case cards
        self.cases_scroll = customtkinter.CTkScrollableFrame(
            right_pad, fg_color="transparent"
        )
        self.cases_scroll.pack(fill="both", expand=True)

        self.load_my_cases()

    def _toggle_symptom_chip(self, symptom):
        pri    = self._t(DK_BTN_PRI, LT_BTN_PRI)
        pri_h  = self._t(DK_BTN_HVR, LT_BTN_HVR)
        pri_tc = self._t(DK_BTN_PRI_T, LT_BTN_PRI_T)
        sec    = self._t(DK_BTN_SEC, LT_BTN_SEC)
        sec_h  = self._t(DK_BTN_SECH, LT_BTN_SECH)
        t_col  = self._t(DK_TEXT, LT_TEXT)

        if symptom in self.selected_symptoms:
            self.selected_symptoms.remove(symptom)
            self.chip_buttons[symptom].configure(
                text=symptom, fg_color=sec, hover_color=sec_h, text_color=t_col
            )
        else:
            self.selected_symptoms.add(symptom)
            self.chip_buttons[symptom].configure(
                text=f"✔ {symptom}", fg_color=pri, hover_color=pri_h, text_color=pri_tc
            )

    def submit_illness_report(self):
        brgy = self.entry_report_brgy.get().strip()
        if not brgy:
            messagebox.showwarning("Location Required", "Please enter your barangay.")
            return

        if not self.selected_symptoms:
            messagebox.showwarning("Symptoms Required", "Please select at least one symptom you are feeling.")
            return

        symptoms_str = ", ".join(sorted(self.selected_symptoms))
        other_txt = self.entry_other_notes.get().strip()
        if other_txt:
            symptoms_str += f" ({other_txt})"

        username = self.user_info.get("username", "")
        full_name = self.user_info.get("full_name", "Resident")
        today_str = str(date.today())

        ok, rec_id = group4database.add_patient_record(
            full_name=full_name,
            age=68,
            sex="Male",
            barangay=brgy,
            disease=symptoms_str,
            status="Under Observation",
            date_logged=today_str,
            patient_username=username
        )

        if ok:
            messagebox.showinfo(
                "Report Submitted!",
                f"Thank you, {full_name}!\n\n"
                f"Your symptoms ({symptoms_str}) have been forwarded to the local health worker.\n"
                f"Status: Being watched."
            )
            self.entry_other_notes.delete(0, "end")
            self.load_my_cases()
        else:
            messagebox.showerror("Error", f"Failed to record report:\n{rec_id}")

    def load_my_cases(self):
        for w in self.cases_scroll.winfo_children():
            try:
                w.destroy()
            except Exception:
                pass

        username = self.user_info.get("username", "")
        patient_name = self.user_info.get("full_name", "")
        records = group4database.get_patient_records_by_account(patient_username=username, patient_name=patient_name)

        if not records:
            customtkinter.CTkLabel(
                self.cases_scroll,
                text="No cases reported yet.\nUse the form on the left to report sickness.",
                font=self._f(13), text_color=self._t(DK_MUTED, LT_MUTED), justify="center"
            ).pack(pady=40)
            return

        t_col  = self._t(DK_TEXT, LT_TEXT)
        muted  = self._t(DK_MUTED, LT_MUTED)
        border = self._t(DK_BORDER, LT_BORDER)

        for rec in records:
            # rec: (id, full_name, age, sex, barangay, disease, status, date_logged)
            rec_id, name, age, sex, brgy, disease, status_str, dt = rec

            card = customtkinter.CTkFrame(
                self.cases_scroll,
                fg_color=self._t("#212D40", "#FFFFFF"),
                border_width=1, border_color=border,
                corner_radius=12
            )
            card.pack(fill="x", pady=6)

            top_row = customtkinter.CTkFrame(card, fg_color="transparent")
            top_row.pack(fill="x", padx=14, pady=(12, 4))

            # Title
            customtkinter.CTkLabel(
                top_row, text=disease,
                font=self._f(15, "bold"), text_color=t_col, anchor="w"
            ).pack(side="left")

            # Status Pill (Color + Icon + Word)
            if status_str == "Admitted":
                pill_txt = "🏥 In treatment"
                pill_col = COLOR_DANGER
                active_step = 2
            elif status_str == "Recovered":
                pill_txt = "✔ Recovered"
                pill_col = COLOR_SUCCESS
                active_step = 3
            else:
                pill_txt = "⚠ Being watched"
                pill_col = COLOR_WARNING
                active_step = 1

            customtkinter.CTkLabel(
                top_row, text=pill_txt,
                font=self._f(12, "bold"), text_color=pill_col
            ).pack(side="right")

            # Date & Barangay line
            # Friendly date (e.g. Sent Oct 15 · Brgy. Pantal)
            try:
                d_obj = datetime.strptime(dt, "%Y-%m-%d")
                friendly_date = d_obj.strftime("%b %d")
            except Exception:
                friendly_date = dt

            customtkinter.CTkLabel(
                card, text=f"Sent {friendly_date} · {brgy}",
                font=self._f(12), text_color=muted, anchor="w"
            ).pack(fill="x", padx=14, pady=(0, 10))

            # 3-Step Visual Tracker: ① Being watched ── ② In treatment ── ③ Recovered
            tracker = customtkinter.CTkFrame(card, fg_color=self._t("#182234", "#F3F4F6"), corner_radius=8)
            tracker.pack(fill="x", padx=14, pady=(0, 12))

            t_inner = customtkinter.CTkFrame(tracker, fg_color="transparent")
            t_inner.pack(fill="x", padx=10, pady=8)

            steps_info = [
                (1, "① Being watched", COLOR_WARNING),
                (2, "② In treatment", COLOR_DANGER),
                (3, "③ Recovered", COLOR_SUCCESS)
            ]
            for step_num, step_label, col in steps_info:
                is_step_active = (step_num == active_step)
                is_past = (step_num <= active_step)

                step_col = col if is_step_active else (t_col if is_past else muted)
                customtkinter.CTkLabel(
                    t_inner, text=step_label,
                    font=self._f(11, "bold" if is_step_active else "normal"),
                    text_color=step_col
                ).pack(side="left", expand=True)

                if step_num < 3:
                    customtkinter.CTkLabel(
                        t_inner, text="──",
                        font=self._f(10), text_color=muted
                    ).pack(side="left")

    def export_my_cases_csv(self):
        username = self.user_info.get("username", "")
        patient_name = self.user_info.get("full_name", "")
        records = group4database.get_patient_records_by_account(patient_username=username, patient_name=patient_name)

        if not records:
            messagebox.showinfo("Export", "No case records to export.")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Spreadsheet", "*.csv")],
            initialfile=f"my_wildcare_cases_{date.today()}.csv",
            title="Export My Case Records"
        )
        if not filename:
            return

        try:
            with open(filename, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Name", "Age", "Sex", "Barangay", "Illness", "Status", "Date Logged"])
                for row in records:
                    writer.writerow(row)
            messagebox.showinfo("Export Successful", f"Saved {len(records)} record(s) to:\n{filename}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Could not save CSV file:\n{e}")

    # WINDOW 4: RESIDENT PORTAL — DISEASE WATCH

    def _build_disease_watch_view(self):
        t_col  = self._t(DK_TEXT, LT_TEXT)
        muted  = self._t(DK_MUTED, LT_MUTED)

        pad_box = customtkinter.CTkFrame(self.content_frame, fg_color="transparent")
        pad_box.pack(fill="both", expand=True, padx=20, pady=16)

        # Header Title & Subtitle
        customtkinter.CTkLabel(
            pad_box, text="Disease Watch",
            font=self._f(22, "bold"), text_color=t_col, anchor="w"
        ).pack(fill="x", pady=(0, 2))

        customtkinter.CTkLabel(
            pad_box, text="The four flood-season illnesses (W·I·L·D). Philippines, DOH figures 2026.",
            font=self._f(13), text_color=muted, anchor="w"
        ).pack(fill="x", pady=(0, 14))

        # Scrollable Cards Grid
        self.watch_scroll = customtkinter.CTkScrollableFrame(
            pad_box, fg_color="transparent"
        )
        self.watch_scroll.pack(fill="both", expand=True)

        self.load_disease_watch()

        # Sources Citation Footer
        customtkinter.CTkLabel(
            pad_box,
            text="Sources: DOH figures via Philstar, Daily Tribune, Manila Bulletin (Aug to Oct 2026); Manila Health Department. Updated Oct 15, 2026.",
            font=self._f(10), text_color=muted, anchor="w"
        ).pack(fill="x", pady=(10, 0))

    def load_disease_watch(self):
        for w in self.watch_scroll.winfo_children():
            try:
                w.destroy()
            except Exception:
                pass

        stats = group4database.get_all_disease_statistics()
        # Fallback dictionary for W.I.L.D. disease static details
        wild_metadata = {
            "leptospirosis": {
                "letter": "L",
                "name": "Leptospirosis",
                "cause": "From floodwater",
                "default_cases": "10,936",
                "default_prev": "7,931",
                "sub": "38% more than last year · 5.1% died (last year 10.55%)",
                "tip": "🛡 Waded in floodwater? Visit the health station within 24 to 48 hours."
            },
            "dengue": {
                "letter": "D",
                "name": "Dengue",
                "cause": "From mosquito bites",
                "default_cases": "192,112",
                "default_prev": "254,137",
                "sub": "24% fewer than last year",
                "tip": "🦟 Turn over, empty, dry and cover water containers."
            },
            "bloody diarrhea": {
                "letter": "W",
                "name": "Water-borne illness",
                "cause": "Dirty water or food",
                "default_cases": "6,456",
                "default_prev": "9,520",
                "sub": "bloody diarrhea, 32% fewer · cholera 428, 67% fewer",
                "tip": "💧 Drink boiled or bottled water. Wash hands with soap."
            },
            "flu-like illness": {
                "letter": "I",
                "name": "Flu-like illness",
                "cause": "Fever and cough",
                "default_cases": "1,788",
                "default_prev": "0",
                "sub": "cases in Manila City (no national total found)",
                "tip": "😷 Rest, drink fluids, see a doctor if fever lasts over 3 days."
            }
        }

        # Grid of 2x2 cards
        grid = customtkinter.CTkFrame(self.watch_scroll, fg_color="transparent")
        grid.pack(fill="both", expand=True)
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        # Match database stats to WILD keys
        ordered_keys = ["leptospirosis", "dengue", "bloody diarrhea", "flu-like illness"]
        
        row_idx = 0
        col_idx = 0

        for key in ordered_keys:
            meta = wild_metadata[key]
            # Find in stats
            stat_match = None
            for s in stats:
                if key in s["disease"].lower():
                    stat_match = s
                    break

            cases_str = f"{stat_match['cases']:,}" if stat_match else meta["default_cases"]
            prev_cases = stat_match['cases_last_year'] if stat_match else (int(meta["default_prev"].replace(",", "")) if meta["default_prev"] != "0" else 0)
            change_str = stat_match["change_str"] if stat_match else ""

            # Card container
            card = customtkinter.CTkFrame(
                grid,
                fg_color=self._t("#182234", "#FFFFFF"),
                border_width=1,
                border_color=self._t(DK_BORDER, LT_BORDER),
                corner_radius=14
            )
            card.grid(row=row_idx, column=col_idx, padx=6, pady=6, sticky="nsew")

            pad = customtkinter.CTkFrame(card, fg_color="transparent")
            pad.pack(fill="both", expand=True, padx=16, pady=14)

            # Top row: Letter Badge + Name & Cause + Trend Badge
            top_box = customtkinter.CTkFrame(pad, fg_color="transparent")
            top_box.pack(fill="x", pady=(0, 6))

            badge_letter = customtkinter.CTkFrame(
                top_box, fg_color=COLOR_INFO, width=34, height=34, corner_radius=8
            )
            badge_letter.pack(side="left", padx=(0, 10))
            badge_letter.pack_propagate(False)
            customtkinter.CTkLabel(
                badge_letter, text=meta["letter"],
                font=("Segoe UI", 16, "bold"), text_color="#FFFFFF"
            ).place(relx=0.5, rely=0.5, anchor="center")

            title_box = customtkinter.CTkFrame(top_box, fg_color="transparent")
            title_box.pack(side="left", fill="both", expand=True)
            customtkinter.CTkLabel(
                title_box, text=meta["name"],
                font=self._f(16, "bold"), text_color=self._t(DK_TEXT, LT_TEXT), anchor="w"
            ).pack(anchor="w")
            customtkinter.CTkLabel(
                title_box, text=meta["cause"],
                font=self._f(11), text_color=self._t(DK_MUTED, LT_MUTED), anchor="w"
            ).pack(anchor="w")

            # Trend Pill (▲ Going up / ▼ Going down / Local count)
            if "▲" in change_str:
                pill_text = f"▲ Going up ({change_str.replace('▲', '').strip()})"
                pill_color = COLOR_DANGER
            elif "▼" in change_str:
                pill_text = f"▼ Going down ({change_str.replace('▼', '').strip()})"
                pill_color = COLOR_SUCCESS
            elif prev_cases == 0:
                pill_text = "Local count"
                pill_color = COLOR_INFO
            else:
                pill_text = change_str or "Steady"
                pill_color = COLOR_INFO

            customtkinter.CTkLabel(
                top_box, text=pill_text,
                font=self._f(11, "bold"), text_color=pill_color
            ).pack(side="right")

            # Big Number
            customtkinter.CTkLabel(
                pad, text=cases_str,
                font=("Segoe UI", 32, "bold"), text_color=self._t(DK_TEXT, LT_TEXT), anchor="w"
            ).pack(fill="x", pady=(4, 2))

            # Detail sub-label
            customtkinter.CTkLabel(
                pad, text=meta["sub"],
                font=self._f(12), text_color=self._t(DK_MUTED, LT_MUTED), anchor="w"
            ).pack(fill="x", pady=(0, 10))

            # Visual Mini Comparison Bars (This year vs Last year)
            if prev_cases > 0:
                bar_frame = customtkinter.CTkFrame(pad, fg_color=self._t("#212D40", "#F3F4F6"), corner_radius=8)
                bar_frame.pack(fill="x", pady=(0, 10))
                b_inner = customtkinter.CTkFrame(bar_frame, fg_color="transparent")
                b_inner.pack(fill="x", padx=10, pady=6)
                customtkinter.CTkLabel(
                    b_inner, text=f"This year: {cases_str}   |   Last year: {prev_cases:,}",
                    font=self._f(11), text_color=self._t(DK_TEXT, LT_TEXT), anchor="w"
                ).pack(anchor="w")

            # Safety Tip Box
            tip_card = customtkinter.CTkFrame(
                pad, fg_color=self._t("#212D40", "#F0FDF4"),
                corner_radius=8, border_width=1, border_color="#86EFAC"
            )
            tip_card.pack(fill="x")
            customtkinter.CTkLabel(
                tip_card, text=meta["tip"],
                font=self._f(11, "bold"), text_color=self._t("#86EFAC", "#166534"),
                wraplength=310, justify="left"
            ).pack(padx=10, pady=8, anchor="w")

            col_idx += 1
            if col_idx > 1:
                col_idx = 0
                row_idx += 1

    # COMMON ACTION HANDLERS

    def show_emergency_hotlines(self):
        modal = customtkinter.CTkToplevel(self.root)
        modal.title("Emergency Hotlines — Pangasinan")
        modal.geometry("460x420")
        modal.resizable(False, False)
        modal.configure(fg_color=self._t(DK_BG, LT_BG))
        modal.after(10, modal.lift)
        modal.attributes("-topmost", True)

        rx = self.root.winfo_x()
        ry = self.root.winfo_y()
        modal.geometry(f"+{max(0, rx + 320)}+{max(0, ry + 120)}")

        hdr = customtkinter.CTkFrame(modal, fg_color=COLOR_DANGER, height=54, corner_radius=0)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        customtkinter.CTkLabel(
            hdr, text="🚨 Emergency Contact Hotlines",
            font=self._f(15, "bold"), text_color="#FFFFFF"
        ).pack(side="left", padx=18, pady=12)

        body = customtkinter.CTkFrame(modal, fg_color=self._t(DK_CARD, LT_CARD), corner_radius=12)
        body.pack(fill="both", expand=True, padx=16, pady=14)

        hotlines = [
            ("National Emergency Helpline", "911"),
            ("Pangasinan PDRRMO", "(075) 542-7000 / 0917-855-7377"),
            ("Dagupan City CDRRMC", "(075) 522-0007 / 0928-500-2376"),
            ("Region 1 Medical Center (R1MC)", "(075) 515-8901"),
            ("Calasiao RHU & Emergency", "(075) 522-2405"),
            ("Philippine Red Cross (Dagupan)", "(075) 522-2092")
        ]
        for name, num in hotlines:
            row = customtkinter.CTkFrame(body, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=6)
            customtkinter.CTkLabel(row, text=name, font=self._f(12, "bold"), text_color=self._t(DK_TEXT, LT_TEXT)).pack(anchor="w")
            customtkinter.CTkLabel(row, text=num, font=self._f(13), text_color=COLOR_INFO).pack(anchor="w")

        customtkinter.CTkButton(
            modal, text="Close",
            font=self._f(13, "bold"),
            fg_color=self._t(DK_BTN_SEC, LT_BTN_SEC),
            hover_color=self._t(DK_BTN_SECH, LT_BTN_SECH),
            text_color=self._t(DK_TEXT, LT_TEXT),
            height=38, corner_radius=8,
            command=modal.destroy
        ).pack(padx=16, pady=(0, 14), fill="x")

    def handle_logout(self):
        if messagebox.askyesno("Log out", "Are you sure you want to log out of W.I.L.D. CARE?"):
            if self._search_timer:
                try:
                    self.root.after_cancel(self._search_timer)
                except Exception:
                    pass
            if self._refresh_timer:
                try:
                    self.root.after_cancel(self._refresh_timer)
                except Exception:
                    pass
            try:
                self.root.destroy()
            except Exception:
                pass
            self.on_logout_callback()

    def run(self):
        self.root.mainloop()
