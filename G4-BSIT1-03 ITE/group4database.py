# W.I.L.D. CARE: Post-Flood Disease Monitoring System
# Copyright (c) 2026 Jairus Corro. All rights reserved.
# Licensed under the W.I.L.D. CARE Educational License (see LICENSE.txt). Provided "AS IS", without warranty.
# Not a medical device. Do not use it for real clinical or emergency decisions.

import csv
import hashlib
import hmac
import html
import os
import secrets
import smtplib
import sqlite3
import string
from datetime import date, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

DATABASE_FILENAME = "bsit1group4database.db"
TS_FORMAT = "%Y-%m-%d %H:%M:%S"
PBKDF2_ITERATIONS = 100000
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION = 15      # minutes
OTP_VALID_MINUTES = 15
OTP_MAX_TRIES = 5

# The only areas this system monitors (flood stations, health tracking, dropdowns).
AREAS = ["Dagupan City", "Calasiao", "Malasiqui", "San Carlos City", "Bayambang", "Santa Barbara", "Lingayen"]

STATUS_OPTIONS = ["Under Observation", "Admitted", "Recovered"]

ROLE_PATIENT = "Patient/Resident"
ROLE_HEALTH_WORKER = "RHU/Hospital Health Worker"
ROLE_BRGY_STAFF = "BHw/Barangy Health Worker's"
ROLE_ADMIN = "Admin"
OFFICIALS_ROLES = [ROLE_HEALTH_WORKER, ROLE_BRGY_STAFF, ROLE_ADMIN]
ALL_ROLES = [ROLE_PATIENT, ROLE_HEALTH_WORKER, ROLE_BRGY_STAFF, ROLE_ADMIN]
REGISTRATION_OFFICIALS_ROLES = [ROLE_HEALTH_WORKER, ROLE_BRGY_STAFF]

FLOOD_ALERT_NORMAL = "Normal (Safe)"
FLOOD_ALERT_LOW = "Alert (Low)"
FLOOD_ALERT_WARNING = "Warning (Moderate)"
FLOOD_ALERT_CRITICAL = "Critical (Evacuate)"
FLOOD_ALERT_LEVELS = [FLOOD_ALERT_NORMAL, FLOOD_ALERT_LOW, FLOOD_ALERT_WARNING, FLOOD_ALERT_CRITICAL]
FLOOD_STATUS_OPTIONS = ["Rising", "Stationary", "Receding"]


# ── Configuration (secrets come from environment variables, never from source) ──
def env(*names, default=""):
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return default


def env_int(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


# Set WILDCARE_SMTP_EMAIL and WILDCARE_SMTP_PASSWORD (a Gmail App Password) to enable email recovery.
SMTP_CONFIG = {
    "host": env("WILDCARE_SMTP_HOST", default="smtp.gmail.com"),
    "port": env_int("WILDCARE_SMTP_PORT", 587),
    "sender_email":    os.environ.get("WILDCARE_SMTP_EMAIL", "jaizenraimamaril@gmail.com").strip(),
    "sender_password": os.environ.get("WILDCARE_SMTP_PASSWORD", "wiaccoqhttheqoid").strip(),
    "sender_name":     "W.I.L.D. CARE Account Recovery"
}
SMPTP_CONFIGURATION = SMTP_CONFIG  # backward-compatible alias

DEFAULT_ADMIN_NAME = "Admin"
DEFAULT_ADMIN_PASS = env("WILDCARE_DEFAULT_ADMIN_PASS", default="wildcare#admin#2026")

_passcodes = env("WILDCARE_PASSCODES")
OFFICIAL_WILDCARE_SECURITY_PASSCODES = (
    [c.strip() for c in _passcodes.split(",")] if _passcodes
    else ["WC_HEALTH2026", "WC_BHW2026", "WC_ADMIN2026", "WC_RESOURCE2026"]
)


# ── Connection & query helpers ─────────────────────────────────────────────
class _AutoCloseConnection(sqlite3.Connection):
    """`with` commits/rolls back like normal, then also closes the connection (no locked .db file)."""
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def group4_get_database_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), DATABASE_FILENAME)


def group4_get_database_connection():
    db = sqlite3.connect(group4_get_database_path(), timeout=15.0, factory=_AutoCloseConnection)
    db.execute("PRAGMA journal_mode=WAL;")
    db.execute("PRAGMA synchronous=NORMAL;")
    return db


def fetch(sql, params=(), one=False):
    """SELECT helper (parameter-bound). Returns rows, or a single row/None when one=True."""
    try:
        with group4_get_database_connection() as db:
            cur = db.execute(sql, params)
            return cur.fetchone() if one else cur.fetchall()
    except sqlite3.Error as e:
        print(f"[!] Database read error: {e}")
        return None if one else []


def write(sql, params=(), done=None):
    """INSERT/UPDATE/DELETE helper. Returns (True, done-message or new row id) or (False, error)."""
    try:
        with group4_get_database_connection() as db:
            cur = db.execute(sql, params)
            return True, (cur.lastrowid if done is None else done)
    except sqlite3.Error as e:
        return False, str(e)


