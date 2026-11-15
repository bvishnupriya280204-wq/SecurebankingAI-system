"""Staff (security analyst) console - indigo theme."""
from dialogs import NotificationTab, ProfileTab
from panels import AlertsPanel, FilesPanel, LivePanel, LoginsPanel, OverviewPanel, UsersPanel
from themes import THEMES
from ui_common import ConsoleBase


class StaffDashboard(ConsoleBase):
    def __init__(self, user, login_window):
        super().__init__(user, login_window, THEMES["staff"],
                         f"Security Analyst Console - {user['full_name'] or user['username']}",
                         "BankShield + LeakGuard  •  real-time threat monitoring", f"🧑‍💼 {user['username']}  |  Staff")
        self.setWindowTitle("SecureBank AI - Staff Console")
        self.resize(1260, 820)
        self.live = LivePanel(admin_mode=False)
        self.overview = OverviewPanel(user, self.theme)
        self.overview.sim_probe = self.live.running
        for w, name in ((self.overview, "📊  Overview"), (LoginsPanel(user), "🛡  BankShield"),
                        (FilesPanel(user), "🔍  LeakGuard"), (AlertsPanel(user), "🔔  Alerts"),
                        (UsersPanel(user, "staff"), "👥  Customers"), (self.live, "⚡  Live Monitor"),
                        (NotificationTab(user), "📬  Notifications"), (ProfileTab(user), "⚙️  My Profile")):
            self.tabs.addTab(w, name)
        self.refresh_current()

    def cleanup(self):
        self.live.stop_all()
