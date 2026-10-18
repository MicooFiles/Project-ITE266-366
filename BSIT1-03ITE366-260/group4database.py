import sqlite3
import hashlib
import hmac
import secrets
import os
import csv
import smtplib
import html
from datetime import date, datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart 


DATABASE_FILENAME = "group4database.db"

STATUS_OPTIONS = ["Under Observation", "Admitted", "Recovered"]

ROLE_PATIENT = "Patient/Resident"
ROLE_HEALTH_WORKER = "RHU/Hospital Health Worker"
ROLE_BRGY_STAFF = "BWH/Barangy Health Worker's"
ROLE_ADMIN = "Admin"


OFFICIALS_ROLES = [ROLE_HEALTH_WORKER, ROLE_BRGY_STAFF, ROLE_ADMIN]
ALL_ROLES = [ROLE_PATIENT, ROLE_HEALTH_WORKER, ROLE_BRGY_STAFF, ROLE_ADMIN]

REGISTRATION_OFFICIALS_ROLES = [ROLE_HEALTH_WORKER, ROLE_BRGY_STAFF]

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION = 15

# WILDCARE PASSCORE AUTHORIZATION CODES FOR HEALTH WORKERS AND BWH

wild_passcodes = os.getenv("WILDCARE_PASSCODES", "").strip()
if wild_passcodes:
    OFFICIAL_WILDCARE_SECURITY_PASSCODES = [code.strip() for code in wild_passcodes.split(",")]
else:
    OFFICIAL_WILDCARE_SECURITY_PASSCODES = ["WC_HEALTH2026", "WC_BHW2026", "WC_ADMIN2026", "WC_RESOURCE2026"]


def _env_first(*names, default=""):
    """Returns the first non-empty environment variable among *names*."""
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return default



SMPTP_CONFIGURATION = {
    "host":            os.environ.get("WILDCARE_SMTP_HOST", "smtp.gmail.com").strip() or "smtp.gmail.com",
    "port":            int(os.environ.get("WILDCARE_SMTP_PORT", 587)),
    "sender_email":    os.environ.get("WILDCARE_SMTP_EMAIL", "jaizenraimamaril@gmail.com").strip(),
    "sender_password": os.environ.get("WILDCARE_SMTP_PASSWORD", "wiaccoqhttheqoid").strip(),
    "sender_name":     "W.I.L.D. CARE Account Recovery"
}
SMTP_CONFIG = SMPTP_CONFIGURATION  # alias

# Default Admin account (created only when no Admin exists yet)
DEFAULT_ADMIN_NAME = "Admin"
DEFAULT_ADMIN_PASS = _env_first("WILDCARE_DEFAULT_ADMIN_PASS", "WILCARE_DEFAULT_ADMIN_PASS", default="wildcare#admin#2026")
PBKDF2_ITERATIONS = 100000

def group4_get_database_path():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, DATABASE_FILENAME)



class _AutoCloseConnection(sqlite3.Connection):
    """sqlite3 'with' commits/rolls back but never closes. This one also closes,
    so the .db file is not left locked between calls."""
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def group4_get_database_connection():
    connect = sqlite3.connect(group4_get_database_path(), timeout=15.0, factory=_AutoCloseConnection)
    connect.execute("PRAGMA journal_mode=WAL;")
    connect.execute("PRAGMA synchronous=NORMAL;")
    return connect


def hash_password(plain_password):
    return hashlib.sha256(plain_password.strip().encode("utf-8")).hexdigest()

def implement_generate_salt(length=32):
    return secrets.token_hex(length)

def hashlib_password_salted(plain_password, salt):
    plain = plain_password.strip().encode("utf-8")
    combowombo = salt.encode("utf-8") + plain
    digestyumyum = hashlib.sha256(combowombo).hexdigest()
    return f"{salt}:{digestyumyum}"

def hashlib_pbkdf2_password(plain_password, salt, iterations=PBKDF2_ITERATIONS):
    """
    Returns a secure PBKDF2-HMAC-SHA256 hash with 100,000 iterations.
    Format: 'pbkdf2:iterations:salt_hex:digest_hex'
    """
    plain_bytes = plain_password.strip().encode("utf-8")
    salted_bytes = bytes.fromhex(salt)
    digestdelicious = hashlib.pbkdf2_hmac("sha256", plain_bytes, salted_bytes, iterations).hex()
    return f"pbkdf2:{iterations}:{salt}:{digestdelicious}"

def group4_verify_password(plain_password, stored_hash):
    # this function password verification is compatible with both salted SHA256 and PBKDF2-HMAC-SHA256 formats
    password = plain_password.strip()
    if not stored_hash:
        return False

    if stored_hash.startswith("pbkdf2:"):
        parts = stored_hash.split(":")
        if len(parts) == 4:
            _, iter_str, salt, expected_digest = parts
            try:
                iterations = int(iter_str)
            except ValueError:
                iterations = PBKDF2_ITERATIONS
            password_bytes = password.encode("utf-8")
            salted_bytes = bytes.fromhex(salt) if (len(salt) % 2 == 0 and all(c in "0123456789abcdefABCDEF" for c in salt)) else salt.encode("utf-8")
            actual_digest = hashlib.pbkdf2_hmac("sha256", password_bytes, salted_bytes, iterations).hex()
            return hmac.compare_digest(actual_digest, expected_digest)
        return False
    elif ":" in stored_hash:
        # Legacy salted format
        salt, expected_digest = stored_hash.split(":", 1)
        combined = salt.encode("utf-8") + password.encode("utf-8")
        actual_digest = hashlib.sha256(combined).hexdigest()
        return hmac.compare_digest(actual_digest, expected_digest)
    else:
        # Legacy unsalted format
        actual = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return hmac.compare_digest(actual, stored_hash)