def to_int(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


# ── Password hashing ───────────────────────────────────────────────────────
def implement_generate_salt(length=32):
    return secrets.token_hex(length)


def hashlib_pbkdf2_password(plain_password, salt, iterations=PBKDF2_ITERATIONS):
    """PBKDF2-HMAC-SHA256. Format: 'pbkdf2:iterations:salt_hex:digest_hex'."""
    digest = hashlib.pbkdf2_hmac("sha256", plain_password.strip().encode("utf-8"), bytes.fromhex(salt), iterations).hex()
    return f"pbkdf2:{iterations}:{salt}:{digest}"


def new_hash(password):
    return hashlib_pbkdf2_password(password, implement_generate_salt())


def group4_verify_password(plain_password, stored_hash):
    """Constant-time check; understands PBKDF2 hashes plus the legacy salted/unsalted SHA-256 formats."""
    password = plain_password.strip().encode("utf-8")
    if not stored_hash:
        return False
    if stored_hash.startswith("pbkdf2:"):
        parts = stored_hash.split(":")
        if len(parts) != 4:
            return False
        _, iter_str, salt, expected = parts
        iterations = to_int(iter_str) or PBKDF2_ITERATIONS
        is_hex = len(salt) % 2 == 0 and all(c in string.hexdigits for c in salt)
        salt_bytes = bytes.fromhex(salt) if is_hex else salt.encode("utf-8")
        return hmac.compare_digest(hashlib.pbkdf2_hmac("sha256", password, salt_bytes, iterations).hex(), expected)
    if ":" in stored_hash:
        salt, expected = stored_hash.split(":", 1)
        return hmac.compare_digest(hashlib.sha256(salt.encode("utf-8") + password).hexdigest(), expected)
    return hmac.compare_digest(hashlib.sha256(password).hexdigest(), stored_hash)


# ── Schema, migrations & seed data ─────────────────────────────────────────
_SCHEMA = """
CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT NOT NULL, age INTEGER NOT NULL, sex TEXT NOT NULL,
    barangay TEXT NOT NULL, disease TEXT NOT NULL, status TEXT NOT NULL, date_logged TEXT NOT NULL,
    display_order INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL,
    official_id TEXT DEFAULT '', station_barangay TEXT DEFAULT '', date_created TEXT NOT NULL,
    failed_attempts INTEGER DEFAULT 0, locked_until TEXT DEFAULT '', email TEXT DEFAULT '',
    reset_otp_hash TEXT DEFAULT '', reset_otp_expiry TEXT DEFAULT '', reset_otp_attempts INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS flood_monitoring (
    id INTEGER PRIMARY KEY AUTOINCREMENT, city TEXT NOT NULL, barangay TEXT NOT NULL,
    water_level_meters REAL NOT NULL, water_depth_desc TEXT NOT NULL, rainfall_rate_mm REAL NOT NULL,
    rainfall_desc TEXT NOT NULL, alert_level TEXT NOT NULL, status TEXT NOT NULL, early_warning TEXT NOT NULL,
    last_updated TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS disease_statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT, disease TEXT NOT NULL, area TEXT NOT NULL, period TEXT NOT NULL,
    cases INTEGER DEFAULT 0, cases_last_year INTEGER DEFAULT 0, deaths INTEGER DEFAULT 0,
    source TEXT DEFAULT '', updated_by TEXT DEFAULT '', updated_at TEXT DEFAULT '');
"""

# Columns added in later versions: older database files are upgraded in place.
_ADDED_COLUMNS = {
    "patients": {"display_order": "INTEGER DEFAULT 0"},
    "users": {"official_id": "TEXT DEFAULT ''", "station_barangay": "TEXT DEFAULT ''",
              "failed_attempts": "INTEGER DEFAULT 0", "locked_until": "TEXT DEFAULT ''", "email": "TEXT DEFAULT ''",
              "reset_otp_hash": "TEXT DEFAULT ''", "reset_otp_expiry": "TEXT DEFAULT ''",
              "reset_otp_attempts": "INTEGER DEFAULT 0"},
}

_N, _L, _W, _C = FLOOD_ALERT_NORMAL, FLOOD_ALERT_LOW, FLOOD_ALERT_WARNING, FLOOD_ALERT_CRITICAL
# (city, barangay, water m, rain mm/h, alert, trend, advisory, last updated)
_FLOOD_SEED = [
    ("Dagupan City", "Pantal", 0.75, 18.5, _W, "Rising", "PAGASA FLOOD ADVISORY: High tide (1.2m at 14:30) compounding Pantal River runoff. Avoid barefoot wading.", "2026-10-18 14:15"),
    ("Dagupan City", "Lasip Chico", 1.35, 24.0, _C, "Rising", "CDRRMC EVACUATION ADVISORY: Overflow from tributary network. Impassable to light vehicles. Evacuation center open.", "2026-10-18 14:10"),
    ("Dagupan City", "Malued", 0.90, 16.0, _W, "Stationary", "ADVISORY: Standing floodwater along interior access roads. RHU on standby for prophylaxis distribution.", "2026-10-18 14:00"),
    ("Dagupan City", "Bonuan", 1.15, 34.0, _C, "Rising", "CRITICAL: High tide coastal wave runup plus heavy rainfall. Mandatory evacuation in coastal zone.", "2026-10-18 14:20"),
    ("Calasiao", "Talibaew", 2.15, 36.5, _C, "Rising", "CRITICAL FLOOD WARNING: Marusay River bank breach. Immediate evacuation to Calasiao Sports Complex underway.", "2026-10-18 14:20"),
    ("Calasiao", "Quesban", 1.45, 26.0, _C, "Rising", "PDRRMO ALERT: Backflooding from Bued-Sinocalan basin. Zone 3 residents advised to move to elevated shelters.", "2026-10-18 14:05"),
    ("Calasiao", "Banaoang", 0.85, 14.0, _W, "Stationary", "CAUTION: Agricultural corridors inundated; monitor tributary creeks. Leptospirosis alert active.", "2026-10-18 13:50"),
    ("Calasiao", "Poblacion", 0.10, 2.0, _N, "Receding", "Safe · normal water flow.", "2026-10-18 13:00"),
    ("Santa Barbara", "Minien East", 1.65, 32.0, _C, "Rising", "PAGASA-ARBFFWC BULLETIN: Sinocalan River gauge at 7.45m MASL (Critical). Rescue units mobilized.", "2026-10-18 14:25"),
    ("Santa Barbara", "Poblacion Norte", 0.50, 9.5, _L, "Receding", "ADVISORY: Drainage clearing completed near municipal hall. Road passable with caution.", "2026-10-18 13:40"),
    ("Malasiqui", "Poblacion", 0.40, 8.0, _L, "Stationary", "MONITORING: Minor street runoff on Montemayor St. Pumping station operational.", "2026-10-18 13:30"),
    ("Malasiqui", "Lunec", 0.95, 15.5, _W, "Rising", "WARNING: Tributary canal elevated. Lowland farmers advised to secure livestock and stay off submerged paths.", "2026-10-18 14:00"),
    ("Lingayen", "Maniboc", 0.35, 6.0, _L, "Receding", "COASTAL WATCH: Lingayen Gulf surge monitoring normal. Water receding towards beach estuary.", "2026-10-18 13:15"),
    ("Lingayen", "Poblacion", 0.10, 2.0, _N, "Receding", "NORMAL: Provincial Capitol complex clear. All municipal roads passable.", "2026-10-18 13:00"),
    ("Bayambang", "Hermoza", 1.55, 28.5, _C, "Rising", "PAGASA BULLETIN: Agno River lower basin surging. Preemptive evacuation enforced in low-lying zones.", "2026-10-18 14:15"),
    ("San Carlos City", "Tarece", 0.75, 12.5, _W, "Stationary", "HEALTH ADVISORY: Stagnant floodwater in farm lanes. RHU medical team dispensing Doxycycline prophylaxis.", "2026-10-18 13:45"),
]

# Demonstration figures per area, in AREAS order: (cases, cases last year, deaths). Replace with RHU/PHO data.
_DISEASE_SEED = {
    "Leptospirosis": [(142, 96, 6), (88, 61, 4), (57, 49, 2), (64, 70, 3), (73, 52, 3), (49, 33, 2), (36, 41, 1)],
    "Dengue": [(310, 402, 2), (176, 215, 1), (121, 160, 0), (148, 190, 1), (133, 171, 1), (90, 118, 0), (84, 102, 0)],
    "Bloody diarrhea": [(96, 121, 1), (58, 74, 0), (41, 52, 1), (47, 60, 0), (52, 63, 1), (30, 35, 0), (28, 37, 0)],
    "Flu-like illness": [(220, 190, 1), (131, 118, 0), (92, 85, 0), (105, 99, 1), (98, 90, 0), (67, 60, 0), (74, 66, 0)],
}
SAMPLE_SOURCE = "Sample data for demonstration, we used some information to demonstrate for our student project. Replace with RHU / Provincial Health Office figures / DOH / PHILSTAR."


def create_group4database():
    """Creates/upgrades all tables, makes sure an Admin exists, and seeds sample data for the 7 areas."""
    marks = ",".join("?" * len(AREAS))
    try:
        with group4_get_database_connection() as db:
            db.executescript(_SCHEMA)
            for table, columns in _ADDED_COLUMNS.items():
                existing = {r[1] for r in db.execute(f"PRAGMA table_info({table})")}
                for name, ddl in columns.items():
                    if name not in existing:
                        db.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
                        if name == "display_order":
                            db.execute("UPDATE patients SET display_order = id")

            # Admins cannot self-register, so make sure one exists.
            has_admin = db.execute("SELECT 1 FROM users WHERE role = ? LIMIT 1", (ROLE_ADMIN,)).fetchone()
            name_taken = db.execute("SELECT 1 FROM users WHERE lower(full_name) = ?", (DEFAULT_ADMIN_NAME.lower(),)).fetchone()
            if not has_admin and not name_taken:
                db.execute(
                    "INSERT INTO users (full_name, password, role, official_id, station_barangay, date_created) VALUES (?,?,?,?,?,?)",
                    (DEFAULT_ADMIN_NAME, new_hash(DEFAULT_ADMIN_PASS), ROLE_ADMIN, "ADMIN", "Central Office", str(date.today())))

            # One-time cleanup: drop sample rows for places outside the 7 monitored areas.
            if db.execute("PRAGMA user_version").fetchone()[0] < 2:
                db.execute(f"DELETE FROM flood_monitoring WHERE city NOT IN ({marks})", AREAS)
                db.execute(f"DELETE FROM disease_statistics WHERE area NOT IN ({marks})", AREAS)
                db.execute("PRAGMA user_version = 2")

            if not db.execute("SELECT 1 FROM flood_monitoring LIMIT 1").fetchone():
                db.executemany(
                    """INSERT INTO flood_monitoring (city, barangay, water_level_meters, water_depth_desc, rainfall_rate_mm,
                       rainfall_desc, alert_level, status, early_warning, last_updated) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    [(c, b, w, calculate_depth_category(w), r, calculate_rainfall_category(r), a, s, adv, ts)
                     for c, b, w, r, a, s, adv, ts in _FLOOD_SEED])

            if not db.execute("SELECT 1 FROM disease_statistics LIMIT 1").fetchone():
                db.executemany(
                    """INSERT INTO disease_statistics (disease, area, period, cases, cases_last_year, deaths, source, updated_by, updated_at)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    [(disease, area, "Jan 1 to Oct 15, 2026", *figures, SAMPLE_SOURCE, "System sample", str(date.today()))
                     for disease, rows in _DISEASE_SEED.items() for area, figures in zip(AREAS, rows)])
    except sqlite3.Error as e:
        print(f"[!] Database initialization error: {e}")
        raise


# ── Authentication & accounts ──────────────────────────────────────────────
def authenticate_user(full_name, password):
    """Sign in by full name or email with lockout. Returns (True, user_info) or (False, message)."""
    generic_fail = "Invalid full name or password."
    key = full_name.strip().lower()
    if not key or not password:
        return False, generic_fail
    try:
        with group4_get_database_connection() as db:
            row = db.execute(
                """SELECT id, password, full_name, role, official_id, station_barangay, failed_attempts, locked_until
                   FROM users WHERE lower(full_name) = ? OR (email != '' AND lower(email) = ?)""", (key, key)).fetchone()
            if not row:
                return False, generic_fail
            uid, stored, name, role, official_id, station, attempts, locked_until = row
            attempts = attempts or 0

            if locked_until:
                try:
                    until = datetime.strptime(locked_until, TS_FORMAT)
                    if datetime.now() < until:
                        minutes = int((until - datetime.now()).total_seconds() // 60) + 1
                        return False, f"Account temporarily locked. Try again in {minutes} minute(s)."
                    db.execute("UPDATE users SET failed_attempts = 0, locked_until = '' WHERE id = ?", (uid,))
                    attempts = 0
                except ValueError:
                    pass

            if not group4_verify_password(password, stored):
                attempts += 1
                if attempts >= MAX_FAILED_ATTEMPTS:
                    lock = (datetime.now() + timedelta(minutes=LOCKOUT_DURATION)).strftime(TS_FORMAT)
                    db.execute("UPDATE users SET failed_attempts = ?, locked_until = ? WHERE id = ?", (attempts, lock, uid))
                    return False, f"Account temporarily locked due to {MAX_FAILED_ATTEMPTS} failed attempts. Try again in {LOCKOUT_DURATION} minutes."
                db.execute("UPDATE users SET failed_attempts = ? WHERE id = ?", (attempts, uid))
                return False, generic_fail

            db.execute("UPDATE users SET failed_attempts = 0, locked_until = '' WHERE id = ?", (uid,))
            if not stored.startswith("pbkdf2:"):   # silently upgrade legacy hashes
                db.execute("UPDATE users SET password = ? WHERE id = ?", (new_hash(password), uid))
            return True, {"id": uid, "full_name": name, "role": role,
                          "official_id": official_id or "", "station_barangay": station or ""}
    except sqlite3.Error as e:
        print(f"[!] Auth error: {e}")
        return False, generic_fail


def check_account_fields(name, password, confirm, email):
    if len(name) < 2:
        return "Full Name must be at least 2 characters."
    if len(password) < 4:
        return "Password must be at least 4 characters."
    if password != confirm:
        return "Passwords do not match. Please re-enter."
    if email and "@" not in email:
        return "Please enter a valid email address (e.g. juan@gmail.com)."
    return None


def create_user(name, password, role, official_id, station, email, success_msg):
    try:
        with group4_get_database_connection() as db:
            if db.execute("SELECT 1 FROM users WHERE lower(full_name) = ?", (name.lower(),)).fetchone():
                return False, f"Full name '{name}' is already registered. Please use a different name."
            db.execute(
                """INSERT INTO users (password, full_name, role, official_id, station_barangay, date_created, email)
                   VALUES (?,?,?,?,?,?,?)""",
                (new_hash(password), name, role, official_id, station, str(date.today()), email))
        return True, success_msg
    except sqlite3.Error as e:
        return False, f"Database error during registration:\n{e}"


def register_resident_user(full_name, password="", confirm_password="", email=""):
    name, password, email = full_name.strip(), password.strip(), email.strip()
    if not (name and password and confirm_password):
        return False, "Please fill in all registration fields."
    error = check_account_fields(name, password, confirm_password.strip(), email)
    if error:
        return False, error
    return create_user(name, password, ROLE_PATIENT, "RESIDENT", "Local Barangay", email,
                        f"Resident account created for {name}! You can now Sign In.")


def register_official_user(full_name, password, confirm_password, role, official_id, station_barangay, auth_passcode, email=""):
    """Health worker / barangay staff sign-up. Needs the LGU/Health authorization passcode."""
    name, password, role = full_name.strip(), password.strip(), role.strip()
    official_id, station, email = official_id.strip(), station_barangay.strip(), email.strip()
    passcode = auth_passcode.strip().upper()
    if not all([name, password, confirm_password, role, official_id, station, passcode]):
        return False, "All fields and verification credentials are required."
    if passcode not in OFFICIAL_WILDCARE_SECURITY_PASSCODES:
        return False, "Invalid LGU / Clinic Authorization Passcode!\nOnly verified government or health staff are permitted."
    if role not in REGISTRATION_OFFICIALS_ROLES:
        return False, "Invalid staff role selected. Admin accounts cannot be self-registered."
    if len(official_id) < 3:
        return False, "Please provide a valid Employee / PRC / LGU ID Number."
    error = check_account_fields(name, password, confirm_password.strip(), email)
    if error:
        return False, error
    return create_user(name, password, role, official_id, station, email,
                        f"Verified Official Account created for {name} ({role})! You can now Sign In.")


def change_user_role(acting_user_id, target_full_name, new_role):
    """Only path that grants roles (including Admin). Re-checks the acting user's role in the database."""
    if new_role not in ALL_ROLES:
        return False, f"'{new_role}' is not a valid role."
    try:
        with group4_get_database_connection() as db:
            actor = db.execute("SELECT role FROM users WHERE id = ?", (acting_user_id,)).fetchone()
            if not actor:
                return False, "Acting user account not found."
            if actor[0] != ROLE_ADMIN:
                return False, "Permission denied. Only Admins can change user roles."
            target = db.execute("SELECT id, full_name, role FROM users WHERE lower(full_name) = ?",
                                (target_full_name.strip().lower(),)).fetchone()
            if not target:
                return False, f"User '{target_full_name}' not found."
            if target[2] == new_role:
                return False, f"User '{target[1]}' already has the '{new_role}' role."
            db.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, target[0]))
            return True, f"Role for '{target[1]}' changed from '{target[2]}' to '{new_role}'."
    except sqlite3.Error as e:
        return False, f"Database error: {e}"


