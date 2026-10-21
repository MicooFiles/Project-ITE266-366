import re
import sys
from datetime import date, datetime
from tkinter import filedialog, messagebox

import customtkinter

import group4database
import ui_theme as ui
from ui_theme import C

ALL_AREAS = "All areas"
HINT = "Drag rows to reorder the queue. Changes are saved automatically."
STATUS_TAGS = {"admitted": ("danger_bg", "danger"), "critical_obs": ("warn_bg", "warn"), "recovered": ("ok_bg", "ok"),
               "dragging": ("info_bg", "info"), "drag_target": ("accent_soft", "accent_text")}


def split_location(text):
    """'Pantal, Dagupan City' -> ('Dagupan City', 'Pantal'). Handles older free-text locations too."""
    for area in group4database.AREAS:
        if text.lower().endswith(", " + area.lower()):
            return area, text[:-(len(area) + 2)].strip()
    for area in group4database.AREAS:
        key = area.lower().replace(" city", "")
        if key in text.lower():
            return area, re.sub(rf",?\s*{re.escape(key)}(\s+city)?", "", text, flags=re.I).strip(" ,")
    return "", text


def row_tag(values):
    disease, status = str(values[5]).lower(), str(values[6]).lower()
    if "admitted" in status:
        return "admitted"
    if "observation" in status:
        return "critical_obs" if "lepto" in disease else ""
    return "recovered" if "recovered" in status else ""


