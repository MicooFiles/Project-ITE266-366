import os
import sys
import customtkinter
from tkinter import messagebox
from PIL import Image
import group4database

def _logo_image(filename, size):
    try:
        folder = os.path.dirname(os.path.abspath(__file__))
        img = Image.open(os.path.join(folder, filename)).convert("RGBA")
        return customtkinter.CTkImage(light_image=img, dark_image=img, size=size)
    except Exception:
        return None

def _set_app_icon(window):
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

# Light Mode
GROUP4_LT_BG = "#F3F4F6"
GROUP4_LT_CARD = "#FFFFFF"
GROUP4_LT_HEROBG = "#E5E7EB"
GROUP4_LT_TEXT = "#111827"
GROUP4_LT_MUTED = "#4B5563"
GROUP4_LT_ENTRY_BG = "#F9FAFB"
GROUP4_LT_BORDER = "#D1D5DB"
GROUP4_LT_BUTTON_PRIMARY = "#1F2937"
GROUP4_LT_BTNHOVER = "#374151"
GROUP4_LT_PRIMARY_TEXT = "#FFFFFF"
GROUP4_LT_BTN_SECONDARY = "#E5E7EB"
GROUP4_LT_BTN_SECONDARY_HOVER = "#D1D5DB"

# Dark Mode

DARK_BACKGROUND = "#111827"
DARK_CARD      = "#1F2937"
DARK_HERO_BG   = "#182234"
DARK_TEXT      = "#F9FAFB"
DARK_MUTED     = "#9CA3AF"
DARK_ENTRY_BG  = "#111827"
DARK_BORDER    = "#374151"
DARK_BTN_PRIMARY = "#F9FAFB"
DARK_BTN_HOVER = "#E5E7EB"
DARK_PRIMARY_TEXT = "#111827"
DARK_BTN_SECONDARY = "#374151"
DARK_BTN_SECONDARY_HOVER = "#4B5563"

COLOR_DANGER  = "#DC2626"
COLOR_SUCCESS = "#16A34A"
COLOR_INFO    = "#2563EB"
COLOR_WARNING = "#D97706"

