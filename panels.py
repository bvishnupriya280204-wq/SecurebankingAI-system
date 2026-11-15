"""Reusable pages (panels) for the Staff and Admin consoles."""
import os
import shutil
from datetime import datetime, timedelta

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QGridLayout, QGroupBox,
                               QFrame, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget, QMessageBox,
                               QPushButton, QScrollArea, QTextEdit, QVBoxLayout, QWidget)

import accounts
import config
import database as db
import datasets
import logimport
import monitor
import notifier
from dialogs import CreateUserDialog
from ml_engine import engine
from simulator import Simulator
from ui_common import (BLUE, GREEN, ORANGE, PURPLE, RED, Card, Charts, attach_filter, feed_fill, fill_table,
                       make_table, pill, restore_selection, section, selected_key, status_style)

ACTIONS = {
    "BankShield": "1) Contact the account holder through a verified channel.<br>2) If the login is not recognised, "
                  "reset the password and disable the account.<br>3) Review other logins from the same IP/device.",
    "LeakGuard": "1) Review the user's recent downloads and sensitivity levels.<br>2) Suspend access to sensitive data."
                 "<br>3) Escalate to security / HR.<br>4) Preserve logs as evidence.",
    "CustomerReport": "1) Call the customer to confirm details.<br>2) Check their login history and devices."
                      "<br>3) Reset credentials if needed.",
    "Account": "Informational - an account change was recorded. No action is needed unless it was unexpected.",
}


def _count_label(text=""):
    lb = QLabel(text)
    lb.setObjectName("count")
    return lb


def _save_template(parent, text, default_name):
    path, _ = QFileDialog.getSaveFileName(parent, "Save CSV template", default_name, "CSV (*.csv)")
    if path:
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        QMessageBox.information(parent, "Template saved", f"Template saved to:\n{path}")


def _import_log_csv(panel, user, kind=None):
    """Shared CSV upload flow (auto-detects file-access vs login-event logs)."""
    path, _ = QFileDialog.getOpenFileName(panel, "Select log CSV", "", "CSV (*.csv)")
    if not path:
        return
    QApplication.setOverrideCursor(Qt.WaitCursor)
    try:
        s = logimport.import_csv(path, user["username"], kind)
        QApplication.restoreOverrideCursor()
        box = QMessageBox.warning if s["errors"] and not s["imported"] else QMessageBox.information
        box(panel, "Log import", logimport.summary_text(s))
        notifier.notify_activity(
            user["username"], "Security log import completed", "[SecureBank AI] Log import completed",
            f"Your {s['kind']}-event log import finished. {s['imported']} of {s['total']} rows were analyzed; "
            f"{s['high']} were HIGH risk, {s['medium']} were MEDIUM risk, and {len(s['errors'])} rows had errors.")
    except Exception as e:
        QApplication.restoreOverrideCursor()
        QMessageBox.critical(panel, "Upload failed", str(e))
        notifier.notify_activity(user["username"], "Security log import failed",
                                 "[SecureBank AI] Log import failed",
                                 f"A security-log import could not be completed: {str(e)[:240]}")
    panel.refresh()