class AdminDashboardWindow:
    def __init__(self, user_info, on_logout_callback):
        self.user_info = user_info
        self.on_logout_callback = on_logout_callback
        self.selected_record_id = None
        self.selected_flood_id = None
        self._drag = {"item": "", "y": 0, "active": False}
        self._hint_timer = None

        self.root = customtkinter.CTk()
        self.root.title(f"W.I.L.D. CARE — {user_info.get('role', 'Staff')} Portal")
        ui.setup(self.root)
        ui.place_window(self.root, 1320, 800, min_size=(1120, 700))
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

        self.pages = {"Patient records": ui.row(self.root), "Flood management": ui.row(self.root)}
        self.build_topbar()
        self.build_patient_page(self.pages["Patient records"])
        self.build_flood_page(self.pages["Flood management"])
        self.show_page("Patient records")
        self.load_records()
        self.load_flood()

    # ── Shell ────────────────────────────────────────────────────────────────
    def build_topbar(self):
        bar = customtkinter.CTkFrame(self.root, fg_color=C["side"], corner_radius=0, height=64)
        bar.grid(row=0, column=0, sticky="ew")
        bar.pack_propagate(False)
        self.logo = ui.logo_image("wildcare_logo_shield.png", (30, 34))
        if self.logo:
            tile = customtkinter.CTkFrame(bar, fg_color="#FFFFFF", corner_radius=ui.R_CTRL)
            tile.pack(side="left", padx=(24, 12))
            customtkinter.CTkLabel(tile, text="", image=self.logo).pack(padx=7, pady=5)
        brand = ui.row(bar)
        brand.pack(side="left", padx=(0 if self.logo else 24, 28))
        ui.label(brand, "W.I.L.D. CARE", "heading", "side_text", anchor="w").pack(fill="x", pady=(10, 0))
        ui.label(brand, "Pangasinan disease surveillance", "small", "side_muted", anchor="w").pack(fill="x")

        self.tabs = {}
        for name in self.pages:
            btn = ui.button(bar, name, lambda n=name: self.show_page(n), kind="nav", width=150, height=36)
            btn.pack(side="left", padx=2)
            self.tabs[name] = btn

        ui.button(bar, "Log out", self.handle_logout, kind="danger", width=84, height=34).pack(side="right", padx=(10, 24))
        role, off_id = self.user_info.get("role", "Staff"), self.user_info.get("official_id", "")
        who = f"{self.user_info.get('full_name', 'Staff')}  ·  {role}" + (f"  ·  ID {off_id}" if off_id and off_id != "RESIDENT" else "")
        ui.label(bar, who, "smallbold", "side_text").pack(side="right", padx=(10, 0))
        ui.button(bar, "Theme", ui.toggle_dark, kind="nav", width=70, height=34, font="small").pack(side="right")
        ui.text_size_control(bar).pack(side="right", padx=10)

    def show_page(self, name):
        for key, frame in self.pages.items():
            frame.grid_forget()
            ui.restyle(self.tabs[key], "nav_active" if key == name else "nav")
        self.pages[name].grid(row=1, column=0, sticky="nsew", padx=20, pady=18)

    def button_row(self, parent, buttons):
        """Primary action full width, then the rest side by side."""
        first, *rest = buttons
        ui.button(parent, *first[:2], kind=first[2]).pack(fill="x", pady=(0, 6))
        line = ui.row(parent)
        line.pack(fill="x")
        line.grid_columnconfigure(tuple(range(len(rest))), weight=1, uniform="btn")
        for i, (text, command, kind) in enumerate(rest):
            ui.button(line, text, command, kind=kind, height=34).grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 3, 3 if i < len(rest) - 1 else 0))

    @staticmethod
    def field_pair(parent):
        line = ui.row(parent)
        line.pack(fill="x")
        line.grid_columnconfigure((0, 1), weight=1, uniform="pair")
        left, right = ui.row(line), ui.row(line)
        left.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        right.grid(row=0, column=1, sticky="ew", padx=(5, 0))
        return left, right

    # ── Patient records page ─────────────────────────────────────────────────
    def build_patient_page(self, page):
        page.grid_columnconfigure(1, weight=1)
        page.grid_rowconfigure(0, weight=1)

        form = ui.card(page, width=356)
        form.grid(row=0, column=0, sticky="ns", padx=(0, 14))
        form.pack_propagate(False)
        box = ui.row(form)
        box.pack(fill="both", expand=True, padx=18, pady=16)
        ui.label(box, "Patient record", "title", anchor="w").pack(fill="x", pady=(0, 12))
        self.f_name = ui.field(box, "Full name", placeholder="e.g. Graizler Untalan", pady=(0, 6), height=34)
        left, right = self.field_pair(box)
        self.f_age = ui.field(left, "Age", placeholder="e.g. 67", pady=(0, 6), height=34)
        self.f_sex = ui.field(right, "Sex", "combo", ["Male", "Female", "Other"], "Male", pady=(0, 6), height=34)
        self.f_area = ui.field(box, "City / municipality", "combo", group4database.AREAS, group4database.AREAS[0], pady=(0, 6), height=34)
        self.f_brgy = ui.field(box, "Barangay", placeholder="e.g. Pantal", pady=(0, 6), height=34)
        self.f_disease = ui.field(box, "Disease / illness", placeholder="e.g. Leptospirosis", pady=(0, 6), height=34)
        left, right = self.field_pair(box)
        self.f_status = ui.field(left, "Case status", "combo", group4database.STATUS_OPTIONS, "Under Observation", pady=(0, 6), height=34)
        self.f_date = ui.field(right, "Date logged", placeholder=str(date.today()), pady=(0, 6), height=34)
        ui.set_text(self.f_date, date.today())
        ui.divider(box).pack(fill="x", pady=10)
        self.button_row(box, [("Add record", self.create_record, "primary"), ("Update", self.update_record, "secondary"),
                               ("Delete", self.delete_record, "danger"), ("Clear", self.clear_form, "ghost")])

        main = ui.row(page)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(3, weight=1)

        tiles = ui.row(main)
        tiles.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        tiles.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="tile")
        self.lbl_total = self.metric_tile(tiles, 0, "Total cases", "text")
        self.lbl_obs = self.metric_tile(tiles, 1, "Under observation", "warn")
        self.lbl_adm = self.metric_tile(tiles, 2, "Admitted", "danger")
        self.lbl_rec = self.metric_tile(tiles, 3, "Recovered", "ok")

        tools = ui.card(main)
        tools.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        line = ui.row(tools)
        line.pack(fill="x", padx=12, pady=10)
        self.search = ui.entry(line, "Search name, disease or barangay...", height=34)
        self.search.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.search.bind("<Return>", lambda e: self.search_records())
        self.search_by = ui.combo(line, ["All Fields", "Name", "Disease", "Barangay"], "All Fields", height=34, width=120)
        self.search_by.pack(side="left", padx=(0, 8))
        ui.button(line, "Search", self.search_records, height=34, width=80).pack(side="left", padx=(0, 6))
        ui.button(line, "Reset", self.reset_search, kind="secondary", height=34, width=70).pack(side="left", padx=(0, 6))
        ui.button(line, "Export CSV", self.export_csv, kind="secondary", height=34, width=100).pack(side="left")

        queue = ui.card(main)
        queue.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        line = ui.row(queue)
        line.pack(fill="x", padx=14, pady=9)
        ui.pill(line, "QUEUE", "accent").pack(side="left", padx=(0, 10))
        self.lbl_hint = ui.label(line, HINT, "small", "muted", anchor="w")
        self.lbl_hint.pack(side="left")
        for text, command, kind in reversed([("Smart triage", self.smart_triage, "primary"), ("Up", self.move_up, "secondary"),
                                             ("Down", self.move_down, "secondary"), ("Prioritize", self.move_top, "secondary"),
                                             ("Chrono", self.reset_order, "ghost")]):
            ui.button(line, text, command, kind=kind, height=30, font="smallbold", width=96 if text == "Smart triage" else 68).pack(side="right", padx=2)

        table = ui.card(main)
        table.grid(row=3, column=0, sticky="nsew")
        holder = ui.row(table)
        holder.pack(fill="both", expand=True, padx=8, pady=8)
        self.tree = ui.make_tree(holder, [("id", "ID", 46, "center"), ("name", "Full name", 150, "w"), ("age", "Age", 50, "center"),
                                          ("sex", "Sex", 64, "center"), ("place", "Barangay / area", 200, "w"),
                                          ("disease", "Disease", 150, "w"), ("status", "Status", 124, "center"),
                                          ("date", "Date", 96, "center")])
        ui.style_tags(self.tree, STATUS_TAGS)
        self.tree.bind("<<TreeviewSelect>>", self.on_row_select)
        self.tree.bind("<ButtonPress-1>", self.dnd_press)
        self.tree.bind("<B1-Motion>", self.dnd_motion)
        self.tree.bind("<ButtonRelease-1>", self.dnd_release)
        self.tree.bind("<Double-1>", self.on_double_click)
        self.lbl_count = ui.label(main, "Total records: 0", "small", "muted", anchor="w")
        self.lbl_count.grid(row=4, column=0, sticky="ew", pady=(6, 0))

    @staticmethod
    def metric_tile(parent, col, title, tone):
        tile, value = ui.metric(parent, title, "0", tone)
        tile.configure(fg_color=C["card"], border_width=1, border_color=C["border"])
        tile.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 5, 5 if col < 3 else 0))
        return value

    # ── Patient CRUD ─────────────────────────────────────────────────────────
    def read_form(self):
        place = f"{self.f_brgy.get().strip()}, {self.f_area.get()}" if self.f_brgy.get().strip() and self.f_area.get() else ""
        values = [self.f_name.get().strip(), self.f_age.get().strip(), self.f_sex.get(), place,
                  self.f_disease.get().strip(), self.f_status.get(), self.f_date.get().strip()]
        if not all(values):
            messagebox.showwarning("Validation error", "All fields are required (including city and barangay).")
            return None
        return values

    def create_record(self):
        values = self.read_form()
        if not values:
            return
        ok, result = group4database.add_patient_record(*values)
        if ok:
            messagebox.showinfo("Success", f"Patient record #{result} for '{values[0]}' added.")
            self.clear_form()
            self.load_records()
        else:
            messagebox.showerror("Error", f"Failed to add record:\n{result}")

    def update_record(self):
        if not self.selected_record_id:
            messagebox.showwarning("No selection", "Please click a patient row from the table to update.")
            return
        values = self.read_form()
        if not values:
            return
        ok, msg = group4database.update_patient_record(self.selected_record_id, *values)
        if ok:
            messagebox.showinfo("Success", f"Record #{self.selected_record_id} updated.")
            self.clear_form()
            self.load_records()
        else:
            messagebox.showerror("Error", f"Failed to update:\n{msg}")

    def delete_record(self):
        if not self.selected_record_id:
            messagebox.showwarning("No selection", "Please click a patient row from the table to delete.")
            return
        if not messagebox.askyesno("Confirm delete", f"Permanently delete record #{self.selected_record_id} for '{self.f_name.get().strip()}'?"):
            return
        ok, msg = group4database.delete_patient_record(self.selected_record_id)
        if ok:
            self.clear_form()
            self.load_records()
        else:
            messagebox.showerror("Error", f"Failed to delete:\n{msg}")

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Spreadsheet", "*.csv"), ("All Files", "*.*")],
                                            initialfile=f"wild_care_report_{date.today()}.csv", title="Export health monitoring report")
        if not path:
            return
        ok, result = group4database.export_records_to_csv(path)
        if ok:
            messagebox.showinfo("Export complete", f"Exported {result} record(s) to:\n{path}")
        else:
            messagebox.showerror("Export failed", f"Could not save the CSV report:\n{result}")

    def on_row_select(self, _event):
        sel = self.tree.selection()
        if not sel:
            return
        rec_id, name, age, sex, place, disease, status, logged = self.tree.item(sel[0], "values")[:8]
        self.selected_record_id = rec_id
        area, brgy = split_location(place)
        for widget, value in ((self.f_name, name), (self.f_age, age), (self.f_brgy, brgy), (self.f_disease, disease), (self.f_date, logged)):
            ui.set_text(widget, value)
        self.f_sex.set(sex)
        self.f_status.set(status)
        self.f_area.set(area)
        children = self.tree.get_children()
        self.flash(f"Selected file #{children.index(sel[0]) + 1} of {len(children)}: {name} · {status}", "accent_text", reset=False)

    def clear_form(self):
        self.selected_record_id = None
        for widget in (self.f_name, self.f_age, self.f_brgy, self.f_disease):
            widget.delete(0, "end")
        self.f_sex.set("Male")
        self.f_status.set("Under Observation")
        self.f_area.set(group4database.AREAS[0])
        ui.set_text(self.f_date, date.today())

    def load_records(self, records=None):
        records = group4database.get_all_patient_records() if records is None else records
        self.tree.delete(*self.tree.get_children())
        for rec in records:
            self.tree.insert("", "end", iid=str(rec[0]), values=rec)
        self.retag()
        self.lbl_count.configure(text=f"Total records: {len(records)}")
        stats = group4database.get_summary_counts()
        for label, key in ((self.lbl_total, "total"), (self.lbl_obs, "observation"), (self.lbl_adm, "admitted"), (self.lbl_rec, "recovered")):
            label.configure(text=str(stats[key]))

    def search_records(self):
        self.selected_record_id = None
        self.load_records(group4database.search_patient_records(self.search.get(), self.search_by.get()))

    def reset_search(self):
        self.selected_record_id = None
        self.search.delete(0, "end")
        self.load_records()

    # ── Queue ordering: drag & drop, buttons, smart triage ───────────────────
    def retag(self, dragging="", target=""):
        for item in self.tree.get_children():
            tags = [t for t in (row_tag(self.tree.item(item, "values")),) if t]
            if item == dragging:
                tags.append("dragging")
            if item == target:
                tags.append("drag_target")
            self.tree.item(item, tags=tuple(tags))

    def flash(self, text, tone="muted", reset=True, delay=3500):
        self.lbl_hint.configure(text=text, text_color=C[tone])
        if self._hint_timer:
            self.root.after_cancel(self._hint_timer)
            self._hint_timer = None
        if reset:
            self._hint_timer = self.root.after(delay, lambda: self.lbl_hint.configure(text=HINT, text_color=C["muted"]))

    def save_order(self, message, tone="ok"):
        ok, msg = group4database.update_patient_display_order(list(self.tree.get_children()))
        self.flash(message if ok else msg, tone if ok else "danger")

    def dnd_press(self, event):
        self._drag = {"item": self.tree.identify_row(event.y), "y": event.y, "active": False}

    def dnd_motion(self, event):
        drag = self._drag
        if not drag["item"] or (not drag["active"] and abs(event.y - drag["y"]) < 6):
            return
        drag["active"] = True
        self.tree.configure(cursor="fleur")
        target = self.tree.identify_row(event.y)
        target = "" if target == drag["item"] else target
        self.retag(drag["item"], target)
        name = self.tree.item(drag["item"], "values")[1]
        where = f"before '{self.tree.item(target, 'values')[1]}'" if target else "at the new position"
        self.flash(f"Moving '{name}': release to drop {where}.", "info", reset=False)

    def dnd_release(self, event):
        drag, self._drag = self._drag, {"item": "", "y": 0, "active": False}
        self.tree.configure(cursor="")
        if drag["active"] and drag["item"]:
            target = self.tree.identify_row(event.y)
            children = self.tree.get_children()
            if target and target != drag["item"]:
                index = self.tree.index(target)
                self.tree.move(drag["item"], "", index)
                self.save_order(f"Queue saved. File moved to #{index + 1}.")
            elif not target and children and (self.tree.bbox(children[-1]) or [0, 1 << 30])[1] < event.y:
                self.tree.move(drag["item"], "", len(children) - 1)
                self.save_order("Queue saved. File moved to the end.")
            self.tree.selection_set(drag["item"])
        self.retag()

    def move_selected(self, delta=None, top=False):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select patient", "Please select a patient row first.")
            return
        item, index, total = sel[0], self.tree.index(sel[0]), len(self.tree.get_children())
        new = 0 if top else index + delta
        if not 0 <= new < total or new == index:
            return
        self.tree.move(item, "", new)
        self.tree.selection_set(item)
        self.retag()
        if top:
            self.save_order(f"Priority: '{self.tree.item(item, 'values')[1]}' moved to #1.", "danger")
        else:
            self.save_order(f"File moved to position #{new + 1}.")

    def move_up(self):
        self.move_selected(-1)

    def move_down(self):
        self.move_selected(1)

    def move_top(self):
        self.move_selected(top=True)

    def smart_triage(self):
        ok, res = group4database.auto_triage_patient_records()
        if not ok:
            messagebox.showwarning("Triage notice", str(res))
            return
        self.load_records()
        messagebox.showinfo("Smart clinical triage", (
            f"Triage complete.\n\nPatients evaluated: {res['total']}\nCritical tier: {res['critical']}\n"
            f"Moderate tier: {res['moderate']}\nRoutine tier: {res['low']}\n\n"
            f"#1 in queue: '{res['top_patient']}' ({res['top_score']} pts)\nFactors: {res['top_reasons']}\n\n"
            "All files were arranged by urgency and saved."))
        self.flash(f"Triage applied: {res['total']} files ordered by urgency and flood risk.", "ok")

    def reset_order(self):
        if messagebox.askyesno("Reset order", "Reset the queue to chronological order (newest first)?"):
            ok, msg = group4database.reset_patient_display_order()
            if ok:
                self.load_records()
                self.flash("Queue reset to chronological order.")
            else:
                messagebox.showerror("Error", msg)

    # ── Clinical dossier ─────────────────────────────────────────────────────
    def on_double_click(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.open_dossier(self.tree.item(item, "values"))

    def open_dossier(self, vals):
        rec_id, name, age, sex, place, disease, status, logged = vals[:8]
        children = self.tree.get_children()
        rank = children.index(str(rec_id)) + 1 if str(rec_id) in children else 1
        flood = group4database.find_flood_for_location(place)

        dlg = ui.modal(self.root, f"Clinical dossier — #{rec_id} {name}", 540, 560)
        panel = ui.card(dlg)
        panel.pack(fill="both", expand=True, padx=16, pady=16)
        box = ui.row(panel)
        box.pack(fill="both", expand=True, padx=22, pady=20)
        head = ui.row(box)
        head.pack(fill="x")
        ui.label(head, name, "title", anchor="w").pack(side="left")
        ui.pill(head, status, "danger" if status == "Admitted" else "ok" if status == "Recovered" else "warn").pack(side="right")
        ui.label(box, f"Case #{rec_id} · queue rank {rank} of {len(children)}", "small", "muted", anchor="w").pack(fill="x", pady=(0, 14))

        info = ui.inset(box)
        info.pack(fill="x", pady=(0, 10))
        for key, value in (("Age / sex", f"{age} yrs · {sex}"), ("Residence", place), ("Date logged", logged), ("Condition", disease)):
            line = ui.row(info)
            line.pack(fill="x", padx=14, pady=4)
            ui.label(line, key, "small", "muted", anchor="w", width=90).pack(side="left")
            ui.label(line, value, "body", anchor="w", wraplength=330, justify="left").pack(side="left", fill="x")

        ctx = ui.inset(box)
        ctx.pack(fill="x", pady=(0, 14))
        ui.label(ctx, "Flood context", "smallbold", "accent_text", anchor="w").pack(fill="x", padx=14, pady=(10, 4))
        if flood:
            tone = ui.FLOOD_TONES.get(ui.flood_tag(flood[7]), "text")
            text = (f"{group4database.place_label(flood[1], flood[2])}\nAlert: {flood[7]} · {flood[4]}\n"
                    f"Rainfall: {flood[5]:.1f} mm/h\nBulletin: {flood[9]}")
        else:
            tone, text = "muted", f"No flood station on record for '{place}'. Leptospirosis prophylaxis is available at the health station."
        ui.label(ctx, text, "small", tone, anchor="w", justify="left", wraplength=420).pack(fill="x", padx=14, pady=(0, 12))

        def set_status(new_status):
            group4database.update_patient_record(rec_id, name, age, sex, place, disease, new_status, logged)
            self.load_records()
            dlg.destroy()

        actions = ui.row(box)
        actions.pack(fill="x", pady=(0, 8))
        actions.grid_columnconfigure((0, 1, 2), weight=1, uniform="act")
        for i, (text, value, kind) in enumerate((("Mark admitted", "Admitted", "danger"), ("Under observation", "Under Observation", "secondary"),
                                                 ("Mark recovered", "Recovered", "primary"))):
            ui.button(actions, text, lambda v=value: set_status(v), kind=kind, height=36, font="smallbold").grid(
                row=0, column=i, sticky="ew", padx=(0 if i == 0 else 3, 3 if i < 2 else 0))
        ui.button(box, "Close", dlg.destroy, kind="ghost", height=32).pack(fill="x")

    # ── Flood management page ────────────────────────────────────────────────
    def build_flood_page(self, page):
        page.grid_columnconfigure(1, weight=1)
        page.grid_rowconfigure(0, weight=1)

        form = ui.card(page, width=356)
        form.grid(row=0, column=0, sticky="ns", padx=(0, 14))
        form.pack_propagate(False)
        box = ui.row(form)
        box.pack(fill="both", expand=True, padx=18, pady=16)
        ui.label(box, "Flood & rainfall log", "title", anchor="w").pack(fill="x", pady=(0, 12))
        self.fl_area = ui.field(box, "City / municipality", "combo", group4database.AREAS, group4database.AREAS[0], pady=(0, 6), height=34)
        self.fl_brgy = ui.field(box, "Barangay", placeholder="e.g. Pantal", pady=(0, 6), height=34)
        left, right = self.field_pair(box)
        self.fl_water = ui.field(left, "Water level (m)", placeholder="e.g. 1.85", pady=(0, 6), height=34)
        self.fl_rain = ui.field(right, "Rainfall (mm/h)", placeholder="e.g. 32.0", pady=(0, 6), height=34)
        left, right = self.field_pair(box)
        self.fl_trend = ui.field(left, "Water trend", "combo", group4database.FLOOD_STATUS_OPTIONS, "Rising", pady=(0, 6), height=34)
        self.fl_alert = ui.field(right, "Alert level", "combo", group4database.FLOOD_ALERT_LEVELS, group4database.FLOOD_ALERT_WARNING, pady=(0, 6), height=34)
        self.fl_note = ui.field(box, "Early-warning advisory", placeholder="e.g. River overflow; prepare evacuation.", pady=(0, 6), height=34)
        ui.divider(box).pack(fill="x", pady=10)
        self.button_row(box, [("Log flood reading", self.create_flood, "primary"), ("Update", self.update_flood, "secondary"),
                               ("Delete", self.delete_flood, "danger"), ("Clear", self.clear_flood_form, "ghost")])

        main = ui.row(page)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(2, weight=1)

        tiles = ui.row(main)
        tiles.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        tiles.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="tile")
        self.lbl_f_total = self.metric_tile(tiles, 0, "Monitored stations", "text")
        self.lbl_f_crit = self.metric_tile(tiles, 1, "Critical / evacuate", "danger")
        self.lbl_f_warn = self.metric_tile(tiles, 2, "Warning / high water", "orange")
        self.lbl_f_peak = self.metric_tile(tiles, 3, "Peak water level", "info")
        self.lbl_f_peak.configure(font=ui.FONTS["heading"], wraplength=240, justify="left")

        tools = ui.card(main)
        tools.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        line = ui.row(tools)
        line.pack(fill="x", padx=12, pady=10)
        self.fl_filter = ui.combo(line, [ALL_AREAS] + group4database.AREAS, ALL_AREAS, height=34, width=150, command=lambda _: self.load_flood())
        self.fl_filter.pack(side="left", padx=(0, 8))
        self.fl_search = ui.entry(line, "Search barangay...", height=34)
        self.fl_search.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.fl_search.bind("<KeyRelease>", lambda e: self.load_flood())
        ui.button(line, "Refresh", self.load_flood, kind="secondary", height=34, width=80).pack(side="left", padx=(0, 6))
        ui.button(line, "Broadcast early alert", self.broadcast_alert, kind="danger", height=34, width=160).pack(side="left")

        table = ui.card(main)
        table.grid(row=2, column=0, sticky="nsew")
        holder = ui.row(table)
        holder.pack(fill="both", expand=True, padx=8, pady=8)
        self.flood_tree = ui.make_tree(holder, [("id", "ID", 40, "center"), ("city", "City", 100, "w"), ("brgy", "Barangay", 110, "w"),
                                                ("level", "Level (m)", 70, "center"), ("depth", "Depth", 125, "w"),
                                                ("rain", "Rain mm/h", 80, "center"), ("trend", "Trend", 80, "center"),
                                                ("alert", "Alert level", 125, "center"), ("note", "Early-warning advisory", 300, "w"),
                                                ("updated", "Updated", 110, "center")])
        ui.style_tags(self.flood_tree, ui.FLOOD_ROW_TAGS)
        self.flood_tree.bind("<<TreeviewSelect>>", self.on_flood_select)

    def read_flood_form(self):
        data = [self.fl_area.get(), self.fl_brgy.get().strip(), self.fl_water.get().strip(), self.fl_rain.get().strip(),
                self.fl_note.get().strip()]
        if not all(data):
            messagebox.showwarning("Missing fields", "Please fill in all flood monitoring fields.")
            return None
        try:
            water, rain = float(data[2]), float(data[3])
        except ValueError:
            messagebox.showwarning("Invalid input", "Water level and rainfall must be valid numbers.")
            return None
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        return (data[0], data[1], water, group4database.calculate_depth_category(water), rain,
                group4database.calculate_rainfall_category(rain), self.fl_alert.get(), self.fl_trend.get(), data[4], stamp)