def create_group4database():
    
    
    try:
        with group4_get_database_connection() as connect:   
            cursor = connect.cursor()


            cursor.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name        TEXT    NOT NULL,
                    age              INTEGER NOT NULL,
                    sex              TEXT    NOT NULL,
                    barangay         TEXT    NOT NULL,
                    disease          TEXT    NOT NULL,
                    status           TEXT    NOT NULL,
                    date_logged      TEXT    NOT NULL,
                    display_order    INTEGER DEFAULT 0        
                    )    
            """)


            cursor.execute("PRAGMA table_info(patients)")
            patients_columns = [columns[1] for columns in cursor.fetchall()]
            if "display_order" not in patients_columns:
                cursor.execute("ALTER TABLE patients ADD COLUMN display_order INTEGER DEFAULT 0")
                cursor.execute("""
                UPDATE patients
                SET display_order = id
                WHERE display_order IS NULL OR display_order = 0
            """)


            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name        TEXT    NOT NULL,
                    password         TEXT    NOT NULL,
                    role             TEXT    NOT NULL,
                    official_id      TEXT    DEFAULT '',
                    station_barangay TEXT    DEFAULT '',
                    date_created     TEXT    NOT NULL

                )
            """)


            cursor.execute("PRAGMA table_info(users)")
            user_columns = [columns[1] for columns in cursor.fetchall()]
            if "official_id" not in user_columns:
                cursor.execute("ALTER TABLE users ADD COLUMN official_id TEXT DEFAULT ''")
            if "station_barangay" not in user_columns:
                cursor.execute("ALTER TABLE users ADD COLUMN station_barangay TEXT DEFAULT ''")
            if "failed_attempts" not in user_columns:
                cursor.execute("ALTER TABLE users ADD COLUMN failed_attempts INTEGER DEFAULT 0")
            if "locked_until" not in user_columns:
                cursor.execute("ALTER TABLE users ADD COLUMN locked_until TEXT DEFAULT ''")
            if "email" not in user_columns:
                cursor.execute("ALTER TABLE users ADD COLUMN email TEXT DEFAULT ''")
            if "reset_otp_hash" not in user_columns:
                cursor.execute("ALTER TABLE users ADD COLUMN reset_otp_hash TEXT DEFAULT ''")
            if "reset_otp_expiry" not in user_columns:
                cursor.execute("ALTER TABLE users ADD COLUMN reset_otp_expiry TEXT DEFAULT ''")
            if "reset_otp_attempts" not in user_columns:
                cursor.execute("ALTER TABLE users ADD COLUMN reset_otp_attempts INTEGER DEFAULT 0")
    
            # Make sure at least one Admin exists (Admins cannot self-register)
            cursor.execute("SELECT id FROM users WHERE role = ? LIMIT 1", (ROLE_ADMIN,))
            if cursor.fetchone() is None:
                cursor.execute("SELECT id FROM users WHERE lower(full_name) = ?", (DEFAULT_ADMIN_NAME.lower(),))
                if cursor.fetchone() is None:
                    admin_hash = hashlib_pbkdf2_password(DEFAULT_ADMIN_PASS, implement_generate_salt())
                    cursor.execute("""
                        INSERT INTO users (full_name, password, role, official_id, station_barangay, date_created, email)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (DEFAULT_ADMIN_NAME, admin_hash, ROLE_ADMIN, "ADMIN", "Central Office", str(date.today()), ""))
                    print("[+] Default Admin account created.")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS flood_monitoring (
                    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
                    city                    TEXT    NOT NULL,
                    barangay                TEXT    NOT NULL,
                    water_level_meters      REAL    NOT NULL,
                    water_depth_desc        TEXT    NOT NULL,
                    rainfall_rate_mm        REAL    NOT NULL,
                    rainfall_desc           TEXT    NOT NULL,
                    alert_level             TEXT    NOT NULL,
                    status                  TEXT    NOT NULL,
                    early_warning           TEXT    NOT NULL,
                    last_updated            TEXT    NOT NULL
                )
            """)
            # Seed sample Pangasinan flood monitoring data if table is newly created or empty
            cursor.execute("SELECT COUNT(*) FROM flood_monitoring")
            if cursor.fetchone()[0] == 0:
                sample_flood_data = [
                    ("Dagupan City", "Pantal, Dagupan", 0.75, "Knee Deep (0.75m)", 18.5, "Heavy Rain", "Warning (Moderate)", "Rising", "PAGASA FLOOD ADVISORY: High tide (1.2m at 14:30) compounding Pantal River runoff. Avoid barefoot wading.", "2026-10-18 14:15"),
                    ("Dagupan City", "Brgy. Lasip Chico", 1.35, "Waist Deep (1.35m)", 24.0, "Heavy Rain", "Critical (Evacuate)", "Rising", "CDRRMC EVACUATION ADVISORY: Overflow from tributary network. Impassable to light vehicles. Evacuation center open.", "2026-10-18 14:10"),
                    ("Dagupan City", "Brgy. Malued", 0.90, "Knee Deep (0.90m)", 16.0, "Heavy Rain", "Warning (Moderate)", "Stationary", "ADVISORY: Standing floodwater along interior access roads. RHU on standby for prophylaxis distribution.", "2026-10-18 14:00"),
                    ("Calasiao", "Brgy. Talibaew", 2.15, "Submerged / Severe (2.15m)", 36.5, "Torrential Rain", "Critical (Evacuate)", "Rising", "CRITICAL FLOOD WARNING: Marusay River bank breach. Immediate evacuation to Calasiao Sports Complex underway.", "2026-10-18 14:20"),
                    ("Calasiao", "Brgy. Quesban", 1.45, "Waist Deep (1.45m)", 26.0, "Heavy Rain", "Critical (Evacuate)", "Rising", "PDRRMO ALERT: Backflooding from Bued-Sinocalan basin. Zone 3 residents advised to move to elevated shelters.", "2026-10-18 14:05"),
                    ("Calasiao", "Brgy. Banaoang", 0.85, "Knee Deep (0.85m)", 14.0, "Moderate Rain", "Warning (Moderate)", "Stationary", "CAUTION: Agricultural corridors inundated; monitor tributary creeks. Leptospirosis alert active.", "2026-10-18 13:50"),
                    ("Santa Barbara", "Brgy. Minien East", 1.65, "Chest Deep (1.65m)", 32.0, "Torrential Rain", "Critical (Evacuate)", "Rising", "PAGASA-ARBFFWC BULLETIN: Sinocalan River gauge at 7.45m MASL (Critical). Rescue units mobilized.", "2026-10-18 14:25"),
                    ("Santa Barbara", "Brgy. Poblacion Norte", 0.50, "Ankle Deep (0.50m)", 9.5, "Moderate Rain", "Alert (Low)", "Receding", "ADVISORY: Drainage clearing completed near municipal hall. Road passable with caution.", "2026-10-18 13:40"),
                    ("Malasiqui", "Brgy. Poblacion", 0.40, "Ankle Deep (0.40m)", 8.0, "Moderate Rain", "Alert (Low)", "Stationary", "MONITORING: Minor street runoff on Montemayor St. Pumping station operational.", "2026-10-18 13:30"),
                    ("Malasiqui", "Brgy. Lunec", 0.95, "Knee Deep (0.95m)", 15.5, "Heavy Rain", "Warning (Moderate)", "Rising", "WARNING: Tributary canal elevated. Lowland farmers advised to secure livestock and stay off submerged paths.", "2026-10-18 14:00"),
                    ("Lingayen", "Brgy. Maniboc", 0.35, "Ankle Deep (0.35m)", 6.0, "Light Rain", "Alert (Low)", "Receding", "COASTAL WATCH: Lingayen Gulf surge monitoring normal. Water receding towards beach estuary.", "2026-10-18 13:15"),
                    ("Lingayen", "Brgy. Poblacion", 0.10, "Passable / Safe (0.10m)", 2.0, "Light Drizzle", "Normal (Safe)", "Receding", "NORMAL: Provincial Capitol complex clear. All municipal roads passable.", "2026-10-18 13:00"),
                    ("Binmaley", "Brgy. Naguilayan", 1.20, "Waist Deep (1.20m)", 22.0, "Heavy Rain", "Warning (Moderate)", "Rising", "WARNING: Fishpond overflow into residential roads. High risk of water contamination; boil drinking water.", "2026-10-18 14:10"),
                    ("Bayambang", "Brgy. Hermoza", 1.55, "Chest Deep (1.55m)", 28.5, "Heavy Rain", "Critical (Evacuate)", "Rising", "PAGASA BULLETIN: Agno River lower basin surging. Preemptive evacuation enforced in low-lying zones.", "2026-10-18 14:15"),
                    ("San Carlos City", "Brgy. Tarece", 0.75, "Knee Deep (0.75m)", 12.5, "Moderate Rain", "Warning (Moderate)", "Stationary", "HEALTH ADVISORY: Stagnant floodwater in farm lanes. RHU medical team dispensing Doxycycline prophylaxis.", "2026-10-18 13:45"),
                    ("Urdaneta City", "Brgy. Nancayasan", 0.20, "Gutter Deep (0.20m)", 5.0, "Light Rain", "Normal (Safe)", "Receding", "SAFE: McArthur Highway clear. Normal traffic flow.", "2026-10-18 13:10"),
                    ("Bugallon", "Brgy. Salasa", 0.80, "Knee Deep (0.80m)", 13.0, "Moderate Rain", "Warning (Moderate)", "Stationary", "ADVISORY: Agno tributary creek level stationary. Local disaster desk monitoring river dike.", "2026-10-18 13:35"),
                    ("Dagupan City", "Bonuan, Dagupan", 1.15, "Waist Deep (1.15m)", 34.0, "Torrential Rain", "Critical (Evacuate)", "Rising", "CRITICAL: High tide coastal wave runup plus heavy rainfall. Mandatory evacuation in coastal zone.", "2026-10-18 14:20")
                ]
                cursor.executemany("""
                    INSERT INTO flood_monitoring (city, barangay, water_level_meters, water_depth_desc, rainfall_rate_mm, rainfall_desc, alert_level, status, early_warning, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, sample_flood_data)

            # 4. Disease Statistics Table (DOH Flood-Season Illnesses: W.I.L.D.)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS disease_statistics (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    disease          TEXT    NOT NULL,
                    area             TEXT    NOT NULL,
                    period           TEXT    NOT NULL,
                    cases            INTEGER DEFAULT 0,
                    cases_last_year  INTEGER DEFAULT 0,
                    deaths           INTEGER DEFAULT 0,
                    source           TEXT    DEFAULT '',
                    updated_by       TEXT    DEFAULT '',
                    updated_at       TEXT    DEFAULT ''
                )
            """)

            cursor.execute("SELECT COUNT(*) FROM disease_statistics")
            if cursor.fetchone()[0] == 0:
                seed_stats = [
                    ("Leptospirosis", "Philippines", "Jan 1 to Oct 15, 2026", 10936, 7931, 558,
                     "DOH figures via Philstar, Daily Tribune, Manila Bulletin (Aug to Oct 2026)", "PHO Surveillance", "2026-10-15"),
                    ("Dengue", "Philippines", "Jan 1 to Oct 15, 2026", 192112, 254137, 640,
                     "DOH figures via Philstar, Daily Tribune, Manila Bulletin", "PHO Surveillance", "2026-10-15"),
                    ("Bloody diarrhea", "Philippines", "Jan 1 to Oct 15, 2026", 6456, 9520, 32,
                     "DOH figures via Philstar, Daily Tribune, Manila Bulletin (cholera 428)", "PHO Surveillance", "2026-10-15"),
                    ("Flu-like illness", "Manila City", "Jan 1 to Oct 15, 2026", 1788, 0, 12,
                     "Manila Health Department", "MHO Weekly", "2026-10-15")
                ]
                cursor.executemany("""
                    INSERT INTO disease_statistics (disease, area, period, cases, cases_last_year, deaths, source, updated_by, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, seed_stats)

            # Ensure specific flood stations matching board are present
            cursor.execute("SELECT id FROM flood_monitoring WHERE lower(barangay) LIKE '%pantal%' LIMIT 1")
            pantal_row = cursor.fetchone()
            if pantal_row:
                cursor.execute("""
                    UPDATE flood_monitoring
                    SET city = 'Dagupan City',
                        barangay = 'Pantal, Dagupan',
                        water_level_meters = 0.75,
                        water_depth_desc = 'Knee Deep (0.75m)',
                        rainfall_rate_mm = 18.5,
                        rainfall_desc = 'Heavy Rain',
                        alert_level = 'Warning (Moderate)',
                        status = 'Rising',
                        early_warning = 'PAGASA FLOOD ADVISORY: High tide (1.2m at 14:30) compounding Pantal River runoff. Avoid barefoot wading.',
                        last_updated = '2026-10-18 14:15'
                    WHERE id = ?
                """, (pantal_row[0],))
            else:
                cursor.execute("""
                    INSERT INTO flood_monitoring (city, barangay, water_level_meters, water_depth_desc, rainfall_rate_mm, rainfall_desc, alert_level, status, early_warning, last_updated)
                    VALUES ('Dagupan City', 'Pantal, Dagupan', 0.75, 'Knee Deep (0.75m)', 18.5, 'Heavy Rain', 'Warning (Moderate)', 'Rising', 'PAGASA FLOOD ADVISORY: High tide (1.2m at 14:30) compounding Pantal River runoff. Avoid barefoot wading.', '2026-10-18 14:15')
                """)

            # Ensure Poblacion, Calasiao (0.10m, Normal)
            cursor.execute("SELECT id FROM flood_monitoring WHERE lower(barangay) LIKE '%calasiao%' OR (lower(city) LIKE '%calasiao%' AND lower(barangay) LIKE '%poblacion%') LIMIT 1")
            cal_row = cursor.fetchone()
            if cal_row:
                cursor.execute("""
                    UPDATE flood_monitoring
                    SET city = 'Calasiao',
                        barangay = 'Poblacion, Calasiao',
                        water_level_meters = 0.10,
                        water_depth_desc = 'Safe / Ankle Deep (0.10m)',
                        rainfall_rate_mm = 2.0,
                        rainfall_desc = 'Light Drizzle',
                        alert_level = 'Normal (Safe)',
                        status = 'Receding',
                        early_warning = 'Safe · normal water flow.',
                        last_updated = '2026-10-18 13:00'
                    WHERE id = ?
                """, (cal_row[0],))

            # Ensure Bonuan, Dagupan (1.15m, Critical)
            cursor.execute("SELECT id FROM flood_monitoring WHERE lower(barangay) LIKE '%bonuan%' LIMIT 1")
            bon_row = cursor.fetchone()
            if bon_row:
                cursor.execute("""
                    UPDATE flood_monitoring
                    SET city = 'Dagupan City',
                        barangay = 'Bonuan, Dagupan',
                        water_level_meters = 1.15,
                        water_depth_desc = 'Waist Deep (1.15m)',
                        rainfall_rate_mm = 34.0,
                        rainfall_desc = 'Torrential Rain',
                        alert_level = 'Critical (Evacuate)',
                        status = 'Rising',
                        early_warning = 'CRITICAL: High tide coastal wave runup plus heavy rainfall. Mandatory evacuation in coastal zone.',
                        last_updated = '2026-10-18 14:20'
                    WHERE id = ?
                """, (bon_row[0],))
            else:
                cursor.execute("""
                    INSERT INTO flood_monitoring (city, barangay, water_level_meters, water_depth_desc, rainfall_rate_mm, rainfall_desc, alert_level, status, early_warning, last_updated)
                    VALUES ('Dagupan City', 'Bonuan, Dagupan', 1.15, 'Waist Deep (1.15m)', 34.0, 'Torrential Rain', 'Critical (Evacuate)', 'Rising', 'CRITICAL: High tide coastal wave runup plus heavy rainfall. Mandatory evacuation in coastal zone.', '2026-10-18 14:20')
                """)

            # Ensure Poblacion, Urdaneta (0.25m, Alert)
            cursor.execute("SELECT id FROM flood_monitoring WHERE lower(barangay) LIKE '%urdaneta%' OR (lower(city) LIKE '%urdaneta%' AND lower(barangay) LIKE '%nancayasan%') LIMIT 1")
            urd_row = cursor.fetchone()
            if urd_row:
                cursor.execute("""
                    UPDATE flood_monitoring
                    SET city = 'Urdaneta City',
                        barangay = 'Poblacion, Urdaneta',
                        water_level_meters = 0.25,
                        water_depth_desc = 'Ankle Deep (0.25m)',
                        rainfall_rate_mm = 7.0,
                        rainfall_desc = 'Light Rain',
                        alert_level = 'Alert (Low)',
                        status = 'Receding',
                        early_warning = 'MONITORING: MacArthur Highway clear. Commercial district drainage flowing smoothly.',
                        last_updated = '2026-10-18 13:20'
                    WHERE id = ?
                """, (urd_row[0],))

            connect.commit()
            print("[+] Group4Database initialized successfully, salamat bai.")

    except sqlite3.Error as error:
        print(f"[!] Database initialization error: {error}")
        raise error



def authenticate_user(full_name, password):
    generic_fail = "Invalid full name or password."
    norm_full_name = full_name.strip().lower()
    if not norm_full_name or not password:
        return False, generic_fail

    try:
        with group4_get_database_connection() as connection:
            cursor = connection.cursor()

            # Fetch user row by full_name, or email
            cursor.execute("""
                SELECT id, password, full_name, role, official_id, station_barangay,
                       failed_attempts, locked_until
                FROM users
                WHERE lower(full_name) = ? OR (email != '' AND lower(email) = ?)
            """, (norm_full_name, norm_full_name))

            row = cursor.fetchone()
            if not row:
                # Full name not found — return generic message (do not reveal non-existence)
                return False, generic_fail

            user_id         = row[0]
            stored_hash     = row[1]
            full_name       = row[2]
            role            = row[3]
            official_id     = row[4] if row[4] else ""
            station_brgy    = row[5] if row[5] else ""
            failed_attempts = row[6] if row[6] else 0
            locked_until    = row[7] if row[7] else ""

            # ── Check lockout ────────────────────────────────────────────
            if locked_until:
                try:
                    lock_dt = datetime.strptime(locked_until, "%Y-%m-%d %H:%M:%S")
                    if datetime.now() < lock_dt:
                        remaining = (lock_dt - datetime.now()).seconds // 60 + 1
                        return False, f"Account temporarily locked. Try again in {remaining} minute(s)."
                    else:
                        # Lock expired — reset counters
                        cursor.execute(
                            "UPDATE users SET failed_attempts = 0, locked_until = '' WHERE id = ?",
                            (user_id,)
                        )
                        connection.commit()
                        failed_attempts = 0
                except ValueError:
                    pass  # Malformed date — proceed normally

            # ── Verify password (supports both salted and legacy hashes) ─
            if not group4_verify_password(password, stored_hash):
                # Increment failed attempts
                failed_attempts += 1
                if failed_attempts >= MAX_FAILED_ATTEMPTS:
                    lock_time = (datetime.now() + timedelta(minutes=LOCKOUT_DURATION)).strftime("%Y-%m-%d %H:%M:%S")
                    cursor.execute(
                        "UPDATE users SET failed_attempts = ?, locked_until = ? WHERE id = ?",
                        (failed_attempts, lock_time, user_id)
                    )
                    connection.commit()
                    return False, f"Account temporarily locked due to {MAX_FAILED_ATTEMPTS} failed attempts. Try again in {LOCKOUT_DURATION} minutes."
                else:
                    cursor.execute(
                        "UPDATE users SET failed_attempts = ? WHERE id = ?",
                        (failed_attempts, user_id)
                    )
                    connection.commit()
                return False, generic_fail

            # ── Login success ────────────────────────────────────────────
            # Reset failed attempts on successful login
            cursor.execute(
                "UPDATE users SET failed_attempts = 0, locked_until = '' WHERE id = ?",
                (user_id,)
            )

            # Silent hash upgrade: if not modern PBKDF2-SHA256, upgrade silently
            if not stored_hash.startswith("pbkdf2:"):
                new_salt = implement_generate_salt()
                new_hash = hashlib_pbkdf2_password(password, new_salt)
                cursor.execute(
                    "UPDATE users SET password = ? WHERE id = ?",
                    (new_hash, user_id)
                )
                print(f"[+] Silently upgraded password hash to PBKDF2-SHA256 for user '{full_name}'.")

            connection.commit()

            user_info = {
                "id": user_id,
                "full_name": full_name,
                "role": role,
                "official_id": official_id,
                "station_barangay": station_brgy
            }
            return True, user_info

    except sqlite3.Error as e:
        print(f"[!] Auth error: {e}")
        return False, generic_fail


def register_resident_user(full_name, password="", confirm_password="", email=""):

    clean_name = full_name.strip()
    password   = password.strip()
    email      = email.strip()

    if not all([clean_name, password, confirm_password]):
        return False, "Please fill in all registration fields."

    if len(clean_name) < 2:
        return False, "Full Name must be at least 2 characters."

    if len(password) < 4:
        return False, "Password must be at least 4 characters."

    if password != confirm_password.strip():
        return False, "Passwords do not match. Please re-enter."

    if email and "@" not in email:
        return False, "Please enter a valid email address (e.g. juan@gmail.com)."

    try:
        with group4_get_database_connection() as connection:
            cursor = connection.cursor()

            # Case-insensitive duplicate check
            cursor.execute("SELECT id FROM users WHERE lower(full_name) = ?", (clean_name.lower(),))
            if cursor.fetchone() is not None:
                return False, f"Full name '{clean_name}' is already registered. Please use a different name."

            salt = implement_generate_salt()
            pw_hash = hashlib_pbkdf2_password(password, salt)
            cursor.execute("""
                INSERT INTO users (password, full_name, role, official_id, station_barangay, date_created, email)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (pw_hash, clean_name, ROLE_PATIENT, "RESIDENT", "Local Barangay", str(date.today()), email))
            connection.commit()

        return True, f"Resident account created for {clean_name}! You can now Sign In."

    except sqlite3.Error as e:
        return False, f"Database error during registration:\n{e}"


