"""SQLite storage: users, login events, file events, alerts."""
import hashlib, hmac, secrets, sqlite3, threading
from datetime import datetime
import config

_lock = threading.RLock()

USERS_DDL = """CREATE TABLE {name}(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL, full_name TEXT, email TEXT, phone TEXT,
  role TEXT NOT NULL CHECK(role IN ('customer','staff','admin')),
  salt TEXT NOT NULL, password_hash TEXT NOT NULL,
  home_device TEXT, created_at TEXT, disabled INTEGER DEFAULT 0,
  notify_email INTEGER DEFAULT 1, notify_level TEXT DEFAULT 'MEDIUM')"""

SCHEMA = USERS_DDL.format(name="IF NOT EXISTS users").replace("CREATE TABLE IF NOT EXISTS users(", "CREATE TABLE IF NOT EXISTS users(") + """;
CREATE TABLE IF NOT EXISTS login_events(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, username TEXT, success INTEGER,
  hour INTEGER, device TEXT, ip TEXT, country TEXT, failed_streak INTEGER,
  new_device INTEGER, new_country INTEGER, logins_last_hour INTEGER,
  risk REAL, verdict TEXT);
CREATE TABLE IF NOT EXISTS file_events(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, username TEXT, filename TEXT,
  action TEXT, size_mb REAL, sensitivity INTEGER, hour INTEGER,
  files_last_10min INTEGER, mb_last_hour REAL, risk REAL, verdict TEXT);
CREATE TABLE IF NOT EXISTS alerts(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, source TEXT, username TEXT,
  severity TEXT, risk REAL, message TEXT, notified TEXT DEFAULT 'pending', status TEXT DEFAULT 'Open');
CREATE TABLE IF NOT EXISTS email_events(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, username TEXT NOT NULL,
  role TEXT, event_type TEXT NOT NULL, status TEXT DEFAULT 'pending', recipients TEXT DEFAULT '');
"""


def now():
    return datetime.now().isoformat(timespec="seconds")


def execute(sql, params=()):
    with _lock:
        c = sqlite3.connect(config.DB_PATH)
        try:
            cur = c.execute(sql, params)
            c.commit()
            return cur.lastrowid
        finally:
            c.close()


def query(sql, params=()):
    with _lock:
        c = sqlite3.connect(config.DB_PATH)
        c.row_factory = sqlite3.Row
        try:
            return [dict(r) for r in c.execute(sql, params).fetchall()]
        finally:
            c.close()


def init_db():
    with _lock:
        c = sqlite3.connect(config.DB_PATH)
        c.executescript(SCHEMA)
        for table, col, ddl in (("users", "disabled", "INTEGER DEFAULT 0"),
                                ("users", "notify_email", "INTEGER DEFAULT 1"),
                                ("users", "notify_level", "TEXT DEFAULT 'MEDIUM'"),
                                ("alerts", "status", "TEXT DEFAULT 'Open'")):
            cols = [r[1] for r in c.execute(f"PRAGMA table_info({table})")]
            if col not in cols:                       # upgrade databases from older versions
                c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
        row = c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='users'").fetchone()
        if row and "'admin'" not in row[0]:           # old table only allowed customer/staff -> rebuild it
            c.executescript("ALTER TABLE users RENAME TO users_old;\n" + USERS_DDL.format(name="users") + ";\n"
                            "INSERT INTO users(id,username,full_name,email,phone,role,salt,password_hash,home_device,"
                            "created_at,disabled,notify_email,notify_level) "
                            "SELECT id,username,full_name,email,phone,role,salt,password_hash,home_device,created_at,"
                            "COALESCE(disabled,0),COALESCE(notify_email,1),COALESCE(notify_level,'HIGH') "
                            "FROM users_old;\nDROP TABLE users_old;")
        c.commit()
        c.close()


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000)
    return salt, digest.hex()


def verify_password(password, salt, stored_hash):
    _, h = hash_password(password, salt)
    return hmac.compare_digest(h, stored_hash)


def get_user(username):
    rows = query("SELECT * FROM users WHERE username=?", (username,))
    return rows[0] if rows else None


def create_user(username, password, role, full_name="", email="", home_device=""):
    if get_user(username):
        return False, "Username already exists"
    salt, h = hash_password(password)
    execute("INSERT INTO users(username,full_name,email,phone,role,salt,password_hash,home_device,created_at)"
            " VALUES(?,?,?,?,?,?,?,?,?)",
            (username, full_name, email, "", role, salt, h, home_device, now()))
    return True, "Account created"


def set_password(username, new_password):
    salt, h = hash_password(new_password)
    execute("UPDATE users SET salt=?, password_hash=? WHERE username=?", (salt, h, username))


def update_profile(username, full_name, email):
    execute("UPDATE users SET full_name=?, email=? WHERE username=?", (full_name, email, username))


def set_disabled(username, disabled):
    execute("UPDATE users SET disabled=? WHERE username=?", (int(disabled), username))


def delete_user(username):
    execute("DELETE FROM users WHERE username=?", (username,))


def resolve_alert(alert_id):
    execute("UPDATE alerts SET status='Resolved' WHERE id=?", (alert_id,))


def create_email_event(username, role, event_type, recipients="", status="pending"):
    return execute("INSERT INTO email_events(ts,username,role,event_type,status,recipients) VALUES(?,?,?,?,?,?)",
                   (now(), username, role, event_type, status, recipients))


def update_email_event(event_id, status):
    execute("UPDATE email_events SET status=? WHERE id=?", (status, event_id))


def set_role(username, role):
    execute("UPDATE users SET role=? WHERE username=?", (role, username))


def update_notify_prefs(username, email_on, level):
    execute("UPDATE users SET notify_email=?, notify_level=? WHERE username=?",
            (int(email_on), level, username))


def clear_activity():
    """Deletes all login, file, alert and email activity (users are kept)."""
    for t in ("login_events", "file_events", "alerts", "email_events"):
        execute(f"DELETE FROM {t}")


def users_summary():
    return query("SELECT u.username, u.full_name, u.role, u.email, u.disabled, u.created_at, u.notify_email, "
                 "(SELECT MAX(ts) FROM login_events l WHERE l.username=u.username AND l.success=1) AS last_login, "
                 "(SELECT COUNT(*) FROM login_events l WHERE l.username=u.username AND l.success=0) AS failed "
                 "FROM users u ORDER BY u.id")


