"""Load and normalize public Risk-Based Authentication (RBA) login data."""
import re

import pandas as pd

from ml_engine import FILE_FEATURES, LOGIN_FEATURES


def _normalise_header(value):
    """Make headers comparable despite spaces, punctuation, and underscores."""
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _find_column(df, label):
    wanted = _normalise_header(label)
    for name in df.columns:
        if wanted in _normalise_header(name):
            return name
    available = ", ".join(str(name) for name in df.columns[:30])
    raise ValueError(f"Missing required RBA column '{label}'. CSV headers found: {available}")


def _as_binary(series, label):
    """Parse bool, 0/1, and common yes/no strings with useful errors."""
    if pd.api.types.is_bool_dtype(series):
        return series.astype("int8")
    if pd.api.types.is_numeric_dtype(series):
        values = pd.to_numeric(series, errors="coerce")
        if values.dropna().isin([0, 1]).all():
            return values.fillna(0).astype("int8")
    mapping = {"true": 1, "false": 0, "1": 1, "0": 0, "yes": 1, "no": 0}
    values = series.astype(str).str.strip().str.lower().map(mapping)
    if values.isna().any():
        examples = series[values.isna()].dropna().astype(str).unique()[:5]
        raise ValueError(f"Column '{label}' must contain boolean or 0/1 values; found {list(examples)}")
    return values.astype("int8")


def _parse_timestamps(series):
    """Parse either readable dates or Unix timestamps (s, ms, us, or ns)."""
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().all():
        magnitude = numeric.abs().median()
        unit = "ns" if magnitude >= 1e17 else "us" if magnitude >= 1e14 else "ms" if magnitude >= 1e11 else "s"
        return pd.to_datetime(numeric, unit=unit, errors="coerce", utc=True).dt.tz_localize(None)
    return pd.to_datetime(series, errors="coerce", utc=True).dt.tz_localize(None)


def load_rba(path, nrows=300_000):
    """Load the Wiefling RBA dataset and map it to BankShield features.

    The public CSV uses headers such as ``User Agent String`` and ``Is Attack IP``;
    matching is punctuation-insensitive so these work alongside hyphenated variants.
    The source dataset is synthesized for research, not production banking data.
    """
    df = pd.read_csv(path, nrows=nrows, low_memory=False)
    user_col = _find_column(df, "user id")
    timestamp_col = _find_column(df, "timestamp")
    success_col = _find_column(df, "successful")
    agent_col = _find_column(df, "user-agent")
    country_col = _find_column(df, "country")
    takeover_col = _find_column(df, "takeover")
    attack_ip_col = _find_column(df, "attack ip")

    timestamps = _parse_timestamps(df[timestamp_col])
    if timestamps.isna().any():
        raise ValueError(f"Column '{timestamp_col}' contains missing or invalid timestamps.")
    success = _as_binary(df[success_col], success_col)
    takeover = _as_binary(df[takeover_col], takeover_col)
    attack_ip = _as_binary(df[attack_ip_col], attack_ip_col)

    d = pd.DataFrame({
        "user": df[user_col].astype(str),
        "ts": timestamps,
        "succ": success,
        "dev": df[agent_col].fillna("unknown").astype(str),
        "ctry": df[country_col].fillna("unknown").astype(str),
        "y": (takeover | attack_ip).astype("int8"),
    }).sort_values(["user", "ts"]).reset_index(drop=True)

    d["hour"] = d.ts.dt.hour
    d["success"] = d.succ
    streak_group = d.succ.groupby(d.user).cumsum()
    d["failed_streak"] = (1 - d.succ).groupby([d.user, streak_group]).cumsum()
    d["new_device"] = ((~d.duplicated(["user", "dev"])) & d.duplicated("user")).astype(int)
    d["new_country"] = ((~d.duplicated(["user", "ctry"])) & d.duplicated("user")).astype(int)
    d["logins_last_hour"] = d.groupby(["user", d.ts.dt.floor("h")]).cumcount()
    return d[LOGIN_FEATURES + ["y"]]


LEAKGUARD_ALIASES = {
    "hour": ("hour", "hour_of_day", "time_hour"),
    "size_mb": ("size_mb", "file_size_mb", "filesize_mb", "size"),
    "files_last_10min": ("files_last_10min", "file_count_10min", "files_10min"),
    "mb_last_hour": ("mb_last_hour", "megabytes_last_hour", "data_mb_last_hour"),
    "sensitivity": ("sensitivity", "sensitivity_level", "classification"),
    "is_download": ("is_download", "download", "download_flag"),
}


def load_leakguard(path, nrows=300_000):
    """Load a labelled LeakGuard CSV using the app's file-activity features."""
    df = pd.read_csv(path, nrows=nrows, low_memory=False)
    normalized = {_normalise_header(name): name for name in df.columns}
    selected = {}
    for feature, aliases in LEAKGUARD_ALIASES.items():
        found = next((normalized[_normalise_header(alias)] for alias in aliases
                      if _normalise_header(alias) in normalized), None)
        if found is None:
            raise ValueError(f"Missing LeakGuard feature '{feature}'. Required features: "
                             f"{', '.join(FILE_FEATURES)} plus y (0=normal, 1=suspicious). "
                             f"CSV headers found: {', '.join(map(str, df.columns))}")
        selected[feature] = found
    label_col = next((normalized[name] for name in
                      ("y", "label", "target", "ismalicious", "isleak", "attack")
                      if name in normalized), None)
    if label_col is None:
        raise ValueError("Missing target label column. Add y (0=normal, 1=suspicious).")

    out = pd.DataFrame(index=df.index)
    for feature in FILE_FEATURES:
        raw = df[selected[feature]]
        if feature == "sensitivity":
            mapped = raw.astype(str).str.strip().str.lower().map(
                {"public": 0, "internal": 1, "confidential": 2, "restricted": 3})
            out[feature] = mapped.fillna(pd.to_numeric(raw, errors="coerce"))
        elif feature == "is_download":
            out[feature] = _as_binary(raw, selected[feature])
        else:
            out[feature] = pd.to_numeric(raw, errors="coerce")
        if out[feature].isna().any():
            raise ValueError(f"Feature '{selected[feature]}' contains blank or non-numeric values.")
    if not out["sensitivity"].between(0, 3).all():
        raise ValueError("Sensitivity must be Public/Internal/Confidential/Restricted or a number from 0 to 3.")
    if df[label_col].isna().any() or df[label_col].astype(str).str.strip().eq("").any():
        raise ValueError(f"Target column '{label_col}' contains blank labels.")
    out["y"] = _as_binary(df[label_col], label_col)
    for feature in ("hour", "size_mb", "files_last_10min", "mb_last_hour"):
        if (out[feature] < 0).any():
            raise ValueError(f"Feature '{feature}' cannot contain negative values.")
    if not out["hour"].between(0, 23).all():
        raise ValueError("Hour must be between 0 and 23.")
    if out["y"].nunique() < 2 or out["y"].value_counts().min() < 2:
        raise ValueError("The labelled dataset needs at least two normal (0) and two suspicious (1) rows.")
    return out[FILE_FEATURES + ["y"]]
