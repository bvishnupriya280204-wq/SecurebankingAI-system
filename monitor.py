"""BankShield (login monitoring) and LeakGuard (file-access monitoring) logic."""
import platform, socket
from datetime import datetime, timedelta
import config
import database as db
import notifier
from ml_engine import engine

def _iso(dt):
    return dt.isoformat(timespec="seconds")


def local_device():
    return f"{platform.node()}-{platform.system()}"


def local_ip():
    try:
        return socket.gethostbyname(socket.gethostname())
    except OSError:
        return "127.0.0.1"


def verdict(risk):
    return "HIGH" if risk >= config.HIGH_RISK else "MEDIUM" if risk >= config.MEDIUM_RISK else "LOW"


RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}


def recipients_for(username, sev, notify_user=True):
    """Return e-mail recipients for the account owner, admins and security team."""
    emails = set()

    def add(u):
        if RANK[sev] < RANK.get(u.get("notify_level") or "HIGH", 2):
            return
        if u.get("notify_email", 1) and u.get("email"):
            emails.add(u["email"])

    if notify_user and db.get_user(username):
        add(db.get_user(username))
    for adm in db.query("SELECT * FROM users WHERE role='admin' AND disabled=0"):
        add(adm)
    if sev == "HIGH" and config.SECURITY_TEAM_EMAIL:
        emails.add(config.SECURITY_TEAM_EMAIL)
    return sorted(emails)


def raise_alert(source, username, risk, message, notify_user=True, send_email=True):
    sev = verdict(risk)
    aid = db.execute("INSERT INTO alerts(ts,source,username,severity,risk,message) VALUES(?,?,?,?,?,?)",
                     (db.now(), source, username, sev, risk, message))
    if sev == "LOW":
        db.execute("UPDATE alerts SET notified='not required' WHERE id=?", (aid,))
        return aid
    if not send_email:
        db.execute("UPDATE alerts SET notified='e-mail skipped - simulator or imported log' WHERE id=?", (aid,))
        return aid
    emails = recipients_for(username, sev, notify_user)
    if not emails:
        db.execute("UPDATE alerts SET notified='no e-mail recipient has alerts switched on / e-mail address' WHERE id=?", (aid,))
        return aid
    body = (f"SecureBank AI security alert\n\nSeverity : {sev}\nModule   : {source}\nAccount  : {username}\n"
            f"Risk     : {risk}/100\nTime     : {db.now()}\n\n{message}\n\n"
            "If this was not you, change your password immediately and contact the bank.")
    notifier.notify(aid, f"[SecureBank AI] {sev} security alert - {source}", body, emails)
    return aid


def process_login(username, success, device=None, ip=None, country="IN", hour=None, send_notifications=True):
    device, ip = device or local_device(), ip or local_ip()
    now = datetime.now()
    hour = now.hour if hour is None else hour
    prev = db.query("SELECT success,device,country,ts FROM login_events WHERE username=? "
                    "ORDER BY id DESC LIMIT 50", (username,))
    streak = 0
    for e in prev:
        if e["success"]:
            break
        streak += 1
    good = [e for e in prev if e["success"]]
    new_dev = int(bool(good) and device not in {e["device"] for e in good})
    new_ctry = int(bool(good) and country not in {e["country"] for e in good})
    cutoff = _iso(now - timedelta(hours=1))
    feats = dict(hour=hour, success=int(success),
                 failed_streak=streak + (0 if success else 1),
                 new_device=new_dev, new_country=new_ctry,
                 logins_last_hour=sum(1 for e in prev if e["ts"] >= cutoff) + 1)
    risk = engine.score_login(feats)
    v = verdict(risk)
    db.execute("INSERT INTO login_events(ts,username,success,hour,device,ip,country,failed_streak,"
               "new_device,new_country,logins_last_hour,risk,verdict) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
               (db.now(), username, int(success), hour, device, ip, country, feats["failed_streak"],
                new_dev, new_ctry, feats["logins_last_hour"], risk, v))
    if risk >= config.MEDIUM_RISK:
        why = []
        if feats["failed_streak"] >= 3: why.append(f"{feats['failed_streak']} consecutive failed attempts")
        if new_dev: why.append(f"unfamiliar device ({device})")
        if new_ctry: why.append(f"login from new country ({country})")
        if hour < 6 or hour >= 23: why.append(f"unusual login time ({hour:02d}:00)")
        if feats["logins_last_hour"] >= 6: why.append(f"{feats['logins_last_hour']} attempts in the last hour")
        raise_alert("BankShield", username, risk,
                    f"Suspicious login for '{username}' from {ip}: " + ("; ".join(why) or "ML anomaly pattern"),
                    send_email=send_notifications)
    elif send_notifications:
        event = "Successful sign-in" if success else "Unsuccessful sign-in attempt"
        notifier.notify_activity(
            username, event, f"[SecureBank AI] {event}",
            f"Sign-in activity recorded: {event.lower()}.\n\n"
            f"Time: {db.now()}\nDevice: {device}\nIP: {ip}\nCountry: {country}\nRisk: {risk}/100 ({v})\n\n"
            "If you do not recognize this activity, contact your bank through its official support channel.")
    return {"risk": risk, "verdict": v, **feats}


