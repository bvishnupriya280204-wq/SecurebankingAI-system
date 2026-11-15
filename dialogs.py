"""Forgot-password dialog and the profile / change-password tab (used by both portals)."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QFormLayout, QGroupBox, QHBoxLayout,
                               QLabel, QLineEdit, QMessageBox, QProgressBar, QPushButton, QVBoxLayout, QWidget)

import accounts
import config
import database as db
import monitor
import notifier
from ui_common import app_icon, fill_table, make_table, pill, style_meter


def _password_field(placeholder=""):
    e = QLineEdit()
    e.setEchoMode(QLineEdit.Password)
    e.setPlaceholderText(placeholder)
    return e


class ForgotPasswordDialog(QDialog):
    """Step 1: enter username -> receive a 6-digit code. Step 2: enter code + new password."""

    def __init__(self, parent=None, username=""):
        super().__init__(parent)
        self.setWindowTitle("Forgot password")
        self.setWindowIcon(app_icon())
        self.resize(430, 470)
        lay = QVBoxLayout(self)
        title = QLabel("🔑 Reset your password")
        title.setObjectName("title")
        lay.addWidget(title)
        lay.addWidget(QLabel("We will send a verification code to your registered e-mail."))
        form = QFormLayout()
        self.user = QLineEdit(username)
        self.user.setPlaceholderText("Your username")
        self.btn_send = QPushButton("Send verification code")
        self.btn_send.clicked.connect(self.send_code)
        self.code = QLineEdit()
        self.code.setPlaceholderText("6-digit code")
        self.p1 = _password_field("New password")
        self.p2 = _password_field("Repeat new password")
        self.meter = QProgressBar()
        style_meter(self.meter, "")
        self.p1.textChanged.connect(lambda t: style_meter(self.meter, t))
        self.btn_reset = QPushButton("Reset password")
        self.btn_reset.setObjectName("success")
        self.btn_reset.clicked.connect(self.reset)
        form.addRow("Username", self.user)
        form.addRow(self.btn_send)
        form.addRow("Code", self.code)
        form.addRow("New password", self.p1)
        form.addRow("", self.meter)
        form.addRow("Confirm", self.p2)
        form.addRow(self.btn_reset)
        lay.addLayout(form)
        self.info = QLabel("")
        self.info.setWordWrap(True)
        lay.addWidget(self.info)
        lay.addStretch()
        self._enable_step2(False)

    def _enable_step2(self, on):
        for w in (self.code, self.p1, self.p2, self.btn_reset):
            w.setEnabled(on)

    def _say(self, text, good=True):
        self.info.setStyleSheet(f"color: {'#2e7d32' if good else '#c62828'}; font-weight: 600;")
        self.info.setText(text)

    def send_code(self):
        ok, msg, _otp = accounts.start_reset(self.user.text().strip())
        if not ok:
            self._say(msg, False)
            return
        self._enable_step2(True)
        self._say(msg)
        self.code.setFocus()

    def reset(self):
        if self.p1.text() != self.p2.text():
            self._say("The two passwords do not match.", False)
            return
        ok, msg = accounts.finish_reset(self.user.text().strip(), self.code.text(), self.p1.text())
        if ok:
            QMessageBox.information(self, "Password reset", msg)
            self.accept()
        else:
            self._say(msg, False)


class ProfileTab(QWidget):
    """Edit contact details and change password."""

    def __init__(self, user):
        super().__init__()
        self.user = user
        lay = QHBoxLayout(self)

        box = QGroupBox("👤 My profile")
        f = QFormLayout()
        f.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        f.setFormAlignment(Qt.AlignTop)
        f.setHorizontalSpacing(18)
        f.setVerticalSpacing(14)
        self.username = QLineEdit(user["username"]); self.username.setReadOnly(True)
        self.role = QLineEdit(user["role"].title()); self.role.setReadOnly(True)
        self.name = QLineEdit(user.get("full_name") or "")
        self.mail = QLineEdit(user.get("email") or "")
        for field in (self.username, self.name, self.mail, self.role):
            field.setMinimumHeight(38)
        f.addRow("Username", self.username)
        f.addRow("Full name", self.name)
        f.addRow("E-mail", self.mail)
        f.addRow("Role", self.role)
        profile_layout = QVBoxLayout(box)
        profile_layout.addLayout(f)
        save = QPushButton("Save profile")
        save.setObjectName("success")
        save.setMinimumHeight(42)
        save.clicked.connect(self.save_profile)
        profile_layout.addSpacing(8)
        profile_layout.addWidget(save)
        profile_layout.addStretch()
        lay.addWidget(box)

        box2 = QGroupBox("🔒 Change password")
        f2 = QFormLayout(box2)
        self.cur, self.new1, self.new2 = _password_field(), _password_field(), _password_field()
        self.meter = QProgressBar()
        style_meter(self.meter, "")
        self.new1.textChanged.connect(lambda t: style_meter(self.meter, t))
        change = QPushButton("Update password")
        change.setObjectName("purple")
        change.setMinimumHeight(42)
        change.clicked.connect(self.change_password)
        f2.addRow("Current", self.cur)
        f2.addRow("New", self.new1)
        f2.addRow("", self.meter)
        f2.addRow("Repeat new", self.new2)
        f2.addRow(change)
        lay.addWidget(box2)

    def save_profile(self):
        for ok, msg in (accounts.validate_email(self.mail.text().strip()),):
            if not ok:
                QMessageBox.warning(self, "Profile", msg)
                return
        db.update_profile(self.user["username"], self.name.text().strip(), self.mail.text().strip())
        notifier.notify_activity(self.user["username"], "Profile updated", "[SecureBank AI] Profile updated",
                                 "Your account profile details were updated. If you did not make this change, "
                                 "contact your bank through an official support channel.")
        QMessageBox.information(self, "Profile", "Profile updated.")

    def change_password(self):
        fresh = db.get_user(self.user["username"])
        if not db.verify_password(self.cur.text(), fresh["salt"], fresh["password_hash"]):
            QMessageBox.warning(self, "Password", "Current password is incorrect.")
            return
        ok, msg = accounts.validate_password(self.new1.text())
        if not ok:
            QMessageBox.warning(self, "Password", msg)
            return
        if self.new1.text() != self.new2.text():
            QMessageBox.warning(self, "Password", "The new passwords do not match.")
            return
        db.set_password(self.user["username"], self.new1.text())
        monitor.raise_alert("Account", self.user["username"], 10, "Password changed by the user",
                            notify_user=False)
        notifier.notify_activity(self.user["username"], "Password changed", "[SecureBank AI] Password changed",
                                 "Your SecureBank AI account password was changed. If you did not make this change, "
                                 "contact your bank through an official support channel.")
        for w in (self.cur, self.new1, self.new2):
            w.clear()
        QMessageBox.information(self, "Password", "Password changed successfully.")


class CreateUserDialog(QDialog):
    """Admin: create an account of any role."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create user")
        self.setWindowIcon(app_icon())
        self.resize(420, 420)
        lay = QVBoxLayout(self)
        t = QLabel("➕ Create a new account")
        t.setObjectName("title")
        lay.addWidget(t)
        f = QFormLayout()
        self.name, self.user, self.mail = QLineEdit(), QLineEdit(), QLineEdit()
        self.role = QComboBox()
        self.role.addItems(["customer", "staff", "admin"])
        self.pw = QLineEdit(accounts.temp_password())
        for label, w in (("Full name", self.name), ("Username", self.user), ("E-mail", self.mail),
                         ("Role", self.role), ("Password", self.pw)):
            f.addRow(label, w)
        lay.addLayout(f)
        self.msg = QLabel("")
        self.msg.setWordWrap(True)
        lay.addWidget(self.msg)
        b = QPushButton("Create account")
        b.setObjectName("success")
        b.clicked.connect(self.create)
        lay.addWidget(b)
        lay.addStretch()

    def create(self):
        u, mail, pw = self.user.text().strip(), self.mail.text().strip(), self.pw.text()
        for ok, msg in (accounts.validate_username(u), accounts.validate_email(mail),
                        accounts.validate_password(pw)):
            if not ok:
                self.msg.setStyleSheet("color:#c62828; font-weight:600;")
                self.msg.setText("❌ " + msg)
                return
        ok, msg = db.create_user(u, pw, self.role.currentText(), self.name.text().strip(), mail,
                                 monitor.local_device())
        if not ok:
            self.msg.setStyleSheet("color:#c62828; font-weight:600;")
            self.msg.setText("❌ " + msg)
            return
        notifier.notify_activity(u, "Account created", "[SecureBank AI] Account created",
                                 "A SecureBank AI account was created for you by the bank. If you did not expect it, "
                                 "contact your bank through an official support channel.")
        QMessageBox.information(self, "Account created",
                                f"Username: {u}\nPassword: {pw}\nRole: {self.role.currentText()}\n\n"
                                "Give these details to the user.")
        self.accept()