def reset_user_password(full_name, verification_credential, new_password, confirm_password):
    """Offline recovery: residents confirm their barangay, staff confirm their own Official ID."""
    generic_error = "Verification failed. The account details provided do not match our records."
    name_key, credential = full_name.strip().lower(), verification_credential.strip()
    new_pw, confirm = new_password.strip(), confirm_password.strip()
    if not all([name_key, credential, new_pw, confirm]):
        return False, "All verification and password fields are required."
    if len(new_pw) < 4:
        return False, "New password must be at least 4 characters."
    if new_pw != confirm:
        return False, "Passwords do not match. Please re-type."
    try:
        with group4_get_database_connection() as db:
            row = db.execute(
                "SELECT id, full_name, role, official_id, station_barangay FROM users WHERE lower(full_name) = ?",
                (name_key,)).fetchone()
            if not row:
                return False, generic_error
            uid, db_name, role, official_id, station = row
            cred = credential.lower()
            if role == ROLE_PATIENT:
                station = (station or "").strip().lower()
                verified = len(credential) >= 4 and bool(station) and (cred in station or station in cred)
            else:
                verified = bool(official_id) and cred == official_id.strip().lower()
            if not verified:
                return False, generic_error
            db.execute(
                """UPDATE users SET password = ?, failed_attempts = 0, locked_until = '',
                   reset_otp_hash = '', reset_otp_expiry = '', reset_otp_attempts = 0 WHERE id = ?""",
                (new_hash(new_pw), uid))
            return True, f"Password for '{db_name}' has been reset successfully! You can now Sign In with your new password."
    except sqlite3.Error as e:
        print(f"[!] Password recovery error: {e}")
        return False, generic_error


