"""Backend self-test (no GUI needed): python smoke_test.py"""
import os, tempfile
import config
config.SMTP_USER = ""
config.SMTP_APP_PASSWORD = ""
config.DB_PATH = os.path.join(tempfile.mkdtemp(), "t.db")
import database as db
db.init_db()
assert db.query("SELECT COUNT(*) AS n FROM users")[0]["n"] == 0
import monitor
from ml_engine import engine

print("Model metrics:", {k: {a: (round(b, 3) if isinstance(b, (int, float)) else b) for a, b in v.items()} for k, v in engine.metrics.items()})
assert db.create_user("testcustomer", "Secure123", "customer", "Test Customer", "test@example.com", "device-test")[0]
u, msg = monitor.authenticate("testcustomer", "Secure123"); print("good login ->", msg)
u, msg = monitor.authenticate("testcustomer", "wrong"); print("bad login  ->", msg)

n = monitor.process_login("testcustomer", True, monitor.local_device(), "10.0.0.5", "IN", 11)
print("normal login risk:", n["risk"], n["verdict"]); assert n["verdict"] == "LOW"

for _ in range(6):
    a = monitor.process_login("testcustomer", False, "attacker-1", "1.2.3.4", "RU", 3)
print("brute force risk :", a["risk"], a["verdict"]); assert a["verdict"] == "HIGH"

f = monitor.process_file("teststaff", "report.pdf", "View", 1.2, 1, 11)
print("normal file risk :", f["risk"], f["verdict"]); assert f["verdict"] == "LOW"
for i in range(25):
    f = monitor.process_file("teststaff", f"db_{i}.csv", "Download", 60, 3, 1)
print("bulk download    :", f["risk"], f["verdict"]); assert f["verdict"] == "HIGH"
print("alerts:", len(db.query("SELECT * FROM alerts")), "| ALL TESTS PASSED")

import accounts
assert accounts.validate_password("abc")[0] is False and accounts.validate_password("Secure123")[0]
assert db.create_user("newuser", "Secure123", "customer", "New User", "n@x.com", "dev")[0]
assert not db.create_user("newuser", "Secure123", "customer")[0]          # duplicate refused
assert monitor.authenticate("newuser", "Secure123")[0] is not None
ok, m, otp = accounts.start_reset("newuser")
assert not ok and otp is None and "not configured" in m
db.set_disabled("newuser", True)
assert monitor.authenticate("newuser", "Secure123")[0] is None            # disabled account refused
db.set_disabled("newuser", False)
db.update_profile("newuser", "N U", "z@x.com"); assert db.get_user("newuser")["email"] == "z@x.com"
assert len(db.users_summary()) >= 2
aid = db.query("SELECT id FROM alerts LIMIT 1")[0]["id"]; db.resolve_alert(aid)
assert db.query("SELECT status FROM alerts WHERE id=?", (aid,))[0]["status"] == "Resolved"
print("ACCOUNT FEATURES PASSED")

import sqlite3, notifier
assert db.create_user("testadmin", "Secure123", "admin", "Test Admin", "boss@x.com")[0]
assert db.create_user("teststaff", "Secure123", "staff", "Test Staff", "staff@x.com")[0]
db.update_profile("testadmin", "Admin", "boss@x.com")
db.update_profile("testcustomer", "Test Customer", "testcustomer@x.com")
sent = []
notifier.notify = lambda *a: sent.append(a)
for _ in range(6): monitor.process_login("testcustomer", False, "evil", "9.9.9.9", "RU", 3)
assert sent, "HIGH alert should notify"
emails = sent[-1][3]
assert "testcustomer@x.com" in emails and "boss@x.com" in emails, emails
db.update_notify_prefs("testcustomer", False, "HIGH")
e2 = monitor.recipients_for("testcustomer", "HIGH"); assert "testcustomer@x.com" not in e2 and "boss@x.com" in e2
print("MEDIUM for admin default:", monitor.recipients_for("testcustomer", "MEDIUM"))
r = notifier.__dict__  # send_now works without config
import importlib; importlib.reload(notifier)
print("send_now:", notifier.send_now([], "t", "b"))
import tempfile, os
old = os.path.join(tempfile.mkdtemp(), "old.db"); c = sqlite3.connect(old)
c.executescript("CREATE TABLE users(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, full_name TEXT, email TEXT, phone TEXT, role TEXT NOT NULL CHECK(role IN ('customer','staff')), salt TEXT NOT NULL, password_hash TEXT NOT NULL, home_device TEXT, created_at TEXT);"
                "INSERT INTO users(username,role,salt,password_hash) VALUES('olduser','customer','aa','bb');")
c.commit(); c.close(); config.DB_PATH = old
db.init_db()
assert db.get_user("olduser") and db.query("SELECT COUNT(*) n FROM users")[0]["n"] == 1
db.set_role("olduser", "staff"); assert db.get_user("olduser")["role"] == "staff"
print("ROLE + ROUTING + MIGRATION PASSED")
