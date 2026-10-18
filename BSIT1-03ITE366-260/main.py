import group4database
import customtkinter
from main_login_ui import LoginWindow
from public import PatientPortalWindow
from staff import AdminDashboardWindow

try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

def launch_login():
    group4database.create_group4database()
    customtkinter.set_appearance_mode("dark")
    customtkinter.set_default_color_theme("dark-blue")

    def on_login_success(user_info):
        role = user_info.get("role", group4database.ROLE_PATIENT)

        if role == group4database.ROLE_PATIENT:
            portal = PatientPortalWindow(user_info, on_logout_callback=launch_login)
            portal.run()
        else:
            dashboard = AdminDashboardWindow(user_info, on_logout_callback=launch_login)
            dashboard.run()

    login_app = LoginWindow(on_login_success_callback=on_login_success)
    login_app.run()

if __name__ == "__main__":
    launch_login()



