"""Shared UI toolkit: painted logo, banner, cards, tables, charts and the dashboard base classes."""
import time
import os
from datetime import datetime

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import QDateTime, QEvent, QObject, QPointF, QSize, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QIcon, QLinearGradient, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QHeaderView, QLabel, QListWidgetItem,
                               QMainWindow, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QTabWidget,
                               QVBoxLayout, QWidget)

import accounts
import config
import database as db
import notifier
from themes import THEMES, make_style

BLUE, RED, GREEN, PURPLE, ORANGE, TEAL = "#2d6cdf", "#e53935", "#2e9d5b", "#7e57c2", "#fb8c00", "#00acc1"

_STATE = {"dark": False}
ROW_LIGHT = {"LOW": "#e3f6e5", "MEDIUM": "#fff2c9", "HIGH": "#ffd9d9"}
ROW_DARK = {"LOW": "#1d3b2a", "MEDIUM": "#4a3f1a", "HIGH": "#4d2024"}
SEV_ICON = {"LOW": "🟢", "MEDIUM": "🟠", "HIGH": "🔴"}


def set_dark(flag):
    _STATE["dark"] = bool(flag)


def status_style(kind):
    """Inline style for status boxes / pills that works in light and dark themes."""
    d = _STATE["dark"]
    bg, fg = {"good": ("#143d27", "#8ff0b5") if d else ("#e0f6e6", "#1b5e20"),
              "bad": ("#4d1f24", "#ffb4b4") if d else ("#ffe0e0", "#b71c1c"),
              "warn": ("#4a3a14", "#ffd27a") if d else ("#fff3d6", "#8a5a00"),
              "info": ("#1c2c4d", "#9cc2ff") if d else ("#e3edff", "#1d4ed8")}[kind]
    return f"background:{bg}; color:{fg};"