# CRUD 
    def create_flood(self):
        args = self.read_flood_form()
        if not args:
            return
        ok, result = group4database.add_flood_record(*args)
        if ok:
            messagebox.showinfo("Success", f"Flood entry for {args[1]}, {args[0]} saved.")
            self.clear_flood_form()
            self.load_flood()
        else:
            messagebox.showerror("Error", f"Failed to save flood record:\n{result}")

    def update_flood(self):
        if not self.selected_flood_id:
            messagebox.showwarning("No selection", "Please click a row from the flood table to update.")
            return
        args = self.read_flood_form()
        if not args:
            return
        ok, msg = group4database.update_flood_record(self.selected_flood_id, *args)
        if ok:
            messagebox.showinfo("Updated", f"Flood record #{self.selected_flood_id} updated.")
            self.clear_flood_form()
            self.load_flood()
        else:
            messagebox.showerror("Error", f"Failed to update:\n{msg}")

    def delete_flood(self):
        if not self.selected_flood_id:
            messagebox.showwarning("No selection", "Please click a row from the flood table to delete.")
            return
        if not messagebox.askyesno("Confirm delete", f"Delete flood monitoring record #{self.selected_flood_id}?"):
            return
        ok, msg = group4database.delete_flood_record(self.selected_flood_id)
        if ok:
            self.clear_flood_form()
            self.load_flood()
        else:
            messagebox.showerror("Error", f"Failed to delete:\n{msg}")

    def load_flood(self):
        area = self.fl_filter.get()
        records = group4database.get_flood_records(city_filter="All Cities" if area == ALL_AREAS else area, search_query=self.fl_search.get().strip())
        self.flood_tree.delete(*self.flood_tree.get_children())
        for r in records:
            tag = ui.flood_tag(r[7])
            self.flood_tree.insert("", "end", iid=str(r[0]), tags=(tag,),
                                   values=(r[0], r[1], r[2], f"{r[3]:.2f}", r[4], f"{r[5]:.1f}", r[8], r[7], r[9], r[10]))
        stats = group4database.get_flood_statistics()
        self.lbl_f_total.configure(text=str(stats["total"]))
        self.lbl_f_crit.configure(text=str(stats["critical"]))
        self.lbl_f_warn.configure(text=str(stats["warning"]))
        self.lbl_f_peak.configure(text=stats["highest_area"])

    def on_flood_select(self, _event):
        sel = self.flood_tree.selection()
        if not sel:
            return
        _id, city, brgy, level, _depth, rain, trend, alert, note, _upd = self.flood_tree.item(sel[0], "values")
        self.selected_flood_id = _id
        self.fl_area.set(city)
        self.fl_trend.set(trend)
        self.fl_alert.set(alert)
        for widget, value in ((self.fl_brgy, brgy), (self.fl_water, level), (self.fl_rain, rain), (self.fl_note, note)):
            ui.set_text(widget, value)

    def clear_flood_form(self):
        self.selected_flood_id = None
        for widget in (self.fl_brgy, self.fl_water, self.fl_rain, self.fl_note):
            widget.delete(0, "end")
        self.fl_trend.set("Rising")
        self.fl_alert.set(group4database.FLOOD_ALERT_WARNING)

    def broadcast_alert(self):
        stats = group4database.get_flood_statistics()
        messagebox.showinfo("Broadcast sent", (
            f"Official early-warning broadcast dispatched.\n\n"
            f"Sender: {self.user_info.get('full_name', 'Admin')} ({self.user_info.get('role', 'Health official')})\n"
            f"Scope: all monitored areas ({stats['total']} stations)\n"
            f"High water: {stats['critical']} critical and {stats['warning']} warning stations\n"
            f"Highest: {stats['highest_area']}\n\n"
            "Residents will see the warning in their portal."))

    # ── Session ──────────────────────────────────────────────────────────────
    def on_close(self):
        try:
            self.root.destroy()
        except Exception:
            pass
        sys.exit(0)

    def handle_logout(self):
        if messagebox.askyesno("Log out", "Are you sure you want to log out or switch account?"):
            try:
                self.root.destroy()
            except Exception:
                pass
            self.on_logout_callback()

    def run(self):
        self.root.mainloop()