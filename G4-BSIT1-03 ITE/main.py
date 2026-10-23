# W.I.L.D. CARE: Post-Flood Disease Monitoring System
# MIT LISENCE
# Copyright (c) 2026 Jairus Corro. All rights reserved.
# Licensed under the W.I.L.D. CARE Educational License (see LICENSE.txt). Provided "AS IS", without warranty.
# Not a medical device. Do not use it for real clinical or emergency decisions.

import customtkinter

import group4database
from main_login_ui import LoginWindow
from public import PatientPortalWindow
from staff import AdminDashboardWindow

try:    # crisp text on high-DPI Windows screens
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass


def launch_login():
    group4database.create_group4database()
    customtkinter.set_default_color_theme("dark-blue")

    def on_login_success(user_info):
        window = PatientPortalWindow if user_info.get("role") == group4database.ROLE_PATIENT else AdminDashboardWindow
        window(user_info, on_logout_callback=launch_login).run()

    LoginWindow(on_login_success_callback=on_login_success).run()


if __name__ == "__main__":
    launch_login()