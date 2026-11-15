"""Central configuration. Secrets come from environment variables / .env file."""
import os
import sys
import shutil


# Project directory
# Project directory
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Store application data outside the GitHub project
DATA_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "SecureBankAI"
)

os.makedirs(DATA_DIR, exist_ok=True)

LOCAL_DATA_DIR = DATA_DIR
DB_PATH = os.path.join(DATA_DIR, "securebank.db")
# Load .env from the parent folder of the project
try:
    from dotenv import load_dotenv

    EXTERNAL_ENV = os.path.join(
        os.path.dirname(BASE_DIR),
        ".env"
    )

    load_dotenv(EXTERNAL_ENV, override=True)

except ImportError:
    pass

def resource_path(name):
    """Path of a bundled resource (icon) both in development and inside the .exe."""
    base = getattr(sys, "_MEIPASS", BASE_DIR)
    return os.path.join(base, name)


LOCAL_DATA_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "SecureBankAI"
)

os.makedirs(LOCAL_DATA_DIR, exist_ok=True)

DB_PATH = os.path.join(LOCAL_DATA_DIR, "securebank.db")
if getattr(sys, "frozen", False) and not os.path.exists(DB_PATH):
    packaged_db = os.path.join(BASE_DIR, "securebank.db")
    if os.path.isfile(packaged_db):
        shutil.copy2(packaged_db, DB_PATH)

STAFF_CODE = os.getenv("SB_STAFF_CODE", "").strip()
ADMIN_CODE = os.getenv("SB_ADMIN_CODE", "").strip()

SMTP_USER = os.getenv("SB_SMTP_USER", "")
SMTP_APP_PASSWORD = os.getenv("SB_SMTP_APP_PASSWORD", "")
SECURITY_TEAM_EMAIL = os.getenv("SB_SECURITY_EMAIL", SMTP_USER)

MEDIUM_RISK = 40          # risk score thresholds (0-100)
HIGH_RISK = 70
LOCKOUT_FAILS = 5         # consecutive failures before temporary lock
LOCKOUT_SECONDS = 120
IDLE_TIMEOUT = 300        # seconds of inactivity before automatic logout


def email_configured():
    return bool(SMTP_USER and SMTP_APP_PASSWORD)