def register_official_user(full_name, password, confirm_password, role, official_id, station_barangay, auth_passcode, email=""):
    clean_name = full_name.strip()
    password  = password.strip()
    role      = role.strip()
    official_id = official_id.strip()
    station_barangay = station_barangay.strip()
    auth_passcode = auth_passcode.strip().upper()
    email     = email.strip()

    if not all([clean_name, password, confirm_password, role, official_id, station_barangay, auth_passcode]):
        return False, "All fields and verification credentials are required."

    # Verify Passcode
    if auth_passcode not in OFFICIAL_WILDCARE_SECURITY_PASSCODES:
        return False, "Invalid LGU / Clinic Authorization Passcode!\nOnly verified government or health staff are permitted."

    if role not in REGISTRATION_OFFICIALS_ROLES:
        return False, "Invalid staff role selected. Admin accounts cannot be self-registered."

    if len(official_id) < 3:
        return False, "Please provide a valid Employee / PRC / LGU ID Number."

    if len(clean_name) < 2:
        return False, "Full Name must be at least 2 characters."

    if len(password) < 4:
        return False, "Password must be at least 4 characters."

    if password != confirm_password.strip():
        return False, "Passwords do not match."

    if email and "@" not in email:
        return False, "Please enter a valid email address."

    try:
        with group4_get_database_connection() as connection:
            cursor = connection.cursor()

            cursor.execute("SELECT id FROM users WHERE lower(full_name) = ?", (clean_name.lower(),))
            if cursor.fetchone() is not None:
                return False, f"Full name '{clean_name}' is already registered."

            salt = implement_generate_salt()
            pw_hash = hashlib_pbkdf2_password(password, salt)
            cursor.execute("""
                INSERT INTO users (password, full_name, role, official_id, station_barangay, date_created, email)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (pw_hash, clean_name, role, official_id, station_barangay, str(date.today()), email))
            connection.commit()

        return True, f"Verified Official Account created for {clean_name} ({role})! You can now Sign In."

    except sqlite3.Error as e:
        return False, f"Database error during registration:\n{e}"


def reset_user_password(full_name, verification_credential, new_password, confirm_password):

    generic_error = "Verification failed. The account details provided do not match our records."

    norm_name = full_name.strip().lower()
    cred_clean = verification_credential.strip()
    new_pw = new_password.strip()
    conf_pw = confirm_password.strip()

    if not all([norm_name, cred_clean, new_pw, conf_pw]):
        return False, "All verification and password fields are required."

    if len(new_pw) < 4:
        return False, "New password must be at least 4 characters."

    if new_pw != conf_pw:
        return False, "Passwords do not match. Please re-type."

    try:
        with group4_get_database_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("""
                SELECT id, full_name, role, official_id, station_barangay
                FROM users
                WHERE lower(full_name) = ?
            """, (norm_name,))
            row = cursor.fetchone()

            if not row:
                return False, generic_error

            uid, db_name, db_role, db_off_id, db_station = row

            verified = False
            if db_role == ROLE_PATIENT:
                # Residents must enter their registered barangay (at least 4 characters)
                if len(cred_clean) < 4:
                    return False, generic_error
                db_station_clean = (db_station or "").strip().lower()
                cred_lower = cred_clean.lower()
                if db_station_clean and (cred_lower in db_station_clean or db_station_clean in cred_lower):
                    verified = True
            else:
                # Staff must enter their own Official/Employee ID (shared passcodes do NOT count)
                if db_off_id and cred_clean.lower() == db_off_id.strip().lower():
                    verified = True

            if not verified:
                return False, generic_error

            # Generate fresh salt and PBKDF2 hash
            new_salt = implement_generate_salt()
            new_hash = hashlib_pbkdf2_password(new_pw, new_salt)

            cursor.execute("""
                UPDATE users
                SET password = ?, failed_attempts = 0, locked_until = '',
                    reset_otp_hash = '', reset_otp_expiry = '', reset_otp_attempts = 0
                WHERE id = ?
            """, (new_hash, uid))
            connection.commit()

            return True, f"Password for '{db_name}' has been reset successfully! You can now Sign In with your new password."

    except sqlite3.Error as e:
        print(f"[!] Password recovery error: {e}")
        return False, generic_error


def _send_otp_email(to_email, full_name, otp_code):
    host            = SMPTP_CONFIGURATION.get("host", "smtp.gmail.com")
    port            = SMPTP_CONFIGURATION.get("port", 587)
    sender_email    = SMPTP_CONFIGURATION.get("sender_email", "")
    sender_password = SMPTP_CONFIGURATION.get("sender_password", "")
    sender_name     = SMPTP_CONFIGURATION.get("sender_name", "W.I.L.D. CARE")

    if not sender_email or not sender_password:
        return False, (
            "Email service is not configured.\n\n"
            "To enable email OTP recovery, set the WILDCARE_SMTP_EMAIL and\n"
            "WILDCARE_SMTP_PASSWORD environment variables (or edit the\n"
            "SMPTP_CONFIGURATION block in group4database.py) using your Gmail\n"
            "address and a Gmail App Password."
        )

    subject = "W.I.L.D. CARE \u2014 Your Password Recovery Code"
    safe_name = html.escape(full_name)

    html_body = f"""\
<html>
<body style="margin:0;padding:20px;font-family:Arial,sans-serif;background:#101626;color:#EAEAEA;">
  <div style="max-width:480px;margin:0 auto;background:#16213E;border-radius:12px;
              padding:30px;border:1px solid #1E6F5C;">
    <h2 style="color:#29BB89;margin-top:0;">&#127754; W.I.L.D. CARE &#8212; Password Recovery</h2>
    <p>Hello, <strong>{safe_name}</strong>!</p>
    <p>A password recovery request was made for your W.I.L.D. CARE account.</p>
    <p>Your one-time recovery code is:</p>
    <div style="text-align:center;margin:24px 0;">
      <span style="font-size:40px;font-weight:bold;color:#67E8F9;letter-spacing:10px;
                   background:#0F2B48;padding:14px 28px;border-radius:10px;
                   display:inline-block;font-family:monospace;">
        {otp_code}
      </span>
    </div>
    <p style="color:#94A3B8;font-size:13px;">&#9200; This code expires in <strong>15 minutes</strong>.</p>
    <p style="color:#94A3B8;font-size:13px;">
      If you did not request a password reset, you can safely ignore this email.
      Your account remains secure.
    </p>
    <hr style="border:none;border-top:1px solid #1E6F5C;margin:20px 0;">
    <p style="color:#4B5563;font-size:11px;">
      W.I.L.D. CARE &#8212; Waterborne Illness &amp; Leptospirosis Detection<br>
      Pangasinan Post-Flood Disease Surveillance System
    </p>
  </div>
</body>
</html>"""

    plain_body = (
        "W.I.L.D. CARE \u2014 Password Recovery (by Group 4)\n\n"
        f"Hello {full_name},\n\n"
        f"Your one-time recovery code is: {otp_code}\n\n"
        "This code expires in 15 minutes.\n\n"
        "If you did not request this reset, please ignore this email."
    )

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"{sender_name} <{sender_email}>"
        msg["To"]      = to_email

        msg.attach(MIMEText(plain_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body,  "html",  "utf-8"))

        with smtplib.SMTP(host, port, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, msg.as_string())

        return True, None

    except smtplib.SMTPAuthenticationError:
        return False, (
            "Gmail authentication failed.\n"
            "Check the sender email and password in SMPTP_CONFIGURATION (group4database.py).\n"
            "Ensure you are using a Gmail App Password, not your regular login password."
        )
    except smtplib.SMTPException as e:
        return False, f"Email delivery failed: {e}"
    except Exception as e:
        return False, f"Unexpected email error: {e}"


def send_password_reset_otp(identifier):
    """
    Generates a cryptographically random 6-digit OTP using secrets, stores its SHA-256 hash
    and a 15-minute expiry timestamp in the database, then sends the plain OTP
    code to the user's registered email address.
    `identifier` is the person's Full Name or registered email.
    If email delivery fails, the pending code is immediately cleared.
    Returns identical generic error when the account does not exist or has no registered email.
    Returns: (True, masked_email_string) or (False, error_message)
    """
    generic_msg = "Unable to process recovery request. Please verify your full name or email, or contact the clinic administrator if you do not have an email registered."
    norm_id = identifier.strip().lower()
    if not norm_id:
        return False, "Please enter your full name or email."

    try:
        with group4_get_database_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, email, full_name FROM users
                WHERE lower(full_name) = ? OR (email != '' AND lower(email) = ?)
            """, (norm_id, norm_id))
            row = cursor.fetchone()

            if not row:
                return False, generic_msg

            uid, email_addr, full_name = row

            if not email_addr or not email_addr.strip() or "@" not in email_addr:
                return False, generic_msg

            email_addr = email_addr.strip()

            # Generate cryptographically secure 6-digit OTP using secrets (never plain random)
            otp_code = f"{secrets.randbelow(900000) + 100000}"
            otp_hash = hashlib.sha256(otp_code.encode("utf-8")).hexdigest()
            expiry_str = (datetime.now() + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute(
                "UPDATE users SET reset_otp_hash = ?, reset_otp_expiry = ?, reset_otp_attempts = 0 WHERE id = ?",
                (otp_hash, expiry_str, uid)
            )
            conn.commit()

            # Send the OTP via SMTP
            send_ok, send_err = _send_otp_email(email_addr, full_name, otp_code)
            if not send_ok:
                # If email fails to send, clear the pending code
                cursor.execute(
                    "UPDATE users SET reset_otp_hash = '', reset_otp_expiry = '', reset_otp_attempts = 0 WHERE id = ?",
                    (uid,)
                )
                conn.commit()
                return False, send_err

            # Mask email for privacy (show only first 2 chars before @)
            parts = email_addr.split("@")
            if len(parts) == 2 and len(parts[0]) > 2:
                masked = parts[0][:2] + "\u2022\u2022\u2022\u2022@" + parts[1]
            else:
                masked = "your registered email"

            return True, masked

    except sqlite3.Error as e:
        print(f"[!] OTP generation error: {e}")
        return False, generic_msg


def verify_and_reset_password_with_otp(identifier, otp_code, new_password, confirm_password):
    """
    Verifies the 6-digit OTP against the stored SHA-256 hash using a timing-safe
    comparison. Five wrong guesses cancel the code completely.
    `identifier` is the person's Full Name or registered email.
    On success: computes fresh PBKDF2 hash, resets failed_attempts to 0,
    unlocks the account, and clears all OTP fields.
    Returns: (True, success_message) or (False, error_message)
    """
    norm_id = identifier.strip().lower()
    otp   = otp_code.strip()
    new_pw  = new_password.strip()
    conf_pw = confirm_password.strip()

    if not otp:
        return False, "Please enter the 6-digit recovery code from your email."

    if len(new_pw) < 4:
        return False, "New password must be at least 4 characters."

    if new_pw != conf_pw:
        return False, "Passwords do not match. Please re-type carefully."

    try:
        with group4_get_database_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, full_name, reset_otp_hash, reset_otp_expiry, reset_otp_attempts
                FROM users
                WHERE lower(full_name) = ? OR (email != '' AND lower(email) = ?)
            """, (norm_id, norm_id))
            row = cursor.fetchone()

            if not row:
                return False, "Invalid recovery session. Please start over."

            uid, db_name, stored_hash, expiry_str, otp_attempts = row
            otp_attempts = otp_attempts if otp_attempts else 0

            if not stored_hash:
                return False, "No active recovery code found. Please request a new one."

            # Verify expiry timestamp
            try:
                expiry_dt = datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
                if datetime.now() > expiry_dt:
                    cursor.execute(
                        "UPDATE users SET reset_otp_hash = '', reset_otp_expiry = '', reset_otp_attempts = 0 WHERE id = ?",
                        (uid,)
                    )
                    conn.commit()
                    return False, "Recovery code has expired (15-minute limit). Please request a new code."
            except (ValueError, TypeError):
                return False, "Invalid recovery session. Please request a new code."

            # Timing-safe SHA-256 OTP comparison (prevents timing attacks)
            submitted_hash = hashlib.sha256(otp.encode("utf-8")).hexdigest()
            if not hmac.compare_digest(submitted_hash, stored_hash):
                new_attempts = otp_attempts + 1
                if new_attempts >= 5:
                    cursor.execute("""
                        UPDATE users
                        SET reset_otp_hash = '', reset_otp_expiry = '', reset_otp_attempts = 0
                        WHERE id = ?
                    """, (uid,))
                    conn.commit()
                    return False, "Too many incorrect attempts. The recovery code has been cancelled for security. Please request a new code."
                else:
                    cursor.execute("""
                        UPDATE users SET reset_otp_attempts = ? WHERE id = ?
                    """, (new_attempts, uid))
                    conn.commit()
                    return False, f"Incorrect recovery code. ({5 - new_attempts} attempt(s) remaining)"

            # Hash new password with fresh salt using PBKDF2-SHA256
            new_salt = implement_generate_salt()
            new_hash = hashlib_pbkdf2_password(new_pw, new_salt)

            # Apply reset: new password, unlock account, clear OTP session
            cursor.execute("""
                UPDATE users
                SET password           = ?,
                    failed_attempts    = 0,
                    locked_until       = '',
                    reset_otp_hash     = '',
                    reset_otp_expiry   = '',
                    reset_otp_attempts = 0
                WHERE id = ?
            """, (new_hash, uid))
            conn.commit()

            return True, f"Password for '{db_name}' has been successfully reset! Sign in with your new password."

    except sqlite3.Error as e:
        print(f"[!] OTP verification error: {e}")
        return False, f"Database error: {e}"


def change_user_role(acting_user_id, target_full_name, new_role):
    if new_role not in ALL_ROLES:
        return False, f"'{new_role}' is not a valid role."

    try:
        with group4_get_database_connection() as connection:
            cursor = connection.cursor()

            # Re-verify the acting user's role from the DB (never trust in-memory)
            cursor.execute("SELECT role FROM users WHERE id = ?", (acting_user_id,))
            actor_row = cursor.fetchone()
            if not actor_row:
                return False, "Acting user account not found."
            if actor_row[0] != ROLE_ADMIN:
                return False, "Permission denied. Only Admins can change user roles."

            # Find target user
            norm_target = target_full_name.strip().lower()
            cursor.execute("SELECT id, full_name, role FROM users WHERE lower(full_name) = ?", (norm_target,))
            target_row = cursor.fetchone()
            if not target_row:
                return False, f"User '{target_full_name}' not found."

            old_role = target_row[2]
            if old_role == new_role:
                return False, f"User '{target_row[1]}' already has the '{new_role}' role."

            cursor.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, target_row[0]))
            connection.commit()

            return True, f"Role for '{target_row[1]}' changed from '{old_role}' to '{new_role}'."

    except sqlite3.Error as e:
        return False, f"Database error: {e}"



# CRUD OPERATIONS

def add_patient_record(full_name, age, sex, barangay, disease, status, date_logged, display_order=None):
    try:
        age_int = int(age)
        if age_int < 0 or age_int > 150:
            return False, "Age must be between 0 and 150."
    except (ValueError, TypeError):
        return False, "Age must be a valid number."

    try:
        with group4_get_database_connection() as connection:
            cursor = connection.cursor()
            if display_order is None:
                # Place at top of active queue (order = 1), shift other orders
                cursor.execute("UPDATE patients SET display_order = display_order + 1")
                order_val = 1
            else:
                order_val = int(display_order)

            cursor.execute("""
                INSERT INTO patients (full_name, age, sex, barangay, disease, status, date_logged, display_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (full_name.strip(), age_int, sex.strip(), barangay.strip(), disease.strip(), status.strip(), date_logged.strip(), order_val))
            connection.commit()
            return True, cursor.lastrowid
    except (sqlite3.Error, ValueError) as e:
        return False, str(e)


def get_all_patient_records():
    try:
        with group4_get_database_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("""
                SELECT id, full_name, age, sex, barangay, disease, status, date_logged
                FROM patients
                ORDER BY display_order ASC, id DESC
            """)
            return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"[!] Error fetching records: {e}")
        return []


