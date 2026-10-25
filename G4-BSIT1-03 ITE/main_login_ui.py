# W.I.L.D. CARE: Post-Flood Disease Monitoring System
# MIT LISENCE
# Copyright (c) 2026 Jairus Corro. All rights reserved.
# Licensed under the W.I.L.D. CARE Educational License (see LICENSE.txt). Provided "AS IS", without warranty.
# Not a medical device. Do not use it for real clinical or emergency decisions.

import os
import sys
from tkinter import messagebox, filedialog

import customtkinter
from PIL import Image

import group4database
import ui_theme as ui
from ui_theme import COLOR_THEME_NAMIN


class LoginWindow:
    def __init__(self, on_login_success_callback):
        self.on_login_success = on_login_success_callback
        self._pwd_visible = False
        self._selected_id_photo = ""
        self._thumb_img = None

        self.root = customtkinter.CTk()
        self.root.title("W.I.L.D. CARE — Sign In BY GROUP4 BSIT1-03")
        ui.setup(self.root)
        ui.place_window(self.root, 940, 640, min_size=(860, 600))
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        self.build_hero()
        self.build_form()
        self.entry_user.focus_set()
        self.root.resizable(False, False)

    def on_close(self):
        try:
            self.root.destroy()
        except Exception:
            pass
        sys.exit(0)

    # ── Brand panel ──────────────────────────────────────────────────────────
    def build_hero(self):
        hero = customtkinter.CTkFrame(self.root, fg_color=COLOR_THEME_NAMIN["side"], corner_radius=0, width=340)
        hero.grid(row=0, column=0, sticky="nsew")
        hero.pack_propagate(False)

        tile = customtkinter.CTkFrame(hero, fg_color="#FFFFFF", corner_radius=ui.R_CARD)
        tile.pack(anchor="w", padx=32, pady=(44, 18))
        self.logo = ui.logo_image("wildcare_logo_shield.png", (72, 80))
        if self.logo:
            customtkinter.CTkLabel(tile, text="", image=self.logo).pack(padx=14, pady=12)
        else:
            customtkinter.CTkLabel(tile, text="WC", font=ui.FONTS["title"], text_color="#0F766E", width=48, height=48).pack(padx=8, pady=8)

        ui.label(hero, "W.I.L.D. CARE", "display", "side_text", anchor="w").pack(fill="x", padx=32)
        ui.label(hero, "Post-Flood Disease Monitoring System", "bodybold", "side_accent", anchor="w",
                 wraplength=270, justify="left").pack(fill="x", padx=32, pady=(2, 12))
        ui.label(hero, "Report illness, follow flood levels and reach your health workers sooner.", "body", "side_muted",
                 anchor="w", wraplength=270, justify="left").pack(fill="x", padx=32, pady=(0, 26))

        for title, desc in (("Live flood levels", "Water depth and rainfall in 7 Pangasinan areas"),
                            ("Early illness reports", "Health workers are alerted right away"),
                            ("One sign-in", "Residents, health workers and administrators")):
            item = ui.row(hero)
            item.pack(fill="x", padx=32, pady=7)
            customtkinter.CTkFrame(item, fg_color=COLOR_THEME_NAMIN["side_accent"], width=3, height=34, corner_radius=2).pack(side="left", padx=(0, 12))
            col = ui.row(item)
            col.pack(side="left", fill="x")
            ui.label(col, title, "bodybold", "side_text", anchor="w").pack(fill="x")
            ui.label(col, desc, "small", "side_muted", anchor="w").pack(fill="x")

        ui.label(hero, "Emergency: dial 911 or visit your nearest Barangay Health Station.", "small", "side_muted",
                 anchor="w", wraplength=270, justify="left").pack(side="bottom", fill="x", padx=32, pady=28)

    # ── Form panel ───────────────────────────────────────────────────────────
    def build_form(self):
        right = customtkinter.CTkFrame(self.root, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        bar = ui.row(right)
        bar.grid(row=0, column=0, sticky="ew", padx=28, pady=(20, 0))
        ui.button(bar, "Theme", ui.toggle_dark, kind="ghost", width=92, height=32, font="small").pack(side="right")
        ui.text_size_control(bar).pack(side="right", padx=(0, 10))

        body = ui.row(right)
        body.grid(row=1, column=0, sticky="ew", padx=60)
        right.bind("<Configure>", lambda e: body.grid_configure(padx=max(32, (e.width - 420) // 2)))

        self.views = {"Sign in": ui.row(body), "New resident": ui.row(body)}
        ui.segmented(body, list(self.views), self.show_view, "Sign in", height=36).pack(fill="x", pady=(0, 22))
        self.build_signin(self.views["Sign in"])
        self.build_register(self.views["New resident"])
        self.show_view("Sign in")

    def show_view(self, name):
        for key, frame in self.views.items():
            frame.pack_forget()
        self.views[name].pack(fill="x")

    def build_signin(self, view):
        ui.label(view, "Welcome back", "title", anchor="w").pack(fill="x")
        ui.label(view, "Sign in with your full name or email.", "body", "muted", anchor="w").pack(fill="x", pady=(2, 18))

        self.entry_user = ui.field(view, "Full name or email", placeholder="e.g. Jairus Mj Corro")
        label_row = ui.row(view)
        label_row.pack(fill="x")
        ui.label(label_row, "Password", "label", "muted", anchor="w").pack(side="left", pady=(0, 4))
        pw_row = ui.row(view)
        pw_row.pack(fill="x", pady=(0, 6))
        self.entry_pass = ui.entry(pw_row, "Your password", show="•")
        self.entry_pass.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.btn_eye = ui.button(pw_row, "Show", self.toggle_password, kind="secondary", width=70)
        self.btn_eye.pack(side="right")

        help_row = ui.row(view)
        help_row.pack(fill="x", pady=(0, 16))
        self.lbl_msg = ui.label(help_row, "", "small", "danger", anchor="w", wraplength=240, justify="left")
        self.lbl_msg.pack(side="left")
        ui.button(help_row, "Forgot password?", self.open_recovery, kind="link", font="small", height=26, width=120).pack(side="right")

        ui.button(view, "Sign in", self.handle_signin, height=46).pack(fill="x")
        ui.label(view, "One sign-in for everyone. You will be taken to your Resident or Health Worker portal.",
                 "small", "muted", wraplength=400, justify="left", anchor="w").pack(fill="x", pady=(14, 0))
        for widget in (self.entry_user, self.entry_pass):
            widget.bind("<Return>", lambda e: self.handle_signin())

    def build_register(self, view):
        ui.label(view, "Create a resident account", "title", anchor="w").pack(fill="x")
        ui.label(view, "Sign up with a photo of your valid ID as proof of real identity.", "body", "muted", anchor="w").pack(fill="x", pady=(2, 10))
        self.reg_name = ui.field(view, "Full name", placeholder="e.g. Ronaldo jr. V. Deguzman", pady=(0, 6))

        id_row = ui.row(view)
        id_row.pack(fill="x", pady=(0, 6))
        id_row.grid_columnconfigure((0, 1), weight=1)
        id_left, id_right = ui.row(id_row), ui.row(id_row)
        id_left.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        id_right.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        self.reg_id_type = ui.field(id_left, "Valid ID type", kind="combo",
                                    values=group4database.VALID_RESIDENT_ID_TYPES,
                                    default=group4database.VALID_RESIDENT_ID_TYPES[0],
                                    pady=(0, 0), height=34)

        # ID Photo attachment widget
        ui.label(id_right, "Proof of real identity (ID photo)", "small", "muted", anchor="w").pack(fill="x", pady=(0, 2))
        upload_card = customtkinter.CTkFrame(id_right, fg_color=COLOR_THEME_NAMIN["input"],
                                             corner_radius=ui.R_CTRL, border_width=1,
                                             border_color=COLOR_THEME_NAMIN["border"], height=34)
        upload_card.pack(fill="x")
        upload_card.pack_propagate(False)

        def browse_id_photo():
            path = filedialog.askopenfilename(
                title="Select Valid ID Photo (Proof of Real Identity)",
                filetypes=[
                    ("ID Image files", "*.png *.jpg *.jpeg *.webp *.bmp"),
                    ("PNG files", "*.png"),
                    ("JPEG files", "*.jpg *.jpeg"),
                    ("All files", "*.*")
                ]
            )
            if not path:
                return
            ok, res = group4database.validate_resident_id_photo(path)
            if not ok:
                self.lbl_reg.configure(text=f"⚠️ {res}", text_color=COLOR_THEME_NAMIN["danger"])
                messagebox.showerror("Invalid ID Photo", res)
                return
            self._selected_id_photo = res
            fname = os.path.basename(res)
            short_name = fname if len(fname) <= 15 else fname[:12] + "..."
            self.lbl_photo_info.configure(text=f"✓ {short_name}", text_color=COLOR_THEME_NAMIN["ok"])
            self.btn_preview_photo.pack(side="right", padx=(0, 4), pady=2)
            self.lbl_reg.configure(text=f"✓ ID photo attached: {fname}", text_color=COLOR_THEME_NAMIN["ok"])

        def preview_attached_photo():
            if not self._selected_id_photo:
                messagebox.showwarning("No Photo", "Please attach a photo of your valid ID first.")
                return
            self.show_photo_dialog(self._selected_id_photo, title=f"Valid ID Proof — {self.reg_id_type.get()}")

        btn_browse = ui.button(upload_card, "📷 Choose photo...", browse_id_photo,
                               kind="secondary", height=28, font="smallbold")
        btn_browse.pack(side="left", padx=(3, 4), pady=3)

        self.btn_preview_photo = ui.button(upload_card, "👁️ View", preview_attached_photo,
                                           kind="ghost", height=28, font="smallbold")

        self.lbl_photo_info = ui.label(upload_card, "No photo attached", "small", "muted", anchor="w")
        self.lbl_photo_info.pack(side="left", fill="x", expand=True, padx=(2, 2))

        self.reg_email = ui.field(view, "Email (for 6-digit recovery codes)", placeholder="e.g. ronaldojr@gmail.com", pady=(0, 6))

        pw_row = ui.row(view)
        pw_row.pack(fill="x", pady=(0, 6))
        pw_row.grid_columnconfigure((0, 1), weight=1)
        pw_left, pw_right = ui.row(pw_row), ui.row(pw_row)
        pw_left.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        pw_right.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        self.reg_pass = ui.field(pw_left, "Password", placeholder="At least 4 characters", show="•", pady=(0, 0), height=34)
        self.reg_conf = ui.field(pw_right, "Confirm password", placeholder="Re-type your password", show="•", pady=(0, 0), height=34)

        self.lbl_reg = ui.label(view, "", "small", "danger", anchor="w", wraplength=400, justify="left")
        self.lbl_reg.pack(fill="x", pady=(4, 6))
        ui.button(view, "Verify ID photo & create resident account", self.handle_register, height=44).pack(fill="x")
        self.reg_conf.bind("<Return>", lambda e: self.handle_register())

        def on_name_blur(event):
            val = self.reg_name.get().strip()
            if val:
                ok, err = group4database.validate_full_name(val)
                if not ok:
                    self.lbl_reg.configure(text=f"⚠️ {err}", text_color=COLOR_THEME_NAMIN["warn"])
                elif self.lbl_reg.cget("text").startswith("⚠️"):
                    self.lbl_reg.configure(text="")
        self.reg_name.bind("<FocusOut>", on_name_blur)

    def toggle_password(self):
        self._pwd_visible = not self._pwd_visible
        self.entry_pass.configure(show="" if self._pwd_visible else "•")
        self.btn_eye.configure(text="Hide" if self._pwd_visible else "Show")

    # ── Actions ──────────────────────────────────────────────────────────────
    def handle_signin(self):
        name, password = self.entry_user.get().strip(), self.entry_pass.get().strip()
        if not name or not password:
            self.lbl_msg.configure(text="Please enter your full name and password.", text_color=COLOR_THEME_NAMIN["danger"])
            return
        ok, result = group4database.authenticate_user(name, password)
        if ok:
            self.root.destroy()
            self.on_login_success(result)
            return
        message = result if isinstance(result, str) else "Invalid full name or password."
        if "locked" in message.lower():
            messagebox.showerror("Account locked", message)
            message = "Account is temporarily locked for 15 minutes."
        self.lbl_msg.configure(text=message, text_color=COLOR_THEME_NAMIN["danger"])
        self.entry_pass.delete(0, "end")

    def handle_register(self):
        name = self.reg_name.get().strip()
        ok_name, name_res = group4database.validate_full_name(name)
        if not ok_name:
            self.lbl_reg.configure(text=name_res, text_color=COLOR_THEME_NAMIN["danger"])
            self.reg_name.focus_set()
            return

        id_type = self.reg_id_type.get()
        if not self._selected_id_photo:
            msg = "Please attach a photo or picture of your valid ID as proof of real identity."
            self.lbl_reg.configure(text=f"⚠️ {msg}", text_color=COLOR_THEME_NAMIN["danger"])
            messagebox.showwarning(
                "Valid ID Photo Required",
                "Proof of real identity is required for resident registration.\n\n"
                f"Please click '📷 Choose photo...' to attach a picture of your Valid ID\n({id_type})."
            )
            return

        ok_photo, photo_res = group4database.validate_resident_id_photo(self._selected_id_photo)
        if not ok_photo:
            self.lbl_reg.configure(text=f"⚠️ {photo_res}", text_color=COLOR_THEME_NAMIN["danger"])
            return

        password = self.reg_pass.get().strip()
        confirm = self.reg_conf.get().strip()
        email = self.reg_email.get().strip()

        ok, msg = group4database.register_resident_user(
            name_res, password=password, confirm_password=confirm,
            email=email, id_type=id_type, id_photo_path=photo_res)
        if not ok:
            self.lbl_reg.configure(text=msg, text_color=COLOR_THEME_NAMIN["danger"])
            return

        messagebox.showinfo(
            "Resident Account Verified",
            f"Welcome to W.I.L.D. CARE by GROUP4 BSIT1-03, {name_res}!\n\n"
            f"Your proof of real identity has been verified:\n"
            f"• Valid ID Type: {id_type}\n"
            f"• Proof of Identity: Photo Verified ✓\n\n"
            "You can now sign in with your full name.")
        self.reset_register_fields()
        self.show_view("Sign in")
        ui.set_text(self.entry_user, name_res)
        self.entry_pass.delete(0, "end")
        self.entry_pass.focus_set()

    def reset_register_fields(self):
        for widget in (self.reg_name, self.reg_email, self.reg_pass, self.reg_conf):
            widget.delete(0, "end")
        self._selected_id_photo = ""
        if hasattr(self, "lbl_photo_info"):
            self.lbl_photo_info.configure(text="No photo attached", text_color=COLOR_THEME_NAMIN["muted"])
        if hasattr(self, "btn_preview_photo"):
            self.btn_preview_photo.pack_forget()
        self.lbl_reg.configure(text="")

    def show_photo_dialog(self, photo_path, title="Valid ID Proof"):
        if not photo_path or not os.path.isfile(photo_path):
            messagebox.showerror("Error", "ID photo file could not be found.")
            return
        dlg = ui.modal(self.root, title, 520, 500)
        card = ui.card(dlg)
        card.pack(fill="both", expand=True, padx=16, pady=16)

        ui.label(card, title, "title", anchor="w").pack(fill="x", padx=16, pady=(14, 2))
        ui.label(card, f"File: {os.path.basename(photo_path)}  •  Proof of Real Identity", "small", "muted", anchor="w").pack(fill="x", padx=16, pady=(0, 10))

        try:
            with Image.open(photo_path) as pil_img:
                pil_copy = pil_img.copy()
                pil_copy.thumbnail((460, 320), Image.Resampling.LANCZOS)
                modal_ctk_img = customtkinter.CTkImage(light_image=pil_copy, dark_image=pil_copy,
                                                        size=(pil_copy.width, pil_copy.height))
                lbl_img = customtkinter.CTkLabel(card, image=modal_ctk_img, text="", corner_radius=8)
                lbl_img.image = modal_ctk_img
                lbl_img.pack(padx=16, pady=(0, 14), expand=True)
        except Exception as e:
            ui.label(card, f"Could not load image preview:\n{e}", "small", "danger").pack(padx=16, pady=20)

        ui.button(card, "Close", dlg.destroy, kind="secondary", height=36).pack(fill="x", padx=16, pady=(0, 14))

    def open_recovery(self):
        """Two steps in one dialog: request the emailed code, then verify it and set a new password."""
        dlg = ui.modal(self.root, "Account recovery — W.I.L.D. CARE", 480, 520)
        panel = ui.card(dlg)
        panel.pack(fill="both", expand=True, padx=16, pady=16)
        inner = ui.row(panel)
        inner.pack(fill="both", expand=True, padx=22, pady=20)
        step1, step2 = ui.row(inner), ui.row(inner)
        who = {"value": ""}

        ui.label(step1, "Recover your account", "title", anchor="w").pack(fill="x")
        ui.label(step1, "Enter your full name or email. We will send a 6-digit code to the email address registered on your account.",
                 "body", "muted", anchor="w", justify="left", wraplength=400).pack(fill="x", pady=(4, 18))
        entry_who = ui.field(step1, "Full name or email", placeholder="Type your full name or email", pady=(0, 6))
        ui.set_text(entry_who, self.entry_user.get().strip())
        lbl1 = ui.label(step1, "", "small", "danger", anchor="w", justify="left", wraplength=400)
        lbl1.pack(fill="x", pady=(0, 10))
        btn_send = ui.button(step1, "Send 6-digit code", height=44)
        btn_send.pack(fill="x", pady=(0, 8))
        ui.button(step1, "Cancel", dlg.destroy, kind="secondary").pack(fill="x")

        lbl_sent = ui.label(step2, "", "body", "ok", anchor="w", justify="left", wraplength=400)
        lbl_sent.pack(fill="x", pady=(0, 14))
        ui.label(step2, "6-digit code", "label", "muted", anchor="w").pack(fill="x", pady=(0, 4))
        entry_otp = ui.entry(step2, "123456", height=46, font=ui.FONTS["mono"])
        entry_otp.pack(fill="x", pady=(0, 12))
        pw_grid = ui.row(step2)
        pw_grid.pack(fill="x")
        pw_grid.grid_columnconfigure((0, 1), weight=1)
        ui.label(pw_grid, "New password", "label", "muted", anchor="w").grid(row=0, column=0, sticky="w")
        ui.label(pw_grid, "Confirm password", "label", "muted", anchor="w").grid(row=0, column=1, sticky="w", padx=(8, 0))
        entry_new = ui.entry(pw_grid, "Min. 4 characters", show="•")
        entry_new.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        entry_conf = ui.entry(pw_grid, "Re-type", show="•")
        entry_conf.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(4, 0))
        lbl2 = ui.label(step2, "", "small", "danger", anchor="w", justify="left", wraplength=400)
        lbl2.pack(fill="x", pady=(8, 8))
        btn_reset = ui.button(step2, "Verify code and reset password", height=44)
        btn_reset.pack(fill="x", pady=(0, 8))
        nav = ui.row(step2)
        nav.pack(fill="x")
        btn_back = ui.button(nav, "Request a new code", kind="secondary", height=34, font="small")
        btn_back.pack(side="left", fill="x", expand=True, padx=(0, 4))
        ui.button(nav, "Cancel", dlg.destroy, kind="secondary", height=34, font="small").pack(side="left", fill="x", expand=True, padx=(4, 0))
        step1.pack(fill="both", expand=True)

        def go_back():
            step2.pack_forget()
            step1.pack(fill="both", expand=True)
            for widget in (entry_otp, entry_new, entry_conf):
                widget.delete(0, "end")
            lbl1.configure(text="")
            lbl2.configure(text="")

        def do_send():
            value = entry_who.get().strip()
            if not value:
                lbl1.configure(text="Please enter your full name or email.")
                return
            btn_send.configure(state="disabled", text="Sending code...")
            lbl1.configure(text="")
            dlg.update()
            ok, result = group4database.send_password_reset_otp(value)
            btn_send.configure(state="normal", text="Send 6-digit code")
            if not ok:
                lbl1.configure(text=result)
                return
            who["value"] = value
            lbl_sent.configure(text=f"Code sent to {result}. It expires in {group4database.OTP_VALID_MINUTES} minutes. "
                                    "Check your inbox and spam folder.")
            step1.pack_forget()
            step2.pack(fill="both", expand=True)
            entry_otp.focus_set()

        def do_reset():
            otp = entry_otp.get().strip()
            if not otp:
                lbl2.configure(text="Please enter the 6-digit code.")
                return
            ok, msg = group4database.verify_and_reset_password_with_otp(
                who["value"], otp, entry_new.get().strip(), entry_conf.get().strip())
            if not ok:
                lbl2.configure(text=msg)
                return
            messagebox.showinfo("Password reset", "Your password has been reset.\nYou may now sign in.")
            dlg.destroy()
            ui.set_text(self.entry_user, who["value"])
            self.entry_pass.delete(0, "end")
            self.entry_pass.focus_set()
            self.lbl_msg.configure(text="Password reset. Sign in with your new password.", text_color=COLOR_THEME_NAMIN["ok"])

        btn_send.configure(command=do_send)
        btn_reset.configure(command=do_reset)
        btn_back.configure(command=go_back)
        entry_who.bind("<Return>", lambda e: do_send())
        entry_otp.bind("<Return>", lambda e: do_reset())

    def run(self):
        self.root.mainloop()