class OverviewPanel(QWidget):
    def __init__(self, user, theme, admin=False):
        super().__init__()
        self.user, self.admin = user, admin
        self.sim_probe = lambda: False
        page = QVBoxLayout(self)
        page.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(20, 18, 20, 24)
        lay.setSpacing(16)

        hdr = QHBoxLayout()
        title_block = QVBoxLayout()
        self.hello = QLabel()
        self.hello.setObjectName("title")
        self.subtitle = QLabel(
            "Organization-wide posture, account risk, and security alerts" if admin else
            "A focused view of login risk, file activity, and alerts that need review")
        self.subtitle.setObjectName("subtitle")
        title_block.addWidget(self.hello)
        title_block.addWidget(self.subtitle)
        hdr.addLayout(title_block)
        hdr.addStretch(1)
        self.posture = QLabel()
        self.posture.setObjectName("statusBox")
        hdr.addWidget(self.posture)
        lay.addLayout(hdr)

        strip = QGridLayout()
        strip.setHorizontalSpacing(10)
        self.p_ml, self.p_mail, self.p_sim, self.p_roles = (QLabel() for _ in range(4))
        status_pills = (self.p_ml, self.p_mail, self.p_sim) + ((self.p_roles,) if admin else ())
        for col, p in enumerate(status_pills):
            strip.addWidget(p, 0, col)
            strip.setColumnStretch(col, 1)
        lay.addLayout(strip)

        cards = QHBoxLayout()
        cards.setSpacing(12)
        self.c_logins = Card("Login events", BLUE, "🔐")
        self.c_failed = Card("Failed logins", RED, "❌")
        self.c_files = Card("File events", PURPLE, "📁")
        self.c_high = Card("Open HIGH alerts", ORANGE, "🚨")
        self.c_hour = Card("Alerts (last hour)", "#00acc1", "⏱")
        self.c_users = Card("Registered users", GREEN, "👥")
        for c in (self.c_logins, self.c_failed, self.c_files, self.c_high, self.c_hour, self.c_users):
            cards.addWidget(c, 1)
        for c in (self.c_logins, self.c_failed, self.c_files, self.c_high, self.c_hour, self.c_users):
            c.setMinimumHeight(92)
        self.c_logins.setToolTip("Total login attempts analyzed by BankShield")
        self.c_failed.setToolTip("Login attempts rejected or marked as unsuccessful")
        self.c_files.setToolTip("File-access actions analyzed by LeakGuard")
        self.c_high.setToolTip("High-severity alerts that still need review")
        self.c_hour.setToolTip("Alerts generated during the previous hour")
        self.c_users.setToolTip("Accounts registered in the application")
        lay.addLayout(cards)

        chart_box = QGroupBox("BankShield and LeakGuard activity")
        chart_layout = QVBoxLayout(chart_box)
        chart_layout.setContentsMargins(12, 20, 12, 10)
        self.charts = Charts(theme["dark"], theme["chart"])
        self.charts.setMinimumHeight(430)
        chart_layout.addWidget(self.charts)
        lay.addWidget(chart_box)

        body = QHBoxLayout()
        body.setSpacing(14)
        alerts_box = QGroupBox("Latest alerts · newest first")
        alerts_layout = QVBoxLayout(alerts_box)
        self.feed = QListWidget()
        self.feed.setWordWrap(True)
        self.feed.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        alerts_layout.addWidget(self.feed)
        top_box = QGroupBox("Top risky accounts · by alert count")
        top_layout = QVBoxLayout(top_box)
        self.t_top = make_table(["Account", "Alerts", "Max risk"])
        self.t_top.setMinimumHeight(260)
        top_layout.addWidget(self.t_top)
        body.addWidget(alerts_box, 1)
        body.addWidget(top_box, 1)
        lay.addLayout(body, 1)
        lay.addStretch(1)
        scroll.setWidget(content)
        page.addWidget(scroll)

    def refresh(self):
        n = lambda sql, p=(): db.query(sql, p)[0]["n"]
        hour_ago = (datetime.now() - timedelta(hours=1)).isoformat(timespec="seconds")
        logins = db.query("SELECT * FROM login_events ORDER BY id DESC LIMIT 300")
        files = db.query("SELECT * FROM file_events ORDER BY id DESC LIMIT 300")
        self.hello.setText("📊 Administrator security overview" if self.admin else "📊 Staff security overview")
        open_high = n("SELECT COUNT(*) n FROM alerts WHERE severity='HIGH' AND status='Open'")
        if open_high == 0:
            self.posture.setText("🟢  All clear - no open HIGH alerts")
            self.posture.setStyleSheet(status_style("good"))
        elif open_high <= 3:
            self.posture.setText(f"🟠  {open_high} open HIGH alert(s) need attention")
            self.posture.setStyleSheet(status_style("warn"))
        else:
            self.posture.setText(f"🔴  Elevated threat level - {open_high} open HIGH alerts")
            self.posture.setStyleSheet(status_style("bad"))
        pill(self.p_ml, "🤖 ML models ready", "good")
        pill(self.p_mail, "📧 E-mail alerts ON" if config.email_configured() else "📧 E-mail not configured",
             "good" if config.email_configured() else "warn")
        pill(self.p_sim, "⚡ Live simulator running" if self.sim_probe() else "⚡ Simulator stopped",
             "good" if self.sim_probe() else "info")
        if self.admin:
            r = {x["role"]: x["n"] for x in db.query("SELECT role, COUNT(*) n FROM users GROUP BY role")}
            pill(self.p_roles, f"👥 {r.get('admin', 0)} admin · {r.get('staff', 0)} staff · {r.get('customer', 0)} customers",
                 "info")
        self.c_logins.set(n("SELECT COUNT(*) n FROM login_events"))
        self.c_failed.set(n("SELECT COUNT(*) n FROM login_events WHERE success=0"))
        self.c_files.set(n("SELECT COUNT(*) n FROM file_events"))
        self.c_high.set(open_high)
        self.c_hour.set(n("SELECT COUNT(*) n FROM alerts WHERE ts>=?", (hour_ago,)))
        self.c_users.set(n("SELECT COUNT(*) n FROM users"))
        sev = {r["severity"]: r["n"] for r in db.query("SELECT severity, COUNT(*) n FROM alerts GROUP BY severity")}
        src = {r["source"]: r["n"] for r in db.query("SELECT source, COUNT(*) n FROM alerts GROUP BY source")}
        hours = {}
        for r in db.query("SELECT hour, success, COUNT(*) n FROM login_events GROUP BY hour, success"):
            ok, bad = hours.get(r["hour"], (0, 0))
            hours[r["hour"]] = (ok + r["n"], bad) if r["success"] else (ok, bad + r["n"])
        self.charts.refresh(logins, files, sev, src, hours)
        feed_fill(self.feed, db.query("SELECT * FROM alerts ORDER BY id DESC LIMIT 12"))
        fill_table(self.t_top, db.query("SELECT username, COUNT(*) n, MAX(risk) m FROM alerts GROUP BY username "
                                        "ORDER BY n DESC LIMIT 6"), ["username", "n", "m"])