def get_patient_records_by_account(patient_name=""):
    try:
        with group4_get_database_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("""
                SELECT id, full_name, age, sex, barangay, disease, status, date_logged
                FROM patients
                WHERE lower(full_name) = lower(?)
                ORDER BY id DESC
            """, (patient_name.strip(),))
            return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"[!] Error fetching patient records: {e}")
        return []


def update_patient_record(record_id, full_name, age, sex, barangay, disease, status, date_logged):
    try:
        rec_id = int(record_id)
        age_int = int(age)
        if age_int < 0 or age_int > 150:
            return False, "Age must be between 0 and 150."
    except (ValueError, TypeError):
        return False, "Invalid record ID or age value."

    try:
        with group4_get_database_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("""
                UPDATE patients
                SET full_name   = ?,
                    age         = ?,
                    sex         = ?,
                    barangay    = ?,
                    disease     = ?,
                    status      = ?,
                    date_logged = ?
                WHERE id = ?
            """, (full_name.strip(), age_int, sex.strip(), barangay.strip(), disease.strip(), status.strip(), date_logged.strip(), rec_id))
            connection.commit()
            return True, "Record updated successfully."
    except sqlite3.Error as e:
        return False, str(e)


def delete_patient_record(record_id):
    try:
        rec_id = int(record_id)
    except (ValueError, TypeError):
        return False, "Invalid record ID."

    try:
        with group4_get_database_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM patients WHERE id = ?", (rec_id,))
            connection.commit()
            return True, "Record deleted successfully."
    except sqlite3.Error as e:
        return False, str(e)


