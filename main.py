"""SecureBank AI v2.1 - start-up, login and registration.
Run:  python main.py"""
import os
import sys
import time
import traceback

from PySide6.QtCore import QSettings, Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QGuiApplication, QPainter
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QLineEdit, QMessageBox, QProgressBar, QPushButton, QTabWidget, QVBoxLayout, QWidget)
from PySide6.QtWidgets import QGraphicsDropShadowEffect

import accounts
import config
import database as db
import monitor
import notifier
from admin_ui import AdminDashboard
from customer_ui import CustomerDashboard
from dialogs import ForgotPasswordDialog
from staff_ui import StaffDashboard
from themes import THEMES, make_style
from login_art import field_icon, paint_login_background, shield_pixmap
from ui_common import app_icon, style_meter

HERO = {
    "Customer": ("#082f72", "#0759a8", "#087fba", "Customer Portal", "#0759c7", "#087fba"),
    "Staff": ("#064e3b", "#087f5b", "#15966b", "Security Operations", "#087f5b", "#15966b"),
    "Admin": ("#7f1018", "#b91c2b", "#e04445", "Administrator Console", "#b91c2b", "#e04445"),
}
DASHBOARDS = {"customer": CustomerDashboard, "staff": StaffDashboard, "admin": AdminDashboard}

DARK_ROLE = {"Customer": ("#0a78ff", "#19b7ff"), "Staff": ("#0d9467", "#23c995"), "Admin": ("#c81e30", "#f0525e")}