def authenticate(username, password):
    """Returns (user_dict | None, message). Every attempt is recorded and risk-scored."""
    recent = db.query("SELECT success,ts FROM login_events WHERE username=? ORDER BY id DESC LIMIT ?",
                      (username, config.LOCKOUT_FAILS))
    if len(recent) == config.LOCKOUT_FAILS and not any(r["success"] for r in recent):
        age = (datetime.now() - datetime.fromisoformat(recent[0]["ts"])).total_seconds()
        if age < config.LOCKOUT_SECONDS:
            if db.get_user(username):
                notifier.notify_activity(username, "Sign-in blocked", "[SecureBank AI] Sign-in temporarily blocked",
                                         "A sign-in attempt was blocked because the account is temporarily locked. "
                                         "If you did not make these attempts, contact your bank through an official channel.")
            return None, f"Account temporarily locked. Try again in {int(config.LOCKOUT_SECONDS - age)}s."
    user = db.get_user(username)
    ok = bool(user) and db.verify_password(password, user["salt"], user["password_hash"])
    if ok and user.get("disabled"):
        process_login(username, False)
        return None, "This account has been disabled by the bank. Please contact support."
    process_login(username, ok)
    return (user, "OK") if ok else (None, "Invalid username or password")


def process_file(username, filename, action, size_mb, sensitivity, hour=None, send_notifications=True):
    now = datetime.now()
    hour = now.hour if hour is None else hour
    rows = db.query("SELECT ts,size_mb FROM file_events WHERE username=? AND ts>=?",
                    (username, _iso(now - timedelta(hours=1))))
    c10 = _iso(now - timedelta(minutes=10))
    files10 = sum(1 for r in rows if r["ts"] >= c10) + 1
    mb_hr = sum(r["size_mb"] for r in rows) + size_mb
    feats = dict(hour=hour, size_mb=size_mb, files_last_10min=files10, mb_last_hour=mb_hr,
                 sensitivity=sensitivity, is_download=int(action not in ("View", "Edit")))
    risk = engine.score_file(feats)
    v = verdict(risk)
    db.execute("INSERT INTO file_events(ts,username,filename,action,size_mb,sensitivity,hour,"
               "files_last_10min,mb_last_hour,risk,verdict) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
               (db.now(), username, filename, action, round(size_mb, 2), sensitivity, hour,
                files10, round(mb_hr, 1), risk, v))
    if risk >= config.MEDIUM_RISK:
        raise_alert("LeakGuard", username, risk,
                    f"Possible data leakage by '{username}': {action} '{filename}' ({size_mb:.1f} MB), "
                    f"{files10} files in 10 min, {mb_hr:.0f} MB in 1 hour, sensitivity level {sensitivity}",
                    notify_user=False, send_email=send_notifications)   # do not alert a suspected insider
    elif send_notifications:
        notifier.notify_activity(
            username, "File activity", "[SecureBank AI] File activity recorded",
            f"A file activity was recorded for your account.\n\nFile: {filename}\nAction: {action}\n"
            f"Size: {size_mb:.1f} MB\nRisk: {risk}/100 ({v})\nTime: {db.now()}\n\n"
            "If you do not recognize this activity, contact your bank through its official support channel.")
    return {"risk": risk, "verdict": v, **feats}