def search_patient_records(query, filter_by="All Fields"):
    query = query.strip()
    if not query:
        return get_all_patient_records()

    param = f"%{query}%"
    try:
        with group4_get_database_connection() as connection:
            cursor = connection.cursor()

            if filter_by == "Name":
                cursor.execute("""
                    SELECT id, full_name, age, sex, barangay, disease, status, date_logged
                    FROM patients WHERE full_name LIKE ? ORDER BY display_order ASC, id DESC
                """, (param,))
            elif filter_by == "Disease":
                cursor.execute("""
                    SELECT id, full_name, age, sex, barangay, disease, status, date_logged
                    FROM patients WHERE disease LIKE ? ORDER BY display_order ASC, id DESC
                """, (param,))
            elif filter_by == "Barangay":
                cursor.execute("""
                    SELECT id, full_name, age, sex, barangay, disease, status, date_logged
                    FROM patients WHERE barangay LIKE ? ORDER BY display_order ASC, id DESC
                """, (param,))
            else:  # All Fields
                cursor.execute("""
                    SELECT id, full_name, age, sex, barangay, disease, status, date_logged
                    FROM patients
                    WHERE full_name LIKE ? OR disease LIKE ? OR barangay LIKE ?
                    ORDER BY display_order ASC, id DESC
                """, (param, param, param))

            return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"[!] Search error: {e}")
        return []