class LoginWindow:
    def __init__(self, on_login_success_callback):
        self.on_login_success = on_login_success_callback
        self._is_dark = True
        self._font_scale = 1.0 
        self._pwd_visible = False

        self.root = customtkinter.CTk()
        self.root.title("W.I.L.D. CARE — Sign In")
        self.root.after(300, lambda: _set_app_icon(self.root))
        
        # Exact UI board desktop dimension: 860 px wide
        window_width = 860
        window_height = 660
        self.root.geometry(f"{window_width}x{window_height}")
        self.root.minsize(820, 620)
        self.root.resizable(False, False)

        # Center on screen
        self.root.update_idletasks()
        screenwidth = self.root.winfo_screenwidth()
        screenheight = self.root.winfo_screenheight()
        x = max(0, (screenwidth - window_width) // 2)
        y = max(0, (screenheight - window_height) // 2)
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self._apply_mode()
        self.set_background_image("flood.jpg")
        self.build_ui()

    # ── THEME & FONT HELPERS ─────────────────────────────────────────────────
    def _apply_mode(self):
        mode = "dark" if self._is_dark else "light"
        customtkinter.set_appearance_mode(mode)
        self.root.configure(fg_color=self._theme(DARK_BACKGROUND, GROUP4_LT_BG))

    def _theme(self, dark_val, light_val):
        return dark_val if self._is_dark else light_val

    def _f(self, base_size, weight="normal"):
        scaled = max(11, int(round(base_size * self._font_scale)))
        return ("Segoe UI", scaled, weight)

    def _set_font_scale(self, scale_val):
        self._font_scale = scale_val
        self.rebuild_ui()

    def _toggle_theme(self):
        self._is_dark = not self._is_dark
        self._apply_mode()
        self.rebuild_ui()

    def rebuild_ui(self):
        saved_user = ""
        try:
            saved_user = self.entry_signin_user.get()
        except Exception:
            pass

        for widget in self.root.winfo_children():
            try:
                widget.destroy()
            except Exception:
                pass
        self.set_background_image("flood.jpg")
        self.build_ui()
        if saved_user:
            try:
                self.entry_signin_user.delete(0, "end")
                self.entry_signin_user.insert(0, saved_user)
            except Exception:
                pass

    def set_background_image(self, image_path):
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            full_path = os.path.join(script_dir, image_path)
            if not os.path.exists(full_path):
                full_path = image_path
            
            pil_img = Image.open(full_path)
            self.bg_image = customtkinter.CTkImage(
                light_image=pil_img,
                dark_image=pil_img,
                size=(860, 660)
            )
            bg_label = customtkinter.CTkLabel(self.root, text="", image=self.bg_image)
            bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        except Exception as e:
            pass

    def on_close(self):
        try:
            self.root.destroy()
        except Exception:
            pass
        sys.exit(0)

    # ── BUILD MAIN UI ────────────────────────────────────────────────────────
    def build_ui(self):
        card_bg   = self._theme(DARK_CARD, GROUP4_LT_CARD)
        hero_bg   = self._theme(DARK_HERO_BG, GROUP4_LT_HEROBG)
        text_col  = self._theme(DARK_TEXT, GROUP4_LT_TEXT)
        muted_col = self._theme(DARK_MUTED, GROUP4_LT_MUTED)
        border    = self._theme(DARK_BORDER, GROUP4_LT_BORDER)
        sec_btn   = self._theme(DARK_BTN_SECONDARY, GROUP4_LT_BTN_SECONDARY)
        sec_btn_h = self._theme(DARK_BTN_SECONDARY_HOVER, GROUP4_LT_BTN_SECONDARY_HOVER)

        # Outer card container (860 px canvas)
        main_card = customtkinter.CTkFrame(
            self.root, fg_color=card_bg, corner_radius=18,
            border_width=1, border_color=border,
            width=820, height=610
        )
        main_card.place(relx=0.5, rely=0.5, anchor="center")


        left_hero = customtkinter.CTkFrame(
            main_card, fg_color=hero_bg, corner_radius=16,
            border_width=0,
            width=320, height=582
        )
        left_hero.pack_propagate(False)
        left_hero.grid_propagate(False)
        left_hero.place(x=14, y=14)

        # Emblem
        emblem_box = customtkinter.CTkFrame(left_hero, fg_color="#FFFFFF", corner_radius=16)
        emblem_box.pack(pady=(28, 8))
        self.logo_img = _logo_image("wildcare_logo.png", (72, 80))
        customtkinter.CTkLabel(
            emblem_box, text="" if self.logo_img else "🌊", image=self.logo_img,
            font=("Segoe UI", 48)
        ).pack(padx=16, pady=10)

        customtkinter.CTkLabel(
            left_hero, text="W.I.L.D. CARE",
            font=self._f(24, "bold"), text_color=text_col
        ).pack(pady=(0, 4))

        customtkinter.CTkLabel(
            left_hero,
            text="Post-Flood Disease Monitoring\nSystem",
            font=self._f(13, "bold"), text_color=COLOR_INFO,
            justify="center"
        ).pack(pady=(0, 10))

        customtkinter.CTkLabel(
            left_hero,
            text="Report sickness, check flood levels,\nand get health help sooner.",
            font=self._f(12), text_color=muted_col,
            justify="center"
        ).pack(padx=16, pady=(0, 24))

        # Reassurance badges
        bullets = [
            ("🌊", "Live Flood Levels", "Monitors Pangasinan river basins"),
            ("🛡", "One Sign-in", "Residents, health workers & nurses"),
            ("🏥", "Direct Care", "Fast alerts to local health centers")
        ]
        for icon, title, desc in bullets:
            b_box = customtkinter.CTkFrame(left_hero, fg_color=self._theme("#243044", "#F0F2F5"), corner_radius=10)
            b_box.pack(fill="x", padx=16, pady=5)
            customtkinter.CTkLabel(
                b_box, text=icon, font=("Segoe UI", 16)
            ).pack(side="left", padx=(10, 8), pady=8)
            t_col_box = customtkinter.CTkFrame(b_box, fg_color="transparent")
            t_col_box.pack(side="left", fill="both", expand=True, pady=4)
            customtkinter.CTkLabel(
                t_col_box, text=title, font=self._f(12, "bold"), text_color=text_col, anchor="w"
            ).pack(anchor="w")
            customtkinter.CTkLabel(
                t_col_box, text=desc, font=self._f(10), text_color=muted_col, anchor="w"
            ).pack(anchor="w")

        # Emergency hotline note at bottom of left panel
        customtkinter.CTkLabel(
            left_hero,
            text="Emergency: Dial 911 or visit your\nnearest Barangay Health Station.",
            font=self._f(11), text_color=muted_col, justify="center"
        ).pack(side="bottom", pady=18)

        # ── RIGHT CONTENT PANEL (Sign in / New resident tabs) 
        right_panel = customtkinter.CTkFrame(main_card, fg_color="transparent",
                                             width=458, height=582)
        right_panel.pack_propagate(False)
        right_panel.grid_propagate(False)
        right_panel.place(x=348, y=14)

        # Top Bar: Text Size controls (A A A) and Theme toggle
        top_ctrls = customtkinter.CTkFrame(right_panel, fg_color="transparent")
        top_ctrls.pack(fill="x", pady=(4, 8))

        lbl_ts = customtkinter.CTkLabel(
            top_ctrls, text="Text size:",
            font=self._f(12, "bold"), text_color=muted_col
        )
        lbl_ts.pack(side="left", padx=(0, 6))

        # A A A text size buttons
        for lbl, scale in [("A", 0.9), ("A", 1.0), ("A", 1.18)]:
            is_active = (abs(self._font_scale - scale) < 0.05)
            btn_sz = customtkinter.CTkButton(
                top_ctrls, text=lbl,
                font=("Segoe UI", 11 if scale == 0.9 else (13 if scale == 1.0 else 16), "bold"),
                fg_color=self._theme(DARK_BTN_PRIMARY, GROUP4_LT_BUTTON_PRIMARY) if is_active else sec_btn,
                hover_color=self._theme(DARK_BTN_HOVER, GROUP4_LT_BTNHOVER) if is_active else sec_btn_h,
                text_color=self._theme(DARK_PRIMARY_TEXT, GROUP4_LT_PRIMARY_TEXT) if is_active else text_col,
                width=32, height=28, corner_radius=6,
                command=lambda s=scale: self._set_font_scale(s)
            )
            btn_sz.pack(side="left", padx=2)

        # Theme toggle on the right
        theme_label = "☀ Light" if self._is_dark else "🌙 Dark"
        customtkinter.CTkButton(
            top_ctrls, text=theme_label,
            font=self._f(11, "bold"),
            fg_color=sec_btn, hover_color=sec_btn_h,
            text_color=text_col, width=80, height=28, corner_radius=14,
            command=self._toggle_theme
        ).pack(side="right")

        # Tabs: Sign in & New resident
        self.tabview = customtkinter.CTkTabview(
            right_panel,
            fg_color="transparent",
            segmented_button_fg_color=self._theme(DARK_ENTRY_BG,   GROUP4_LT_ENTRY_BG),
            segmented_button_selected_color=self._theme(DARK_BTN_PRIMARY, GROUP4_LT_BUTTON_PRIMARY),
            segmented_button_selected_hover_color=self._theme(DARK_BTN_HOVER, GROUP4_LT_BTNHOVER),
            segmented_button_unselected_color=self._theme(DARK_ENTRY_BG, GROUP4_LT_ENTRY_BG),
            segmented_button_unselected_hover_color=sec_btn_h,
            text_color=text_col
        )
        self.tabview.pack(fill="both", expand=True, pady=(0, 4))

        self.tab_signin   = self.tabview.add("  Sign in  ")
        self.tab_resident = self.tabview.add("  New resident  ")
        self.tabview.set("  Sign in  ")

        self._build_signin_view(self.tab_signin)
        self._build_resident_view(self.tab_resident)
        self.entry_signin_user.focus_set()


    def _build_signin_view(self, container):
        t_col  = self._theme(DARK_TEXT, GROUP4_LT_TEXT)
        e_bg   = self._theme(DARK_ENTRY_BG, GROUP4_LT_ENTRY_BG)
        border = self._theme(DARK_BORDER, GROUP4_LT_BORDER)
        pri    = self._theme(DARK_BTN_PRIMARY, GROUP4_LT_BUTTON_PRIMARY)
        pri_h  = self._theme(DARK_BTN_HOVER, GROUP4_LT_BTNHOVER)
        pri_tc = self._theme(DARK_PRIMARY_TEXT, GROUP4_LT_PRIMARY_TEXT)
        muted  = self._theme(DARK_MUTED, GROUP4_LT_MUTED)

        # Account Identifier Field (Full Name, Email, or Username)
        customtkinter.CTkLabel(
            container, text="Full Name, Email",
            font=self._f(17, "bold"), text_color=t_col, anchor="w"
        ).pack(fill="x", pady=(16, 4))

        self.entry_signin_user = customtkinter.CTkEntry(
            container, placeholder_text="Type your name or email",
            font=self._f(16), height=48,
            fg_color=e_bg, border_color=border, text_color=t_col, corner_radius=10
        )
        self.entry_signin_user.pack(fill="x", pady=(0, 14))

        # Password Field with Show/Hide Eye Toggle
        customtkinter.CTkLabel(
            container, text="Password",
            font=self._f(17, "bold"), text_color=t_col, anchor="w"
        ).pack(fill="x", pady=(0, 4))

        pw_row = customtkinter.CTkFrame(container, fg_color="transparent")
        pw_row.pack(fill="x", pady=(0, 4))

        self.entry_signin_pass = customtkinter.CTkEntry(
            pw_row, placeholder_text="Type your password",
            font=self._f(16), height=48,
            fg_color=e_bg, border_color=border, text_color=t_col, corner_radius=10,
            show="*"
        )
        self.entry_signin_pass.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.btn_eye = customtkinter.CTkButton(
            pw_row, text="👁 Show",
            font=self._f(13, "bold"),
            fg_color=self._theme(DARK_BTN_SECONDARY, GROUP4_LT_BTN_SECONDARY),
            hover_color=self._theme(DARK_BTN_SECONDARY_HOVER, GROUP4_LT_BTN_SECONDARY_HOVER),
            text_color=t_col, width=82, height=48, corner_radius=10,
            command=self._toggle_password_visibility
        )
        self.btn_eye.pack(side="right")

        # Forgot password row
        help_row = customtkinter.CTkFrame(container, fg_color="transparent")
        help_row.pack(fill="x", pady=(4, 14))

        self.lbl_attempts = customtkinter.CTkLabel(
            help_row, text="", font=self._f(12), text_color=COLOR_DANGER
        )
        self.lbl_attempts.pack(side="left")

        customtkinter.CTkButton(
            help_row, text="Forgot password? Get a code by email",
            font=self._f(12, "underline"),
            fg_color="transparent", hover_color=self._theme(DARK_ENTRY_BG, GROUP4_LT_ENTRY_BG),
            text_color=COLOR_INFO, height=26,
            command=self.open_forgot_password_dialog
        ).pack(side="right")

        # Big Sign In button (56 px high!)
        btn_sign = customtkinter.CTkButton(
            container, text="Sign In",
            font=self._f(18, "bold"),
            fg_color=pri, hover_color=pri_h, text_color=pri_tc,
            height=56, corner_radius=12,
            command=self.handle_signin
        )
        btn_sign.pack(fill="x", pady=(6, 12))

        # Direct talking point notice for user
        customtkinter.CTkLabel(
            container,
            text="One sign-in for everyone: database.py automatically opens\nyour matching portal (Resident or Health Worker).",
            font=self._f(11), text_color=muted, justify="center"
        ).pack(pady=(4, 0))

        self.entry_signin_pass.bind("<Return>", lambda e: self.handle_signin())
        self.entry_signin_user.bind("<Return>", lambda e: self.handle_signin())

    def _toggle_password_visibility(self):
        self._pwd_visible = not self._pwd_visible
        if self._pwd_visible:
            self.entry_signin_pass.configure(show="")
            self.btn_eye.configure(text="🙈 Hide")
        else:
            self.entry_signin_pass.configure(show="*")
            self.btn_eye.configure(text="👁 Show")


    def _build_resident_view(self, container):
        t_col  = self._theme(DARK_TEXT, GROUP4_LT_TEXT)
        e_bg   = self._theme(DARK_ENTRY_BG, GROUP4_LT_ENTRY_BG)
        border = self._theme(DARK_BORDER, GROUP4_LT_BORDER)
        pri    = self._theme(DARK_BTN_PRIMARY, GROUP4_LT_BUTTON_PRIMARY)
        pri_h  = self._theme(DARK_BTN_HOVER, GROUP4_LT_BTNHOVER)
        pri_tc = self._theme(DARK_PRIMARY_TEXT, GROUP4_LT_PRIMARY_TEXT)
        muted  = self._theme(DARK_MUTED, GROUP4_LT_MUTED)

        scroll = customtkinter.CTkScrollableFrame(container, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        def make_field(parent, label_text, placeholder, is_pwd=False):
            customtkinter.CTkLabel(
                parent, text=label_text,
                font=self._f(14, "bold"), text_color=t_col, anchor="w"
            ).pack(fill="x", pady=(6, 2))
            e = customtkinter.CTkEntry(
                parent, placeholder_text=placeholder,
                font=self._f(14), height=42,
                fg_color=e_bg, border_color=border, text_color=t_col, corner_radius=8,
                show="*" if is_pwd else ""
            )
            e.pack(fill="x", pady=(0, 4))
            return e

        self.entry_res_name  = make_field(scroll, "Your Full Name", "e.g. Lolo Ronaldo Jr. De Guzman")
        self.entry_res_email = make_field(scroll, "Email (for 6-digit recovery code)", "e.g. ronaldo@gmail.com")
        self.entry_res_pass  = make_field(scroll, "Password", "At least 4 characters", is_pwd=True)
        self.entry_res_conf  = make_field(scroll, "Confirm Password", "Re-type your password", is_pwd=True)

        self.lbl_res_msg = customtkinter.CTkLabel(
            scroll, text="", font=self._f(12), text_color=COLOR_DANGER
        )
        self.lbl_res_msg.pack(pady=(4, 6))

        # Big Create Account Button (56 px high!)
        customtkinter.CTkButton(
            scroll, text="Create Resident Account",
            font=self._f(17, "bold"),
            fg_color=pri, hover_color=pri_h, text_color=pri_tc,
            height=56, corner_radius=12,
            command=self.handle_resident_register
        ).pack(fill="x", pady=(4, 10))

        self.entry_res_conf.bind("<Return>", lambda e: self.handle_resident_register())


    def open_forgot_password_dialog(self):
        card_bg = self._theme(DARK_CARD, GROUP4_LT_CARD)
        t_col   = self._theme(DARK_TEXT, GROUP4_LT_TEXT)
        e_bg    = self._theme(DARK_ENTRY_BG, GROUP4_LT_ENTRY_BG)
        border  = self._theme(DARK_BORDER, GROUP4_LT_BORDER)
        pri     = self._theme(DARK_BTN_PRIMARY, GROUP4_LT_BUTTON_PRIMARY)
        pri_h   = self._theme(DARK_BTN_HOVER, GROUP4_LT_BTNHOVER)
        pri_tc  = self._theme(DARK_PRIMARY_TEXT, GROUP4_LT_PRIMARY_TEXT)
        muted   = self._theme(DARK_MUTED, GROUP4_LT_MUTED)
        sec     = self._theme(DARK_BTN_SECONDARY, GROUP4_LT_BTN_SECONDARY)
        sec_h   = self._theme(DARK_BTN_SECONDARY_HOVER, GROUP4_LT_BTN_SECONDARY_HOVER)
        bg_col  = self._theme(DARK_BACKGROUND, GROUP4_LT_BG)

        modal = customtkinter.CTkToplevel(self.root)
        modal.title("Account Recovery — W.I.L.D. CARE")
        modal.geometry("500x480")
        modal.resizable(False, False)
        modal.configure(fg_color=bg_col)
        modal.after(10, modal.lift)
        modal.attributes("-topmost", True)

        rx = self.root.winfo_x()
        ry = self.root.winfo_y()
        modal.geometry(f"+{max(0, rx + 180)}+{max(0, ry + 80)}")

        hdr = customtkinter.CTkFrame(modal, fg_color=pri, corner_radius=0, height=60)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        customtkinter.CTkLabel(
            hdr, text="✉ Account Recovery — 6-Digit Email Code",
            font=self._f(15, "bold"), text_color=pri_tc
        ).pack(side="left", padx=18, pady=12)

        body = customtkinter.CTkFrame(modal, fg_color=card_bg, corner_radius=12)
        body.pack(fill="both", expand=True, padx=18, pady=14)

        _state = {"username": ""}

        # Step 1: Request Code
        step1 = customtkinter.CTkFrame(body, fg_color="transparent")
        step1.pack(fill="both", expand=True, padx=16, pady=14)

        customtkinter.CTkLabel(
            step1,
            text="Type your Full Name, Email, below. We will send a 6-digit recovery code to your registered email address.",
            font=self._f(13), text_color=muted, wraplength=430, justify="left"
        ).pack(anchor="w", pady=(0, 14))

        customtkinter.CTkLabel(
            step1, text="Full Name, Email", font=self._f(14, "bold"), text_color=t_col
        ).pack(anchor="w")

        entry_user = customtkinter.CTkEntry(
            step1, placeholder_text="Type your name and email here",
            font=self._f(14), height=44,
            fg_color=e_bg, border_color=border, text_color=t_col, corner_radius=8
        )
        entry_user.pack(fill="x", pady=(4, 12))

        cur_u = self.entry_signin_user.get().strip()
        if cur_u:
            entry_user.insert(0, cur_u)

        lbl_s1 = customtkinter.CTkLabel(
            step1, text="", font=self._f(12), text_color=COLOR_DANGER, wraplength=430
        )
        lbl_s1.pack(pady=(0, 8))

        btn_send = customtkinter.CTkButton(
            step1, text="Send 6-Digit Code",
            font=self._f(15, "bold"),
            fg_color=pri, hover_color=pri_h, text_color=pri_tc,
            height=50, corner_radius=10
        )
        btn_send.pack(fill="x", pady=(0, 8))

        customtkinter.CTkButton(
            step1, text="Cancel", font=self._f(13),
            fg_color=sec, hover_color=sec_h, text_color=t_col,
            height=38, corner_radius=8,
            command=modal.destroy
        ).pack(fill="x")

        # Step 2: Enter 6-digit Code + Set New Password
        step2 = customtkinter.CTkFrame(body, fg_color="transparent")
        email_lbl = customtkinter.CTkLabel(
            step2, text="", font=self._f(12), text_color=COLOR_SUCCESS, wraplength=430, justify="left"
        )
        email_lbl.pack(anchor="w", pady=(0, 10))

        customtkinter.CTkLabel(
            step2, text="6-Digit Code", font=self._f(14, "bold"), text_color=t_col
        ).pack(anchor="w")

        entry_otp = customtkinter.CTkEntry(
            step2, placeholder_text="e.g. 123456",
            font=("Courier New", 20, "bold"), height=48,
            fg_color=e_bg, border_color=border, text_color=t_col, corner_radius=8
        )
        entry_otp.pack(fill="x", pady=(4, 12))

        pw_row = customtkinter.CTkFrame(step2, fg_color="transparent")
        pw_row.pack(fill="x", pady=(0, 6))
        pw_row.columnconfigure(0, weight=1)
        pw_row.columnconfigure(1, weight=1)

        customtkinter.CTkLabel(pw_row, text="New Password", font=self._f(12, "bold"), text_color=t_col).grid(row=0, column=0, sticky="w", padx=(0, 4))
        customtkinter.CTkLabel(pw_row, text="Confirm Password", font=self._f(12, "bold"), text_color=t_col).grid(row=0, column=1, sticky="w", padx=(4, 0))

        entry_new_pw = customtkinter.CTkEntry(pw_row, placeholder_text="Min 4 chars", font=self._f(12), height=40, fg_color=e_bg, border_color=border, text_color=t_col, corner_radius=8, show="*")
        entry_new_pw.grid(row=1, column=0, sticky="ew", padx=(0, 4))

        entry_conf_pw = customtkinter.CTkEntry(pw_row, placeholder_text="Re-type", font=self._f(12), height=40, fg_color=e_bg, border_color=border, text_color=t_col, corner_radius=8, show="*")
        entry_conf_pw.grid(row=1, column=1, sticky="ew", padx=(4, 0))

        lbl_s2 = customtkinter.CTkLabel(step2, text="", font=self._f(12), text_color=COLOR_DANGER, wraplength=430)
        lbl_s2.pack(pady=(4, 6))

        btn_reset = customtkinter.CTkButton(
            step2, text="Verify Code & Reset Password",
            font=self._f(15, "bold"),
            fg_color=pri, hover_color=pri_h, text_color=pri_tc,
            height=50, corner_radius=10
        )
        btn_reset.pack(fill="x", pady=(0, 6))

        nav = customtkinter.CTkFrame(step2, fg_color="transparent")
        nav.pack(fill="x")
        btn_back = customtkinter.CTkButton(nav, text="Back / Request New Code", font=self._f(11), fg_color=sec, hover_color=sec_h, text_color=t_col, height=32, corner_radius=8)
        btn_back.pack(side="left", fill="x", expand=True, padx=(0, 4))
        customtkinter.CTkButton(nav, text="Cancel", font=self._f(11), fg_color=sec, hover_color=sec_h, text_color=t_col, height=32, corner_radius=8, command=modal.destroy).pack(side="left", fill="x", expand=True, padx=(4, 0))

        def show_step2(masked_email):
            step1.pack_forget()
            step2.pack(fill="both", expand=True, padx=16, pady=14)

        def go_back():
            step2.pack_forget()
            step1.pack(fill="both", expand=True, padx=16, pady=14)
            lbl_s1.configure(text="")
            lbl_s2.configure(text="")
            entry_otp.delete(0, "end")
            entry_new_pw.delete(0, "end")
            entry_conf_pw.delete(0, "end")

        def do_send():
            u = entry_user.get().strip()
            if not u:
                lbl_s1.configure(text="Please enter your username.")
                return
            btn_send.configure(state="disabled", text="Sending code...")
            lbl_s1.configure(text="")
            modal.update()
            ok, result = group4database.send_password_reset_otp(u)
            btn_send.configure(state="normal", text="Send 6-Digit Code")
            if ok:
                _state["username"] = u
                email_lbl.configure(text=f"✔ Code sent to: {result}\nCode expires in 15 minutes. Check your inbox and spam folder.", text_color=COLOR_SUCCESS)
                show_step2(result)
            else:
                lbl_s1.configure(text=result)

        def do_reset():
            otp = entry_otp.get().strip()
            p1  = entry_new_pw.get().strip()
            p2  = entry_conf_pw.get().strip()
            if not otp:
                lbl_s2.configure(text="Please enter the 6-digit code.")
                return
            ok, msg = group4database.verify_and_reset_password_with_otp(_state["username"], otp, p1, p2)
            if ok:
                messagebox.showinfo("Password Reset", "Your password has been reset successfully!\nYou may now sign in.")
                modal.destroy()
                self.entry_signin_user.delete(0, "end")
                self.entry_signin_user.insert(0, _state["username"])
                self.entry_signin_pass.delete(0, "end")
                self.entry_signin_pass.focus_set()
                self.lbl_attempts.configure(text="Password reset! Sign in with your new password.", text_color=COLOR_SUCCESS)
            else:
                lbl_s2.configure(text=msg)

        btn_send.configure(command=do_send)
        btn_reset.configure(command=do_reset)
        btn_back.configure(command=go_back)
        entry_user.bind("<Return>", lambda e: do_send())
        entry_otp.bind("<Return>", lambda e: do_reset())

    def handle_signin(self):
        username = self.entry_signin_user.get().strip()
        password = self.entry_signin_pass.get().strip()
        if not username or not password:
            self.lbl_attempts.configure(text="Please enter both your username and password.", text_color=COLOR_DANGER)
            return

        success, result = group4database.authenticate_user(username, password)
        if success:
            self.root.destroy()
            self.on_login_success(result)
        else:
            error_msg = result if isinstance(result, str) else "Invalid username or password."
            if "locked" in error_msg.lower():
                messagebox.showerror("Account Locked (15 Minutes)", error_msg)
                self.lbl_attempts.configure(text="Account is temporarily locked for 15 minutes.", text_color=COLOR_DANGER)
            else:
                self.lbl_attempts.configure(text=error_msg, text_color=COLOR_DANGER)
            self.entry_signin_pass.delete(0, "end")

    def handle_resident_register(self):
        name  = self.entry_res_name.get().strip()
        email = self.entry_res_email.get().strip()
        pwd   = self.entry_res_pass.get().strip()
        conf  = self.entry_res_conf.get().strip()

        ok, msg = group4database.register_resident_user(name, pwd, conf, email)
        if ok:
            messagebox.showinfo("Account Created!", f"Welcome to W.I.L.D. CARE, {name}!\n\nYou can now sign in using your Full Name.")
            self.tabview.set("  Sign in  ")
            self.entry_signin_user.delete(0, "end")
            self.entry_signin_user.insert(0, name)
            self.entry_signin_pass.delete(0, "end")
            self.entry_signin_pass.focus_set()
            for e in [self.entry_res_name, self.entry_res_email, self.entry_res_pass, self.entry_res_conf]:
                e.delete(0, "end")
            self.lbl_res_msg.configure(text="")
        else:
            self.lbl_res_msg.configure(text=msg, text_color=COLOR_DANGER)

    def run(self):
        self.root.mainloop()
