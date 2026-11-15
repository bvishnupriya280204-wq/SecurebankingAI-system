"""Administrator console - dark crimson/amber theme."""
from dialogs import NotificationTab, ProfileTab
from panels import (AlertsPanel, FilesPanel, LivePanel, LoginsPanel, OverviewPanel, SystemPanel, UsersPanel)
from themes import THEMES
from ui_common import ConsoleBase


class AdminDashboard(ConsoleBase):
    def __init__(self, user, login_window):
        super().__init__(user, login_window, THEMES["admin"],
                         f"Administrator Control Room - {user['full_name'] or user['username']}",
                         "Full control: users, alerts, ML, notifications and system health",
                         f"🛠 {user['username']}  |  Admin")
        self.setWindowTitle("SecureBank AI - Administrator Console")
        self.resize(1300, 840)
        self.live = LivePanel(admin_mode=True, current_user=user)
        self.overview = OverviewPanel(user, self.theme, admin=True)
        self.overview.sim_probe = self.live.running
        for w, name in ((self.overview, "📊  Overview"), (UsersPanel(user, "admin"), "👥  Users"),
                        (AlertsPanel(user), "🔔  Alerts & Audit"), (LoginsPanel(user), "🛡  BankShield"),
                        (FilesPanel(user), "🔍  LeakGuard"), (self.live, "⚡  Live & ML"),
                        (SystemPanel(user), "🛠  System & Notifications"),
                        (NotificationTab(user), "📬  My Alerts"), (ProfileTab(user), "⚙️  My Profile")):
            self.tabs.addTab(w, name)
        self.refresh_current()

    def cleanup(self):
        self.live.stop_all()
