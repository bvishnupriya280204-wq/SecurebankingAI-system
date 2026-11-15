"""Flexible CSV import for LeakGuard (file-access logs) and BankShield (login events).

The importer auto-detects which kind of log a CSV contains, accepts common column-name
aliases, understands text values (e.g. sensitivity "Confidential", result "Failed") and
reports row-level problems instead of failing the whole file.
"""
import re

import pandas as pd

import monitor

MAX_ROWS = 2000
SENSITIVITY_LABELS = ["Public", "Internal", "Confidential", "Restricted"]

FILE_ALIASES = {
    "username": ["username", "user", "usernam", "account", "userid", "employee", "staff", "owner"],
    "filename": ["filename", "file", "name", "document", "path", "filepath", "resource"],
    "action": ["action", "activity", "operation", "event", "eventtype", "accesstype"],
    "size_mb": ["sizemb", "size", "mb", "filesize", "filesizemb", "sizeinmb"],
    "sensitivity": ["sensitivity", "classification", "sensitivitylevel", "level", "label"],
    "hour": ["hour", "hourofday"],
    "timestamp": ["timestamp", "time", "datetime", "date", "ts"],
}
LOGIN_ALIASES = {
    "username": ["username", "user", "account", "userid", "customer"],
    "success": ["success", "successful", "result", "status", "outcome", "loginsuccessful", "loginresult"],
    "hour": ["hour", "hourofday"],
    "timestamp": ["timestamp", "time", "datetime", "date", "ts", "logintimestamp"],
    "device": ["device", "useragent", "devicename", "browser", "deviceid"],
    "ip": ["ip", "ipaddress", "sourceip", "clientip"],
    "country": ["country", "ctry", "countrycode", "location"],
}
FILE_REQUIRED = ["filename", "action", "size_mb", "sensitivity"]      # username is optional (defaults to you)
LOGIN_REQUIRED = ["username", "success"]

ACTION_MAP = {
    "view": "View", "open": "View", "read": "View", "preview": "View",
    "edit": "Edit", "modify": "Edit", "write": "Edit", "update": "Edit", "save": "Edit",
    "download": "Download", "get": "Download", "fetch": "Download",
    "export": "Export", "print": "Export",
    "copytousb": "Copy to USB", "usb": "Copy to USB", "copyusb": "Copy to USB", "removable": "Copy to USB",
    "emailexternal": "Email External", "email": "Email External", "externalemail": "Email External",
    "send": "Email External", "share": "Email External", "upload": "Email External",
}
SENS_MAP = {"public": 0, "low": 0, "internal": 1, "medium": 1, "confidential": 2, "high": 2,
            "restricted": 3, "secret": 3, "critical": 3, "topsecret": 3}
OK_WORDS = {"1", "true", "yes", "y", "success", "successful", "ok", "pass", "passed", "allowed", "granted"}
BAD_WORDS = {"0", "false", "no", "n", "fail", "failed", "failure", "denied", "invalid", "wrong", "blocked"}

FILE_TEMPLATE = ("username,filename,action,size_mb,sensitivity,hour\n"
                 "analyst1,loans_2026.xlsx,View,1.2,Internal,10\n"
                 "analyst1,customer_db_export.csv,Download,85,Restricted,23\n"
                 "analyst2,report_q3.pdf,Export,4.5,Confidential,14\n")
LOGIN_TEMPLATE = ("username,success,hour,device,ip,country\n"
                  "customer1,Success,11,laptop-home,10.0.0.5,IN\n"
                  "customer1,Failed,3,unknown-device,185.23.4.9,RU\n"
                  "customer2,Success,15,phone-android,10.0.1.7,IN\n")


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def _map_columns(df, aliases):
    """Return {canonical: actual column name} for every canonical column found."""
    lookup = {_norm(c): c for c in df.columns}
    found = {}
    for canon, names in aliases.items():
        for n in names:
            if n in lookup:
                found[canon] = lookup[n]
                break
    return found


def detect_kind(df):
    """'file', 'login' or None, depending on which columns the CSV carries."""
    f, l = _map_columns(df, FILE_ALIASES), _map_columns(df, LOGIN_ALIASES)
    has_file = all(c in f for c in ("filename", "action")) or all(c in f for c in ("size_mb", "sensitivity"))
    has_login = "success" in l and "username" in l and "filename" not in f
    if has_file and not has_login:
        return "file"
    if has_login:
        return "login"
    return None


