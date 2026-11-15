"""Customer portal - friendly teal theme."""
import pandas as pd
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (QCheckBox, QFileDialog, QGroupBox, QHBoxLayout, QInputDialog, QLabel, QLineEdit,
                               QListWidget, QMessageBox, QProgressBar, QPushButton, QTabWidget, QTextEdit,
                               QVBoxLayout, QWidget)

import config
import database as db
import monitor
import notifier
from dialogs import NotificationTab, ProfileTab
from themes import THEMES
from ui_common import (BLUE, GREEN, ORANGE, RED, Card, DashboardBase, MiniChart, attach_filter, banner, fill_table,
                       make_table, restore_selection, section, selected_key, status_style)


class CustomerDashboard(DashboardBase):
    def __init__(self, user, login_window):
        super().__init__(user, login_window, THEMES["customer"])
        self.setWindowTitle("SecureBank AI - Customer Portal")
        self.resize(1100, 740)
        root = QWidget(); root.setObjectName("root"); self.setCentralWidget(root)
        lay = QVBoxLayout(root)
        b = banner(f"{self.greeting()}, {user['full_name'] or user['username']} 👋",
                   "Customer Portal  •  your login activity, devices and security alerts",
                   f"👤 {user['username']}  |  Customer")
        b.logout_btn.clicked.connect(lambda: self.logout())
        lay.addWidget(b)
        self.tabs = QTabWidget(); lay.addWidget(self.tabs)

        ov = QWidget(); ol = QVBoxLayout(ov)
        ol.setContentsMargins(14, 12, 14, 16)
        ol.setSpacing(14)
        ol.addWidget(section("Your security at a glance",
                             "A clear summary of sign-ins, trusted devices, and alerts for your account."))
        self.status = QLabel(); self.status.setObjectName("statusBox"); self.status.setWordWrap(True)
        self.status.setMinimumHeight(48)
        ol.addWidget(self.status)
        cards = QHBoxLayout()
        cards.setSpacing(12)
        self.c_ok = Card("Successful logins", BLUE, "✅")
        self.c_fail = Card("Failed attempts", RED, "⚠️")
        self.c_dev = Card("Trusted devices", GREEN, "💻")
        self.c_alerts = Card("Security alerts", ORANGE, "🔔")
        for c in (self.c_ok, self.c_fail, self.c_dev, self.c_alerts):
            c.setMinimumHeight(102)
            cards.addWidget(c)
        ol.addLayout(cards)

        mid = QHBoxLayout()
        left = QVBoxLayout()
        self.mini = MiniChart(self.theme["accent"]); self.mini.setMinimumHeight(210); left.addWidget(self.mini)
        left.addWidget(section("🕒 Recent activity", "The latest sign-ins and security alerts on your account."))
        self.activity = QListWidget(); self.activity.setMinimumHeight(210); left.addWidget(self.activity)
        mid.addLayout(left, 3)

        right = QVBoxLayout()
        sc = QGroupBox("🛡 My security score")
        sl = QVBoxLayout(sc)
        self.score = QProgressBar(); self.score.setRange(0, 100); self.score.setFormat("Security score  %v / 100")
        self.score.setMinimumHeight(26)
        self.checklist = QLabel(); self.checklist.setWordWrap(True)
        sl.addWidget(self.score); sl.addWidget(self.checklist)
        right.addWidget(sc)
        qa = QGroupBox("⚡ Quick actions")
        ql = QVBoxLayout(qa)
        for text, name, fn in (("🔔  Set up e-mail alerts", None, lambda: self.go(self.notif_tab)),
                               ("🔒  Change my password", "purple", lambda: self.go(self.profile_tab)),
                               ("🚩  Report suspicious activity", "warn", self.report)):
            btn = QPushButton(text)
            btn.setMinimumHeight(40)
            if name:
                btn.setObjectName(name)
            btn.clicked.connect(fn)
            ql.addWidget(btn)
        right.addWidget(qa)
        tips = QLabel("💡 Never share your password or OTP. Banks never ask for them by phone or e-mail.")
        tips.setWordWrap(True); tips.setObjectName("hint")
        right.addWidget(tips); right.addStretch()
        mid.addLayout(right, 2)
        ol.addLayout(mid, 1)
        self.tabs.addTab(ov, "🏠  Overview")

        w = QWidget(); wl = QVBoxLayout(w)
        wl.addWidget(section("📜 My login activity", "Every attempt on your account, with the risk score we calculated."))
        top = QHBoxLayout()
        self.e_logins = QLineEdit(); self.e_logins.setPlaceholderText("🔎  Search my activity...")
        self.only_fail = QCheckBox("Only failed / risky")
        dl = QPushButton("⬇ Download my history (CSV)"); dl.setObjectName("purple"); dl.clicked.connect(self.download)
        self.count = QLabel(); self.count.setObjectName("count")
        top.addWidget(self.e_logins, 1); top.addWidget(self.only_fail); top.addWidget(self.count); top.addWidget(dl)
        wl.addLayout(top)
        self.t_logins = make_table(["Time", "Result", "Device", "IP", "Country", "Risk", "Level"])
        self.f_logins = attach_filter(self.t_logins, self.e_logins)
        wl.addWidget(self.t_logins)
        self.tabs.addTab(w, "📜  Activity")

        w = QWidget(); wl = QVBoxLayout(w)
        wl.addWidget(section("💻 Trusted devices", "Devices that logged in successfully. Don't recognise one? "
                                                   "Change your password and report it."))
        self.t_dev = make_table(["Device", "Country", "Successful logins", "Last seen"])
        wl.addWidget(self.t_dev)
        self.tabs.addTab(w, "💻  Devices")

        w = QWidget(); wl = QVBoxLayout(w)
        wl.addWidget(section("🔔 My security alerts", "Select an alert to see what to do."))
        self.t_alerts = make_table(["ID", "Time", "Severity", "Status", "Sent via", "Message"])
        self.t_alerts.itemSelectionChanged.connect(self.show_alert)
        wl.addWidget(self.t_alerts, 3)
        self.detail = QTextEdit(); self.detail.setReadOnly(True); self.detail.setMaximumHeight(150)
        self.detail.setPlaceholderText("Select an alert above for details.")
        wl.addWidget(self.detail, 1)
        self.tabs.addTab(w, "🔔  Alerts")

        self.notif_tab = NotificationTab(user)
        self.tabs.addTab(self.notif_tab, "📬  Notifications")
        self.profile_tab = ProfileTab(user)
        self.tabs.addTab(self.profile_tab, "⚙️  Profile & Settings")
        self.tabs.currentChanged.connect(lambda _i: self._tab_changed())

        self.timer = QTimer(self); self.timer.timeout.connect(self.refresh); self.timer.start(4000)
        self.refresh()

    def go(self, widget):
        self.tabs.setCurrentWidget(widget)

    def _tab_changed(self):
        w = self.tabs.currentWidget()
        if w is self.notif_tab:
            self.notif_tab.refresh()

    def refresh(self):
        u = self.user["username"]
        me = db.get_user(u) or self.user
        logins = db.query("SELECT * FROM login_events WHERE username=? ORDER BY id DESC LIMIT 200", (u,))
        alerts = db.query("SELECT * FROM alerts WHERE username=? ORDER BY id DESC LIMIT 100", (u,))
        devices = db.query("SELECT device, country, COUNT(*) n, MAX(ts) last_seen FROM login_events "
                           "WHERE username=? AND success=1 GROUP BY device, country ORDER BY last_seen DESC", (u,))
        for r in logins:
            r["result"] = "Success" if r["success"] else "Failed"
        shown = [r for r in logins if not self.only_fail.isChecked() or not r["success"] or r["verdict"] != "LOW"]
        fill_table(self.t_logins, shown, ["ts", "result", "device", "ip", "country", "risk", "verdict"], "verdict")
        self.f_logins()
        self.count.setText(f"{len(shown)} event(s)")
        keep = selected_key(self.t_alerts)
        fill_table(self.t_alerts, alerts, ["id", "ts", "severity", "status", "notified", "message"], "severity")
        restore_selection(self.t_alerts, 0, keep)
        fill_table(self.t_dev, devices, ["device", "country", "n", "last_seen"])
        self.c_ok.set(sum(1 for r in logins if r["success"]))
        self.c_fail.set(sum(1 for r in logins if not r["success"]))
        self.c_dev.set(len(devices))
        self.c_alerts.set(len(alerts))

        open_high = any(a["severity"] == "HIGH" and a["status"] != "Resolved" for a in alerts)
        if open_high:
            self.status.setText("🚨  ATTENTION: suspicious activity was detected on your account. If this was not you, "
                                "change your password now and contact the bank.")
            self.status.setStyleSheet(status_style("bad"))
        else:
            self.status.setText("✅  Your account looks safe. No unresolved high-risk activity.")
            self.status.setStyleSheet(status_style("good"))

        items = [("E-mail address registered", bool(me.get("email"))),
                 ("E-mail alerts switched on", bool(me.get("notify_email"))),
                 ("No unresolved high-risk alerts", not open_high)]
        score = int(100 * sum(ok for _, ok in items) / len(items))
        self.score.setValue(score)
        color = GREEN if score >= 80 else ORANGE if score >= 60 else RED
        self.score.setStyleSheet(f"QProgressBar::chunk {{ background: {color}; border-radius: 7px; }}")
        self.checklist.setText("<br>".join(f"{'✅' if ok else '❌'} {t}" for t, ok in items))

        feed = [(r["ts"], f"{'✅' if r['success'] else '❌'}  {r['ts'][5:16]}  Login {r['result']} from {r['device']} "
                          f"({r['country']}) - risk {r['risk']}") for r in logins[:8]]
        feed += [(a["ts"], f"🔔  {a['ts'][5:16]}  {a['severity']} alert: {a['message'][:80]}") for a in alerts[:8]]
        self.activity.clear()
        for _, text in sorted(feed, reverse=True)[:8]:
            self.activity.addItem(text)
        self.mini.refresh([r["risk"] for r in reversed(logins[:40])])

    def show_alert(self):
        aid = selected_key(self.t_alerts)
        if not aid:
            return
        a = db.query("SELECT * FROM alerts WHERE id=?", (int(aid),))
        if a:
            a = a[0]
            self.detail.setHtml(f"<b>{a['severity']} alert</b> - {a['ts']}<br><br>{a['message']}<br><br>"
                                f"<b>Sent via:</b> {a['notified']}<br><br><b>What should I do?</b><br>"
                                "If this was you, no action is needed. If not: change your password (Profile & "
                                "Settings), review Trusted Devices and press 'Report suspicious activity'.")

    def download(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save my history", "my_login_history.csv", "CSV (*.csv)")
        if path:
            pd.DataFrame(db.query("SELECT ts,success,device,ip,country,risk,verdict FROM login_events "
                                  "WHERE username=? ORDER BY id DESC", (self.user["username"],))).to_csv(path, index=False)
            QMessageBox.information(self, "Saved", f"History saved to {path}")

    def report(self):
        text, ok = QInputDialog.getMultiLineText(self, "Report suspicious activity",
                                                 "Describe what looks wrong (e.g. a login you do not recognise):")
        if ok and text.strip():
            monitor.raise_alert("CustomerReport", self.user["username"], 55,
                                f"Customer report: {text.strip()[:300]}", notify_user=False)
            notifier.notify_activity(self.user["username"], "Suspicious activity report",
                                     "[SecureBank AI] Suspicious activity report received",
                                     "We received your security report and routed it to the security team.")
            QMessageBox.information(self, "Report sent", "Thank you. The security team has been notified.")
            self.refresh()
