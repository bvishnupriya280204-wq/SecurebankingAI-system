"""Gmail SMTP e-mail notifications."""
import smtplib, ssl, threading
from email.message import EmailMessage
import config
import database as db


def _send_email(recipients, subject, body):
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = config.SMTP_USER, ", ".join(recipients), subject
    msg.set_content(body)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context(), timeout=15) as s:
        s.login(config.SMTP_USER, config.SMTP_APP_PASSWORD)
        s.send_message(msg)


def send_now(emails, subject, body):
    """Send an e-mail immediately and return its delivery status."""
    if not emails:
        return {"email": "no e-mail address to send to"}
    if not config.email_configured():
        return {"email": "e-mail service is not configured by the administrator"}
    try:
        _send_email(emails, subject, body)
        return {"email": "sent to " + ", ".join(emails)}
    except Exception as e:
        return {"email": f"FAILED - {str(e)[:120]}"}


def _work(alert_id, subject, body, emails):
    res = send_now(emails, subject, body)
    db.execute("UPDATE alerts SET notified=? WHERE id=?", ("; ".join(f"{k}: {v}" for k, v in res.items()), alert_id))


def notify(alert_id, subject, body, emails):
    threading.Thread(target=_work, args=(alert_id, subject, body, emails), daemon=True).start()


def _activity_work(event_id, subject, body, recipient):
    res = send_now([recipient], subject, body)
    db.update_email_event(event_id, "; ".join(f"{k}: {v}" for k, v in res.items()))


def notify_activity(username, event_type, subject, body, enabled=True):
    """Email the account holder about their own routine login/file event and record delivery state."""
    user = db.get_user(username)
    if not user:
        return None
    recipient = (user.get("email") or "").strip()
    if not enabled:
        status = "email: skipped - historical/imported or simulated event"
    elif not user.get("notify_email", 1):
        status = "email: skipped - account email alerts are switched off"
    elif not recipient:
        status = "email: skipped - no e-mail address on the account"
    elif not config.email_configured():
        status = "email: not configured by admin"
    else:
        status = "pending"
    event_id = db.create_email_event(username, user.get("role", ""), event_type, recipient, status)
    if status == "pending":
        threading.Thread(target=_activity_work, args=(event_id, subject, body, recipient), daemon=True).start()
    return event_id


def send_email_async(recipients, subject, body):
    """Plain e-mail (used for password-reset codes)."""
    def work():
        try:
            _send_email(recipients, subject, body)
        except Exception:
            pass
    threading.Thread(target=work, daemon=True).start()