def logo_pixmap(size=96):
    artwork = QPixmap(config.resource_path("icon.png"))
    if not artwork.isNull():
        return artwork.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    g = QLinearGradient(0, 0, size, size)
    g.setColorAt(0, QColor("#6a11cb"))
    g.setColorAt(1, QColor("#2575fc"))
    p.setBrush(QBrush(g))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(0, 0, size, size, size * 0.22, size * 0.22)

    def poly(points):
        return QPolygonF([QPointF(size * x, size * y) for x, y in points])

    p.setBrush(QColor("white"))
    p.drawPolygon(poly([(.5, .13), (.81, .25), (.81, .54), (.5, .88), (.19, .54), (.19, .25)]))
    p.setBrush(QColor("#1e3c72"))
    p.drawPolygon(poly([(.5, .20), (.74, .30), (.74, .52), (.5, .80), (.26, .52), (.26, .30)]))
    p.setPen(QPen(QColor("#4ddc8c"), size * 0.07, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    p.drawPolyline(poly([(.37, .50), (.47, .60), (.65, .40)]))
    p.end()
    return pm


def app_icon():
    """Use the real multi-resolution ICO so title bar and Windows taskbar agree."""
    ico = config.resource_path("icon.ico")
    if os.path.isfile(ico):
        icon = QIcon(ico)
        if not icon.isNull():
            return icon
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(logo_pixmap(size))
    return icon


def section(title, sub=""):
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(0)
    t = QLabel(title)
    t.setObjectName("sectionTitle")
    lay.addWidget(t)
    return w


def pill(label, text, kind="info"):
    label.setObjectName("pill")
    label.setText(text)
    label.setStyleSheet(status_style(kind))


def banner(title, subtitle, chip_text):
    f = QFrame()
    f.setObjectName("banner")
    h = QHBoxLayout(f)
    h.setContentsMargins(14, 10, 14, 10)
    logo = QLabel()
    logo.setPixmap(logo_pixmap(50))
    box = QVBoxLayout()
    t = QLabel(title)
    t.setObjectName("bannerTitle")
    box.addWidget(t)
    box.addWidget(QLabel(subtitle))
    h.addWidget(logo)
    h.addLayout(box)
    h.addStretch()
    f.clock = QLabel()
    f.clock.setObjectName("clock")
    chip = QLabel(chip_text)
    chip.setObjectName("chip")
    f.logout_btn = QPushButton("⏻  Logout")
    f.logout_btn.setObjectName("danger")
    for w in (f.clock, chip, f.logout_btn):
        h.addWidget(w)

    def tick():
        f.clock.setText(QDateTime.currentDateTime().toString("ddd dd MMM  hh:mm:ss"))

    f._timer = QTimer(f)
    f._timer.timeout.connect(tick)
    f._timer.start(1000)
    tick()
    return f


class Card(QFrame):
    def __init__(self, title, color=BLUE, icon=""):
        super().__init__()
        self.setObjectName("card")
        self.setStyleSheet(f"QFrame#card {{ border-left: 6px solid {color}; }}")
        lay = QVBoxLayout(self)
        t = QLabel(f"{icon}  {title}")
        t.setObjectName("cardTitle")
        self.value = QLabel("0")
        self.value.setObjectName("cardValue")
        self.value.setStyleSheet(f"color: {color};")
        lay.addWidget(t)
        lay.addWidget(self.value)

    def set(self, v):
        self.value.setText(str(v))


def make_table(headers):
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.setEditTriggers(QTableWidget.NoEditTriggers)
    t.setSelectionBehavior(QTableWidget.SelectRows)
    t.setSelectionMode(QTableWidget.SingleSelection)
    t.verticalHeader().setVisible(False)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    return t


def fill_table(table, rows, keys, color_key=None):
    colors = ROW_DARK if _STATE["dark"] else ROW_LIGHT
    fg = QColor("white" if _STATE["dark"] else "black")
    table.setRowCount(len(rows))
    for r, row in enumerate(rows):
        color = colors.get(row.get(color_key)) if color_key else None
        for c, k in enumerate(keys):
            v = row.get(k, "")
            item = QTableWidgetItem(f"{v:.1f}" if isinstance(v, float) else ("" if v is None else str(v)))
            if color:
                item.setBackground(QColor(color))
                item.setForeground(fg)
            table.setItem(r, c, item)


def selected_key(table, col=0):
    r = table.currentRow()
    return table.item(r, col).text() if r >= 0 and table.item(r, col) is not None else None


def restore_selection(table, col, key):
    if key is None:
        return
    for r in range(table.rowCount()):
        if table.item(r, col) is not None and table.item(r, col).text() == key:
            table.selectRow(r)
            return


def attach_filter(table, edit):
    """Live search box: hides rows that do not contain the typed text."""
    def apply(text=None):
        text = (edit.text() if text is None else text).lower()
        for r in range(table.rowCount()):
            hit = any(table.item(r, c) is not None and text in table.item(r, c).text().lower()
                      for c in range(table.columnCount()))
            table.setRowHidden(r, not hit)
    edit.textChanged.connect(apply)
    return apply


def feed_fill(listw, alerts):
    """Fills a QListWidget with colour-coded alert lines."""
    colors = ROW_DARK if _STATE["dark"] else ROW_LIGHT
    fg = QColor("white" if _STATE["dark"] else "black")
    listw.clear()
    for a in alerts:
        text = f"{SEV_ICON.get(a['severity'], '')} {a['ts'][11:16]}  {a['source']}  -  {a['message'][:95]}"
        it = QListWidgetItem(text)
        chars_per_line = max(30, listw.viewport().width() // 8)
        lines = max(2, (len(text) + chars_per_line - 1) // chars_per_line)
        it.setSizeHint(QSize(0, lines * 19 + 12))
        it.setBackground(QColor(colors.get(a["severity"], "#ffffff")))
        it.setForeground(fg)
        listw.addItem(it)


def style_meter(bar, password):
    score, label = accounts.password_strength(password)
    bar.setRange(0, 100)
    bar.setValue(score * 20)
    bar.setFormat(label if password else "Password strength")
    color = ["#e53935", "#e53935", "#fb8c00", "#fdd835", "#7cb342", "#2e9d5b"][score]
    bar.setStyleSheet(f"QProgressBar::chunk {{ background: {color}; border-radius: 7px; }}")


def _theme_ax(ax, dark):
    if dark:
        ax.set_facecolor("#131a2b")
        ax.title.set_color("#e8edff")
        ax.tick_params(colors="#93a0c4")
        for sp in ax.spines.values():
            sp.set_color("#2b3656")


class Charts(FigureCanvas):
    """Overview: 2x2 colourful charts."""

    def __init__(self, dark=False, colors=None):
        fig = Figure(figsize=(10, 5), layout="tight", facecolor="#171e30" if dark else "white")
        super().__init__(fig)
        self.fig, self.dark = fig, dark
        self.c1, self.c2 = (colors or [BLUE, PURPLE])[:2]
        self.axs = fig.subplots(2, 2)

    def refresh(self, logins, files, sev, sources, hours):
        (a, b), (c, d) = self.axs
        for ax in (a, b, c, d):
            ax.clear()
        a.set_title("Risk score of latest events")
        lr = [x["risk"] for x in reversed(logins[:80])]
        fr = [x["risk"] for x in reversed(files[:80])]
        a.plot(lr, color=self.c1, label="BankShield")
        a.fill_between(range(len(lr)), lr, color=self.c1, alpha=0.15)
        a.plot(fr, color=self.c2, label="LeakGuard")
        a.axhline(config.HIGH_RISK, color=RED, ls="--", lw=1)
        a.set_ylim(0, 100)
        a.legend(loc="upper left", fontsize=8)
        b.set_title("Alerts by severity")
        names = ["LOW", "MEDIUM", "HIGH"]
        b.bar(names, [sev.get(n, 0) for n in names], color=[GREEN, ORANGE, RED])
        c.set_title("Alerts by module")
        if sources:
            c.pie(list(sources.values()), labels=list(sources.keys()), autopct="%1.0f%%", startangle=90,
                  colors=[BLUE, PURPLE, ORANGE, TEAL, GREEN], wedgeprops={"width": 0.45},
                  textprops={"fontsize": 8, "color": "#e8edff" if self.dark else "black"})
        else:
            c.text(0.5, 0.5, "No alerts yet", ha="center", va="center", color="#93a0c4" if self.dark else "black")
        d.set_title("Logins by hour (green = ok, red = failed)")
        ok = [hours.get(h, (0, 0))[0] for h in range(24)]
        bad = [hours.get(h, (0, 0))[1] for h in range(24)]
        d.bar(range(24), ok, color=GREEN)
        d.bar(range(24), bad, bottom=ok, color=RED)
        d.set_xticks(range(0, 24, 3))
        for ax in (a, b, c, d):
            _theme_ax(ax, self.dark)
        self.draw_idle()


class MiniChart(FigureCanvas):
    """Customer: own login risk over time."""

    def __init__(self, color=BLUE):
        fig = Figure(figsize=(6, 2.6), layout="tight")
        super().__init__(fig)
        self.fig, self.color = fig, color
        self.ax = fig.add_subplot(111)

    def refresh(self, risks):
        a = self.ax
        a.clear()
        a.set_title("My login risk over time")
        a.set_ylim(0, 100)
        if risks:
            a.plot(range(len(risks)), risks, color=self.color, marker="o", ms=4)
            a.fill_between(range(len(risks)), risks, color=self.color, alpha=0.18)
        a.axhline(config.HIGH_RISK, color=RED, ls="--", lw=1)
        self.draw_idle()


class IdleWatcher(QObject):
    def __init__(self):
        super().__init__()
        self.last = time.time()

    def eventFilter(self, obj, ev):
        if ev.type() in (QEvent.MouseMove, QEvent.MouseButtonPress, QEvent.KeyPress):
            self.last = time.time()
        return False


class DashboardBase(QMainWindow):
    """Applies the role theme, handles logout and automatic logout after inactivity."""

    def __init__(self, user, login_window, theme):
        super().__init__()
        self.user, self.login_window, self.theme = user, login_window, theme
        set_dark(theme["dark"])
        self.setStyleSheet(make_style(theme))
        self.setWindowIcon(app_icon())
        self.idle = IdleWatcher()
        QApplication.instance().installEventFilter(self.idle)
        self.idle_timer = QTimer(self)
        self.idle_timer.timeout.connect(self._check_idle)
        self.idle_timer.start(1000)

    def greeting(self):
        h = datetime.now().hour
        return "Good morning" if h < 12 else "Good afternoon" if h < 18 else "Good evening"

    def _check_idle(self):
        if time.time() - self.idle.last > config.IDLE_TIMEOUT:
            self.logout(timeout=True)

    def logout(self, timeout=False):
        self.idle_timer.stop()
        notifier.notify_activity(self.user["username"], "Sign-out", "[SecureBank AI] Sign-out recorded",
                                 "A sign-out was recorded for your SecureBank AI account.")
        self.login_window.show_again()
        self.close()
        if timeout:
            QMessageBox.information(self.login_window, "Session expired",
                                    "You were logged out automatically after a period of inactivity.")

    def cleanup(self):
        pass

    def closeEvent(self, e):
        self.idle_timer.stop()
        QApplication.instance().removeEventFilter(self.idle)
        self.cleanup()
        set_dark(False)
        super().closeEvent(e)


class ConsoleBase(DashboardBase):
    """Staff/Admin window: banner, red pop-up bar for new HIGH alerts, tab container that
    refreshes only the visible tab every 3 seconds."""

    def __init__(self, user, login_window, theme, title, subtitle, chip):
        super().__init__(user, login_window, theme)
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        self.lay = QVBoxLayout(root)
        b = banner(title, subtitle, chip)
        b.logout_btn.clicked.connect(lambda: self.logout())
        self.lay.addWidget(b)
        self.alert_bar = QLabel()
        self.alert_bar.setObjectName("alertBar")
        self.alert_bar.hide()
        self.lay.addWidget(self.alert_bar)
        self.tabs = QTabWidget()
        self.lay.addWidget(self.tabs)
        self._last_alert_id = db.query("SELECT COALESCE(MAX(id),0) m FROM alerts")[0]["m"]
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(3000)
        self.tabs.currentChanged.connect(lambda _i: self.refresh_current())

    def refresh_current(self):
        w = self.tabs.currentWidget()
        if hasattr(w, "refresh"):
            w.refresh()

    def tick(self):
        self.refresh_current()
        new = db.query("SELECT * FROM alerts WHERE id>? AND severity='HIGH' ORDER BY id", (self._last_alert_id,))
        self._last_alert_id = db.query("SELECT COALESCE(MAX(id),0) m FROM alerts")[0]["m"]
        if new:
            QApplication.beep()
            self.alert_bar.setText(f"🚨  NEW HIGH ALERT: {new[-1]['message'][:160]}"
                                   + (f"   (+{len(new) - 1} more)" if len(new) > 1 else ""))
            self.alert_bar.show()
            QTimer.singleShot(8000, self.alert_bar.hide)