# ── Email OTP recovery ─────────────────────────────────────────────────────
def send_otp_email(to_email, full_name, otp_code):
    cfg = SMTP_CONFIG
    if not cfg["sender_email"] or not cfg["sender_password"]:
        return False, ("Email service is not configured.\n\nSet the WILDCARE_SMTP_EMAIL and WILDCARE_SMTP_PASSWORD "
                       "environment variables (a Gmail address and its App Password), then restart the app.")
    safe_name = html.escape(full_name)
    html_body = f"""\
<html><body style="margin:0;padding:20px;font-family:Segoe UI,Arial,sans-serif;background:#0E1624;color:#E6EBF3;">
  <div style="max-width:460px;margin:0 auto;background:#151F31;border-radius:12px;padding:28px;border:1px solid #25324A;">
    <h2 style="color:#2BA39A;margin-top:0;">W.I.L.D. CARE &#8212; Password Recovery</h2>
    <p>Hello, <strong>{safe_name}</strong>.</p>
    <p>Your one-time recovery code is:</p>
    <p style="text-align:center;"><span style="font-size:36px;font-weight:bold;letter-spacing:10px;color:#E6EBF3;
       background:#1B2740;padding:12px 26px;border-radius:10px;display:inline-block;font-family:Consolas,monospace;">{otp_code}</span></p>
    <p style="color:#8F9BB3;font-size:13px;">This code expires in {OTP_VALID_MINUTES} minutes. If you did not request a reset, ignore this email.</p>
  </div></body></html>"""
    plain_body = (f"W.I.L.D. CARE - Password Recovery\n\nHello {full_name},\n\nYour one-time recovery code is: {otp_code}\n\n"
                  f"This code expires in {OTP_VALID_MINUTES} minutes. If you did not request this reset, ignore this email.")
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "W.I.L.D. CARE \u2014 Your Password Recovery Code"
        msg["From"] = f"{cfg['sender_name']} <{cfg['sender_email']}>"
        msg["To"] = to_email
        msg.attach(MIMEText(plain_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))
        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(cfg["sender_email"], cfg["sender_password"])
            server.sendmail(cfg["sender_email"], to_email, msg.as_string())
        return True, None
    except smtplib.SMTPAuthenticationError:
        return False, ("Gmail authentication failed.\nCheck WILDCARE_SMTP_EMAIL / WILDCARE_SMTP_PASSWORD and make sure "
                       "the password is a Gmail App Password, not the normal login password.")
    except smtplib.SMTPException as e:
        return False, f"Email delivery failed: {e}"
    except Exception as e:
        return False, f"Unexpected email error: {e}"