DARK_CARD_QSS = """
QFrame#authCard { background: rgba(7, 26, 68, 190); border: 1px solid rgba(40, 150, 255, 200); border-radius: 22px; }
QFrame#authCard QLabel { color: #cfe3ff; background: transparent; border: 0; }
QFrame#authCard QLabel#formTitle { font-size: 22px; font-weight: 800; color: white; }
QFrame#authCard QLabel#formSub { font-size: 12px; color: #8db4e6; }
QFrame#authCard QLabel#fieldLabel { font-size: 15px; font-weight: 600; color: #e6f0ff; }
QFrame#authCard QLabel#miniLabel { font-size: 10px; font-weight: 800; letter-spacing: 0.8px; color: #6fa3dd; }
QFrame#authCard QLineEdit { background: rgba(10, 40, 98, 200); color: #eaf3ff; border: 1px solid rgba(50, 140, 240, 170);
    border-radius: 12px; padding: 0 12px; selection-background-color: #1565d8; }
QFrame#authCard QLineEdit:focus { border: 2px solid #19b7ff; background: rgba(12, 50, 120, 220); }
QFrame#authCard QLineEdit:disabled { color: #6f8fb8; background: rgba(10, 30, 70, 160); }
QFrame#authCard QComboBox { background: rgba(10, 40, 98, 200); color: #eaf3ff; border: 1px solid rgba(50, 140, 240, 170);
    border-radius: 12px; padding: 0 12px; }
QFrame#authCard QComboBox:focus { border: 2px solid #19b7ff; }
QFrame#authCard QComboBox QAbstractItemView { background: #0a2352; color: #eaf3ff; selection-background-color: #1565d8; }
QFrame#authCard QCheckBox { color: #9fc2ee; background: transparent; spacing: 7px; }
QFrame#authCard QPushButton#link { background: transparent; color: #19d3ff; border: 0; padding: 2px; font-size: 13px;
    text-decoration: underline; }
QFrame#authCard QPushButton#link:hover { color: white; }
QFrame#authCard QPushButton#registerButton { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #0d9467, stop:1 #23c995);
    color: white; border: 1px solid rgba(255,255,255,60); border-radius: 11px; font-size: 15px; font-weight: 700; }
QFrame#authCard QPushButton#registerButton:hover { background: #23c995; }
QFrame#authCard QTabWidget::pane { background: transparent; border: 0; top: 0; }
QFrame#authCard QTabBar { background: transparent; }
QFrame#authCard QTabBar::tab { background: transparent; color: #7fa6d6; padding: 9px 22px; margin-right: 6px; border: 0;
    border-bottom: 2px solid rgba(70, 140, 230, 90); min-width: 110px; font-weight: 600; border-radius: 0; }
QFrame#authCard QTabBar::tab:selected { color: white; border-bottom: 2px solid #19b7ff; background: transparent; }
QFrame#authCard QTabBar::tab:hover:!selected { color: #cfe3ff; }
QFrame#authCard QProgressBar { border: 1px solid rgba(50, 140, 240, 140); border-radius: 8px; text-align: center;
    background: rgba(10, 40, 98, 160); color: #dbe9ff; }
"""

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("loginRoot")
        self.setWindowTitle("SecureBank AI - Secure Login")
        self.setWindowIcon(app_icon())
        screen = QGuiApplication.primaryScreen()
        available = screen.availableGeometry() if screen else None
        target_w = min(1100, max(760, available.width() - 80)) if available else 1040
        target_h = min(760, max(560, available.height() - 80)) if available else 720
        self.setMinimumSize(760, 560)
        self.setMaximumSize(16777215, 16777215)
        self.resize(target_w, target_h)
        if available:
            self.move(available.center().x() - target_w // 2,
                      available.center().y() - target_h // 2)
        self.settings = QSettings("SecureBankAI", "SecureBankAI")
        page = QHBoxLayout(self); page.setContentsMargins(0, 0, 0, 0); page.setSpacing(0)

        left = QWidget(); left.setObjectName("brandPanel")
        left.setStyleSheet("QWidget#brandPanel { background:transparent; }")
        lv = QVBoxLayout(left); lv.setContentsMargins(40, 30, 40, 30); lv.setSpacing(6)
        lv.addStretch(3)
        big_logo = QLabel(); big_logo.setPixmap(shield_pixmap(320)); big_logo.setAlignment(Qt.AlignCenter)
        big_logo.setStyleSheet("background:transparent;")
        big_name = QLabel('SECUREBANK <span style="color:#1ea0ff; font-style:italic;">AI</span>')
        big_name.setAlignment(Qt.AlignCenter)
        big_name.setStyleSheet("font-size:44px; font-weight:800; color:white; background:transparent;")
        big_tag = QLabel("BANKSHIELD  ·  LEAKGUARD")
        big_tag.setAlignment(Qt.AlignCenter)
        big_tag.setStyleSheet("font-size:12px; font-weight:700; letter-spacing:3px; color:#6fb4ff; background:transparent;")
        accent_line = QFrame(); accent_line.setFixedSize(90, 3)
        accent_line.setStyleSheet("background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 transparent, "
                                  "stop:0.5 #19b7ff, stop:1 transparent); border:0;")
        lv.addWidget(big_logo); lv.addWidget(big_name); lv.addWidget(big_tag)
        lv.addSpacing(8); lv.addWidget(accent_line, 0, Qt.AlignHCenter)
        lv.addStretch(4)

        contact = QWidget(); contact.setStyleSheet("background:transparent;")
        contact_row = QHBoxLayout(contact); contact_row.setContentsMargins(0, 0, 0, 0); contact_row.setSpacing(10)
        contact_title = QLabel("CONTACT US")
        contact_title.setStyleSheet("color:#5f8fc9; font-size:9px; font-weight:800; letter-spacing:1px; background:transparent;")
        contact_row.addWidget(contact_title)
        email_contact = QPushButton("✉  securebank26@gmail.com")
        phone_contact = QPushButton("☎  180068")
        for button in (email_contact, phone_contact):
            button.setCursor(Qt.PointingHandCursor); button.setMinimumHeight(34)
            button.setStyleSheet("QPushButton { background:rgba(14,39,83,165); color:#c4ddff; "
                                 "border:1px solid rgba(66,136,215,115); border-radius:8px; "
                                 "padding:6px 8px; text-align:left; font-size:9px; font-weight:600; } "
                                 "QPushButton:hover { background:rgba(20,67,128,210); border-color:#19b7ff; color:white; }")
            contact_row.addWidget(button)
        contact_row.addStretch(1)
        email_contact.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("mailto:securebank26@gmail.com")))
        phone_contact.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("tel:180068")))
        lv.addWidget(contact)

        right = QWidget(); right.setObjectName("authSide"); right.setStyleSheet("QWidget#authSide { background:transparent; }")
        rv = QVBoxLayout(right); rv.setContentsMargins(20, 24, 40, 24); rv.setSpacing(14)
        self.auth_card = auth_card = QFrame(); auth_card.setObjectName("authCard")
        auth_card.setFixedWidth(560)
        auth_card.setStyleSheet(DARK_CARD_QSS)
        shadow = QGraphicsDropShadowEffect(auth_card); shadow.setBlurRadius(46)
        shadow.setOffset(0, 0); shadow.setColor(QColor(25, 140, 255, 120))
        auth_card.setGraphicsEffect(shadow)
        card_layout = QVBoxLayout(auth_card); card_layout.setContentsMargins(26, 24, 26, 22); card_layout.setSpacing(0)

        brand_row = QHBoxLayout(); brand_row.setSpacing(10); brand_row.addStretch(1)
        small_logo = QLabel(); small_logo.setPixmap(shield_pixmap(120).scaled(
            54, 54, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        small_logo.setFixedSize(56, 56)
        small_name = QLabel('SECUREBANK <span style="color:#1ea0ff; font-style:italic;">AI</span>')
        small_name.setStyleSheet("font-size:27px; font-weight:800; color:white;")
        brand_row.addWidget(small_logo); brand_row.addWidget(small_name); brand_row.addStretch(1)
        card_layout.addLayout(brand_row); card_layout.addSpacing(8)

        self.tabs = QTabWidget()
        self.tabs.tabBar().setDrawBase(False)
        card_layout.addWidget(self.tabs, 1)
        rv.addStretch(1)
        rv.addWidget(auth_card, 0, Qt.AlignHCenter)
        rv.addStretch(1)
        footer = QLabel("SECURE ACCESS  ·  BANKSHIELD  ·  LEAKGUARD")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color:#6fa3dd; background:rgba(8,30,75,150); padding:8px 16px; "
                             "border:1px solid rgba(40,130,230,110); border-radius:10px; "
                             "font-size:9px; font-weight:800; letter-spacing:1.2px;")
        rv.addWidget(footer, 0, Qt.AlignHCenter)

        page.addWidget(left, 45); page.addWidget(right, 55)

        lw = QWidget(); lw.setObjectName("loginFormPage")
        lf = QVBoxLayout(lw); lf.setContentsMargins(6, 14, 6, 6); lf.setSpacing(9)
        h = QLabel("Welcome back"); h.setObjectName("formTitle")
        self.login_title = h
        s = QLabel("Your banking security workspace starts here.")
        s.setObjectName("formSub")
        self.login_subtitle = s
        self.l_role = QComboBox(); self.l_role.addItems(["Customer", "Staff", "Admin"])
        self.l_role.setMinimumHeight(46); self.l_role.setCursor(Qt.PointingHandCursor)
        self.l_role.setToolTip("Choose Customer, Staff, or Admin sign-in")
        self.l_role.setObjectName("roleSelect")
        self.l_role.currentTextChanged.connect(self.set_hero)
        self.l_user = QLineEdit(); self.l_pass = QLineEdit()
        self.l_user.setMinimumHeight(48); self.l_pass.setMinimumHeight(48)
        self.l_user.setPlaceholderText("Enter your username")
        self.l_pass.setPlaceholderText("Enter your password")
        self.l_user.addAction(field_icon("user"), QLineEdit.LeadingPosition)
        self.l_pass.addAction(field_icon("lock"), QLineEdit.LeadingPosition)
        self.l_pass.setEchoMode(QLineEdit.Password)
        self.pw_toggle = self.l_pass.addAction(field_icon("eye_off"), QLineEdit.TrailingPosition)
        self.pw_toggle.setToolTip("Show / hide password")
        self.pw_toggle.triggered.connect(self._toggle_password)
        self.l_pass.returnPressed.connect(self.do_login)
        self.l_user.returnPressed.connect(self.do_login)
        self.remember = QCheckBox("Remember me")
        forgot = QPushButton("Forgot Password?"); forgot.setObjectName("link")
        forgot.setCursor(Qt.PointingHandCursor); forgot.clicked.connect(self.forgot)
        self.l_msg = QLabel(""); self.l_msg.setWordWrap(True)
        btn = QPushButton("Login"); btn.setObjectName("roleLoginButton"); btn.clicked.connect(self.do_login)
        btn.setMinimumHeight(52); btn.setCursor(Qt.PointingHandCursor)
        self.login_button = btn
        lf.addWidget(h); lf.addWidget(s); lf.addSpacing(4)

        def field_block(title, field):
            block = QWidget()
            layout = QVBoxLayout(block); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(6)
            label = QLabel(title); label.setObjectName("fieldLabel")
            layout.addWidget(label); layout.addWidget(field)
            return block

        portal_label = QLabel("Login as"); portal_label.setObjectName("fieldLabel")
        lf.addWidget(portal_label); lf.addWidget(self.l_role)
        lf.addWidget(field_block("Username", self.l_user))
        lf.addWidget(field_block("Password", self.l_pass))
        lf.addWidget(self.l_msg)
        opts = QHBoxLayout(); opts.setContentsMargins(1, 4, 1, 0); opts.setSpacing(8)
        opts.addWidget(self.remember); opts.addStretch(1); opts.addWidget(forgot)
        lf.addLayout(opts); lf.addWidget(btn)
        security_note = QLabel("🔒  Protected sign-in  •  Continuous activity monitoring")
        security_note.setAlignment(Qt.AlignCenter); security_note.setObjectName("miniLabel")
        lf.addWidget(security_note)
        self.tabs.addTab(lw, "Sign in")

        rw = QWidget()
        rf = QGridLayout(rw); rf.setContentsMargins(6, 14, 6, 6)
        rf.setHorizontalSpacing(15); rf.setVerticalSpacing(10)
        rf.setColumnStretch(0, 1); rf.setColumnStretch(1, 1)
        self.r_name, self.r_user, self.r_mail = QLineEdit(), QLineEdit(), QLineEdit()
        self.r_mail.setPlaceholderText("name@gmail.com  (alerts + password reset)")
        self.r_pass = QLineEdit(); self.r_pass.setEchoMode(QLineEdit.Password)
        self.r_pass2 = QLineEdit(); self.r_pass2.setEchoMode(QLineEdit.Password)
        self.r_meter = QProgressBar(); style_meter(self.r_meter, "")
        self.r_pass.textChanged.connect(lambda t_: style_meter(self.r_meter, t_))
        self.r_role = QComboBox(); self.r_role.addItems(["Customer", "Staff", "Admin"])
        self.r_code = QLineEdit(); self.r_code.setPlaceholderText("Authorisation code (staff / admin only)")
        for field in (self.r_name, self.r_user, self.r_mail, self.r_pass, self.r_pass2, self.r_role, self.r_code):
            field.setMinimumHeight(40)
        self.r_code.setEnabled(False)
        self.r_role.currentTextChanged.connect(lambda txt: self.r_code.setEnabled(txt != "Customer"))
        self.r_msg = QLabel(""); self.r_msg.setWordWrap(True)
        reg = QPushButton("Create account  →"); reg.setObjectName("registerButton"); reg.clicked.connect(self.do_register)
        reg.setMinimumHeight(48); reg.setCursor(Qt.PointingHandCursor)
        self.r_meter.setMinimumHeight(14)

        def reg_field(title, widget):
            block = QWidget()
            layout = QVBoxLayout(block); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(4)
            label = QLabel(title); label.setObjectName("fieldLabel")
            layout.addWidget(label); layout.addWidget(widget)
            return block

        rf.addWidget(reg_field("Full name", self.r_name), 0, 0)
        rf.addWidget(reg_field("Username", self.r_user), 0, 1)
        rf.addWidget(reg_field("E-mail", self.r_mail), 1, 0, 1, 2)
        rf.addWidget(reg_field("Password", self.r_pass), 2, 0)
        rf.addWidget(reg_field("Confirm password", self.r_pass2), 2, 1)
        rf.addWidget(self.r_meter, 3, 0, 1, 2)
        rf.addWidget(reg_field("Account type", self.r_role), 4, 0)
        rf.addWidget(reg_field("Access code", self.r_code), 4, 1)
        rf.addWidget(self.r_msg, 5, 0, 1, 2)
        rf.addWidget(reg, 6, 0, 1, 2)
        self.tabs.addTab(rw, "Register")

        last = str(self.settings.value("last_user", "") or "")
        if last:
            self.l_user.setText(last)
            self.remember.setChecked(True)
        self.l_role.setCurrentText(str(self.settings.value("last_role", "Customer") or "Customer"))
        self.set_hero(self.l_role.currentText())
        self._fit_card()

    def paintEvent(self, event):
        p = QPainter(self)
        paint_login_background(p, self.width(), self.height())
        p.end()

    def _fit_card(self):
        """Keep the login card inside the right-hand side on smaller windows."""
        if hasattr(self, "auth_card"):
            self.auth_card.setFixedWidth(max(380, min(560, int(self.width() * 0.55) - 70)))

    def resizeEvent(self, event):
        self._fit_card()
        super().resizeEvent(event)

    def _toggle_password(self):
        show = self.l_pass.echoMode() == QLineEdit.Password
        self.l_pass.setEchoMode(QLineEdit.Normal if show else QLineEdit.Password)
        self.pw_toggle.setIcon(field_icon("eye" if show else "eye_off"))

    def set_hero(self, role):
        a, b = DARK_ROLE.get(role, DARK_ROLE["Customer"])
        if hasattr(self, "login_button"):
            self.login_button.setStyleSheet(
                f"QPushButton#roleLoginButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, "
                f"stop:0 {a}, stop:1 {b}); color:white; border:1px solid rgba(255,255,255,60); "
                "border-radius:11px; padding:11px 18px; font-size:16px; font-weight:700; }"
                f"QPushButton#roleLoginButton:hover {{ background:{b}; }}")

    def _msg(self, label, text, good=False):
        label.setStyleSheet(f"color: {'#4ade80' if good else '#ff7b7b'}; font-weight: 600; background:transparent;")
        label.setText(text)

    def fade_in(self):
        self.setWindowOpacity(1.0)
        self.showMaximized()
        self.raise_()
        self.activateWindow()

    def show_again(self):
        self.l_pass.clear()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized)
        self.showMaximized()
        self.raise_()
        self.activateWindow()

    def forgot(self):
        ForgotPasswordDialog(self, self.l_user.text().strip()).exec()

    def do_login(self):
        u, p = self.l_user.text().strip(), self.l_pass.text()
        if not u or not p:
            self._msg(self.l_msg, "Please enter both username and password.")
            return
        user, msg = monitor.authenticate(u, p)
        if not user:
            self.l_pass.clear()
            self._msg(self.l_msg, "❌ " + msg)
            return
        chosen = self.l_role.currentText()
        if user["role"].title() != chosen:
            self.l_role.setCurrentText(user["role"].title())
            self._msg(self.l_msg, f"This is a {user['role'].title()} account - the page switched to "
                                  f"'{user['role'].title()}'. Press Login again.")
            return
        self.settings.setValue("last_user", u if self.remember.isChecked() else "")
        self.settings.setValue("last_role", chosen)
        self.l_pass.clear()
        self.l_msg.setText("")
        self.dash = DASHBOARDS[user["role"]](user, self)
        self.dash.showMaximized()
        self.hide()

    def do_register(self):
        name, u, mail = self.r_name.text().strip(), self.r_user.text().strip(), self.r_mail.text().strip()
        p, p2 = self.r_pass.text(), self.r_pass2.text()
        role = self.r_role.currentText().lower()
        for ok, msg in (accounts.validate_username(u), accounts.validate_email(mail),
                        accounts.validate_password(p)):
            if not ok:
                self._msg(self.r_msg, "❌ " + msg)
                return
        if p != p2:
            self._msg(self.r_msg, "❌ The two passwords do not match.")
            return
        need = {"staff": config.STAFF_CODE, "admin": config.ADMIN_CODE}.get(role)
        if role in ("staff", "admin") and not need:
            self._msg(self.r_msg, "❌ Privileged account registration is currently disabled. Contact your system administrator.")
            return
        if need and self.r_code.text().strip() != need:
            self._msg(self.r_msg, f"❌ Invalid {role} access code.")
            return
        ok, msg = db.create_user(u, p, role, name, mail, monitor.local_device())
        if not ok:
            self._msg(self.r_msg, "❌ " + msg)
            return
        notifier.notify_activity(u, "Account created", "[SecureBank AI] Account created",
                                 "A SecureBank AI account was created for you. If you did not request this, "
                                 "contact your bank through an official support channel.")
        for w in (self.r_name, self.r_user, self.r_mail, self.r_pass, self.r_pass2, self.r_code):
            w.clear()
        self.r_msg.setText("")
        self.l_user.setText(u)
        self.l_role.setCurrentText(role.title())
        self.l_pass.clear()
        self._msg(self.l_msg, f"✅ Account '{u}' created. Please log in.", True)
        self.tabs.setCurrentIndex(0)
        self.l_pass.setFocus()


def excepthook(exc_type, exc, tb):
    text = "".join(traceback.format_exception(exc_type, exc, tb))
    log = os.path.join(config.DATA_DIR, "securebank_error.log")
    try:
        with open(log, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + text + "\n")
    except OSError:
        pass
    QMessageBox.critical(None, "Unexpected error", f"{exc}\n\nDetails were saved to:\n{log}")


def main():
    sys.excepthook = excepthook
    db.init_db()
    if sys.platform == "win32":
        import ctypes
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("OpenAI.SecureBankAI.Desktop.1")
        except Exception:
            pass
    app = QApplication(sys.argv)
    app.setWindowIcon(app_icon())
    app.setStyleSheet(make_style(THEMES["login"]))
    w = LoginWindow()
    w.showMaximized()
    w.raise_()
    w.activateWindow()
    w.fade_in()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
