# W.I.L.D. CARE: Post-Flood Disease Monitoring System
# Copyright (c) 2026 Jairus Corro. All rights reserved.
# Licensed under the W.I.L.D. CARE Educational License (see LICENSE.txt). Provided "AS IS", without warranty.
# Not a medical device. Do not use it for real clinical or emergency decisions.

import csv
import sys
from datetime import date, datetime
from tkinter import filedialog, messagebox

import customtkinter

import group4database
import ui_theme as ui
from ui_theme import C

SYMPTOMS = ["Fever", "Muscle pain", "Diarrhea", "Cough", "Skin rash", "Other"]
HOTLINES = [("National Emergency Helpline", "911"),
            ("Pangasinan PDRRMO", "(075) 542-7000 / 0917-855-7377"),
            ("Dagupan City CDRRMC", "(075) 522-0007 / 0928-500-2376"),
            ("Region 1 Medical Center (R1MC)", "(075) 515-8901"),
            ("Calasiao RHU & Emergency", "(075) 522-2405"),
            ("Philippine Red Cross (Dagupan)", "(075) 522-2092")]
# disease key -> (badge letter, display name, cause, safety tip)
WILD_META = {
    "leptospirosis": ("L", "Leptospirosis", "From floodwater", "Waded in floodwater? Visit the health station within 24 to 48 hours."),
    "dengue": ("D", "Dengue", "From mosquito bites", "Turn over, empty, dry and cover water containers."),
    "waterborne": ("W", "Water-borne illness", "Dirty water or food", "Drink boiled or bottled water. Wash hands with soap."),
    "influenza": ("I", "Influenza", "Fever, cough and infection", "Rest, drink fluids and see a doctor if fever lasts over 3 days."),
}
GAUGE = [("Safe", "ok"), ("Knee", "yellow"), ("Waist", "orange"), ("Chest", "danger")]
PAGES = [("flood", "Flood monitor"), ("report", "Report illness"), ("watch", "Disease watch")]
ALL_AREAS = "All areas"


def gauge_stage(water_m):
    return "Chest" if water_m >= 1.5 else "Waist" if water_m >= 1.0 else "Knee" if water_m >= 0.5 else "Safe"