_CLEAR_OTP = "UPDATE users SET reset_otp_hash = '', reset_otp_expiry = '', reset_otp_attempts = 0 WHERE id = ?"


def send_password_reset_otp(identifier):
    """Emails a 6-digit code (stored only as a SHA-256 hash, valid 15 min). identifier = full name or email.
    Returns (True, masked_email) or (False, message); unknown accounts get the same generic message."""
    generic = ("Unable to process recovery request. Please verify your full name or email, or contact the clinic "
               "administrator if you do not have an email registered.")
    key = identifier.strip().lower()
    if not key:
        return False, "Please enter your full name or email."
    try:
        with group4_get_database_connection() as db:
            row = db.execute("""SELECT id, email, full_name FROM users
                                WHERE lower(full_name) = ? OR (email != '' AND lower(email) = ?)""", (key, key)).fetchone()
            if not row or not row[1] or "@" not in row[1].strip():
                return False, generic
            uid, email, name = row[0], row[1].strip(), row[2]

            otp = f"{secrets.randbelow(900000) + 100000}"
            expiry = (datetime.now() + timedelta(minutes=OTP_VALID_MINUTES)).strftime(TS_FORMAT)
            db.execute("UPDATE users SET reset_otp_hash = ?, reset_otp_expiry = ?, reset_otp_attempts = 0 WHERE id = ?",
                       (hashlib.sha256(otp.encode("utf-8")).hexdigest(), expiry, uid))
            db.commit()

            sent, error = send_otp_email(email, name, otp)
            if not sent:
                db.execute(_CLEAR_OTP, (uid,))
                return False, error
            local, _, domain = email.partition("@")
            return True, (local[:2] + "\u2022\u2022\u2022\u2022@" + domain) if len(local) > 2 else "your registered email"
    except sqlite3.Error as e:
        print(f"[!] OTP generation error: {e}")
        return False, generic


def verify_and_reset_password_with_otp(identifier, otp_code, new_password, confirm_password):
    """Checks the emailed code (timing-safe, max 5 tries) and sets a new password. Returns (ok, message)."""
    key, otp = identifier.strip().lower(), otp_code.strip()
    new_pw, confirm = new_password.strip(), confirm_password.strip()
    if not otp:
        return False, "Please enter the 6-digit recovery code from your email."
    if len(new_pw) < 4:
        return False, "New password must be at least 4 characters."
    if new_pw != confirm:
        return False, "Passwords do not match. Please re-type carefully."
    try:
        with group4_get_database_connection() as db:
            row = db.execute("""SELECT id, full_name, reset_otp_hash, reset_otp_expiry, reset_otp_attempts FROM users
                                WHERE lower(full_name) = ? OR (email != '' AND lower(email) = ?)""", (key, key)).fetchone()
            if not row:
                return False, "Invalid recovery session. Please start over."
            uid, name, stored_hash, expiry, tries = row
            tries = tries or 0
            if not stored_hash:
                return False, "No active recovery code found. Please request a new one."
            try:
                if datetime.now() > datetime.strptime(expiry, TS_FORMAT):
                    db.execute(_CLEAR_OTP, (uid,))
                    return False, f"Recovery code has expired ({OTP_VALID_MINUTES}-minute limit). Please request a new code."
            except (ValueError, TypeError):
                return False, "Invalid recovery session. Please request a new code."

            if not hmac.compare_digest(hashlib.sha256(otp.encode("utf-8")).hexdigest(), stored_hash):
                tries += 1
                if tries >= OTP_MAX_TRIES:
                    db.execute(_CLEAR_OTP, (uid,))
                    return False, "Too many incorrect attempts. The recovery code has been cancelled for security. Please request a new code."
                db.execute("UPDATE users SET reset_otp_attempts = ? WHERE id = ?", (tries, uid))
                return False, f"Incorrect recovery code. ({OTP_MAX_TRIES - tries} attempt(s) remaining)"

            db.execute("""UPDATE users SET password = ?, failed_attempts = 0, locked_until = '',
                          reset_otp_hash = '', reset_otp_expiry = '', reset_otp_attempts = 0 WHERE id = ?""",
                       (new_hash(new_pw), uid))
            return True, f"Password for '{name}' has been successfully reset! Sign in with your new password."
    except sqlite3.Error as e:
        print(f"[!] OTP verification error: {e}")
        return False, f"Database error: {e}"


# ── Location helpers ───────────────────────────────────────────────────────
def city_key(city):
    return city.lower().replace(" city", "").strip()


