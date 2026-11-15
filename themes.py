"""Unified enterprise banking theme across login, customer, staff and administrator workspaces."""
from string import Template

QSS = Template("""
QWidget { font-family: "Segoe UI", Arial; font-size: 13px; color: $text; }
QMainWindow, QWidget#root, QDialog { background: $bg; }
QToolTip { background: $panel; color: $text; border: 1px solid $border; }

QFrame#banner { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 $g1, stop:0.55 $g2, stop:1 $g3); border-radius: 12px; }
QFrame#banner QLabel { color: white; background: transparent; }
QLabel#bannerTitle { font-size: 20px; font-weight: bold; }
QLabel#clock { font-size: 13px; font-weight: 600; padding-right: 14px; }
QLabel#chip { background: rgba(255,255,255,0.22); border-radius: 12px; padding: 5px 12px; margin-right: 8px; }
QFrame#hero { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #6a11cb, stop:0.5 #2575fc, stop:1 #00c6ff); }
QFrame#hero QLabel { color: white; background: transparent; }
QLabel#heroTitle { font-size: 30px; font-weight: bold; }
QLabel#heroTag { font-size: 14px; }
QLabel#heroFeat { font-size: 14px; }

QLabel#title { font-size: 22px; font-weight: bold; color: $accent; }
QLabel#sectionTitle { font-size: 15px; font-weight: bold; color: $accent; padding-top: 4px; }
QLabel#sectionSub, QLabel#subtitle, QLabel#hint { color: $sub; }
QLabel#statusBox { border-radius: 10px; padding: 12px 16px; font-size: 14px; font-weight: 600; }
QLabel#pill { border-radius: 11px; padding: 4px 12px; font-weight: 600; }
QLabel#alertBar { background: #e53935; color: white; border-radius: 8px; padding: 9px 14px; font-weight: bold; }
QLabel#count { color: $sub; font-style: italic; }

QFrame#card { background: $card_bg; border: 1px solid $border; border-radius: 10px; }
QLabel#cardValue { font-size: 28px; font-weight: bold; }
QLabel#cardTitle { color: $sub; font-weight: 600; }

QPushButton { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 $accent, stop:1 $accent2); color: white;
              border: none; border-radius: 7px; padding: 9px 18px; font-weight: 600; }
QPushButton:hover { background: $accent_hover; }
QPushButton:disabled { background: $border; color: $sub; }
QPushButton#danger { background: #e53935; }
QPushButton#danger:hover { background: #ff5b57; }
QPushButton#success { background: #2e9d5b; }
QPushButton#success:hover { background: #3dbb70; }
QPushButton#warn { background: #fb8c00; }
QPushButton#warn:hover { background: #ffa033; }
QPushButton#purple { background: #7e57c2; }
QPushButton#purple:hover { background: #9575cd; }
QPushButton#link { background: transparent; color: $accent_hover; padding: 2px; text-decoration: underline; }

QLineEdit, QComboBox, QDoubleSpinBox, QTextEdit { background: $input_bg; border: 1px solid $border; border-radius: 7px; padding: 7px; color: $text; }
QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus { border: 2px solid $accent; }
QComboBox QAbstractItemView { background: $input_bg; color: $text; selection-background-color: $sel_bg; selection-color: $sel_text; }
QCheckBox { spacing: 6px; }

QTabWidget::pane { border: 1px solid $border; border-radius: 10px; background: $panel; top: -1px; }
QTabBar::tab { background: $tab_bg; padding: 10px 16px; margin-right: 3px; border-top-left-radius: 9px;
               border-top-right-radius: 9px; font-weight: 600; color: $tab_text; }
QTabBar::tab:hover { background: $tab_hover; }
QTabBar::tab:selected { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 $tab_sel1, stop:1 $tab_sel2); color: white; }
QTableWidget { background: $table_bg; gridline-color: $grid; border: 1px solid $border; border-radius: 8px;
               selection-background-color: $sel_bg; selection-color: $sel_text; }
QHeaderView::section { background: $head_bg; color: $head_text; padding: 7px; border: none; font-weight: 600; }
QGroupBox { background: $panel; border: 1px solid $border; border-radius: 10px; margin-top: 16px; padding: 14px; }
QGroupBox::title { subcontrol-origin: margin; left: 14px; color: $accent; font-weight: bold; }
QProgressBar { border: 1px solid $border; border-radius: 8px; text-align: center; background: $input_bg; height: 22px; color: $text; }
QProgressBar::chunk { background: $accent; border-radius: 7px; }
QListWidget { background: $table_bg; border: 1px solid $border; border-radius: 8px; }
QScrollBar:vertical { background: $panel; width: 12px; }
QScrollBar::handle:vertical { background: $border; border-radius: 6px; min-height: 24px; }
QScrollBar:horizontal { background: $panel; height: 12px; }
QScrollBar::handle:horizontal { background: $border; border-radius: 6px; min-width: 24px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
""")