def update_patient_display_order(ordered_ids):
    if not ordered_ids:
        return False, "No patient records provided to reorder."
    try:
        with group4_get_database_connection() as connection:
            cursor = connection.cursor()
            for idx, pid in enumerate(ordered_ids, start=1):
                cursor.execute(
                    "UPDATE patients SET display_order = ? WHERE id = ?",
                    (idx, int(pid))
                )
            connection.commit()
            return True, f"Successfully rearranged {len(ordered_ids)} patient file(s)."
    except (sqlite3.Error, ValueError) as e:
        print(f"[!] Error updating patient order: {e}")
        return False, str(e)


def reset_patient_display_order():
    try:
        with group4_get_database_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT id FROM patients ORDER BY id DESC")
            rows = cursor.fetchall()
            for idx, row in enumerate(rows, start=1):
                cursor.execute("UPDATE patients SET display_order = ? WHERE id = ?", (idx, row[0]))
            connection.commit()
            return True, "Patient file queue reset to chronological order."
    except sqlite3.Error as e:
        return False, str(e)


def auto_triage_patient_records():
    try:
        with group4_get_database_connection() as connection:
            cursor = connection.cursor()
            # Fetch active flood areas to cross-reference
            cursor.execute("SELECT city, barangay, alert_level FROM flood_monitoring")
            flood_areas = cursor.fetchall()

            critical_flood_keywords = []
            warning_flood_keywords = []
            for city, brgy, alert in flood_areas:
                alert_lower = alert.lower()
                c_clean = city.lower().replace("city", "").strip()
                b_clean = brgy.lower().replace("brgy.", "").strip()
                if "critical" in alert_lower:
                    critical_flood_keywords.extend([c_clean, b_clean])
                elif "warning" in alert_lower or "alert" in alert_lower:
                    warning_flood_keywords.extend([c_clean, b_clean])

            # Fetch all patients
            cursor.execute("SELECT id, full_name, age, sex, barangay, disease, status FROM patients")
            patients = cursor.fetchall()

            if not patients:
                return False, "No patient records available to triage."

            scored_patients = []
            for p in patients:
                pid, name, age, sex, brgy, disease, status = p
                score = 0
                reasons = []

                # 1. Clinical Status
                st_lower = status.lower()
                if "admitted" in st_lower:
                    score += 50
                    reasons.append("Admitted in-patient")
                elif "observation" in st_lower:
                    score += 20
                    reasons.append("Under observation")
                elif "recovered" in st_lower:
                    score += 0
                    reasons.append("Recovered / Routine")

                # 2. Disease Urgency
                dis_lower = disease.lower()
                if "lepto" in dis_lower:
                    score += 40
                    reasons.append("Leptospirosis risk")
                elif "dengue" in dis_lower:
                    score += 30
                    reasons.append("Dengue risk")
                elif any(d in dis_lower for d in ["cholera", "typhoid", "diarrhea", "gastro"]):
                    score += 25
                    reasons.append("Waterborne gastro infection")
                elif any(d in dis_lower for d in ["fever", "infection", "wound"]):
                    score += 15
                    reasons.append("Acute symptoms")

                # 3. Environmental Flood Risk
                brgy_lower = brgy.lower()
                matched_crit = any(kw in brgy_lower for kw in critical_flood_keywords if kw)
                matched_warn = any(kw in brgy_lower for kw in warning_flood_keywords if kw)
                if matched_crit:
                    score += 35
                    reasons.append("Active Critical Flood Zone")
                elif matched_warn:
                    score += 20
                    reasons.append("Flooded / Warning Zone")

                # 4. Age Vulnerability
                try:
                    age_val = int(age)
                    if age_val < 10 or age_val >= 60:
                        score += 15
                        reasons.append(f"Vulnerable Age ({age_val}yo)")
                except Exception:
                    pass

                scored_patients.append({
                    "id": pid,
                    "name": name,
                    "score": score,
                    "status": status,
                    "disease": disease,
                    "reasons": reasons
                })

            # Sort by score descending (highest urgency first)
            scored_patients.sort(key=lambda x: (x["score"], -x["id"]), reverse=True)

            # Update display_order in database
            for order_idx, p_data in enumerate(scored_patients, start=1):
                cursor.execute(
                    "UPDATE patients SET display_order = ? WHERE id = ?",
                    (order_idx, p_data["id"])
                )

            connection.commit()

            crit_count = sum(1 for p in scored_patients if p["score"] >= 60)
            mod_count = sum(1 for p in scored_patients if 30 <= p["score"] < 60)
            low_count = sum(1 for p in scored_patients if p["score"] < 30)
            top_p = scored_patients[0]

            summary = {
                "total": len(scored_patients),
                "critical": crit_count,
                "moderate": mod_count,
                "low": low_count,
                "top_patient": top_p["name"],
                "top_score": top_p["score"],
                "top_reasons": ", ".join(top_p["reasons"])
            }
            return True, summary

    except sqlite3.Error as e:
        print(f"[!] Triage error: {e}")
        return False, str(e)