class NotificationTab(QWidget):
    """Alert delivery preferences and delivery verification."""

    def __init__(self, user):
        super().__init__()
        self.user = user
        lay = QHBoxLayout(self)
        box = QGroupBox("📬 Where should alerts be sent?")
        bl = QVBoxLayout(box)
        self.contact = QLabel()
        self.contact.setWordWrap(True)
        self.chk_mail = QCheckBox("Send account activity and security notices to my e-mail")
        self.level = QComboBox()
        self.level.addItems(["HIGH only", "MEDIUM and HIGH"])
        save = QPushButton("💾 Save preferences")
        save.setObjectName("success")
        save.clicked.connect(self.save)
        t1 = QPushButton("📧 Send test e-mail")
        t1.clicked.connect(self.test)
        t3 = QPushButton("🧪 Trigger a sample HIGH alert (full test)")
        t3.setObjectName("warn")
        t3.setText("🧪 Generate controlled test alert (admin)")
        t3.setVisible(user["role"] == "admin")
        t3.clicked.connect(self.sample_alert)
        self.result = QLabel("")
        self.result.setWordWrap(True)
        for w in (self.contact, self.chk_mail, QLabel("Suspicious-login alert threshold:"), self.level, save, t1, t3,
                  self.result):
            bl.addWidget(w)
        bl.addStretch()
        lay.addWidget(box, 1)

        hist = QGroupBox("🧾 Notification history & delivery status")
        hl = QVBoxLayout(hist)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.svc = QLabel()
        self.only_mine = QCheckBox("Only alerts about my account")
        self.only_mine.setVisible(user["role"] != "customer")
        self.only_mine.toggled.connect(lambda _c: self.refresh())
        self.table = make_table(["Time", "Module", "Account", "Severity", "Delivery status"])
        note = QLabel("This history includes security alerts and routine sign-in/file-activity emails. Delivery status "
                      "shows whether each notice was sent, failed, or skipped because an address, preference, or SMTP "
                      "configuration was missing.")
        note.setWordWrap(True)
        note.setObjectName("hint")
        for w in (self.svc, self.summary, self.only_mine, self.table, note):
            hl.addWidget(w)
        lay.addWidget(hist, 2)
        self.load()

    def load(self):
        u = db.get_user(self.user["username"])
        self.chk_mail.setChecked(bool(u.get("notify_email", 1)))
        self.level.setCurrentIndex(1 if u.get("notify_level") == "MEDIUM" else 0)
        self.refresh()

    def refresh(self):
        u = db.get_user(self.user["username"])
        ok_mail = "✅ " + u["email"] if u.get("email") else "❌ not set (add it in Profile)"
        svc_mail = "✅ ready" if config.email_configured() else "❌ not configured by admin"
        self.contact.setText(f"<b>My e-mail:</b> {ok_mail}<br><b>Bank e-mail service:</b> {svc_mail}")
        pill(self.svc, "📧 E-mail delivery ready" if config.email_configured() else "📧 E-mail service not configured",
             "good" if config.email_configured() else "warn")
        self._fill_history(u)

    def _fill_history(self, u):
        me = self.user["username"]
        if self.user["role"] == "customer" or self.only_mine.isChecked():
            rows = db.query("SELECT ts,source,username,severity,notified FROM alerts WHERE username=? ORDER BY id DESC LIMIT 100", (me,))
            routine = db.query("SELECT ts,event_type AS source,username,'INFO' AS severity,status AS notified "
                               "FROM email_events WHERE username=? ORDER BY id DESC LIMIT 100", (me,))
        else:
            rows = db.query("SELECT ts,source,username,severity,notified FROM alerts ORDER BY id DESC LIMIT 100")
            routine = db.query("SELECT ts,event_type AS source,username,'INFO' AS severity,status AS notified "
                               "FROM email_events ORDER BY id DESC LIMIT 100")
        rows = sorted(rows + routine, key=lambda r: r.get("ts") or "", reverse=True)[:100]

        def state(r):
            n = (r.get("notified") or "").lower()
            return ("sent" if n.startswith("email: sent") or n.startswith("sent") else
                    "failed" if "failed" in n else
                    "suppressed" if "suppressed" in n else
                    "skipped" if ("skipped" in n or "not required" in n or "no e-mail" in n or "not configured" in n)
                    else "pending")
        counts = {}
        for r in rows:
            counts[state(r)] = counts.get(state(r), 0) + 1
            r["notified"] = r.get("notified") or "pending"
        self.summary.setText(
            f"Last {len(rows)} notices: ✅ {counts.get('sent', 0)} e-mailed · ⏸ {counts.get('suppressed', 0)} suppressed "
            f"· ⏭ {counts.get('skipped', 0)} skipped · ❌ {counts.get('failed', 0)} failed "
            f"· ⏳ {counts.get('pending', 0)} pending")
        fill_table(self.table, rows, ["ts", "source", "username", "severity", "notified"], "severity")

    def save(self):
        lvl = "MEDIUM" if self.level.currentIndex() == 1 else "HIGH"
        db.update_notify_prefs(self.user["username"], self.chk_mail.isChecked(), lvl)
        QMessageBox.information(self, "Saved", "Notification preferences saved.")

    def sample_alert(self):
        """Pushes a realistic HIGH alert through the real pipeline (ML alert -> routing -> e-mail)."""
        name = self.user["username"]
        monitor.raise_alert("BankShield", name, 85, f"SAMPLE ALERT for '{name}': simulated suspicious login from a "
                            "new device in another country. This is only a test.", True)
        self.result.setStyleSheet("color: #2e9d5b; font-weight: 600;")
        self.result.setText("Sample HIGH alert created. An e-mail should arrive within a few seconds - "
                            "see the Alerts tab, column 'Sent via', for the delivery status.")

    def test(self):
        u = db.get_user(self.user["username"])
        emails = [u["email"]] if u.get("email") else []
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            res = notifier.send_now(emails, "SecureBank AI - test alert",
                                    f"Hello {u.get('full_name') or u['username']}, this is a test alert from "
                                    "SecureBank AI. Your alert delivery works.")
        finally:
            QApplication.restoreOverrideCursor()
        self.result.setText(f"E-MAIL: {res['email']}")
        ok = res["email"].startswith("sent")
        self.result.setStyleSheet(f"color: {'#2e9d5b' if ok else '#e53935'}; font-weight: 600;")