class PatientPortalWindow:
    def __init__(self, user_info, on_logout_callback):
        self.user_info = user_info
        self.on_logout_callback = on_logout_callback
        self.full_name = user_info.get("full_name", "Resident")
        self.page = "flood"
        self.symptoms = set()
        self._flood_rows = {}
        self._timers = {}

        self.root = customtkinter.CTk()
        self.root.title("W.I.L.D. CARE — Resident Portal")
        ui.setup(self.root)
        ui.place_window(self.root, 1180, 760, min_size=(1000, 660))
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        self.build_sidebar()
        content = ui.row(self.root)
        content.grid(row=0, column=1, sticky="nsew", padx=24, pady=20)
        self.pages = {key: ui.row(content) for key, _ in PAGES}
        self.build_flood_page(self.pages["flood"])
        self.build_report_page(self.pages["report"])
        self.build_watch_page(self.pages["watch"])
        self.navigate("flood")
        self.schedule_refresh()

    # ── Shell ────────────────────────────────────────────────────────────────
    def build_sidebar(self):
        side = customtkinter.CTkFrame(self.root, fg_color=C["side"], corner_radius=0, width=260)
        side.grid(row=0, column=0, sticky="nsew")
        side.pack_propagate(False)

        brand = ui.row(side)
        brand.pack(fill="x", padx=22, pady=(26, 18))
        self.logo = ui.logo_image("wildcare_logo_shield.png", (36, 40))
        if self.logo:
            tile = customtkinter.CTkFrame(brand, fg_color="#FFFFFF", corner_radius=ui.R_CTRL)
            tile.pack(anchor="w", pady=(0, 10))
            customtkinter.CTkLabel(tile, text="", image=self.logo).pack(padx=8, pady=6)
        ui.label(brand, "W.I.L.D. CARE", "heading", "side_text", anchor="w").pack(fill="x")
        ui.label(brand, "Resident health and flood portal", "small", "side_muted", anchor="w").pack(fill="x")

        who = customtkinter.CTkFrame(side, fg_color=C["side_hover"], corner_radius=ui.R_CTRL)
        who.pack(fill="x", padx=16, pady=(0, 18))
        ui.label(who, "Signed in as", "small", "side_muted", anchor="w").pack(fill="x", padx=14, pady=(10, 0))
        ui.label(who, self.full_name, "bodybold", "side_text", anchor="w", wraplength=200, justify="left").pack(fill="x", padx=14, pady=(0, 10))

        self.nav = {}
        for key, text in PAGES:
            btn = ui.button(side, text, lambda k=key: self.navigate(k), kind="nav", height=42, anchor="w")
            btn.pack(fill="x", padx=16, pady=2)
            self.nav[key] = btn

        help_card = customtkinter.CTkFrame(side, fg_color=C["side_danger_bg"], border_width=1, border_color=C["side_danger"],
                                           corner_radius=ui.R_CARD)
        help_card.pack(fill="x", padx=16, pady=(22, 0))
        ui.label(help_card, "Need urgent help?", "bodybold", "side_text", anchor="w").pack(fill="x", padx=14, pady=(12, 2))
        ui.label(help_card, "Call your Barangay Health Station or 911 if fever or vomiting is severe.", "small", "side_danger",
                 anchor="w", wraplength=185, justify="left").pack(fill="x", padx=14)
        ui.button(help_card, "Emergency numbers", self.show_hotlines, kind="nav", font="smallbold", height=30,
                  anchor="w").pack(fill="x", padx=6, pady=(4, 8))

        bottom = ui.row(side)
        bottom.pack(side="bottom", fill="x", padx=16, pady=18)
        ui.text_size_control(bottom).pack(fill="x", pady=(0, 8))
        ui.button(bottom, "Switch light / dark", ui.toggle_dark, kind="nav", height=34, font="small", anchor="w").pack(fill="x")
        ui.button(bottom, "Log out", self.handle_logout, kind="danger", height=40).pack(fill="x", pady=(8, 0))

    def navigate(self, key):
        self.page = key
        for name, frame in self.pages.items():
            frame.pack_forget()
            ui.restyle(self.nav[name], "nav_active" if name == key else "nav")
        self.pages[key].pack(fill="both", expand=True)
        self.refresh()

    def refresh(self):
        {"flood": self.load_flood, "report": self.load_cases, "watch": self.load_watch}[self.page]()

    def schedule_refresh(self):
        self.cancel("refresh")
        self._timers["refresh"] = self.root.after(30000, lambda: (self.refresh(), self.schedule_refresh()))

    def cancel(self, name):
        if self._timers.get(name):
            try:
                self.root.after_cancel(self._timers.pop(name))
            except Exception:
                pass

    def header(self, parent, title, subtitle):
        ui.label(parent, title, "display", anchor="w").pack(fill="x")
        ui.label(parent, subtitle, "body", "muted", anchor="w").pack(fill="x", pady=(2, 16))

    # ── Flood monitor ────────────────────────────────────────────────────────
    def build_flood_page(self, page):
        self.header(page, "Flood monitor", "Live water levels for the 7 monitored Pangasinan areas.")

        self.banner = customtkinter.CTkFrame(page, corner_radius=ui.R_CARD, border_width=1)
        self.banner.pack(fill="x", pady=(0, 14))
        self.lbl_banner_title = ui.label(self.banner, "", "bodybold", anchor="w")
        self.lbl_banner_title.pack(fill="x", padx=16, pady=(12, 0))
        ui.label(self.banner, "WARNING: THIS IS ONLY A DEMONSTRATION FOR FLOOD MONITORING BY GROUP4 BSIT1-03 - FOR FUTURE EDUCATION.",
                 "small", "muted", anchor="w").pack(fill="x", padx=16, pady=(0, 12))

        cols = ui.row(page)
        cols.pack(fill="both", expand=True)
        cols.grid_columnconfigure(0, weight=3, uniform="flood")
        cols.grid_columnconfigure(1, weight=2, uniform="flood")
        cols.grid_rowconfigure(0, weight=1)

        left = ui.card(cols)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        bar = ui.row(left)
        bar.pack(fill="x", padx=16, pady=(16, 10))
        self.flood_area = ui.combo(bar, [ALL_AREAS] + group4database.AREAS, ALL_AREAS, height=34, width=150,
                                   command=lambda _: self.load_flood())
        self.flood_area.pack(side="left")
        self.flood_search = ui.entry(bar, "Search barangay...", height=34)
        self.flood_search.pack(side="left", fill="x", expand=True, padx=(8, 0))
        self.flood_search.bind("<KeyRelease>", lambda e: self.debounce("flood", self.load_flood))
        table = ui.row(left)
        table.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.flood_tree = ui.make_tree(table, [("place", "Barangay / area", 230, "w"), ("water", "Water", 80, "center"),
                                               ("alert", "Alert", 90, "center")])
        ui.style_tags(self.flood_tree, ui.FLOOD_ROW_TAGS)
        self.flood_tree.bind("<<TreeviewSelect>>", self.on_flood_select)

        right = ui.card(cols)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        box = ui.row(right)
        box.pack(fill="both", expand=True, padx=20, pady=18)
        ui.label(box, "Selected area", "small", "muted", anchor="w").pack(fill="x")
        self.lbl_place = ui.label(box, "No data", "heading", anchor="w", wraplength=260, justify="left")
        self.lbl_place.pack(fill="x", pady=(0, 6))
        self.lbl_depth = ui.label(box, "0.00 m", "display", "ok", anchor="w")
        self.lbl_depth.pack(fill="x")
        self.lbl_cond = ui.label(box, "", "bodybold", anchor="w", wraplength=260, justify="left")
        self.lbl_cond.pack(fill="x", pady=(0, 16))
        ui.label(box, "Water level gauge", "label", "muted", anchor="w").pack(fill="x", pady=(0, 6))
        gauge = ui.row(box)
        gauge.pack(fill="x", pady=(0, 18))
        self.gauge = {}
        for name, tone in GAUGE:
            col = ui.row(gauge)
            col.pack(side="left", fill="x", expand=True, padx=3)
            bar_ = customtkinter.CTkFrame(col, width=1, height=10, corner_radius=4, fg_color=C["neutral"])
            bar_.pack(fill="x", pady=(0, 5))
            lbl = ui.label(col, name, "small", "muted")
            lbl.pack()
            self.gauge[name] = (bar_, lbl, tone)
        tip = ui.inset(box)
        tip.pack(fill="x")
        ui.label(tip, "Health advisory", "smallbold", "accent_text", anchor="w").pack(fill="x", padx=14, pady=(10, 2))
        self.lbl_tip = ui.label(tip, "", "small", anchor="w", wraplength=260, justify="left")
        self.lbl_tip.pack(fill="x", padx=14, pady=(0, 12))

    def debounce(self, name, fn, delay=250):
        self.cancel(name)
        self._timers[name] = self.root.after(delay, fn)

    def load_flood(self):
        area = self.flood_area.get()
        rows = group4database.get_flood_records(city_filter="All Cities" if area == ALL_AREAS else area,
                                                search_query=self.flood_search.get())
        keep = self.flood_tree.selection()
        self.flood_tree.delete(*self.flood_tree.get_children())
        self._flood_rows = {str(r[0]): r for r in rows}
        for r in rows:
            level = r[7].split(" ")[0]
            tag = ui.flood_tag(r[7])
            self.flood_tree.insert("", "end", iid=str(r[0]), tags=(tag,),
                                   values=(group4database.place_label(r[1], r[2]), f"{r[3]:.2f} m", level))
        if keep and keep[0] in self._flood_rows:
            self.flood_tree.selection_set(keep[0])
        elif rows:
            self.flood_tree.selection_set(str(rows[0][0]))
        else:
            self.show_flood(None)

        stats = group4database.get_flood_statistics()
        if stats["critical"]:
            tone, text = "danger", f"Critical flooding in {stats['critical']} area(s). Avoid floodwater and follow evacuation advisories."
        elif stats["warning"]:
            tone, text = "orange", f"Flood warning in {stats['warning']} area(s). Do not walk through floodwater."
        else:
            tone, text = "ok", "No critical flooding reported right now. Stay alert and check back often."
        bg, fg = ui.TONES[tone]
        self.banner.configure(fg_color=C[bg], border_color=C[fg])
        self.lbl_banner_title.configure(text=text, text_color=C[fg])

    def on_flood_select(self, _event=None):
        sel = self.flood_tree.selection()
        if sel:
            self.show_flood(self._flood_rows.get(sel[0]))

    def show_flood(self, rec):
        if not rec:
            self.lbl_place.configure(text="No matching areas")
            self.lbl_depth.configure(text="—", text_color=C["muted"])
            self.lbl_cond.configure(text="")
            self.lbl_tip.configure(text="Try a different area or search term.")
            stage = None
        else:
            stage = gauge_stage(rec[3])
            tone = dict(GAUGE)[stage]
            self.lbl_place.configure(text=group4database.place_label(rec[1], rec[2]))
            self.lbl_depth.configure(text=f"{rec[3]:.2f} m", text_color=C[tone])
            self.lbl_cond.configure(text=f"{stage} deep · {rec[8].lower()} · {rec[6].lower()}")
            self.lbl_tip.configure(text=rec[9] or "Avoid contaminated water.")
        for name, (bar_, lbl, tone) in self.gauge.items():
            active = name == stage
            bar_.configure(fg_color=C[tone] if active else C["neutral"], height=16 if active else 10)
            lbl.configure(text_color=C[tone] if active else C["muted"], font=ui.FONTS["smallbold" if active else "small"])

    # ── Report illness & my cases ────────────────────────────────────────────
    def build_report_page(self, page):
        self.header(page, "Report illness", "A health worker is notified as soon as you send a report.")
        cols = ui.row(page)
        cols.pack(fill="both", expand=True)
        cols.grid_columnconfigure((0, 1), weight=1, uniform="report")
        cols.grid_rowconfigure(0, weight=1)

        form = ui.card(cols)
        form.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        box = ui.row(form)
        box.pack(fill="both", expand=True, padx=20, pady=18)
        self.rep_area = ui.field(box, "City / municipality", "combo", group4database.AREAS, group4database.AREAS[0], pady=(0, 8))
        self.rep_brgy = ui.field(box, "Barangay", placeholder="e.g. Pantal", pady=(0, 8))
        who = ui.row(box)
        who.pack(fill="x")
        who.grid_columnconfigure((0, 1), weight=1)
        left_col, right_col = ui.row(who), ui.row(who)
        left_col.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        right_col.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        self.rep_age = ui.field(left_col, "Age", placeholder="e.g. 34", pady=(0, 8))
        self.rep_sex = ui.field(right_col, "Sex", "combo", ["Male", "Female", "Other"], "Male", pady=(0, 8))

        ui.label(box, "What do you feel?", "label", "muted", anchor="w").pack(fill="x", pady=(2, 6))
        chips = ui.row(box)
        chips.pack(fill="x", pady=(0, 8))
        chips.grid_columnconfigure((0, 1), weight=1)
        self.chips = {}
        for i, name in enumerate(SYMPTOMS):
            chip = ui.button(chips, name, lambda n=name: self.toggle_symptom(n), kind="secondary", height=36)
            chip.grid(row=i // 2, column=i % 2, padx=3, pady=3, sticky="ew")
            self.chips[name] = chip
        self.rep_notes = ui.field(box, "Additional details (optional)", placeholder="e.g. Waded in flood yesterday, high fever", pady=(0, 14))
        ui.button(box, "Send report to health worker", self.submit_report, height=46).pack(fill="x")

        cases = ui.card(cols)
        cases.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        head = ui.row(cases)
        head.pack(fill="x", padx=20, pady=(18, 0))
        ui.label(head, "My cases", "title", anchor="w").pack(side="left")
        ui.button(head, "Export CSV", self.export_cases, kind="secondary", height=30, font="small", width=96).pack(side="right")
        ui.label(cases, "Track your assessment and recovery progress.", "small", "muted", anchor="w").pack(fill="x", padx=20, pady=(0, 8))
        self.cases_list = customtkinter.CTkScrollableFrame(cases, fg_color="transparent")
        self.cases_list.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def toggle_symptom(self, name):
        selected = name not in self.symptoms
        (self.symptoms.add if selected else self.symptoms.discard)(name)
        ui.restyle(self.chips[name], "primary" if selected else "secondary")
        self.chips[name].configure(text=f"✓  {name}" if selected else name)

    def submit_report(self):
        brgy, area = self.rep_brgy.get().strip(), self.rep_area.get()
        if not brgy:
            messagebox.showwarning("Location required", "Please enter your barangay.")
            return
        if not self.symptoms:
            messagebox.showwarning("Symptoms required", "Please select at least one symptom you are feeling.")
            return
        symptoms = ", ".join(s for s in SYMPTOMS if s in self.symptoms)
        if self.rep_notes.get().strip():
            symptoms += f" ({self.rep_notes.get().strip()})"
        ok, result = group4database.add_patient_record(
            self.full_name, self.rep_age.get().strip(), self.rep_sex.get(), f"{brgy}, {area}", symptoms,
            "Under Observation", str(date.today()))
        if not ok:
            messagebox.showerror("Could not send report", str(result))
            return
        messagebox.showinfo("Report sent", f"Thank you, {self.full_name}.\n\nYour symptoms ({symptoms}) were forwarded to the "
                                           "local health worker.\nStatus: being watched.")
        ui.set_text(self.rep_notes, "")
        self.load_cases()

    def load_cases(self):
        for widget in self.cases_list.winfo_children():
            widget.destroy()
        records = group4database.get_patient_records_by_account(patient_name=self.full_name)
        if not records:
            ui.label(self.cases_list, "No cases reported yet.\nUse the form to report an illness.", "body", "muted",
                     justify="center").pack(pady=40)
            return
        steps = ["Being watched", "In treatment", "Recovered"]
        for _id, _name, _age, _sex, place, disease, status, logged in records:
            stage = 1 if status == "Admitted" else 2 if status == "Recovered" else 0
            tone = ("warn", "danger", "ok")[stage]
            item = ui.inset(self.cases_list)
            item.pack(fill="x", pady=5, padx=2)
            top = ui.row(item)
            top.pack(fill="x", padx=14, pady=(12, 2))
            ui.label(top, disease, "bodybold", anchor="w", wraplength=210, justify="left").pack(side="left", fill="x", expand=True)
            ui.pill(top, steps[stage], tone).pack(side="right")
            try:
                logged = datetime.strptime(logged, "%Y-%m-%d").strftime("%b %d")
            except ValueError:
                pass
            ui.label(item, f"Sent {logged} · {place}", "small", "muted", anchor="w").pack(fill="x", padx=14, pady=(0, 10))
            track = ui.row(item)
            track.pack(fill="x", padx=14, pady=(0, 12))
            track.grid_columnconfigure((0, 1, 2), weight=1, uniform="track")
            for i, text in enumerate(steps):
                customtkinter.CTkFrame(track, width=1, height=5, corner_radius=3, fg_color=C[tone] if i <= stage else C["neutral"]).grid(
                    row=0, column=i, sticky="ew", padx=2)
                ui.label(track, text, "smallbold" if i == stage else "small", "text" if i == stage else "muted").grid(row=1, column=i, pady=(4, 0))

    def export_cases(self):
        records = group4database.get_patient_records_by_account(patient_name=self.full_name)
        if not records:
            messagebox.showinfo("Export", "No case records to export.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Spreadsheet", "*.csv")],
                                            initialfile=f"my_wildcare_cases_{date.today()}.csv", title="Export my case records")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Name", "Age", "Sex", "Barangay", "Illness", "Status", "Date Logged"])
                writer.writerows(records)
            messagebox.showinfo("Export successful", f"Saved {len(records)} record(s) to:\n{path}")
        except OSError as e:
            messagebox.showerror("Export failed", f"Could not save the CSV file:\n{e}")

    # ── Disease watch ────────────────────────────────────────────────────────
    def build_watch_page(self, page):
        self.header(page, "Disease watch", "Flood-season illnesses (W·I·L·D) across the 7 monitored Pangasinan areas.")
        self.watch_list = customtkinter.CTkScrollableFrame(page, fg_color="transparent")
        self.watch_list.pack(fill="both", expand=True)
        self.watch_list.grid_columnconfigure((0, 1), weight=1, uniform="watch")
        self.lbl_source = ui.label(page, "", "small", "muted", anchor="w", wraplength=820, justify="left")
        self.lbl_source.pack(fill="x", pady=(8, 0))

    def load_watch(self):
        for widget in self.watch_list.winfo_children():
            widget.destroy()
        overview = group4database.get_disease_overview()
        for i, d in enumerate(overview):
            letter, name, cause, tip = WILD_META.get(d["disease"].lower(), (d["disease"][:1].upper(), d["disease"], "", ""))
            tile = ui.card(self.watch_list)
            tile.grid(row=i // 2, column=i % 2, sticky="nsew", padx=6, pady=6)
            box = ui.row(tile)
            box.pack(fill="both", expand=True, padx=18, pady=16)

            head = ui.row(box)
            head.pack(fill="x")
            badge = customtkinter.CTkFrame(head, fg_color=C["accent_soft"], width=36, height=36, corner_radius=ui.R_CTRL)
            badge.pack(side="left", padx=(0, 10))
            badge.pack_propagate(False)
            ui.label(badge, letter, "heading", "accent_text").place(relx=0.5, rely=0.5, anchor="center")
            names = ui.row(head)
            names.pack(side="left", fill="x", expand=True)
            ui.label(names, name, "heading", anchor="w").pack(fill="x")
            ui.label(names, cause, "small", "muted", anchor="w").pack(fill="x")
            change = d["change_str"]
            ui.pill(head, f"{change} vs last year" if change[0] in "▲▼" else change,
                    "danger" if "▲" in change else "ok" if "▼" in change else "neutral").pack(side="right")

            ui.label(box, f"{d['cases']:,}", "display", anchor="w").pack(fill="x", pady=(10, 0))
            ui.label(box, f"cases this year · {d['cases_last_year']:,} last year · {d['deaths']:,} deaths", "small", "muted",
                     anchor="w").pack(fill="x", pady=(0, 10))
            top = d["areas"][:3]
            peak = max((c for _, c in top), default=1) or 1
            for area, cases in top:
                line = ui.row(box)
                line.pack(fill="x", pady=2)
                ui.label(line, area, "small", anchor="w", width=110).pack(side="left")
                bar_ = customtkinter.CTkProgressBar(line, height=6, corner_radius=3, fg_color=C["neutral"], progress_color=C["accent"])
                bar_.set(cases / peak)
                bar_.pack(side="left", fill="x", expand=True, padx=8)
                ui.label(line, f"{cases:,}", "smallbold", anchor="e", width=44).pack(side="right")
            if tip:
                note = ui.inset(box)
                note.pack(fill="x", pady=(12, 0))
                ui.label(note, tip, "small", anchor="w", wraplength=300, justify="left").pack(fill="x", padx=12, pady=9)
        if overview:
            first = overview[0]
            self.lbl_source.configure(text=f"{first['period']} · updated {first['updated_at']} · {first['source']}")

    # ── Dialogs & session ────────────────────────────────────────────────────
    def show_hotlines(self):
        dlg = ui.modal(self.root, "Emergency hotlines — Pangasinan", 460, 440)
        panel = ui.card(dlg)
        panel.pack(fill="both", expand=True, padx=18, pady=0)
        ui.label(panel, "Emergency hotlines", "title", anchor="w").pack(fill="x", padx=22, pady=(18, 8))
        for name, number in HOTLINES:
            line = ui.row(panel)
            line.pack(fill="x", padx=22, pady=5)
            ui.label(line, name, "label", "muted", anchor="w").pack(fill="x")
            ui.label(line, number, "bodybold", "accent_text", anchor="w").pack(fill="x")
        ui.button(panel, "Close", dlg.destroy, kind="secondary").pack(fill="x", padx=22, pady=(14, 18), side="bottom")

    def close_window(self):
        for name in list(self._timers):
            self.cancel(name)
        try:
            self.root.destroy()
        except Exception:
            pass

    def on_close(self):
        self.close_window()
        sys.exit(0)

    def handle_logout(self):
        if messagebox.askyesno("Log out", "Are you sure you want to log out of W.I.L.D. CARE?"):
            self.close_window()
            self.on_logout_callback()

    def run(self):
        self.root.mainloop()