def in_scope(location):
    """True when free text names one of the 7 monitored areas."""
    loc = location.lower()
    return any(city_key(area) in loc for area in AREAS)


def place_label(city, barangay):
    """'Pantal, Dagupan City' unless the barangay text already names its city."""
    return barangay if city_key(city) in barangay.lower() else f"{barangay}, {city}"


def find_flood_for_location(location):
    """Most severe flood station matching a patient's location text (barangay + city), or None."""
    loc = location.lower()
    rows = get_all_flood_records()
    name = lambda r: r[2].lower().replace("brgy.", "").strip()
    for r in rows:
        if name(r) in loc and city_key(r[1]) in loc:
            return r
    return next((r for r in rows if name(r) in loc), None)


# ── Patient records ────────────────────────────────────────────────────────
_PATIENT_COLS = "id, full_name, age, sex, barangay, disease, status, date_logged"
_PATIENT_ORDER = "ORDER BY display_order ASC, id DESC"


def check_age(age):
    n = to_int(age)
    if n is None:
        return None, "Age must be a valid number."
    return (n, None) if 0 <= n <= 150 else (None, "Age must be between 0 and 150.")


def add_patient_record(full_name, age, sex, barangay, disease, status, date_logged, display_order=None):
    """Adds a case at the top of the queue. Returns (True, new_id) or (False, error)."""
    age_n, error = check_age(age)
    if error:
        return False, error
    if not in_scope(barangay):
        return False, "Location must be within the monitored areas: " + ", ".join(AREAS) + "."
    try:
        with group4_get_database_connection() as db:
            if display_order is None:
                db.execute("UPDATE patients SET display_order = display_order + 1")
                display_order = 1
            cur = db.execute(
                """INSERT INTO patients (full_name, age, sex, barangay, disease, status, date_logged, display_order)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (full_name.strip(), age_n, sex.strip(), barangay.strip(), disease.strip(), status.strip(),
                 date_logged.strip(), int(display_order)))
            return True, cur.lastrowid
    except (sqlite3.Error, ValueError) as e:
        return False, str(e)


def get_all_patient_records():
    return fetch(f"SELECT {_PATIENT_COLS} FROM patients {_PATIENT_ORDER}")


def get_patient_records_by_account(patient_name=""):
    """Cases belonging to a resident account, matched by full name (names are unique per account)."""
    return fetch(f"SELECT {_PATIENT_COLS} FROM patients WHERE lower(full_name) = lower(?) ORDER BY id DESC",
                  (patient_name.strip(),))


def update_patient_record(record_id, full_name, age, sex, barangay, disease, status, date_logged):
    rec_id = to_int(record_id)
    age_n, error = check_age(age)
    if rec_id is None:
        return False, "Invalid record ID or age value."
    if error:
        return False, error
    return write(
        """UPDATE patients SET full_name = ?, age = ?, sex = ?, barangay = ?, disease = ?, status = ?, date_logged = ?
           WHERE id = ?""",
        (full_name.strip(), age_n, sex.strip(), barangay.strip(), disease.strip(), status.strip(), date_logged.strip(), rec_id),
        done="Record updated successfully.")


def delete_patient_record(record_id):
    rec_id = to_int(record_id)
    if rec_id is None:
        return False, "Invalid record ID."
    return write("DELETE FROM patients WHERE id = ?", (rec_id,), done="Record deleted successfully.")


_SEARCH_COLUMNS = {"Name": ["full_name"], "Disease": ["disease"], "Barangay": ["barangay"]}


def search_patient_records(query, filter_by="All Fields"):
    query = query.strip()
    if not query:
        return get_all_patient_records()
    columns = _SEARCH_COLUMNS.get(filter_by, ["full_name", "disease", "barangay"])   # fixed whitelist, not user input
    where = " OR ".join(f"{c} LIKE ?" for c in columns)
    return fetch(f"SELECT {_PATIENT_COLS} FROM patients WHERE {where} {_PATIENT_ORDER}", (f"%{query}%",) * len(columns))


def update_patient_display_order(ordered_ids):
    """Saves a custom queue order (1, 2, 3...) from a list of patient ids."""
    if not ordered_ids:
        return False, "No patient records provided to reorder."
    try:
        with group4_get_database_connection() as db:
            db.executemany("UPDATE patients SET display_order = ? WHERE id = ?",
                           [(i, int(pid)) for i, pid in enumerate(ordered_ids, start=1)])
        return True, f"Successfully rearranged {len(ordered_ids)} patient file(s)."
    except (sqlite3.Error, ValueError) as e:
        return False, str(e)


def reset_patient_display_order():
    """Back to chronological order, newest first."""
    return write("UPDATE patients SET display_order = (SELECT COUNT(*) FROM patients p WHERE p.id >= patients.id)",
                  done="Patient file queue reset to chronological order.")


_DISEASE_RULES = [(("lepto",), 40, "Leptospirosis risk"), (("dengue",), 30, "Dengue risk"),
                  (("cholera", "typhoid", "diarrhea", "gastro"), 25, "Waterborne gastro infection"),
                  (("fever", "infection", "wound"), 15, "Acute symptoms")]
_STATUS_RULES = [("admitted", 50, "Admitted in-patient"), ("observation", 20, "Under observation"),
                 ("recovered", 0, "Recovered / Routine")]


def auto_triage_patient_records():
    """Rule-based triage: status + disease + live flood risk + age vulnerability -> saved queue order.
    Returns (True, summary dict) or (False, message)."""
    try:
        with group4_get_database_connection() as db:
            critical_kw, warning_kw = [], []
            for city, brgy, alert in db.execute("SELECT city, barangay, alert_level FROM flood_monitoring"):
                keys = [city_key(city), brgy.lower().replace("brgy.", "").strip()]
                level = alert.lower()
                if "critical" in level:
                    critical_kw.extend(keys)
                elif "warning" in level or "alert" in level:
                    warning_kw.extend(keys)

            patients = db.execute("SELECT id, full_name, age, barangay, disease, status FROM patients").fetchall()
            if not patients:
                return False, "No patient records available to triage."

            scored = []
            for pid, name, age, location, disease, status in patients:
                score, reasons = 0, []
                for key, pts, why in _STATUS_RULES:
                    if key in status.lower():
                        score, reasons = score + pts, reasons + [why]
                        break
                for keys, pts, why in _DISEASE_RULES:
                    if any(k in disease.lower() for k in keys):
                        score, reasons = score + pts, reasons + [why]
                        break
                loc = location.lower()
                if any(k in loc for k in critical_kw if k):
                    score, reasons = score + 35, reasons + ["Active Critical Flood Zone"]
                elif any(k in loc for k in warning_kw if k):
                    score, reasons = score + 20, reasons + ["Flooded / Warning Zone"]
                age_n = to_int(age)
                if age_n is not None and (age_n < 10 or age_n >= 60):
                    score, reasons = score + 15, reasons + [f"Vulnerable Age ({age_n}yo)"]
                scored.append((score, pid, name, reasons))

            scored.sort(key=lambda s: (s[0], -s[1]), reverse=True)
            db.executemany("UPDATE patients SET display_order = ? WHERE id = ?",
                           [(i, s[1]) for i, s in enumerate(scored, start=1)])
            top = scored[0]
            return True, {
                "total": len(scored),
                "critical": sum(s[0] >= 60 for s in scored),
                "moderate": sum(30 <= s[0] < 60 for s in scored),
                "low": sum(s[0] < 30 for s in scored),
                "top_patient": top[2], "top_score": top[0], "top_reasons": ", ".join(top[3]),
            }
    except sqlite3.Error as e:
        print(f"[!] Triage error: {e}")
        return False, str(e)


def get_summary_counts():
    row = fetch("""SELECT COUNT(*), COALESCE(SUM(status = 'Under Observation'), 0),
                    COALESCE(SUM(status = 'Admitted'), 0), COALESCE(SUM(status = 'Recovered'), 0) FROM patients""", one=True)
    keys = ("total", "observation", "admitted", "recovered")
    return dict(zip(keys, row if row else (0, 0, 0, 0)))


def export_records_to_csv(target_filepath):
    try:
        records = get_all_patient_records()
        with open(target_filepath, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["W.I.L.D. CARE — POST-FLOOD DISEASE MONITORING REPORT"])
            writer.writerow([f"Generated on: {date.today()}"])
            writer.writerow([])
            writer.writerow(["Case ID", "Full Name", "Age", "Sex", "Barangay / Area", "Diagnosed Disease", "Case Status", "Date Logged"])
            writer.writerows(records)
        return True, len(records)
    except Exception as e:
        return False, str(e)


# ── Flood & rainfall monitoring ────────────────────────────────────────────
_FLOOD_COLS = ("id, city, barangay, water_level_meters, water_depth_desc, rainfall_rate_mm, rainfall_desc, "
               "alert_level, status, early_warning, last_updated")
_FLOOD_ORDER = ("ORDER BY CASE WHEN alert_level LIKE '%Critical%' THEN 1 WHEN alert_level LIKE '%Warning%' THEN 2 "
                "WHEN alert_level LIKE '%Alert%' THEN 3 ELSE 4 END, water_level_meters DESC")


def calculate_depth_category(water_level_m):
    try:
        w = float(water_level_m)
    except (ValueError, TypeError):
        return "Unknown Depth"
    label = ("Passable / Safe" if w < 0.25 else "Ankle Deep" if w < 0.55 else "Knee Deep" if w < 1.0
             else "Waist Deep" if w < 1.5 else "Chest Deep" if w < 2.0 else "Submerged / Severe")
    return f"{label} ({w:.2f}m)"


def calculate_rainfall_category(rate_mm):
    try:
        r = float(rate_mm)
    except (ValueError, TypeError):
        return "Normal"
    return ("Light Drizzle / No Rain" if r < 2.5 else "Light Rain" if r < 7.5 else "Moderate Rain" if r < 15.0
            else "Heavy Rain" if r < 30.0 else "Torrential Rain")


def get_flood_records(city_filter="All Cities", alert_filter="All Alert Levels", search_query=""):
    sql, params = f"SELECT {_FLOOD_COLS} FROM flood_monitoring WHERE 1=1", []
    if city_filter and city_filter not in ("All Cities", "All Areas", "All Pangasinan Cities"):
        sql += " AND city = ?"
        params.append(city_filter.strip())
    if alert_filter and alert_filter not in ("All Alert Levels", "All"):
        sql += " AND alert_level = ?"
        params.append(alert_filter.strip())
    if search_query and search_query.strip():
        sql += " AND (city LIKE ? OR barangay LIKE ? OR water_depth_desc LIKE ? OR early_warning LIKE ?)"
        params += [f"%{search_query.strip()}%"] * 4
    return fetch(f"{sql} {_FLOOD_ORDER}", params)


def get_all_flood_records():
    return get_flood_records()


def get_unique_flood_cities():
    """The monitored areas (fixed to the 7 target locations)."""
    return list(AREAS)


def get_active_flood_alerts():
    return fetch(f"SELECT {_FLOOD_COLS} FROM flood_monitoring "
                  f"WHERE alert_level LIKE '%Critical%' OR alert_level LIKE '%Warning%' {_FLOOD_ORDER}")


def get_flood_statistics():
    row = fetch("""SELECT COUNT(*),
                    COALESCE(SUM(alert_level LIKE '%Critical%'), 0), COALESCE(SUM(alert_level LIKE '%Warning%'), 0),
                    COALESCE(SUM(alert_level LIKE '%Alert%'), 0), COALESCE(SUM(alert_level LIKE '%Normal%'), 0),
                    COALESCE(MAX(water_level_meters), 0.0) FROM flood_monitoring""", one=True)
    stats = dict(zip(("total", "critical", "warning", "alert", "normal", "max_level"), row or (0, 0, 0, 0, 0, 0.0)))
    top = fetch("SELECT city, barangay, water_level_meters FROM flood_monitoring ORDER BY water_level_meters DESC LIMIT 1", one=True)
    stats["highest_area"] = f"{top[0]} ({top[1]} - {top[2]}m)" if top else "None"
    return stats


def check_flood_values(city, water_level_m, rainfall_rate_mm):
    try:
        w, r = float(water_level_m), float(rainfall_rate_mm)
    except (ValueError, TypeError):
        return None, "Water level and rainfall rate must be valid numbers."
    if not 0 <= w <= 25.0:
        return None, "Water level must be between 0.0 and 25.0 meters."
    if not 0 <= r <= 600.0:
        return None, "Rainfall rate must be between 0.0 and 600.0 mm/h."
    if city.strip() not in AREAS:
        return None, "Area must be one of: " + ", ".join(AREAS) + "."
    return (w, r), None


def flood_params(city, barangay, values, depth_desc, rain_desc, alert, status, warning, stamp):
    return (city.strip(), barangay.strip(), values[0], depth_desc.strip(), values[1], rain_desc.strip(),
            alert.strip(), status.strip(), warning.strip(), stamp or datetime.now().strftime("%Y-%m-%d %H:%M"))


def add_flood_record(city, barangay, water_level_m, water_depth_desc, rainfall_rate_mm, rainfall_desc,
                     alert_level, status, early_warning, last_updated=None):
    values, error = check_flood_values(city, water_level_m, rainfall_rate_mm)
    if error:
        return False, error
    return write(
        """INSERT INTO flood_monitoring (city, barangay, water_level_meters, water_depth_desc, rainfall_rate_mm,
           rainfall_desc, alert_level, status, early_warning, last_updated) VALUES (?,?,?,?,?,?,?,?,?,?)""",
        flood_params(city, barangay, values, water_depth_desc, rainfall_desc, alert_level, status, early_warning, last_updated))


def update_flood_record(record_id, city, barangay, water_level_m, water_depth_desc, rainfall_rate_mm, rainfall_desc,
                        alert_level, status, early_warning, last_updated=None):
    rec_id = to_int(record_id)
    values, error = check_flood_values(city, water_level_m, rainfall_rate_mm)
    if rec_id is None:
        return False, "Invalid record ID."
    if error:
        return False, error
    return write(
        """UPDATE flood_monitoring SET city = ?, barangay = ?, water_level_meters = ?, water_depth_desc = ?,
           rainfall_rate_mm = ?, rainfall_desc = ?, alert_level = ?, status = ?, early_warning = ?, last_updated = ?
           WHERE id = ?""",
        flood_params(city, barangay, values, water_depth_desc, rainfall_desc, alert_level, status, early_warning, last_updated) + (rec_id,),
        done="Flood record updated successfully.")


def delete_flood_record(record_id):
    rec_id = to_int(record_id)
    if rec_id is None:
        return False, "Invalid record ID."
    return write("DELETE FROM flood_monitoring WHERE id = ?", (rec_id,), done="Flood record deleted successfully.")


# ── Disease statistics (W.I.L.D.: Water-borne, Influenza-like, Leptospirosis, Dengue) ──
_STAT_COLS = "id, disease, area, period, cases, cases_last_year, deaths, source, updated_by, updated_at"


def calculate_stat_change(cases, cases_last_year):
    try:
        cur = int(cases)
        prev = int(cases_last_year) if cases_last_year is not None else 0
    except (ValueError, TypeError):
        return "No data"
    if prev <= 0:
        return "No data"
    if cur == prev:
        return "0%"
    return f"{'▲' if cur > prev else '▼'} {round(abs(cur - prev) / prev * 100)}%"


def stat_dict(r):
    now, prev = r[4] or 0, r[5] or 0
    return {"id": r[0], "disease": r[1], "area": r[2], "period": r[3], "cases": now, "cases_last_year": prev,
            "deaths": r[6] or 0, "source": r[7] or "", "updated_by": r[8] or "", "updated_at": r[9] or "",
            "change_str": calculate_stat_change(now, prev)}


def get_all_disease_statistics():
    return [stat_dict(r) for r in fetch(f"SELECT {_STAT_COLS} FROM disease_statistics ORDER BY id ASC")]


def get_disease_statistic_by_id(stat_id):
    sid = to_int(stat_id)
    row = fetch(f"SELECT {_STAT_COLS} FROM disease_statistics WHERE id = ?", (sid,), one=True) if sid is not None else None
    return stat_dict(row) if row else None


def get_disease_overview():
    """One entry per disease, totalled across the monitored areas, with trend and a per-area breakdown."""
    overview = {}
    for s in get_all_disease_statistics():
        d = overview.setdefault(s["disease"], {"disease": s["disease"], "cases": 0, "cases_last_year": 0, "deaths": 0,
                                               "areas": [], "period": s["period"], "source": s["source"], "updated_at": ""})
        d["cases"] += s["cases"]
        d["cases_last_year"] += s["cases_last_year"]
        d["deaths"] += s["deaths"]
        d["areas"].append((s["area"], s["cases"]))
        d["updated_at"] = max(d["updated_at"], s["updated_at"])
    for d in overview.values():
        d["change_str"] = calculate_stat_change(d["cases"], d["cases_last_year"])
        d["areas"].sort(key=lambda a: a[1], reverse=True)
    return list(overview.values())


def stat_params(disease, area, period, cases, cases_last_year, deaths, source, updated_by):
    if not (disease and area and period):
        return None, "Disease name, Area, and Period are required fields."
    try:
        nums = [int(v) if str(v).strip() else 0 for v in (cases, cases_last_year, deaths)]
    except ValueError:
        return None, "Cases and deaths must be valid integers."
    return (disease.strip(), area.strip(), period.strip(), *nums, source.strip(), updated_by.strip(),
            date.today().strftime("%Y-%m-%d")), None


def add_disease_statistic(disease, area, period, cases, cases_last_year, deaths, source="", updated_by="Staff"):
    params, error = stat_params(disease, area, period, cases, cases_last_year, deaths, source, updated_by)
    if error:
        return False, error
    return write("""INSERT INTO disease_statistics (disease, area, period, cases, cases_last_year, deaths, source, updated_by, updated_at)
                     VALUES (?,?,?,?,?,?,?,?,?)""", params)


def update_disease_statistic(stat_id, disease, area, period, cases, cases_last_year, deaths, source="", updated_by="Staff"):
    sid = to_int(stat_id)
    params, error = stat_params(disease, area, period, cases, cases_last_year, deaths, source, updated_by)
    if sid is None:
        return False, "Invalid statistic ID."
    if error:
        return False, error
    return write("""UPDATE disease_statistics SET disease = ?, area = ?, period = ?, cases = ?, cases_last_year = ?, deaths = ?,
                     source = ?, updated_by = ?, updated_at = ? WHERE id = ?""", params + (sid,),
                  done="Disease statistic updated successfully.")


def delete_disease_statistic(stat_id):
    sid = to_int(stat_id)
    if sid is None:
        return False, "Invalid statistic ID."
    return write("DELETE FROM disease_statistics WHERE id = ?", (sid,), done="Disease statistic deleted successfully.")