def get_summary_counts():
    try:
        with group4_get_database_connection() as connection:
            cursor = connection.cursor()

            cursor.execute("SELECT COUNT(*) FROM patients")
            total = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM patients WHERE status = ?", ("Under Observation",))
            under_obs = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM patients WHERE status = ?", ("Admitted",))
            admitted = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM patients WHERE status = ?", ("Recovered",))
            recovered = cursor.fetchone()[0]

            return {
                "total": total,
                "observation": under_obs,
                "admitted": admitted,
                "recovered": recovered
            }
    except sqlite3.Error as e:
        print(f"[!] Summary error: {e}")
        return {"total": 0, "observation": 0, "admitted": 0, "recovered": 0}


def export_records_to_csv(target_filepath):
    try:
        records = get_all_patient_records()
        headers = ["Case ID", "Full Name", "Age", "Sex", "Barangay / Area", "Diagnosed Disease", "Case Status", "Date Logged"]

        with open(target_filepath, mode="w", newline="", encoding="utf-8-sig") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["W.I.L.D. CARE — POST-FLOOD DISEASE MONITORING REPORT"])
            writer.writerow([f"Generated on: {date.today()}"])
            writer.writerow([])
            writer.writerow(headers)
            for row in records:
                writer.writerow(row)

        return True, len(records)
    except Exception as e:
        return False, str(e)


# FLOOD WATER & RAINFALL MONITORING OPERATIONS


FLOOD_ALERT_NORMAL   = "Normal (Safe)"
FLOOD_ALERT_LOW      = "Alert (Low)"
FLOOD_ALERT_WARNING  = "Warning (Moderate)"
FLOOD_ALERT_CRITICAL = "Critical (Evacuate)"

FLOOD_ALERT_LEVELS = [
    FLOOD_ALERT_NORMAL,
    FLOOD_ALERT_LOW,
    FLOOD_ALERT_WARNING,
    FLOOD_ALERT_CRITICAL
]

FLOOD_STATUS_OPTIONS = ["Rising", "Stationary", "Receding"]


def calculate_depth_category(water_level_m):
    try:
        w = float(water_level_m)
        if w < 0.25:
            return f"Passable / Safe ({w:.2f}m)"
        elif w < 0.55:
            return f"Ankle Deep ({w:.2f}m)"
        elif w < 1.0:
            return f"Knee Deep ({w:.2f}m)"
        elif w < 1.5:
            return f"Waist Deep ({w:.2f}m)"
        elif w < 2.0:
            return f"Chest Deep ({w:.2f}m)"
        else:
            return f"Submerged / Severe ({w:.2f}m)"
    except (ValueError, TypeError):
        return "Unknown Depth"


def calculate_rainfall_category(rate_mm):
    try:
        r = float(rate_mm)
        if r < 2.5:
            return "Light Drizzle / No Rain"
        elif r < 7.5:
            return "Light Rain"
        elif r < 15.0:
            return "Moderate Rain"
        elif r < 30.0:
            return "Heavy Rain"
        else:
            return "Torrential Rain"
    except (ValueError, TypeError):
        return "Normal"


def get_all_flood_records():
    try:
        with group4_get_database_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("""
                SELECT id, city, barangay, water_level_meters, water_depth_desc,
                       rainfall_rate_mm, rainfall_desc, alert_level, status,
                       early_warning, last_updated
                FROM flood_monitoring
                ORDER BY
                    CASE
                        WHEN alert_level LIKE '%Critical%' THEN 1
                        WHEN alert_level LIKE '%Warning%' THEN 2
                        WHEN alert_level LIKE '%Alert%' THEN 3
                        ELSE 4
                    END,
                    water_level_meters DESC
            """)
            return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"[!] Error fetching flood records: {e}")
        return []


def get_flood_records(city_filter="All Cities", alert_filter="All Alert Levels", search_query=""):
    try:
        with group4_get_database_connection() as connection:
            cursor = connection.cursor()

            query = """
                SELECT id, city, barangay, water_level_meters, water_depth_desc,
                       rainfall_rate_mm, rainfall_desc, alert_level, status,
                       early_warning, last_updated
                FROM flood_monitoring
                WHERE 1=1
            """
            params = []

            if city_filter and city_filter not in ("All Cities", "All Pangasinan Cities"):
                query += " AND city = ?"
                params.append(city_filter.strip())

            if alert_filter and alert_filter not in ("All Alert Levels", "All"):
                query += " AND alert_level = ?"
                params.append(alert_filter.strip())

            if search_query and search_query.strip():
                param_str = f"%{search_query.strip()}%"
                query += " AND (city LIKE ? OR barangay LIKE ? OR water_depth_desc LIKE ? OR early_warning LIKE ?)"
                params.extend([param_str, param_str, param_str, param_str])

            query += """
                ORDER BY
                    CASE
                        WHEN alert_level LIKE '%Critical%' THEN 1
                        WHEN alert_level LIKE '%Warning%' THEN 2
                        WHEN alert_level LIKE '%Alert%' THEN 3
                        ELSE 4
                    END,
                    water_level_meters DESC
            """

            cursor.execute(query, params)
            return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"[!] Error filtering flood records: {e}")
        return []


def get_unique_flood_cities():
    try:
        with group4_get_database_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT DISTINCT city FROM flood_monitoring ORDER BY city ASC")
            cities = [row[0] for row in cursor.fetchall()]
            return cities if cities else ["Dagupan City", "Calasiao", "Lingayen", "Malasiqui", "Santa Barbara"]
    except sqlite3.Error:
        return ["Dagupan City", "Calasiao", "Lingayen", "Malasiqui", "Santa Barbara"]


def get_active_flood_alerts():
    try:
        with group4_get_database_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("""
                SELECT city, barangay, water_level_meters, water_depth_desc, alert_level, early_warning
                FROM flood_monitoring
                WHERE alert_level LIKE '%Critical%' OR alert_level LIKE '%Warning%'
                ORDER BY water_level_meters DESC
            """)
            return cursor.fetchall()
    except sqlite3.Error:
        return []


