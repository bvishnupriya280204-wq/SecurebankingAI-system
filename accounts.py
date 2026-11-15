"""Account rules: input validation, password strength, and e-mail OTP password reset."""
import hmac, re, secrets, time
import config
import database as db
import monitor
import notifier

_otps = {}   # username -> {"otp", "exp", "tries"}  (kept in memory only)


def validate_username(u):
    ok = bool(re.fullmatch(r"[A-Za-z0-9_.-]{3,30}", u or ""))
    return ok, "" if ok else "Username must be 3-30 characters: letters, digits, . _ -"


def validate_email(e):
    ok = bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", e or ""))
    return ok, "" if ok else "Enter a valid e-mail address (needed for password reset)."


def validate_password(p):
    if len(p or "") < 8 or not re.search(r"[A-Z]", p) or not re.search(r"[a-z]", p) or not re.search(r"\d", p):
        return False, "Password needs 8+ characters with uppercase, lowercase and a digit."
    return True, ""


def password_strength(p):
    """Returns (score 0-5, label)."""
    score = sum([len(p) >= 8, len(p) >= 12, bool(re.search(r"[A-Z]", p)) and bool(re.search(r"[a-z]", p)),
                 bool(re.search(r"\d", p)), bool(re.search(r"[^A-Za-z0-9]", p))])
    return score, ["Very weak", "Very weak", "Weak", "Fair", "Strong", "Excellent"][score]


def temp_password():
    return secrets.token_urlsafe(6) + "Aa7"


def _mask(email):
    name, _, dom = email.partition("@")
    return name[:2] + "***@" + dom


def start_reset(username):
    """Start an email-verified password reset; never disclose an OTP locally."""
    u = db.get_user(username)
    if not u:
        return False, "No account found with that username.", None
    otp = f"{secrets.randbelow(10 ** 6):06d}"
    _otps[username] = {"otp": otp, "exp": time.time() + 600, "tries": 0}
    if config.email_configured() and u.get("email"):
        notifier.send_email_async([u["email"]], "SecureBank AI - password reset code",
                                  f"Your verification code is {otp}. It is valid for 10 minutes.\n"
                                  "If you did not request this, ignore this e-mail.")
        return True, f"A 6-digit code was e-mailed to {_mask(u['email'])}.", None
    _otps.pop(username, None)
    return False, "Password reset is unavailable because a verified e-mail address or e-mail service is not configured.", None


def finish_reset(username, otp, new_password):
    rec = _otps.get(username)
    if not rec or time.time() > rec["exp"]:
        return False, "Code expired. Please request a new one."
    rec["tries"] += 1
    if rec["tries"] > 5:
        del _otps[username]
        return False, "Too many wrong attempts. Request a new code."
    if not hmac.compare_digest(rec["otp"], (otp or "").strip()):
        return False, "Incorrect code."
    ok, msg = validate_password(new_password)
    if not ok:
        return False, msg
    db.set_password(username, new_password)
    del _otps[username]
    monitor.raise_alert("Account", username, 10, f"Password for '{username}' was reset using a verification code",
                        notify_user=False)
    return True, "Password changed. You can log in now."