class LoginsPanel(QWidget):
    def __init__(self, user=None):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.addWidget(section("🛡 BankShield - login monitoring",
                              "Every login attempt with its ML risk score. Red = HIGH, amber = MEDIUM, green = LOW."))
        top = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔎  Search by user, device, country, level...")
        self.risky = QCheckBox("Only failed / risky")
        self.count = _count_label()
        self.user = user or {"username": "imported"}
        up = QPushButton("Upload login CSV")
        up.setObjectName("purple")
        up.setToolTip("Import login events (username, success/result, hour, device, ip, country) "
                      "and risk-score each one.")
        up.clicked.connect(lambda: _import_log_csv(self, self.user, "login"))
        tpl = QPushButton("CSV template")
        tpl.clicked.connect(lambda: _save_template(self, logimport.LOGIN_TEMPLATE, "login_events_template.csv"))
        top.addWidget(self.search, 1)
        top.addWidget(self.risky)
        top.addWidget(up)
        top.addWidget(tpl)
        top.addWidget(self.count)
        lay.addLayout(top)
        self.table = make_table(["Time", "User", "Result", "Hour", "Device", "Country", "Fail streak", "Risk", "Level"])
        self.apply = attach_filter(self.table, self.search)
        lay.addWidget(self.table)

    def refresh(self):
        rows = db.query("SELECT * FROM login_events ORDER BY id DESC LIMIT 500")
        total = len(rows)
        if self.risky.isChecked():
            rows = [r for r in rows if not r["success"] or r["verdict"] != "LOW"]
        for r in rows:
            r["result"] = "Success" if r["success"] else "Failed"
        fill_table(self.table, rows, ["ts", "username", "result", "hour", "device", "country", "failed_streak",
                                      "risk", "verdict"], "verdict")
        self.apply()
        self.count.setText(f"Showing {len(rows)} of last {total} events")


