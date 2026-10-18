import os
import sys
import customtkinter
from tkinter import ttk, messagebox, filedialog
from datetime import date, datetime
from PIL import Image
import group4database


COLOR_PRIMARY     = "#1E6F5C"
COLOR_SECONDARY   = "#289672"
COLOR_ACCENT      = "#29BB89"
COLOR_DANGER      = "#E74C3C"
COLOR_DANGER_HVR  = "#C0392B"
COLOR_WARNING     = "#F39C12"
COLOR_WARNING_HVR = "#D68910"
COLOR_BG_DARK     = "#101626"
COLOR_BG_CARD     = "#16213E"
COLOR_TEXT        = "#EAEAEA"
COLOR_ENTRY_BG    = "#0F3460"
COLOR_TREE_BG     = "#141C2E"
COLOR_TREE_FG     = "#EAEAEA"
COLOR_TREE_SEL    = "#1E6F5C"


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


class AdminDashboardWindow:
    def __init__(self, user_info, on_logout_callback):
        self.user_info = user_info
        self.on_logout_callback = on_logout_callback
        self.selected_record_id = None
        self.selected_flood_id = None
        self._drag_item = None
        self._drag_start_y = 0
        self._is_dragging = False

        # Main window
        self.root = customtkinter.CTk()
        self.root.title(f"W.I.L.D. CARE — {self.user_info.get('role', 'Staff')} Portal")
        self.root.after(300, lambda: _set_app_icon(self.root))
        self.root.geometry("1240x780")
        self.root.minsize(1050, 680)
        self.root.configure(fg_color=COLOR_BG_DARK)

        # Center on screen
        self.root.update_idletasks()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = max(0, (screen_w - 1240) // 2)
        y = max(0, (screen_h - 780) // 2)
        self.root.geometry(f"1240x780+{x}+{y}")

        # Clean shutdown on window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Atmospheric background using flood.jpg
        self._set_background_image("flood.jpg")

        self._build_header()
        self._build_content()

        # Load initial data
        self.load_records()
        self.load_flood_records()

    def _set_background_image(self, image_filename="flood.jpg"):
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            img_path = os.path.join(script_dir, image_filename)
            if not os.path.exists(img_path):
                img_path = image_filename

            pil_img = Image.open(img_path)
            sw = max(1920, self.root.winfo_screenwidth())
            sh = max(1080, self.root.winfo_screenheight())
            self.bg_image = customtkinter.CTkImage(
                light_image=pil_img,
                dark_image=pil_img,
                size=(sw, sh)
            )
            self.bg_label = customtkinter.CTkLabel(self.root, text="", image=self.bg_image)
            self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        except Exception as e:
            print(f"[!] Background image warning: {e}")

    def on_close(self):
        try:
            self.root.destroy()
        except Exception:
            pass
        sys.exit(0)

    def _build_header(self):
        header = customtkinter.CTkFrame(self.root, fg_color=COLOR_PRIMARY, corner_radius=0, height=65)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        # Branding
        brand_frame = customtkinter.CTkFrame(header, fg_color="transparent")
        brand_frame.pack(side="left", padx=20, pady=8)

        lbl_title = customtkinter.CTkLabel(
            brand_frame,
            text="🌊  W.I.L.D. CARE  —  Health Worker & LGU Administration Dashboard",
            font=("Segoe UI", 16, "bold"),
            text_color="white"
        )
        lbl_title.pack(anchor="w")

        lbl_sub = customtkinter.CTkLabel(
            brand_frame,
            text="Pangasinan Disease Surveillance  •  Live Water-Level Monitoring & Early-Warning Control",
            font=("Segoe UI", 10),
            text_color="#C8E6C9"
        )
        lbl_sub.pack(anchor="w")

        # Right side controls
        right_frame = customtkinter.CTkFrame(header, fg_color="transparent")
        right_frame.pack(side="right", padx=20, pady=10)

        badge = customtkinter.CTkFrame(right_frame, fg_color="#134B3E", corner_radius=8)
        badge.pack(side="left", padx=(0, 10))

        role_name = self.user_info.get("role", "Staff")
        off_id = self.user_info.get("official_id", "")
        badge_text = f"👤 {self.user_info.get('full_name', 'Staff')}  •  [{role_name}]"
        if off_id and off_id != "RESIDENT":
            badge_text += f" (ID: {off_id})"

        user_lbl = customtkinter.CTkLabel(
            badge,
            text=badge_text,
            font=("Segoe UI", 11, "bold"),
            text_color="white"
        )
        user_lbl.pack(padx=12, pady=6)

        btn_logout = customtkinter.CTkButton(
            right_frame,
            text="🚪 Logout",
            font=("Segoe UI", 11, "bold"),
            fg_color="#A93226",
            hover_color="#922B21",
            width=80,
            height=32,
            corner_radius=8,
            command=self.handle_logout
        )
        btn_logout.pack(side="left")

    def _build_content(self):
        content_container = customtkinter.CTkFrame(self.root, fg_color="transparent")
        content_container.pack(fill="both", expand=True, padx=15, pady=(5, 12))

        self.tabview = customtkinter.CTkTabview(
            content_container,
            fg_color=("#121929", "#131C2E"),
            segmented_button_selected_color=COLOR_PRIMARY,
            segmented_button_selected_hover_color=COLOR_SECONDARY,
            segmented_button_unselected_color="#0F2537",
            segmented_button_fg_color="#0A1826"
        )
        self.tabview.pack(fill="both", expand=True)

        self.tab_patients = self.tabview.add("📋  Patient Clinical Records & Surveillance")
        self.tab_flood    = self.tabview.add("🌊  Pangasinan Flood & Rainfall Management")

        self.tabview.set("📋  Patient Clinical Records & Surveillance")

        self._build_patient_tab(self.tab_patients)
        self._build_flood_management_tab(self.tab_flood)

    # TAB 1: PATIENT DISEASE RECORDS & CLINICAL CRUD

    def _build_patient_tab(self, parent):
        content = customtkinter.CTkFrame(parent, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=10, pady=10)
        content.columnconfigure(0, weight=1)  # Form
        content.columnconfigure(1, weight=3)  # Table & stats
        content.rowconfigure(0, weight=1)

        # ── LEFT PANEL: CRUD FORM ──
        left_panel = customtkinter.CTkFrame(content, fg_color=COLOR_BG_CARD,
                                             corner_radius=12, border_width=1,
                                             border_color=COLOR_PRIMARY)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        title = customtkinter.CTkLabel(
            left_panel,
            text="📋  Patient Record Form",
            font=("Segoe UI", 15, "bold"),
            text_color=COLOR_ACCENT
        )
        title.pack(pady=(15, 5), padx=20, anchor="w")

        sep = customtkinter.CTkFrame(left_panel, fg_color=COLOR_PRIMARY, height=2)
        sep.pack(fill="x", padx=20, pady=(0, 10))

        # Inputs
        self.entry_name = self._create_input(left_panel, "Full Name", "e.g. Juan Dela Cruz")
        self.entry_age = self._create_input(left_panel, "Age", "e.g. 25")
        self.combo_sex = self._create_combobox(left_panel, "Sex", ["Male", "Female", "Other"], "Male")
        self.entry_barangay = self._create_input(left_panel, "Barangay / Area", "e.g. Brgy. Pantal, Dagupan")
        self.entry_disease = self._create_input(left_panel, "Disease / Illness", "e.g. Leptospirosis")
        self.combo_status = self._create_combobox(left_panel, "Case Status", group4database.STATUS_OPTIONS, "Under Observation")
        self.entry_date = self._create_input(left_panel, "Date Logged", str(date.today()))
        self.entry_date.insert(0, str(date.today()))

        # Action Buttons
        btn_frame = customtkinter.CTkFrame(left_panel, fg_color="transparent")
        btn_frame.pack(padx=20, pady=(12, 10), fill="x")

        self.btn_add = customtkinter.CTkButton(
            btn_frame,
            text="➕  Add Record",
            font=("Segoe UI", 12, "bold"),
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_SECONDARY,
            height=36,
            corner_radius=8,
            command=self.create_record
        )
        self.btn_add.pack(fill="x", pady=(0, 5))

        self.btn_update = customtkinter.CTkButton(
            btn_frame,
            text="✏️  Update Record",
            font=("Segoe UI", 12, "bold"),
            fg_color=COLOR_WARNING,
            hover_color=COLOR_WARNING_HVR,
            height=36,
            corner_radius=8,
            command=self.update_record
        )
        self.btn_update.pack(fill="x", pady=(0, 5))

        self.btn_delete = customtkinter.CTkButton(
            btn_frame,
            text="🗑️  Delete Record",
            font=("Segoe UI", 12, "bold"),
            fg_color=COLOR_DANGER,
            hover_color=COLOR_DANGER_HVR,
            height=36,
            corner_radius=8,
            command=self.delete_record
        )
        self.btn_delete.pack(fill="x", pady=(0, 5))

        self.btn_clear = customtkinter.CTkButton(
            btn_frame,
            text="🔄  Clear Inputs",
            font=("Segoe UI", 12),
            fg_color="#334155",
            hover_color="#475569",
            height=32,
            corner_radius=8,
            command=self.clear_form
        )
        self.btn_clear.pack(fill="x")

        right_panel = customtkinter.CTkFrame(content, fg_color="transparent")
        right_panel.grid(row=0, column=1, sticky="nsew")
        right_panel.rowconfigure(3, weight=1)
        right_panel.columnconfigure(0, weight=1)

        # 1. Summary Cards
        stats_frame = customtkinter.CTkFrame(right_panel, fg_color=COLOR_BG_CARD, corner_radius=12)
        stats_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        stats_frame.columnconfigure((0, 1, 2, 3), weight=1)

        self.lbl_stat_total = self._create_card(stats_frame, 0, "Total Cases", "0", COLOR_ACCENT)
        self.lbl_stat_obs   = self._create_card(stats_frame, 1, "Under Observation", "0", COLOR_WARNING)
        self.lbl_stat_adm   = self._create_card(stats_frame, 2, "Admitted", "0", COLOR_DANGER)
        self.lbl_stat_rec   = self._create_card(stats_frame, 3, "Recovered", "0", "#38D9A9")

        # 2. Search, Filter & Export Controls
        ctrl_frame = customtkinter.CTkFrame(right_panel, fg_color=COLOR_BG_CARD, corner_radius=12)
        ctrl_frame.grid(row=1, column=0, sticky="ew", pady=(0, 6))

        lbl_s = customtkinter.CTkLabel(ctrl_frame, text="Search:", font=("Segoe UI", 11, "bold"), text_color=COLOR_TEXT)
        lbl_s.pack(side="left", padx=(15, 5), pady=8)

        self.entry_search = customtkinter.CTkEntry(
            ctrl_frame, placeholder_text="Name, disease, barangay...", font=("Segoe UI", 11),
            height=32, fg_color=COLOR_ENTRY_BG, border_color=COLOR_PRIMARY, text_color="white", corner_radius=6
        )
        self.entry_search.pack(side="left", fill="x", expand=True, padx=5, pady=8)
        self.entry_search.bind("<Return>", lambda e: self.search_records())

        self.combo_filter = customtkinter.CTkComboBox(
            ctrl_frame, values=["All Fields", "Name", "Disease", "Barangay"],
            font=("Segoe UI", 10), height=32, width=120, fg_color=COLOR_ENTRY_BG,
            border_color=COLOR_PRIMARY, button_color=COLOR_PRIMARY, text_color="white",
            dropdown_fg_color=COLOR_BG_CARD, corner_radius=6, state="readonly"
        )
        self.combo_filter.set("All Fields")
        self.combo_filter.pack(side="left", padx=5, pady=8)

        btn_search = customtkinter.CTkButton(
            ctrl_frame, text="🔍 Search", font=("Segoe UI", 11, "bold"),
            fg_color=COLOR_PRIMARY, hover_color=COLOR_SECONDARY, width=75, height=32,
            corner_radius=6, command=self.search_records
        )
        btn_search.pack(side="left", padx=5, pady=8)

        btn_reset = customtkinter.CTkButton(
            ctrl_frame, text="Reset", font=("Segoe UI", 11),
            fg_color="#334155", hover_color="#475569", width=65, height=32,
            corner_radius=6, command=self.reset_search
        )
        btn_reset.pack(side="left", padx=5, pady=8)

        btn_export = customtkinter.CTkButton(
            ctrl_frame, text="📥 Export CSV", font=("Segoe UI", 11, "bold"),
            fg_color="#1E8449", hover_color="#196F3D", width=95, height=32,
            corner_radius=6, command=self.export_csv
        )
        btn_export.pack(side="right", padx=(5, 15), pady=8)

        # 3. Futuristic Drag & Drop / Triage HUD Control Bar
        triage_bar = customtkinter.CTkFrame(right_panel, fg_color="#111B2E", corner_radius=10, border_width=1, border_color="#1E40AF")
        triage_bar.grid(row=2, column=0, sticky="ew", pady=(0, 6))

        # Left status badge and dynamic action indicator
        status_left = customtkinter.CTkFrame(triage_bar, fg_color="transparent")
        status_left.pack(side="left", padx=10, pady=5)

        badge_dnd = customtkinter.CTkLabel(
            status_left,
            text="🔀 DRAG & DROP ARRANGE",
            font=("Segoe UI", 9, "bold"),
            text_color="#38BDF8",
            fg_color="#0F2B48",
            corner_radius=6,
            padx=8,
            pady=3
        )
        badge_dnd.pack(side="left", padx=(0, 8))

        self.lbl_arrange_status = customtkinter.CTkLabel(
            status_left,
            text="Drag any row to reorder patient queue • Auto-saves arrangement",
            font=("Segoe UI", 10),
            text_color="#94A3B8"
        )
        self.lbl_arrange_status.pack(side="left")

        # Right control buttons for smart triage & ordering
        btn_box = customtkinter.CTkFrame(triage_bar, fg_color="transparent")
        btn_box.pack(side="right", padx=10, pady=5)

        btn_triage = customtkinter.CTkButton(
            btn_box,
            text="⚡ Smart Triage",
            font=("Segoe UI", 10, "bold"),
            fg_color="#0D9488",
            hover_color="#0F766E",
            width=105,
            height=28,
            corner_radius=6,
            command=self.smart_triage_auto_arrange
        )
        btn_triage.pack(side="left", padx=2)

        btn_up = customtkinter.CTkButton(
            btn_box,
            text="▲ Up",
            font=("Segoe UI", 10, "bold"),
            fg_color="#1E293B",
            hover_color="#334155",
            width=48,
            height=28,
            corner_radius=6,
            command=self.move_row_up
        )
        btn_up.pack(side="left", padx=2)

        btn_down = customtkinter.CTkButton(
            btn_box,
            text="▼ Down",
            font=("Segoe UI", 10, "bold"),
            fg_color="#1E293B",
            hover_color="#334155",
            width=50,
            height=28,
            corner_radius=6,
            command=self.move_row_down
        )
        btn_down.pack(side="left", padx=2)

        btn_top = customtkinter.CTkButton(
            btn_box,
            text="🔝 Prioritize",
            font=("Segoe UI", 10, "bold"),
            fg_color="#B91C1C",
            hover_color="#991B1B",
            width=80,
            height=28,
            corner_radius=6,
            command=self.move_row_to_top
        )
        btn_top.pack(side="left", padx=2)

        btn_reset_order = customtkinter.CTkButton(
            btn_box,
            text="🔄 Chrono",
            font=("Segoe UI", 10),
            fg_color="#1F2937",
            hover_color="#374151",
            width=65,
            height=28,
            corner_radius=6,
            command=self.reset_queue_order
        )
        btn_reset_order.pack(side="left", padx=(2, 0))

        # 4. Patient Table
        table_frame = customtkinter.CTkFrame(right_panel, fg_color=COLOR_BG_CARD, corner_radius=12)
        table_frame.grid(row=3, column=0, sticky="nsew")

        cols = ("ID", "Full Name", "Age", "Sex", "Barangay", "Disease", "Status", "Date Logged")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Admin.Treeview",
            background=COLOR_TREE_BG, foreground=COLOR_TREE_FG, fieldbackground=COLOR_TREE_BG,
            font=("Segoe UI", 10), rowheight=28, borderwidth=0
        )
        style.configure(
            "Admin.Treeview.Heading",
            background=COLOR_PRIMARY, foreground="white",
            font=("Segoe UI", 10, "bold"), borderwidth=0, relief="flat"
        )
        style.map("Admin.Treeview", background=[("selected", COLOR_TREE_SEL)])

        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", style="Admin.Treeview", selectmode="browse")

        # Color-coded tags for clinical urgency, drag-and-drop hover, and active dragging
        self.tree.tag_configure("admitted", background="#36171E", foreground="#FF9EAA")
        self.tree.tag_configure("critical_obs", background="#3A2914", foreground="#FCD34D")
        self.tree.tag_configure("observation", background="#152438", foreground="#93C5FD")
        self.tree.tag_configure("recovered", background="#122A1E", foreground="#86EFAC")
        self.tree.tag_configure("dragging", background="#0C3B53", foreground="#67E8F9")
        self.tree.tag_configure("drag_target", background="#0E7490", foreground="#FFFFFF")

        self.tree.heading("ID", text="ID", anchor="center")
        self.tree.heading("Full Name", text="Full Name", anchor="w")
        self.tree.heading("Age", text="Age", anchor="center")
        self.tree.heading("Sex", text="Sex", anchor="center")
        self.tree.heading("Barangay", text="Barangay / Location", anchor="w")
        self.tree.heading("Disease", text="Diagnosed Disease", anchor="w")
        self.tree.heading("Status", text="Case Status", anchor="center")
        self.tree.heading("Date Logged", text="Date", anchor="center")

        self.tree.column("ID", width=40, anchor="center")
        self.tree.column("Full Name", width=140, anchor="w")
        self.tree.column("Age", width=45, anchor="center")
        self.tree.column("Sex", width=55, anchor="center")
        self.tree.column("Barangay", width=150, anchor="w")
        self.tree.column("Disease", width=140, anchor="w")
        self.tree.column("Status", width=120, anchor="center")
        self.tree.column("Date Logged", width=90, anchor="center")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        scrollbar.pack(side="right", fill="y", pady=10, padx=(0, 10))

        # Event bindings for selection, drag & drop, and double-click clinical dossier
        self.tree.bind("<<TreeviewSelect>>", self.on_row_select)
        self.tree.bind("<ButtonPress-1>", self._on_dnd_press)
        self.tree.bind("<B1-Motion>", self._on_dnd_motion)
        self.tree.bind("<ButtonRelease-1>", self._on_dnd_release)
        self.tree.bind("<Double-1>", self._on_tree_double_click)

        # 5. Bottom Record Counter & Queue Position Status
        bottom_bar = customtkinter.CTkFrame(right_panel, fg_color="transparent")
        bottom_bar.grid(row=4, column=0, sticky="ew", pady=(4, 0))
        self.lbl_record_count = customtkinter.CTkLabel(bottom_bar, text="Total Records: 0", font=("Segoe UI", 10), text_color="#AAAAAA")
        self.lbl_record_count.pack(side="left", padx=5)

        self.lbl_queue_pos = customtkinter.CTkLabel(
            bottom_bar,
            text="💡 Tip: Drag rows to arrange files • Double-click row for Quick Dossier & Flood Risk",
            font=("Segoe UI", 10),
            text_color="#38BDF8"
        )
        self.lbl_queue_pos.pack(side="right", padx=10)

    # TAB 2: PANGASINAN FLOOD & RAINFALL MANAGEMENT

    def _build_flood_management_tab(self, parent):
        content = customtkinter.CTkFrame(parent, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=10, pady=10)
        content.columnconfigure(0, weight=1)  # Left: Flood Log Form
        content.columnconfigure(1, weight=3)  # Right: Stats & Flood Table
        content.rowconfigure(0, weight=1)

        # ── LEFT PANEL: FLOOD LOG & UPDATE FORM ──
        left_panel = customtkinter.CTkFrame(content, fg_color=COLOR_BG_CARD,
                                             corner_radius=12, border_width=1,
                                             border_color=COLOR_PRIMARY)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        title = customtkinter.CTkLabel(
            left_panel,
            text="🌊  Flood & Rainfall Logger",
            font=("Segoe UI", 15, "bold"),
            text_color=COLOR_ACCENT
        )
        title.pack(pady=(15, 5), padx=20, anchor="w")

        sep = customtkinter.CTkFrame(left_panel, fg_color=COLOR_PRIMARY, height=2)
        sep.pack(fill="x", padx=20, pady=(0, 10))

        # Inputs
        self.combo_flood_city = self._create_combobox(
            left_panel, "City / Municipality",
            ["Dagupan City", "Calasiao", "Lingayen", "Santa Barbara", "Malasiqui", "Binmaley", "Bayambang", "San Carlos City", "Urdaneta City", "Bugallon"],
            "Dagupan City"
        )
        self.entry_flood_brgy = self._create_input(left_panel, "Barangay / Area", "e.g. Brgy. Pantal")
        self.entry_flood_water = self._create_input(left_panel, "Water Level (meters)", "e.g. 1.85")
        self.entry_flood_rain = self._create_input(left_panel, "Rainfall Rate (mm/h)", "e.g. 32.0")

        self.combo_flood_status = self._create_combobox(left_panel, "Water Trend", group4database.FLOOD_STATUS_OPTIONS, "Rising")
        self.combo_flood_alert = self._create_combobox(left_panel, "Alert Level", group4database.FLOOD_ALERT_LEVELS, group4database.FLOOD_ALERT_WARNING)
        self.entry_flood_advisory = self._create_input(left_panel, "Early-Warning Advisory", "e.g. River overflow; prepare evacuation.")

        # Action Buttons
        btn_frame = customtkinter.CTkFrame(left_panel, fg_color="transparent")
        btn_frame.pack(padx=20, pady=(10, 10), fill="x")

        self.btn_add_flood = customtkinter.CTkButton(
            btn_frame,
            text="➕  Log Flood Reading",
            font=("Segoe UI", 12, "bold"),
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_SECONDARY,
            height=36,
            corner_radius=8,
            command=self.create_flood_record
        )
        self.btn_add_flood.pack(fill="x", pady=(0, 5))

        self.btn_update_flood = customtkinter.CTkButton(
            btn_frame,
            text="✏️  Update Area Reading",
            font=("Segoe UI", 12, "bold"),
            fg_color=COLOR_WARNING,
            hover_color=COLOR_WARNING_HVR,
            height=36,
            corner_radius=8,
            command=self.update_flood_record
        )
        self.btn_update_flood.pack(fill="x", pady=(0, 5))

        self.btn_delete_flood = customtkinter.CTkButton(
            btn_frame,
            text="🗑️  Delete Reading",
            font=("Segoe UI", 12, "bold"),
            fg_color=COLOR_DANGER,
            hover_color=COLOR_DANGER_HVR,
            height=36,
            corner_radius=8,
            command=self.delete_flood_record
        )
        self.btn_delete_flood.pack(fill="x", pady=(0, 5))

        self.btn_clear_flood = customtkinter.CTkButton(
            btn_frame,
            text="🔄  Clear Inputs",
            font=("Segoe UI", 12),
            fg_color="#334155",
            hover_color="#475569",
            height=32,
            corner_radius=8,
            command=self.clear_flood_form
        )
        self.btn_clear_flood.pack(fill="x")

        # ── RIGHT PANEL: FLOOD STATS & TABLE ──
        right_panel = customtkinter.CTkFrame(content, fg_color="transparent")
        right_panel.grid(row=0, column=1, sticky="nsew")
        right_panel.rowconfigure(2, weight=1)
        right_panel.columnconfigure(0, weight=1)

        # 1. Flood Stats
        stats_frame = customtkinter.CTkFrame(right_panel, fg_color=COLOR_BG_CARD, corner_radius=12)
        stats_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        stats_frame.columnconfigure((0, 1, 2, 3), weight=1)

        self.lbl_flood_total    = self._create_card(stats_frame, 0, "Monitored Areas", "0", COLOR_ACCENT)
        self.lbl_flood_critical = self._create_card(stats_frame, 1, "🚨 Critical / Evacuate", "0", COLOR_DANGER)
        self.lbl_flood_warning  = self._create_card(stats_frame, 2, "⚠️ Warning / High Water", "0", COLOR_WARNING)
        self.lbl_flood_peak     = self._create_card(stats_frame, 3, "🌊 Peak Water Height", "0.0m", "#38D9A9")

        # 2. Controls & Broadcast Button
        ctrl_frame = customtkinter.CTkFrame(right_panel, fg_color=COLOR_BG_CARD, corner_radius=12)
        ctrl_frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        lbl_c = customtkinter.CTkLabel(ctrl_frame, text="Filter City:", font=("Segoe UI", 10, "bold"), text_color=COLOR_TEXT)
        lbl_c.pack(side="left", padx=(15, 5), pady=8)

        cities = ["All Cities"] + group4database.get_unique_flood_cities()
        self.combo_admin_flood_city = customtkinter.CTkComboBox(
            ctrl_frame, values=cities, font=("Segoe UI", 10), height=30, width=150,
            fg_color=COLOR_ENTRY_BG, border_color=COLOR_PRIMARY, button_color=COLOR_PRIMARY,
            state="readonly", command=lambda _: self.load_flood_records()
        )
        self.combo_admin_flood_city.set("All Cities")
        self.combo_admin_flood_city.pack(side="left", padx=5, pady=8)

        self.entry_search_flood_admin = customtkinter.CTkEntry(
            ctrl_frame, placeholder_text="Search barangay...", font=("Segoe UI", 10),
            height=30, fg_color=COLOR_ENTRY_BG, border_color=COLOR_PRIMARY
        )
        self.entry_search_flood_admin.pack(side="left", fill="x", expand=True, padx=8, pady=8)
        self.entry_search_flood_admin.bind("<KeyRelease>", lambda _: self.load_flood_records())

        btn_broadcast = customtkinter.CTkButton(
            ctrl_frame, text="📢 Broadcast Early Alert", font=("Segoe UI", 11, "bold"),
            fg_color="#C0392B", hover_color="#962D22", width=160, height=32,
            corner_radius=6, command=self.broadcast_sample_flood_alert
        )
        btn_broadcast.pack(side="right", padx=(5, 15), pady=8)

        btn_refresh_fl = customtkinter.CTkButton(
            ctrl_frame, text="🔄 Refresh", font=("Segoe UI", 10, "bold"),
            fg_color=COLOR_PRIMARY, hover_color=COLOR_SECONDARY, width=75, height=30,
            corner_radius=6, command=self.load_flood_records
        )
        btn_refresh_fl.pack(side="right", padx=5, pady=8)

        # 3. Table of Flood Records
        table_frame = customtkinter.CTkFrame(right_panel, fg_color=COLOR_BG_CARD, corner_radius=12)
        table_frame.grid(row=2, column=0, sticky="nsew")

        cols = ("id", "city", "barangay", "water_level", "depth_desc", "rainfall", "status", "alert", "warning", "updated")
        self.flood_admin_tree = ttk.Treeview(table_frame, columns=cols, show="headings", style="Admin.Treeview", selectmode="browse")

        self.flood_admin_tree.heading("id", text="ID")
        self.flood_admin_tree.heading("city", text="City / Municipality", anchor="w")
        self.flood_admin_tree.heading("barangay", text="Barangay / Area", anchor="w")
        self.flood_admin_tree.heading("water_level", text="Level (m)", anchor="center")
        self.flood_admin_tree.heading("depth_desc", text="Depth", anchor="w")
        self.flood_admin_tree.heading("rainfall", text="Rainfall", anchor="center")
        self.flood_admin_tree.heading("status", text="Trend", anchor="center")
        self.flood_admin_tree.heading("alert", text="Alert Level", anchor="center")
        self.flood_admin_tree.heading("warning", text="Early-Warning Advisory", anchor="w")
        self.flood_admin_tree.heading("updated", text="Updated", anchor="center")

        self.flood_admin_tree.column("id", width=35, anchor="center")
        self.flood_admin_tree.column("city", width=105, anchor="w")
        self.flood_admin_tree.column("barangay", width=125, anchor="w")
        self.flood_admin_tree.column("water_level", width=65, anchor="center")
        self.flood_admin_tree.column("depth_desc", width=120, anchor="w")
        self.flood_admin_tree.column("rainfall", width=75, anchor="center")
        self.flood_admin_tree.column("status", width=65, anchor="center")
        self.flood_admin_tree.column("alert", width=115, anchor="center")
        self.flood_admin_tree.column("warning", width=210, anchor="w")
        self.flood_admin_tree.column("updated", width=75, anchor="center")

        scroll_fl = ttk.Scrollbar(table_frame, orient="vertical", command=self.flood_admin_tree.yview)
        self.flood_admin_tree.configure(yscrollcommand=scroll_fl.set)
        self.flood_admin_tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        scroll_fl.pack(side="right", fill="y", pady=10, padx=(0, 10))

        self.flood_admin_tree.bind("<<TreeviewSelect>>", self.on_flood_row_select)

    # FLOOD MANAGEMENT CRUD METHODS

    def create_flood_record(self):
        city = self.combo_flood_city.get().strip()
        brgy = self.entry_flood_brgy.get().strip()
        water_str = self.entry_flood_water.get().strip()
        rain_str = self.entry_flood_rain.get().strip()
        status = self.combo_flood_status.get().strip()
        alert = self.combo_flood_alert.get().strip()
        advisory = self.entry_flood_advisory.get().strip()

        if not all([city, brgy, water_str, rain_str, advisory]):
            messagebox.showwarning("Missing Fields", "Please fill in all flood monitoring fields.")
            return

        try:
            w_val = float(water_str)
            r_val = float(rain_str)
        except ValueError:
            messagebox.showwarning("Invalid Input", "Water level and rainfall must be valid numbers.")
            return

        depth_desc = group4database.calculate_depth_category(w_val)
        rain_desc = group4database.calculate_rainfall_category(r_val)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        ok, res = group4database.add_flood_record(
            city, brgy, w_val, depth_desc, r_val, rain_desc, alert, status, advisory, timestamp
        )

        if ok:
            messagebox.showinfo("Success", f"Flood monitoring entry for {brgy}, {city} saved successfully!")
            self.clear_flood_form()
            self.load_flood_records()
        else:
            messagebox.showerror("Error", f"Failed to save flood record:\n{res}")

    def update_flood_record(self):
        if not self.selected_flood_id:
            messagebox.showwarning("No Selection", "Please click a row from the flood table to update.")
            return

        city = self.combo_flood_city.get().strip()
        brgy = self.entry_flood_brgy.get().strip()
        water_str = self.entry_flood_water.get().strip()
        rain_str = self.entry_flood_rain.get().strip()
        status = self.combo_flood_status.get().strip()
        alert = self.combo_flood_alert.get().strip()
        advisory = self.entry_flood_advisory.get().strip()

        try:
            w_val = float(water_str)
            r_val = float(rain_str)
        except ValueError:
            messagebox.showwarning("Invalid Input", "Water level and rainfall must be valid numbers.")
            return

        depth_desc = group4database.calculate_depth_category(w_val)
        rain_desc = group4database.calculate_rainfall_category(r_val)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        ok, msg = group4database.update_flood_record(
            self.selected_flood_id, city, brgy, w_val, depth_desc, r_val, rain_desc, alert, status, advisory, timestamp
        )

        if ok:
            messagebox.showinfo("Updated", f"Flood record #{self.selected_flood_id} updated successfully.")
            self.clear_flood_form()
            self.load_flood_records()
        else:
            messagebox.showerror("Error", f"Failed to update:\n{msg}")

    def delete_flood_record(self):
        if not self.selected_flood_id:
            messagebox.showwarning("No Selection", "Please click a row from the flood table to delete.")
            return

        if not messagebox.askyesno("Confirm Delete", f"Delete flood monitoring record #{self.selected_flood_id}?"):
            return

        ok, msg = group4database.delete_flood_record(self.selected_flood_id)
        if ok:
            messagebox.showinfo("Deleted", "Flood record deleted successfully.")
            self.clear_flood_form()
            self.load_flood_records()
        else:
            messagebox.showerror("Error", f"Failed to delete:\n{msg}")

    def load_flood_records(self):
        for row in self.flood_admin_tree.get_children():
            self.flood_admin_tree.delete(row)

        city_sel = self.combo_admin_flood_city.get().strip()
        search_txt = self.entry_search_flood_admin.get().strip()

        records = group4database.get_flood_records(city_filter=city_sel, search_query=search_txt)

        for rec in records:
            display_vals = (
                rec[0],
                rec[1],
                rec[2],
                f"{rec[3]:.2f}",
                rec[4],
                f"{rec[5]:.1f}",
                rec[8],
                rec[7],
                rec[9],
                rec[10]
            )
            self.flood_admin_tree.insert("", "end", values=display_vals)

        # Update metric cards
        stats = group4database.get_flood_statistics()
        self.lbl_flood_total.configure(text=f"{stats['total']} Areas")
        self.lbl_flood_critical.configure(text=f"{stats['critical']} Areas")
        self.lbl_flood_warning.configure(text=f"{stats['warning']} Areas")
        self.lbl_flood_peak.configure(text=f"{stats['highest_area']}")

    def on_flood_row_select(self, _event):
        selected = self.flood_admin_tree.selection()
        if not selected:
            return

        vals = self.flood_admin_tree.item(selected[0], "values")
        self.selected_flood_id = vals[0]

        self.combo_flood_city.set(vals[1])
        self.entry_flood_brgy.delete(0, "end")
        self.entry_flood_brgy.insert(0, vals[2])

        self.entry_flood_water.delete(0, "end")
        self.entry_flood_water.insert(0, str(vals[3]))

        self.entry_flood_rain.delete(0, "end")
        self.entry_flood_rain.insert(0, str(vals[5]))

        self.combo_flood_status.set(vals[6])
        self.combo_flood_alert.set(vals[7])

        self.entry_flood_advisory.delete(0, "end")
        self.entry_flood_advisory.insert(0, vals[8])

    def clear_flood_form(self):
        self.selected_flood_id = None
        self.entry_flood_brgy.delete(0, "end")
        self.entry_flood_water.delete(0, "end")
        self.entry_flood_rain.delete(0, "end")
        self.entry_flood_advisory.delete(0, "end")
        self.combo_flood_status.set("Rising")
        self.combo_flood_alert.set(group4database.FLOOD_ALERT_WARNING)

    def broadcast_sample_flood_alert(self):
        stats = group4database.get_flood_statistics()
        msg = (
            f"📢 [OFFICIAL PDRRMO EMERGENCY BROADCAST DISPATCHED]\n\n"
            f"• Sender: {self.user_info.get('full_name', 'Admin')} ({self.user_info.get('role', 'Health Official')})\n"
            f"• Scope: All monitored Pangasinan Barangays ({stats['total']} areas)\n"
            f"• High Water Alert: {stats['critical']} Critical & {stats['warning']} Warning areas\n"
            f"• Highest Peak: {stats['highest_area']}\n\n"
            f"Residents in low-lying barangays have received the early-warning notification on their portal."
        )
        messagebox.showinfo("Broadcast Sent", msg)

    # PATIENT CLINICAL CRUD METHODS

    def create_record(self):
        name     = self.entry_name.get().strip()
        age      = self.entry_age.get().strip()
        sex      = self.combo_sex.get().strip()
        barangay = self.entry_barangay.get().strip()
        disease  = self.entry_disease.get().strip()
        status   = self.combo_status.get().strip()
        date_str = self.entry_date.get().strip()

        if not all([name, age, sex, barangay, disease, status, date_str]):
            messagebox.showwarning("Validation Error", "All fields are required.")
            return

        ok, res = group4database.add_patient_record(name, age, sex, barangay, disease, status, date_str)
        if ok:
            messagebox.showinfo("Success", f"Patient record #{res} for '{name}' added successfully!")
            self.clear_form()
            self.load_records()
        else:
            messagebox.showerror("Error", f"Failed to add record:\n{res}")

    def update_record(self):
        if not self.selected_record_id:
            messagebox.showwarning("No Selection", "Please click a patient row from the table to update.")
            return

        name     = self.entry_name.get().strip()
        age      = self.entry_age.get().strip()
        sex      = self.combo_sex.get().strip()
        barangay = self.entry_barangay.get().strip()
        disease  = self.entry_disease.get().strip()
        status   = self.combo_status.get().strip()
        date_str = self.entry_date.get().strip()

        ok, msg = group4database.update_patient_record(
            self.selected_record_id, name, age, sex, barangay, disease, status, date_str
        )
        if ok:
            messagebox.showinfo("Success", f"Record #{self.selected_record_id} updated successfully!")
            self.clear_form()
            self.load_records()
        else:
            messagebox.showerror("Error", f"Failed to update:\n{msg}")

    def delete_record(self):
        if not self.selected_record_id:
            messagebox.showwarning("No Selection", "Please click a patient row from the table to delete.")
            return

        name = self.entry_name.get().strip()
        if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to permanently delete record #{self.selected_record_id} for '{name}'?"):
            return

        ok, msg = group4database.delete_patient_record(self.selected_record_id)
        if ok:
            messagebox.showinfo("Deleted", f"Record #{self.selected_record_id} has been deleted.")
            self.clear_form()
            self.load_records()
        else:
            messagebox.showerror("Error", f"Failed to delete:\n{msg}")

    def export_csv(self):
        target_file = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Spreadsheet", "*.csv"), ("All Files", "*.*")],
            initialfile=f"wild_care_report_{date.today()}.csv",
            title="Export Health Monitoring Report"
        )
        if not target_file:
            return

        ok, count_or_err = group4database.export_records_to_csv(target_file)
        if ok:
            messagebox.showinfo(
                "Export Complete",
                f"Successfully exported {count_or_err} health record(s) to:\n{target_file}"
            )
        else:
            messagebox.showerror("Export Failed", f"Could not save CSV report:\n{count_or_err}")

    def on_row_select(self, _event):
        selected = self.tree.selection()
        if not selected:
            return

        vals = self.tree.item(selected[0], "values")
        self.selected_record_id = vals[0]

        self.entry_name.delete(0, "end")
        self.entry_name.insert(0, vals[1])

        self.entry_age.delete(0, "end")
        self.entry_age.insert(0, vals[2])

        self.combo_sex.set(vals[3])

        self.entry_barangay.delete(0, "end")
        self.entry_barangay.insert(0, vals[4])

        self.entry_disease.delete(0, "end")
        self.entry_disease.insert(0, vals[5])

        self.combo_status.set(vals[6])

        self.entry_date.delete(0, "end")
        self.entry_date.insert(0, vals[7])

        # Update selected file queue status rank in bottom status bar
        children = self.tree.get_children()
        try:
            rank = children.index(selected[0]) + 1
            self.lbl_queue_pos.configure(
                text=f"Selected File: #{rank} of {len(children)} ({vals[1]})  •  Status: {vals[6]}",
                text_color="#38BDF8"
            )
        except (ValueError, IndexError):
            pass

    def load_records(self, records=None):
        for row in self.tree.get_children():
            self.tree.delete(row)

        if records is None:
            records = group4database.get_all_patient_records()

        for rec in records:
            self.tree.insert("", "end", values=rec)

        self._reapply_row_tags()
        self.lbl_record_count.configure(text=f"Total Records: {len(records)}")
        self.update_stats()

    # DRAG & DROP PATIENT FILE ARRANGER & SMART CLINICAL TRIAGE

    def _on_dnd_press(self, event):
        item = self.tree.identify_row(event.y)
        self._drag_item = item
        self._drag_start_y = event.y
        self._is_dragging = False

    def _on_dnd_motion(self, event):
        if not self._drag_item:
            return

        # Threshold to avoid accidental drag when simply clicking to select
        if abs(event.y - self._drag_start_y) < 6:
            return

        if not self._is_dragging:
            self._is_dragging = True
            self.tree.configure(cursor="fleur")
            drag_vals = self.tree.item(self._drag_item, "values")
            drag_name = drag_vals[1] if drag_vals and len(drag_vals) > 1 else "Patient File"
            self.lbl_arrange_status.configure(
                text=f"📦 Moving '{drag_name}' ➔ Hover over target position and release...",
                text_color="#38BDF8"
            )

        target = self.tree.identify_row(event.y)

        # Clear target tags from other items
        for child in self.tree.get_children():
            tags = [t for t in self.tree.item(child, "tags") if t != "drag_target"]
            if child == self._drag_item and "dragging" not in tags:
                tags.append("dragging")
            self.tree.item(child, tags=tuple(tags))

        # Highlight hovered target item
        if target and target != self._drag_item:
            target_tags = list(self.tree.item(target, "tags"))
            if "drag_target" not in target_tags:
                target_tags.append("drag_target")
            self.tree.item(target, tags=tuple(target_tags))
            target_vals = self.tree.item(target, "values")
            target_name = target_vals[1] if target_vals and len(target_vals) > 1 else ""
            self.lbl_arrange_status.configure(
                text=f"📦 Insert before '{target_name}' (Release to drop)",
                text_color="#67E8F9"
            )

    def _on_dnd_release(self, event):
        if self._is_dragging and self._drag_item:
            target = self.tree.identify_row(event.y)
            self.tree.configure(cursor="")

            if target and target != self._drag_item:
                target_idx = self.tree.index(target)
                self.tree.move(self._drag_item, '', target_idx)

                # Fetch updated list of IDs in current visual order
                children = self.tree.get_children()
                ordered_ids = [self.tree.item(c, "values")[0] for c in children]

                ok, msg = group4database.update_patient_display_order(ordered_ids)
                if ok:
                    self.lbl_arrange_status.configure(
                        text=f"✅ Patient file queue arranged & saved! (Moved to #{target_idx + 1})",
                        text_color="#34D399"
                    )
                else:
                    self.lbl_arrange_status.configure(text=f"⚠️ {msg}", text_color="#F87171")

                self.tree.selection_set(self._drag_item)
            elif not target:
                # If dropped at the bottom whitespace of the treeview
                children = self.tree.get_children()
                if children:
                    last_child = children[-1]
                    bbox = self.tree.bbox(last_child)
                    if bbox and event.y > bbox[1]:
                        self.tree.move(self._drag_item, '', len(children) - 1)
                        ordered_ids = [self.tree.item(c, "values")[0] for c in self.tree.get_children()]
                        group4database.update_patient_display_order(ordered_ids)
                        self.lbl_arrange_status.configure(text="✅ Patient file moved to end of queue!", text_color="#34D399")
                        self.tree.selection_set(self._drag_item)

            self._reapply_row_tags()
            self._is_dragging = False
            self._drag_item = None
            self.root.after(3500, self._reset_arrange_status_label)
        else:
            self._is_dragging = False
            self._drag_item = None
            self.tree.configure(cursor="")
            self._reapply_row_tags()

    def _reapply_row_tags(self):
        for item in self.tree.get_children():
            vals = self.tree.item(item, "values")
            if not vals or len(vals) < 7:
                continue
            disease = str(vals[5]).lower()
            status = str(vals[6]).lower()

            if "admitted" in status:
                tag = "admitted"
            elif "lepto" in disease and "observation" in status:
                tag = "critical_obs"
            elif "observation" in status:
                tag = "observation"
            elif "recovered" in status:
                tag = "recovered"
            else:
                tag = "observation"

            self.tree.item(item, tags=(tag,))

    def _reset_arrange_status_label(self):
        try:
            self.lbl_arrange_status.configure(
                text="Drag any row to reorder patient queue • Auto-saves arrangement",
                text_color="#94A3B8"
            )
        except Exception:
            pass

    def move_row_up(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Select Patient", "Please select a patient row to move up.")
            return

        item = selected[0]
        idx = self.tree.index(item)
        if idx > 0:
            self.tree.move(item, '', idx - 1)
            ordered_ids = [self.tree.item(c, "values")[0] for c in self.tree.get_children()]
            group4database.update_patient_display_order(ordered_ids)
            self._reapply_row_tags()
            self.tree.selection_set(item)
            self.lbl_arrange_status.configure(text=f"⬆️ File moved to position #{idx}", text_color="#38BDF8")
            self.root.after(3000, self._reset_arrange_status_label)

    def move_row_down(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Select Patient", "Please select a patient row to move down.")
            return

        item = selected[0]
        idx = self.tree.index(item)
        total = len(self.tree.get_children())
        if idx < total - 1:
            self.tree.move(item, '', idx + 1)
            ordered_ids = [self.tree.item(c, "values")[0] for c in self.tree.get_children()]
            group4database.update_patient_display_order(ordered_ids)
            self._reapply_row_tags()
            self.tree.selection_set(item)
            self.lbl_arrange_status.configure(text=f"⬇️ File moved to position #{idx + 2}", text_color="#38BDF8")
            self.root.after(3000, self._reset_arrange_status_label)

    def move_row_to_top(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Select Patient", "Please select a patient file to prioritize to top.")
            return

        item = selected[0]
        vals = self.tree.item(item, "values")
        self.tree.move(item, '', 0)
        ordered_ids = [self.tree.item(c, "values")[0] for c in self.tree.get_children()]
        group4database.update_patient_display_order(ordered_ids)
        self._reapply_row_tags()
        self.tree.selection_set(item)
        name = vals[1] if len(vals) > 1 else "Patient"
        self.lbl_arrange_status.configure(
            text=f"🚨 EMERGENCY PRIORITY: '{name}' moved to #1 top queue!",
            text_color="#F87171"
        )
        self.root.after(3500, self._reset_arrange_status_label)

    def smart_triage_auto_arrange(self):
        ok, res = group4database.auto_triage_patient_records()
        if ok:
            self.load_records()
            msg = (
                f"⚡ SMART CLINICAL TRIAGE OPTIMIZATION COMPLETE\n\n"
                f"• Total Patients Evaluated: {res['total']}\n"
                f"• Critical Emergency Tier: {res['critical']}\n"
                f"• Moderate Observation Tier: {res['moderate']}\n"
                f"• Routine / Discharged Tier: {res['low']}\n\n"
                f"🏆 #1 Priority File in Queue:\n"
                f"'{res['top_patient']}' (Urgency Score: {res['top_score']} pts)\n"
                f"Clinical & Hazard Factors: {res['top_reasons']}\n\n"
                f"All patient files have been arranged by medical urgency and saved."
            )
            messagebox.showinfo("Smart Clinical Triage", msg)
            self.lbl_arrange_status.configure(
                text=f"⚡ Rule-Based Triage Active: Prioritized {res['total']} files by urgency & flood hazard",
                text_color="#A7F3D0"
            )
        else:
            messagebox.showwarning("Triage Notice", str(res))

    def reset_queue_order(self):
        if messagebox.askyesno("Reset Order", "Reset patient file arrangement back to chronological order (newest first)?"):
            ok, msg = group4database.reset_patient_display_order()
            if ok:
                self.load_records()
                self.lbl_arrange_status.configure(text="🔄 Queue order reset to chronological", text_color="#94A3B8")
                self.root.after(3000, self._reset_arrange_status_label)
            else:
                messagebox.showerror("Error", msg)

    def _on_tree_double_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        vals = self.tree.item(item, "values")
        if vals:
            self.open_patient_dossier(vals)

    def open_patient_dossier(self, vals):
        if not vals or len(vals) < 8:
            return

        rec_id, name, age, sex, brgy, disease, status, date_logged = vals[:8]

        # Calculate queue rank
        children = self.tree.get_children()
        rank = 1
        for idx, c in enumerate(children, start=1):
            if str(self.tree.item(c, "values")[0]) == str(rec_id):
                rank = idx
                break

        # Cross reference flood monitoring database for patient's barangay/city
        flood_hazard = None
        all_flood = group4database.get_all_flood_records()
        b_clean = brgy.lower()
        for f in all_flood:
            f_city, f_brgy = str(f[1]).lower(), str(f[2]).lower()
            if f_brgy in b_clean or any(word in b_clean for word in f_brgy.split() if len(word) > 3):
                flood_hazard = f
                break

        dossier = customtkinter.CTkToplevel(self.root)
        dossier.title(f"Clinical Dossier — #{rec_id} {name}")
        dossier.geometry("540x550")
        dossier.minsize(500, 500)
        dossier.configure(fg_color=COLOR_BG_DARK)
        dossier.after(10, dossier.lift)
        dossier.attributes("-topmost", True)

        # Header Frame
        hdr = customtkinter.CTkFrame(dossier, fg_color=COLOR_PRIMARY, corner_radius=0, height=54)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        lbl_hdr = customtkinter.CTkLabel(
            hdr,
            text=f"📋 CLINICAL DOSSIER: #{rec_id} {name}",
            font=("Segoe UI", 13, "bold"),
            text_color="white"
        )
        lbl_hdr.pack(side="left", padx=15, pady=8)

        # Content container
        body = customtkinter.CTkFrame(dossier, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=15, pady=10)

        # Triage Rank Pill Card
        rank_card = customtkinter.CTkFrame(body, fg_color=COLOR_BG_CARD, corner_radius=10, border_width=1, border_color="#1D4ED8")
        rank_card.pack(fill="x", pady=(0, 8))

        rank_lbl = customtkinter.CTkLabel(
            rank_card,
            text=f"⚡ QUEUE RANK: #{rank} of {len(children)}  •  Status: {status.upper()}",
            font=("Segoe UI", 11, "bold"),
            text_color="#38BDF8"
        )
        rank_lbl.pack(padx=12, pady=6, anchor="w")

        # Patient Info Card
        info_card = customtkinter.CTkFrame(body, fg_color=COLOR_BG_CARD, corner_radius=10)
        info_card.pack(fill="x", pady=(0, 8))

        customtkinter.CTkLabel(info_card, text="👤 Patient Vitals & Demographics", font=("Segoe UI", 11, "bold"), text_color=COLOR_ACCENT).pack(padx=12, pady=(6, 2), anchor="w")

        info_text = (
            f"• Full Name: {name}\n"
            f"• Age: {age} yrs old  |  Sex: {sex}\n"
            f"• Residence / Station: {brgy}\n"
            f"• Logged Date: {date_logged}\n"
            f"• Diagnosed Condition: {disease}"
        )
        customtkinter.CTkLabel(info_card, text=info_text, font=("Segoe UI", 10), justify="left", text_color=COLOR_TEXT).pack(padx=12, pady=(0, 8), anchor="w")

        # Environmental Flood Hazard Card
        flood_card = customtkinter.CTkFrame(body, fg_color="#172235", corner_radius=10, border_width=1, border_color="#2563EB")
        flood_card.pack(fill="x", pady=(0, 8))

        customtkinter.CTkLabel(flood_card, text="🌊 Environmental Hazard & Flood Context", font=("Segoe UI", 11, "bold"), text_color="#67E8F9").pack(padx=12, pady=(6, 2), anchor="w")

        if flood_hazard:
            fh_city = flood_hazard[1]
            fh_brgy = flood_hazard[2]
            fh_water = flood_hazard[3]
            fh_depth = flood_hazard[4]
            fh_rain = flood_hazard[5]
            fh_alert = flood_hazard[7]
            fh_advisory = flood_hazard[9]

            fh_color = "#F87171" if "critical" in fh_alert.lower() else "#FBBF24"
            fl_text = (
                f"📍 Station: {fh_brgy}, {fh_city}\n"
                f"🚨 Alert Status: {fh_alert}  |  Depth: {fh_depth} ({fh_water:.2f}m)\n"
                f"🌧️ Rainfall Rate: {fh_rain:.1f} mm/h\n"
                f"📢 Area Bulletin: {fh_advisory}"
            )
            customtkinter.CTkLabel(flood_card, text=fl_text, font=("Segoe UI", 10), justify="left", text_color=fh_color, wraplength=480).pack(padx=12, pady=(0, 8), anchor="w")
        else:
            customtkinter.CTkLabel(
                flood_card,
                text=f"📍 Location '{brgy}': No critical river overflow recorded at this hour.\nEnsure proper protective boots; Leptospirosis prophylaxis available at health station.",
                font=("Segoe UI", 10),
                justify="left",
                text_color="#94A3B8"
            ).pack(padx=12, pady=(0, 8), anchor="w")

        # Quick Actions inside Dossier
        act_box = customtkinter.CTkFrame(body, fg_color="transparent")
        act_box.pack(fill="x", pady=4)

        def set_status_and_close(new_status):
            group4database.update_patient_record(rec_id, name, age, sex, brgy, disease, new_status, date_logged)
            self.load_records()
            dossier.destroy()

        btn_adm = customtkinter.CTkButton(
            act_box, text="🚨 Mark Admitted", font=("Segoe UI", 10, "bold"),
            fg_color="#B91C1C", hover_color="#991B1B", height=32, corner_radius=6,
            command=lambda: set_status_and_close("Admitted")
        )
        btn_adm.pack(side="left", fill="x", expand=True, padx=(0, 4))

        btn_obs = customtkinter.CTkButton(
            act_box, text="⚠️ Under Observation", font=("Segoe UI", 10, "bold"),
            fg_color="#D97706", hover_color="#B45309", height=32, corner_radius=6,
            command=lambda: set_status_and_close("Under Observation")
        )
        btn_obs.pack(side="left", fill="x", expand=True, padx=4)

        btn_rec = customtkinter.CTkButton(
            act_box, text="✅ Mark Recovered", font=("Segoe UI", 10, "bold"),
            fg_color="#059669", hover_color="#047857", height=32, corner_radius=6,
            command=lambda: set_status_and_close("Recovered")
        )
        btn_rec.pack(side="left", fill="x", expand=True, padx=(4, 0))

        btn_close = customtkinter.CTkButton(
            body, text="Close Dossier", font=("Segoe UI", 10),
            fg_color="#334155", hover_color="#475569", height=30, corner_radius=6,
            command=dossier.destroy
        )
        btn_close.pack(fill="x", pady=(6, 0))

    def update_stats(self):
        stats = group4database.get_summary_counts()
        self.lbl_stat_total.configure(text=str(stats["total"]))
        self.lbl_stat_obs.configure(text=str(stats["observation"]))
        self.lbl_stat_adm.configure(text=str(stats["admitted"]))
        self.lbl_stat_rec.configure(text=str(stats["recovered"]))

    def search_records(self):
        self.selected_record_id = None
        query = self.entry_search.get().strip()
        filter_by = self.combo_filter.get()
        results = group4database.search_patient_records(query, filter_by)
        self.load_records(results)

    def reset_search(self):
        self.selected_record_id = None
        self.entry_search.delete(0, "end")
        self.load_records()

    def clear_form(self):
        self.selected_record_id = None
        self.entry_name.delete(0, "end")
        self.entry_age.delete(0, "end")
        self.combo_sex.set("Male")
        self.entry_barangay.delete(0, "end")
        self.entry_disease.delete(0, "end")
        self.combo_status.set("Under Observation")
        self.entry_date.delete(0, "end")
        self.entry_date.insert(0, str(date.today()))


    # WIDGET BUILDER HELPERS

    def _create_card(self, parent, col, title, value, color):
        card = customtkinter.CTkFrame(parent, fg_color="transparent")
        card.grid(row=0, column=col, padx=10, pady=8, sticky="ew")

        lbl_t = customtkinter.CTkLabel(card, text=title, font=("Segoe UI", 10), text_color="#AAAAAA")
        lbl_t.pack(anchor="w")

        lbl_v = customtkinter.CTkLabel(card, text=value, font=("Segoe UI", 16, "bold"), text_color=color)
        lbl_v.pack(anchor="w")
        return lbl_v

    def _create_input(self, parent, label_text, placeholder):
        """Helper to create a styled input."""
        lbl = customtkinter.CTkLabel(parent, text=label_text, font=("Segoe UI", 10, "bold"), text_color=COLOR_TEXT)
        lbl.pack(padx=20, pady=(3, 1), anchor="w")

        entry = customtkinter.CTkEntry(
            parent, placeholder_text=placeholder, font=("Segoe UI", 10), height=30,
            fg_color=COLOR_ENTRY_BG, border_color=COLOR_PRIMARY, text_color="white", corner_radius=6
        )
        entry.pack(padx=20, pady=(0, 3), fill="x")
        return entry

    def _create_combobox(self, parent, label_text, values, default):
        lbl = customtkinter.CTkLabel(parent, text=label_text, font=("Segoe UI", 10, "bold"), text_color=COLOR_TEXT)
        lbl.pack(padx=20, pady=(3, 1), anchor="w")

        combo = customtkinter.CTkComboBox(
            parent, values=values, font=("Segoe UI", 10), height=30,
            fg_color=COLOR_ENTRY_BG, border_color=COLOR_PRIMARY, button_color=COLOR_PRIMARY,
            text_color="white", dropdown_fg_color=COLOR_BG_CARD, corner_radius=6, state="readonly"
        )
        combo.set(default)
        combo.pack(padx=20, pady=(0, 3), fill="x")
        return combo

    def handle_logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to log out / switch account?"):
            try:
                self.root.destroy()
            except Exception:
                pass
            self.on_logout_callback()

    def run(self):
        """Starts main loop."""
        self.root.mainloop()