def _hour(value, timestamp=None):
    if value is not None and pd.notna(value):
        try:
            return max(0, min(23, int(float(value))))
        except (TypeError, ValueError):
            pass
    if timestamp is not None and pd.notna(timestamp):
        try:
            return int(pd.to_datetime(timestamp).hour)
        except (TypeError, ValueError):
            pass
    return None


def _sensitivity(value):
    s = str(value).strip().lower()
    if s in SENS_MAP:
        return SENS_MAP[s]
    try:
        return max(0, min(3, int(float(s))))
    except ValueError:
        raise ValueError(f"unknown sensitivity '{value}' (use Public/Internal/Confidential/Restricted or 0-3)")


def _action(value):
    key = _norm(value)
    if key in ACTION_MAP:
        return ACTION_MAP[key]
    for k, v in ACTION_MAP.items():            # tolerate e.g. "file download"
        if k in key:
            return v
    return str(value).strip().title() or "View"


def _success(value):
    s = str(value).strip().lower()
    if s in OK_WORDS:
        return True
    if s in BAD_WORDS:
        return False
    raise ValueError(f"unknown login result '{value}' (use Success/Failed or 1/0)")


def import_csv(path, default_user, kind=None):
    """Analyse and record a CSV. Returns a summary dict:
    {kind, total, imported, high, medium, errors: [(row_number, message)], missing: [columns]}"""
    df = pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""]).head(MAX_ROWS)
    if df.empty:
        raise ValueError("The CSV file has no data rows.")
    kind = kind or detect_kind(df)
    if kind is None:
        raise ValueError("Could not recognise this CSV.\n\n"
                         "File-access log needs: filename, action, size_mb, sensitivity "
                         "(username and hour optional).\n"
                         "Login-event log needs: username, success/result "
                         "(hour, device, ip, country optional).\n\n"
                         "Use 'Download CSV template' for a ready-made example.")
    cols = _map_columns(df, FILE_ALIASES if kind == "file" else LOGIN_ALIASES)
    need = FILE_REQUIRED if kind == "file" else LOGIN_REQUIRED
    missing = [c for c in need if c not in cols]
    if missing:
        raise ValueError(f"Missing required column(s): {', '.join(missing)}.\nColumns found in your file: "
                         f"{', '.join(map(str, df.columns))}")

    def cell(row, canon):
        return row[cols[canon]] if canon in cols else None

    summary = {"kind": kind, "total": len(df), "imported": 0, "high": 0, "medium": 0, "errors": [],
               "missing": [], "used_default_user": 0}
    for i, row in df.iterrows():
        n = i + 2                                             # spreadsheet row number (header = row 1)
        try:
            user = cell(row, "username")
            user = str(user).strip() if user is not None and pd.notna(user) else ""
            if not user:
                user = default_user
                summary["used_default_user"] += 1
            hour = _hour(cell(row, "hour"), cell(row, "timestamp"))
            if kind == "file":
                fname = cell(row, "filename")
                if fname is None or pd.isna(fname):
                    raise ValueError("file name is empty")
                size = float(cell(row, "size_mb"))
                if size < 0:
                    raise ValueError("size_mb cannot be negative")
                res = monitor.process_file(user, str(fname).strip(), _action(cell(row, "action")), size,
                                           _sensitivity(cell(row, "sensitivity")), hour, send_notifications=False)
            else:
                dev, ip, ctry = cell(row, "device"), cell(row, "ip"), cell(row, "country")
                res = monitor.process_login(user, _success(cell(row, "success")),
                                            str(dev) if dev is not None and pd.notna(dev) else None,
                                            str(ip) if ip is not None and pd.notna(ip) else None,
                                            str(ctry).strip().upper() if ctry is not None and pd.notna(ctry) else "IN",
                                            hour, send_notifications=False)
            summary["imported"] += 1
            summary["high"] += res["verdict"] == "HIGH"
            summary["medium"] += res["verdict"] == "MEDIUM"
        except Exception as e:                                # keep going; report the row
            summary["errors"].append((n, str(e)[:120]))
    return summary


def summary_text(s):
    label = "file-access" if s["kind"] == "file" else "login-event"
    lines = [f"Detected a {label} log.",
             f"Analysed {s['imported']} of {s['total']} rows - {s['high']} HIGH and {s['medium']} MEDIUM risk."]
    if s["used_default_user"]:
        lines.append(f"{s['used_default_user']} row(s) had no username and were recorded under your account.")
    if s["errors"]:
        lines.append(f"\n{len(s['errors'])} row(s) skipped:")
        lines += [f"  row {n}: {m}" for n, m in s["errors"][:8]]
        if len(s["errors"]) > 8:
            lines.append(f"  ... and {len(s['errors']) - 8} more")
    return "\n".join(lines)