class FilesPanel(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        lay = QVBoxLayout(self)
        lay.addWidget(section("🔍 LeakGuard - file-access monitoring",
                              "Detects bulk downloads, unusual data transfers and risky file actions."))
        box = QGroupBox("Record a file access (as the current user) or upload a log CSV")
        form = QHBoxLayout(box)
        self.f_name = QLineEdit()
        self.f_name.setPlaceholderText("file name, e.g. loans_2026.xlsx")
        self.f_action = QComboBox()
        self.f_action.addItems(["View", "Edit", "Download", "Export", "Copy to USB", "Email External"])
        self.f_size = QDoubleSpinBox()
        self.f_size.setRange(0.01, 5000)
        self.f_size.setSuffix(" MB")
        self.f_size.setValue(2)
        self.f_sens = QComboBox()
        self.f_sens.addItems(["Public", "Internal", "Confidential", "Restricted"])
        go = QPushButton("Analyse & record")
        go.clicked.connect(self.log_file)
        up = QPushButton("Upload log CSV")
        up.setObjectName("purple")
        up.setToolTip("Accepts file-access logs AND login-event logs - the type is detected from the columns.")
        up.clicked.connect(self.upload_logs)
        tpl = QPushButton("CSV templates")
        tpl.setToolTip("Download an example CSV for file-access logs or login-event logs.")
        tpl.clicked.connect(self.templates)
        for x in (self.f_name, self.f_action, self.f_size, self.f_sens, go, up, tpl):
            form.addWidget(x)
        lay.addWidget(box)
        top = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔎  Search file events...")
        self.risky = QCheckBox("Only risky")
        self.count = _count_label()
        top.addWidget(self.search, 1)
        top.addWidget(self.risky)
        top.addWidget(self.count)
        lay.addLayout(top)
        self.table = make_table(["Time", "User", "File", "Action", "MB", "Sensitivity", "Files/10min", "MB/hour",
                                 "Risk", "Level"])
        self.apply = attach_filter(self.table, self.search)
        lay.addWidget(self.table)

    def refresh(self):
        rows = db.query("SELECT * FROM file_events ORDER BY id DESC LIMIT 500")
        total = len(rows)
        if self.risky.isChecked():
            rows = [r for r in rows if r["verdict"] != "LOW"]
        fill_table(self.table, rows, ["ts", "username", "filename", "action", "size_mb", "sensitivity",
                                      "files_last_10min", "mb_last_hour", "risk", "verdict"], "verdict")
        self.apply()
        self.count.setText(f"Showing {len(rows)} of last {total} events")

    def log_file(self):
        res = monitor.process_file(self.user["username"], self.f_name.text().strip() or "untitled.txt",
                                   self.f_action.currentText(), self.f_size.value(), self.f_sens.currentIndex())
        QMessageBox.information(self, "LeakGuard", f"Risk score {res['risk']} - {res['verdict']}")
        self.refresh()

    def upload_logs(self):
        _import_log_csv(self, self.user)

    def templates(self):
        kind, ok = QInputDialog.getItem(self, "CSV templates", "Which template do you need?",
                                        ["File-access log (LeakGuard)", "Login-event log (BankShield)"], 0, False)
        if not ok:
            return
        if kind.startswith("File"):
            _save_template(self, logimport.FILE_TEMPLATE, "file_access_template.csv")
        else:
            _save_template(self, logimport.LOGIN_TEMPLATE, "login_events_template.csv")


class AlertsPanel(QWidget):
    COLS = ["id", "ts", "source", "username", "severity", "risk", "status", "notified", "message"]

    def __init__(self, user=None):
        super().__init__()
        self.user = user or {}
        lay = QVBoxLayout(self)
        lay.addWidget(section("🔔 Alerts & reports", "Select an alert to see details and the recommended action."))
        bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔎  Search alerts...")
        self.f_sev = QComboBox()
        self.f_sev.addItems(["All severities", "HIGH", "MEDIUM", "LOW"])
        self.f_status = QComboBox()
        self.f_status.addItems(["Open + Resolved", "Open", "Resolved"])
        res = QPushButton("✔ Mark resolved")
        res.setObjectName("success")
        res.clicked.connect(self.resolve)
        self.exp = QComboBox()
        self.exp.addItems(["Alerts", "Login events", "File events", "Users"])
        exp = QPushButton("⬇ Export CSV")
        exp.setObjectName("purple")
        exp.clicked.connect(self.export)
        for x in (self.search, self.f_sev, self.f_status, res, self.exp, exp):
            bar.addWidget(x, 1 if x is self.search else 0)
        lay.addLayout(bar)
        self.count = _count_label()
        lay.addWidget(self.count)
        self.table = make_table(["ID", "Time", "Module", "User", "Severity", "Risk", "Status", "Notification",
                                 "Message"])
        self.apply = attach_filter(self.table, self.search)
        self.table.itemSelectionChanged.connect(self.show_detail)
        lay.addWidget(self.table, 3)
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setMaximumHeight(170)
        self.detail.setPlaceholderText("Select an alert above to see full details and recommended actions.")
        lay.addWidget(self.detail, 1)

    def refresh(self):
        keep = selected_key(self.table)
        where, params = [], []
        if self.f_sev.currentIndex() > 0:
            where.append("severity=?")
            params.append(self.f_sev.currentText())
        if self.f_status.currentIndex() > 0:
            where.append("status=?")
            params.append(self.f_status.currentText())
        rows = db.query("SELECT * FROM alerts" + (" WHERE " + " AND ".join(where) if where else "") +
                        " ORDER BY id DESC LIMIT 400", tuple(params))
        fill_table(self.table, rows, self.COLS, "severity")
        self.apply()
        restore_selection(self.table, 0, keep)
        self.count.setText(f"{len(rows)} alert(s) shown")

    def show_detail(self):
        aid = selected_key(self.table)
        if not aid:
            return
        rows = db.query("SELECT * FROM alerts WHERE id=?", (int(aid),))
        if not rows:
            return
        a = rows[0]
        self.detail.setHtml(
            f"<b>Alert #{a['id']}</b> &nbsp; {a['severity']} &nbsp;|&nbsp; {a['source']} &nbsp;|&nbsp; "
            f"account <b>{a['username']}</b> &nbsp;|&nbsp; risk {a['risk']} &nbsp;|&nbsp; {a['ts']} &nbsp;|&nbsp; "
            f"status {a['status']}<br><br><b>What happened</b><br>{a['message']}<br><br>"
            f"<b>Notification</b><br>{a['notified']}<br><br><b>Recommended action</b><br>"
            f"{ACTIONS.get(a['source'], 'Review the activity and confirm with the user.')}")

    def resolve(self):
        aid = selected_key(self.table)
        if not aid:
            QMessageBox.information(self, "Select a row", "Please click an alert first.")
            return
        rows = db.query("SELECT username, source FROM alerts WHERE id=?", (int(aid),))
        db.resolve_alert(int(aid))
        if rows:
            target = rows[0]["username"]
            notifier.notify_activity(target, "Security alert reviewed", "[SecureBank AI] Alert reviewed",
                                     f"Security alert #{aid} ({rows[0]['source']}) was reviewed and marked resolved.")
            actor = self.user.get("username")
            if actor and actor != target:
                notifier.notify_activity(actor, "Security alert resolved", "[SecureBank AI] Alert resolved",
                                         f"You marked alert #{aid} for account {target} as resolved.")
        self.refresh()

    def export(self):
        sql = {"Alerts": "SELECT * FROM alerts", "Login events": "SELECT * FROM login_events",
               "File events": "SELECT * FROM file_events",
               "Users": "SELECT username, full_name, role, email, created_at, disabled FROM users"}[
            self.exp.currentText()]
        path, _ = QFileDialog.getSaveFileName(self, "Save report", "securebank_report.csv", "CSV (*.csv)")
        if path:
            pd.DataFrame(db.query(sql)).to_csv(path, index=False)
            if self.user.get("username"):
                notifier.notify_activity(self.user["username"], "Security report exported",
                                         "[SecureBank AI] Security report exported",
                                         f"You exported a {self.exp.currentText().lower()} report from SecureBank AI.")
            QMessageBox.information(self, "Report", f"Saved to {path}")


class UsersPanel(QWidget):
    """mode='staff': customers only, can disable/enable and reset password.
    mode='admin': all accounts, plus create user, change role, delete."""

    def __init__(self, user, mode="staff"):
        super().__init__()
        self.user, self.mode = user, mode
        lay = QVBoxLayout(self)
        lay.addWidget(section("👥 User management" if mode == "admin" else "👥 Customer accounts",
                              "Select a row, then use a button. You cannot change your own account here."))
        row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔎  Search users...")
        row.addWidget(self.search, 1)
        buttons = [("⛔ Disable / Enable", "warn", self.toggle), ("🔑 Reset password", None, self.reset_pw)]
        if mode == "admin":
            buttons = [("➕ Create user", "success", self.create)] + buttons + [
                ("🎭 Change role", "purple", self.change_role), ("🗑 Delete", "danger", self.delete)]
        for text, name, fn in buttons:
            b = QPushButton(text)
            if name:
                b.setObjectName(name)
            b.clicked.connect(fn)
            row.addWidget(b)
        lay.addLayout(row)
        self.count = _count_label()
        lay.addWidget(self.count)
        self.table = make_table(["Username", "Name", "Role", "E-mail", "E-mail alerts",
                                 "Status", "Last login", "Failed"])
        self.apply = attach_filter(self.table, self.search)
        lay.addWidget(self.table)

    def refresh(self):
        keep = selected_key(self.table)
        users = db.users_summary()
        if self.mode == "staff":
            users = [u for u in users if u["role"] == "customer"]
        for u in users:
            u["status"] = "Disabled" if u["disabled"] else "Active"
            u["em"] = "ON" if u["notify_email"] else "off"
        fill_table(self.table, users, ["username", "full_name", "role", "email", "em", "status",
                                       "last_login", "failed"])
        self.apply()
        restore_selection(self.table, 0, keep)
        self.count.setText(f"{len(users)} account(s)")

    def _target(self):
        u = selected_key(self.table)
        if not u:
            QMessageBox.information(self, "Select a user", "Please click a user row first.")
            return None
        if u == self.user["username"]:
            QMessageBox.warning(self, "Not allowed", "You cannot do this to your own account.")
            return None
        return u

    def _account_notice(self, target, action, target_message):
        """Notify the affected account and the staff/admin who initiated the change."""
        notifier.notify_activity(target, action, f"[SecureBank AI] {action}", target_message)
        actor = self.user.get("username")
        if actor and actor != target:
            notifier.notify_activity(actor, f"Account action: {action}", f"[SecureBank AI] {action} recorded",
                                     f"You performed this account action for {target}.")

    def toggle(self):
        u = self._target()
        if u:
            disabled = not bool(db.get_user(u).get("disabled"))
            db.set_disabled(u, disabled)
            state = "disabled" if disabled else "re-enabled"
            self._account_notice(u, f"Account {state}",
                                 f"Your account was {state} by authorized bank staff. Contact your bank through "
                                 "an official support channel if you did not expect this change.")
            self.refresh()

    def reset_pw(self):
        u = self._target()
        if u:
            temp = accounts.temp_password()
            db.set_password(u, temp)
            self._account_notice(u, "Password reset by bank staff",
                                 "Your account password was reset by authorized bank staff. Obtain the temporary "
                                 "password through the bank's approved secure channel and change it after signing in.")
            QMessageBox.information(self, "Password reset", f"Temporary password for '{u}':\n\n{temp}\n\n"
                                    "Give it to the user and ask them to change it after login.")

    def create(self):
        if CreateUserDialog(self).exec():
            self.refresh()

    def change_role(self):
        u = self._target()
        if u:
            role, ok = QInputDialog.getItem(self, "Change role", f"New role for '{u}':",
                                            ["customer", "staff", "admin"], 0, False)
            if ok:
                old_role = db.get_user(u).get("role")
                db.set_role(u, role)
                if old_role != role:
                    self._account_notice(u, "Account role changed",
                                         f"Your SecureBank AI account role was changed from {old_role} to {role} "
                                         "by an administrator.")
                self.refresh()

    def delete(self):
        u = self._target()
        if u and QMessageBox.question(self, "Delete user", f"Permanently delete '{u}'?") == QMessageBox.Yes:
            self._account_notice(u, "Account deletion requested",
                                 "Your SecureBank AI account was deleted by authorized bank staff. Contact the bank "
                                 "through an official support channel if you believe this was an error.")
            db.delete_user(u)
            self.refresh()


class LivePanel(QWidget):
    def __init__(self, admin_mode=False, current_user=None):
        super().__init__()
        self.sim, self._oneshots = None, []
        self.admin_mode = bool(admin_mode)
        self.current_user = current_user or {}
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(20, 18, 20, 22)
        lay.setSpacing(14)
        subtitle = ("Review current model quality and run controlled scenarios. Generated events are marked as "
                    "synthetic." if self.admin_mode else
                    "Monitor controlled test traffic and review how the security models perform.")
        heading = section("⚡ Live ML & security validation", subtitle)
        heading_subtitle = heading.findChild(QLabel, "sectionSub")
        if heading_subtitle:
            heading_subtitle.setWordWrap(True)
        lay.addWidget(heading)

        controls = QGroupBox("Controlled validation")
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(14, 18, 14, 14)
        row = QGridLayout()
        row.setSpacing(10)
        self.btn = QPushButton("▶ Start test traffic")
        self.btn.setObjectName("success")
        self.btn.setToolTip("Continuously generates a mix of normal and suspicious logins/file activity "
                            "so you can watch the ML models score events live. Click again to stop.")
        self.btn.clicked.connect(self.toggle)
        self.btn.setFixedHeight(44)
        self.btn.setMinimumWidth(0)
        scenario_buttons = []
        for text, mode, name, tip in (
                ("Brute-force test", "brute", "danger",
                 "Simulates one account receiving 6 rapid failed logins from a foreign device, "
                 "sometimes followed by a success. Expected result: a HIGH BankShield alert."),
                ("Unusual-location test", "foreign", "warn",
                 "Simulates a successful login at an odd hour from an unknown device in a high-risk country. "
                 "Expected result: a MEDIUM/HIGH BankShield alert."),
                ("Bulk-download test", "bulk", "purple",
                 "Simulates 25 large Restricted-file downloads in a few seconds by your account. "
                 "Expected result: a HIGH LeakGuard alert.")):
            b = QPushButton(text)
            b.setObjectName(name)
            b.setToolTip(tip)
            b.setFixedHeight(44)
            b.setMinimumWidth(0)
            b.clicked.connect(lambda checked=False, m=mode: self.scenario(m))
            scenario_buttons.append(b)
        imp = QPushButton("📥 BankShield · Import RBA")
        imp.setFixedHeight(44)
        imp.setMinimumWidth(0)
        imp.setToolTip("Retrain the BankShield login model on a real Risk-Based Authentication (RBA) dataset CSV "
                       "(Wiefling et al.) instead of only the built-in synthetic data.")
        imp.clicked.connect(self.import_rba)
        leak_imp = QPushButton("📥 LeakGuard · Import CSV")
        leak_imp.setObjectName("purple")
        leak_imp.setFixedHeight(44)
        leak_imp.setMinimumWidth(0)
        leak_imp.setToolTip("Upload spedia_leakguard_compatible.csv or another labelled LeakGuard CSV. "
                            "This updates LeakGuard only; BankShield and its RBA model remain unchanged.")
        leak_imp.clicked.connect(self.import_leakguard)
        if self.admin_mode:
            row.addWidget(self.btn, 0, 0)
            row.addWidget(imp, 0, 1)
            row.addWidget(leak_imp, 0, 2)
            for col, button in enumerate(scenario_buttons):
                row.addWidget(button, 1, col)
            for col in range(3):
                row.setColumnStretch(col, 1)
        else:
            row.addWidget(self.btn, 0, 0)
            row.addWidget(imp, 0, 1)
            row.addWidget(leak_imp, 0, 2)
            for col, button in enumerate(scenario_buttons):
                row.addWidget(button, 1, col)
            for col in range(3):
                row.setColumnStretch(col, 1)
        controls_layout.addLayout(row)
        guide = QLabel("Start the controlled simulator to stream scored events. Authorized staff and admins can run "
                       "the scenario buttons for specific validation cases. The RBA import retrains BankShield; "
                       "the separate LeakGuard import "
                       "re-trains only LeakGuard. Use spedia_leakguard_compatible.csv for the converted SPEDIA data.")
        guide.setWordWrap(True)
        guide.setObjectName("hint")
        controls_layout.addWidget(guide)
        lay.addWidget(controls)

        self.eval_box = eval_box = QGroupBox("Model evaluation · held-out test data")
        eval_layout = QVBoxLayout(eval_box)
        eval_layout.setContentsMargins(14, 18, 14, 14)
        self.metrics = QLabel()
        self.metrics.setWordWrap(True)
        self.metrics.setObjectName("hint")
        eval_layout.addWidget(self.metrics)
        self.metric_grid = QGridLayout()
        self.metric_grid.setHorizontalSpacing(12)
        self.metric_grid.setVerticalSpacing(10)
        self.metric_values = {}
        colors = (BLUE, GREEN, PURPLE, ORANGE)
        names = ("BankShield · login risk", "LeakGuard · file activity")
        for col, name in enumerate(names):
            group = QGroupBox(name)
            grid = QGridLayout(group)
            grid.setContentsMargins(10, 14, 10, 10)
            for idx, key in enumerate(("accuracy", "precision", "recall", "f1", "roc_auc")):
                tile = QFrame()
                tile.setObjectName("metricTile")
                tile.setStyleSheet(f"QFrame#metricTile {{ background:rgba(37,99,160,18); border:1px solid rgba(85,140,190,80); border-radius:8px; }}")
                tile_layout = QVBoxLayout(tile)
                tile_layout.setContentsMargins(10, 8, 10, 8)
                label = QLabel(key.replace("roc_auc", "ROC-AUC").replace("_", " ").title())
                label.setObjectName("hint")
                value = QLabel("—")
                value.setStyleSheet(f"font-size:19px; font-weight:800; color:{colors[idx % len(colors)]}; background:transparent;")
                tile_layout.addWidget(label)
                tile_layout.addWidget(value)
                grid.addWidget(tile, idx // 3, idx % 3)
                self.metric_values[(col, key)] = value
            rows = QHBoxLayout()
            sample = QLabel("Evaluation rows: —")
            sample.setObjectName("hint")
            rows.addWidget(sample)
            rows.addStretch(1)
            grid.addLayout(rows, 2, 0, 1, 3)
            self.metric_values[(col, "rows_label")] = sample
            self.metric_grid.addWidget(group, col, 0)
        self.metric_grid.setColumnStretch(0, 1)
        eval_layout.addLayout(self.metric_grid)
        lay.addWidget(eval_box)

        stream_box = QGroupBox("Live event stream")
        stream_layout = QVBoxLayout(stream_box)
        stream_layout.setContentsMargins(12, 16, 12, 12)
        self.live = QListWidget()
        self.live.setMinimumHeight(180)
        self.live.setAlternatingRowColors(True)
        self.live.addItem("No live events yet · start controlled test traffic to see scored activity here.")
        stream_layout.addWidget(self.live)
        lay.addWidget(stream_box, 1)
        self.show_metrics()
        lay.addStretch(1)
        self.scroll_area.setWidget(content)
        outer.addWidget(self.scroll_area)

    def running(self):
        return bool(self.sim and self.sim.isRunning())

    def refresh(self):
        self.show_metrics()

    def show_metrics(self):
        m = engine.metrics
        self.metrics.setText(
            f"BankShield: {m['login'].get('evaluation', 'current model')}  ·  "
            f"LeakGuard: {m['file'].get('evaluation', 'current model')}\n"
            "Metrics use held-out evaluation rows and describe the supplied data; they are not a guarantee of "
            "real-world bank performance.")
        for col, key in enumerate(("login", "file")):
            model = m[key]
            for metric in ("accuracy", "precision", "recall", "f1", "roc_auc"):
                self.metric_values[(col, metric)].setText(f"{model[metric] * 100:.1f}%")
            bal = model.get("balanced_accuracy")
            bal_text = f" · Balanced accuracy: {bal * 100:.1f}%" if bal is not None else ""
            self.metric_values[(col, "rows_label")].setText(
                f"Evaluation rows: {model.get('test_rows', 0):,}{bal_text}")

    def on_event(self, text):
        if self.live.count() == 1 and self.live.item(0).text().startswith("No live events yet"):
            self.live.clear()
        self.live.insertItem(0, text)
        while self.live.count() > 200:
            self.live.takeItem(200)

    def toggle(self):
        if self.running():
            self.sim.stop()
            self.sim.wait(5000)
            self.sim = None
            self.btn.setText("▶ Start test traffic")
            action = "Controlled simulator stopped"
        else:
            self.sim = Simulator()
            self.sim.event.connect(self.on_event)
            self.sim.start()
            self.btn.setText("■ Stop test traffic")
            action = "Controlled simulator started"
        actor = self.current_user.get("username") if self.admin_mode else None
        if actor:
            notifier.notify_activity(actor, action, f"[SecureBank AI] {action}",
                                     f"You {action.lower()} in the administrator console. Synthetic events are "
                                     "recorded for demonstration; they do not generate emails for simulated users.")

    def scenario(self, mode):
        actor = self.current_user.get("username")
        t = Simulator(mode, actor_username=actor)
        t.event.connect(self.on_event)
        self._oneshots = [x for x in self._oneshots if x.isRunning()] + [t]
        t.start()
        actor = self.current_user.get("username") if self.admin_mode else None
        if actor:
            notifier.notify_activity(actor, "Security validation scenario started",
                                     "[SecureBank AI] Validation scenario started",
                                     f"You started the {mode} validation scenario. Generated events are synthetic "
                                     "and are recorded without sending mail to the simulated account.")

    def import_rba(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select RBA dataset CSV", "", "CSV (*.csv)")
        if not path:
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            df = datasets.load_rba(path)
            if df["y"].nunique() < 2:
                raise ValueError("The loaded rows contain no attack labels. Use a different slice of the file.")
            engine.train_login(df)
            self.show_metrics()
            QMessageBox.information(self, "Retrained", f"BankShield login model retrained on {len(df):,} RBA "
                                    f"login records ({int(df['y'].sum()):,} labelled attack records).\n"
                                    "This public research dataset is synthesized; updated metrics are shown on this page.")
            self.scroll_area.ensureWidgetVisible(self.eval_box, 0, 12)
        except Exception as e:
            QMessageBox.critical(self, "Import failed", f"{e}\n\nThe file must be the RBA dataset CSV (columns such as User ID, Login Timestamp, User-Agent String, Country, Login Successful, Attack IP, Account Takeover).")
        finally:
            QApplication.restoreOverrideCursor()

    def import_leakguard(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select labelled LeakGuard CSV", "", "CSV (*.csv)")
        if not path:
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            df = datasets.load_leakguard(path)
            engine.train_file(df)
            filename = os.path.basename(path).lower()
            is_spedia = filename == "spedia_leakguard_compatible.csv"
            data_source = ("SPEDIA converted file events · general anomaly labels" if is_spedia else
                           f"{os.path.basename(path)} · labelled file-activity data")
            engine.metrics["file"]["evaluation"] = f"stratified hold-out; {data_source}"
            note = ("SPEDIA's Anomaly label means general anomalous activity, not confirmed data exfiltration. "
                    "Its sensitivity column is a placeholder; metrics describe this dataset only."
                    if is_spedia else
                    "Metrics describe the uploaded dataset and are not a guarantee of real-bank performance.")
            self.show_metrics()
            QMessageBox.information(
                self, "LeakGuard retrained",
                f"LeakGuard was retrained on {len(df):,} labelled file-activity rows "
                f"({int(df['y'].sum()):,} suspicious, {int((df['y'] == 0).sum()):,} normal).\n"
                f"Updated LeakGuard metrics are shown on this page. {note}\n"
                "BankShield was not changed. Training data is kept in memory for this app session.")
            self.scroll_area.ensureWidgetVisible(self.eval_box, 0, 12)
        except Exception as e:
            QMessageBox.critical(
                self, "LeakGuard import failed",
                f"{e}\n\nRequired columns: hour, size_mb, files_last_10min, mb_last_hour, "
                "sensitivity, is_download, and y (0=normal, 1=suspicious).")
        finally:
            QApplication.restoreOverrideCursor()

    def stop_all(self):
        for t in [self.sim] + self._oneshots:
            if t and t.isRunning():
                t.stop()
                t.wait(5000)


class SystemPanel(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        lay = QHBoxLayout(self)
        left = QVBoxLayout()
        box = QGroupBox("📧 E-mail notification service (Gmail)")
        bl = QVBoxLayout(box)
        self.status = QLabel()
        self.status.setWordWrap(True)
        bl.addWidget(self.status)
        test_mail = QPushButton("📧 Send test e-mail to me + security team")
        test_mail.clicked.connect(self.test)
        bl.addWidget(test_mail)
        self.mail_note = QLabel("Set SB_SMTP_USER and SB_SMTP_APP_PASSWORD in the private .env file, shown below, "
                                "then restart the application. Never share the app password.")
        self.mail_note.setWordWrap(True)
        self.mail_note.setObjectName("hint")
        bl.addWidget(self.mail_note)
        left.addWidget(box)
        box2 = QGroupBox("⚙ Security policy & session controls")
        b2 = QVBoxLayout(box2)
        self.cfg = QLabel()
        self.cfg.setWordWrap(True)
        b2.addWidget(self.cfg)
        left.addWidget(box2)
        lay.addLayout(left, 3)

        box3 = QGroupBox("💾 Data & maintenance")
        b3 = QVBoxLayout(box3)
        for text, fn, name in (("💾 Back up database", self.backup, "success"),
                               ("🧹 Clear all events & alerts (keep users)", self.clear, "danger")):
            b = QPushButton(text)
            b.setObjectName(name)
            b.clicked.connect(fn)
            b3.addWidget(b)
        self.dbinfo = QLabel()
        self.dbinfo.setWordWrap(True)
        b3.addWidget(self.dbinfo)
        b3.addStretch()
        lay.addWidget(box3, 2)

    def refresh(self):
        yes, no = "✅ configured", "❌ NOT configured"
        self.status.setText(
            f"<b>Gmail sender:</b> {config.SMTP_USER or '-'} &nbsp; {yes if config.email_configured() else no}<br>"
            f"<b>Security team e-mail:</b> {config.SECURITY_TEAM_EMAIL or '-'}<br>"
            f"<b>.env file:</b> {os.path.join(config.DATA_DIR, '.env')}")
        self.cfg.setText(f"MEDIUM risk ≥ {config.MEDIUM_RISK} &nbsp;|&nbsp; HIGH risk ≥ {config.HIGH_RISK}<br>"
                         f"Account lock after {config.LOCKOUT_FAILS} failed logins for {config.LOCKOUT_SECONDS}s<br>"
                         "Live routine sign-ins and low-risk file events notify the account owner by e-mail.<br>"
                         "Suspicious file events are routed to admins/security, not the potentially involved account.<br>"
                         f"Idle auto-logout: {config.IDLE_TIMEOUT}s")
        size = os.path.getsize(config.DB_PATH) / 1024 if os.path.exists(config.DB_PATH) else 0
        self.dbinfo.setText(f"Database: {config.DB_PATH}<br>Size: {size:.0f} KB")

    def test(self):
        me = db.get_user(self.user["username"])
        emails = sorted({e for e in (me.get("email"), config.SECURITY_TEAM_EMAIL) if e})
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            res = notifier.send_now(emails, "SecureBank AI - test message",
                                    "This is a test message from SecureBank AI. "
                                    "If you can read this, e-mail alert delivery works.")
        finally:
            QApplication.restoreOverrideCursor()
        QMessageBox.information(self, "Test result", f"E-MAIL: {res['email']}")

    def backup(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save backup", "securebank_backup.db", "SQLite (*.db)")
        if path:
            shutil.copy(config.DB_PATH, path)
            QMessageBox.information(self, "Backup", f"Database copied to {path}")

    def clear(self):
        if QMessageBox.question(self, "Clear data", "Delete ALL login events, file events and alerts?\n"
                                "User accounts are kept.") == QMessageBox.Yes:
            db.clear_activity()
            QMessageBox.information(self, "Done", "Activity data cleared.")