def get_flood_statistics():
    try:
        with group4_get_database_connection() as connection:
            cursor = connection.cursor()

            cursor.execute("SELECT COUNT(*) FROM flood_monitoring")
            total = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM flood_monitoring WHERE alert_level LIKE '%Critical%'")
            critical = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM flood_monitoring WHERE alert_level LIKE '%Warning%'")
            warning = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM flood_monitoring WHERE alert_level LIKE '%Alert%'")
            alert = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM flood_monitoring WHERE alert_level LIKE '%Normal%'")
            normal = cursor.fetchone()[0]

            cursor.execute("SELECT MAX(water_level_meters) FROM flood_monitoring")
            max_res = cursor.fetchone()
            max_level = max_res[0] if max_res and max_res[0] is not None else 0.0

            cursor.execute("SELECT city, barangay, water_level_meters FROM flood_monitoring ORDER BY water_level_meters DESC LIMIT 1")
            highest_area = cursor.fetchone()
            highest_area_desc = f"{highest_area[0]} ({highest_area[1]} - {highest_area[2]}m)" if highest_area else "None"

            return {
                "total": total,
                "critical": critical,
                "warning": warning,
                "alert": alert,
                "normal": normal,
                "max_level": max_level,
                "highest_area": highest_area_desc
            }
    except sqlite3.Error as e:
        print(f"[!] Error getting flood stats: {e}")
        return {"total": 0, "critical": 0, "warning": 0, "alert": 0, "normal": 0, "max_level": 0.0, "highest_area": "None"}


def add_flood_record(city, barangay, water_level_m, water_depth_desc, rainfall_rate_mm, rainfall_desc, alert_level, status, early_warning, last_updated=None):
    try:
        w_val = float(water_level_m)
        r_val = float(rainfall_rate_mm)
        if w_val < 0 or w_val > 25.0:
            return False, "Water level must be between 0.0 and 25.0 meters."
        if r_val < 0 or r_val > 600.0:
            return False, "Rainfall rate must be between 0.0 and 600.0 mm/h."
    except (ValueError, TypeError):
        return False, "Water level and rainfall rate must be valid numbers."

    if not last_updated:
        last_updated = datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        with group4_get_database_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("""
                INSERT INTO flood_monitoring (city, barangay, water_level_meters, water_depth_desc, rainfall_rate_mm, rainfall_desc, alert_level, status, early_warning, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (city.strip(), barangay.strip(), w_val, water_depth_desc.strip(), r_val, rainfall_desc.strip(), alert_level.strip(), status.strip(), early_warning.strip(), last_updated.strip()))
            connection.commit()
            return True, cursor.lastrowid
    except sqlite3.Error as e:
        return False, str(e)


def update_flood_record(record_id, city, barangay, water_level_m, water_depth_desc, rainfall_rate_mm, rainfall_desc, alert_level, status, early_warning, last_updated=None):
    try:
        rec_id = int(record_id)
        w_val = float(water_level_m)
        r_val = float(rainfall_rate_mm)
        if w_val < 0 or w_val > 25.0:
            return False, "Water level must be between 0.0 and 25.0 meters."
        if r_val < 0 or r_val > 600.0:
            return False, "Rainfall rate must be between 0.0 and 600.0 mm/h."
    except (ValueError, TypeError):
        return False, "Invalid numeric values for ID, water level, or rainfall."

    if not last_updated:
        last_updated = datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        with group4_get_database_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("""
                UPDATE flood_monitoring
                SET city = ?,
                    barangay = ?,
                    water_level_meters = ?,
                    water_depth_desc = ?,
                    rainfall_rate_mm = ?,
                    rainfall_desc = ?,
                    alert_level = ?,
                    status = ?,
                    early_warning = ?,
                    last_updated = ?
                WHERE id = ?
            """, (city.strip(), barangay.strip(), w_val, water_depth_desc.strip(), r_val, rainfall_desc.strip(), alert_level.strip(), status.strip(), early_warning.strip(), last_updated.strip(), rec_id))
            connection.commit()
            return True, "Flood record updated successfully."
    except sqlite3.Error as e:
        return False, str(e)


def delete_flood_record(record_id):
    try:
        rec_id = int(record_id)
        with group4_get_database_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM flood_monitoring WHERE id = ?", (rec_id,))
            connection.commit()
            return True, "Flood record deleted successfully."
    except Exception as e:
        return False, str(e)



# DISEASE STATISTICS 


def calculate_stat_change(cases, cases_last_year):
    try:
        cur = int(cases)
        prev = int(cases_last_year) if cases_last_year is not None else 0
        if prev <= 0:
            return "No data"
        if cur > prev:
            pct = round(((cur - prev) / prev) * 100)
            return f"▲ {pct}%"
        elif cur < prev:
            pct = round(((prev - cur) / prev) * 100)
            return f"▼ {pct}%"
        else:
            return "0%"
    except Exception:
        return "No data"


def get_all_disease_statistics():
    try:
        with group4_get_database_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("""
                SELECT id, disease, area, period, cases, cases_last_year, deaths, source, updated_by, updated_at
                FROM disease_statistics
                ORDER BY id ASC
            """)
            rows = cursor.fetchall()
            results = []
            for r in rows:
                c_now = r[4] if r[4] is not None else 0
                c_prev = r[5] if r[5] is not None else 0
                results.append({
                    "id": r[0],
                    "disease": r[1],
                    "area": r[2],
                    "period": r[3],
                    "cases": c_now,
                    "cases_last_year": c_prev,
                    "deaths": r[6] if r[6] is not None else 0,
                    "source": r[7] or "",
                    "updated_by": r[8] or "",
                    "updated_at": r[9] or "",
                    "change_str": calculate_stat_change(c_now, c_prev)
                })
            return results
    except sqlite3.Error as e:
        print(f"[!] Error fetching disease statistics: {e}")
        return []


def get_disease_statistic_by_id(stat_id):
    try:
        with group4_get_database_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("""
                SELECT id, disease, area, period, cases, cases_last_year, deaths, source, updated_by, updated_at
                FROM disease_statistics
                WHERE id = ?
            """, (int(stat_id),))
            r = cursor.fetchone()
            if not r:
                return None
            c_now = r[4] if r[4] is not None else 0
            c_prev = r[5] if r[5] is not None else 0
            return {
                "id": r[0],
                "disease": r[1],
                "area": r[2],
                "period": r[3],
                "cases": c_now,
                "cases_last_year": c_prev,
                "deaths": r[6] if r[6] is not None else 0,
                "source": r[7] or "",
                "updated_by": r[8] or "",
                "updated_at": r[9] or "",
                "change_str": calculate_stat_change(c_now, c_prev)
            }
    except Exception as e:
        print(f"[!] Error fetching stat ID {stat_id}: {e}")
        return None


def add_disease_statistic(disease, area, period, cases, cases_last_year, deaths, source="", updated_by="Staff"):
    if not disease or not area or not period:
        return False, "Disease name, Area, and Period are required fields."
    try:
        c_now = int(cases) if str(cases).strip() else 0
        c_prev = int(cases_last_year) if str(cases_last_year).strip() else 0
        d_cnt = int(deaths) if str(deaths).strip() else 0
    except ValueError:
        return False, "Cases and deaths must be valid integers."

    today_str = date.today().strftime("%Y-%m-%d")

    try:
        with group4_get_database_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("""
                INSERT INTO disease_statistics (disease, area, period, cases, cases_last_year, deaths, source, updated_by, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (disease.strip(), area.strip(), period.strip(), c_now, c_prev, d_cnt, source.strip(), updated_by.strip(), today_str))
            connection.commit()
            return True, cursor.lastrowid
    except sqlite3.Error as e:
        return False, str(e)


def update_disease_statistic(stat_id, disease, area, period, cases, cases_last_year, deaths, source="", updated_by="Staff"):
    if not disease or not area or not period:
        return False, "Disease name, Area, and Period are required."
    try:
        sid = int(stat_id)
        c_now = int(cases) if str(cases).strip() else 0
        c_prev = int(cases_last_year) if str(cases_last_year).strip() else 0
        d_cnt = int(deaths) if str(deaths).strip() else 0
    except ValueError:
        return False, "Cases and deaths must be valid numbers."

    today_str = date.today().strftime("%Y-%m-%d")

    try:
        with group4_get_database_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("""
                UPDATE disease_statistics
                SET disease = ?,
                    area = ?,
                    period = ?,
                    cases = ?,
                    cases_last_year = ?,
                    deaths = ?,
                    source = ?,
                    updated_by = ?,
                    updated_at = ?
                WHERE id = ?
            """, (disease.strip(), area.strip(), period.strip(), c_now, c_prev, d_cnt, source.strip(), updated_by.strip(), today_str, sid))
            connection.commit()
            return True, "Disease statistic updated successfully."
    except sqlite3.Error as e:
        return False, str(e)


def delete_disease_statistic(stat_id):
    try:
        sid = int(stat_id)
        with group4_get_database_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM disease_statistics WHERE id = ?", (sid,))
            connection.commit()
            return True, "Disease statistic deleted successfully."
    except Exception as e:
        return False, str(e)