_LIGHT = dict(dark=False, panel="#ffffff", input_bg="#ffffff", card_bg="#ffffff", table_bg="#ffffff",
              tab_sel_text="white", head_text="white")

THEMES = {
    "login": dict(_LIGHT, name="login", bg="#eef3f8", text="#172b3a", sub="#63788a", border="#d7e1e9",
                  g1="#102a43", g2="#174a6e", g3="#0f766e", accent="#174a6e", accent2="#0f766e",
                  accent_hover="#236b91", tab_bg="#e7eef5", tab_hover="#d7e4ee", tab_text="#29445d",
                  tab_sel1="#174a6e", tab_sel2="#0f766e", grid="#e2eaf0", sel_bg="#c8dce8", sel_text="#102a43",
                  head_bg="#174a6e", chart=["#174a6e", "#0f766e"], role="Login"),
    "customer": dict(_LIGHT, name="customer", bg="#eef5f7", text="#172b3a", sub="#63788a", border="#d7e1e9",
                     g1="#102a43", g2="#174a6e", g3="#0f766e", accent="#174a6e", accent2="#0f766e",
                     accent_hover="#236b91", tab_bg="#e7eef5", tab_hover="#d7e4ee", tab_text="#29445d",
                     tab_sel1="#174a6e", tab_sel2="#0f766e", grid="#e2eaf0", sel_bg="#c8dce8", sel_text="#102a43",
                     head_bg="#174a6e", chart=["#174a6e", "#0f766e"], role="Customer"),
    "staff": dict(_LIGHT, name="staff", bg="#eef3f8", text="#172b3a", sub="#63788a", border="#d7e1e9",
                  g1="#102a43", g2="#174a6e", g3="#0f766e", accent="#174a6e", accent2="#0f766e",
                  accent_hover="#236b91", tab_bg="#e7eef5", tab_hover="#d7e4ee", tab_text="#29445d",
                  tab_sel1="#174a6e", tab_sel2="#0f766e", grid="#e2eaf0", sel_bg="#c8dce8", sel_text="#102a43",
                  head_bg="#174a6e", chart=["#174a6e", "#0f766e"], role="Staff"),
    "admin": dict(_LIGHT, name="admin", bg="#edf2f7", text="#172b3a", sub="#63788a", border="#d7e1e9",
                  g1="#102a43", g2="#174a6e", g3="#0f766e", accent="#174a6e", accent2="#0f766e",
                  accent_hover="#236b91", tab_bg="#e7eef5", tab_hover="#d7e4ee", tab_text="#29445d",
                  tab_sel1="#174a6e", tab_sel2="#0f766e", grid="#e2eaf0", sel_bg="#c8dce8", sel_text="#102a43",
                  head_bg="#174a6e", head_text="#ffffff", chart=["#174a6e", "#0f766e"], role="Admin"),
}


def make_style(palette):
    return QSS.substitute(palette)
