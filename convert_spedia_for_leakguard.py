"""Convert SPEDIA annotated logs into SecureBank AI LeakGuard CSV features.

The output contains only file-activity records with an observed file size.
SPEDIA's Anomaly field is a general event-anomaly label, not a confirmed data
exfiltration label. Sensitivity and download are explicitly heuristic proxies.
"""
from __future__ import annotations

import argparse
from collections import defaultdict, deque
from pathlib import Path

import pandas as pd


REQUIRED = {"User", "Timestamp", "Activity", "Action", "Anomaly", "Size_before", "Size_after", "Filename", "Path"}
OUTPUT_COLUMNS = ["hour", "size_mb", "files_last_10min", "mb_last_hour", "sensitivity", "is_download", "y"]
TRANSFER_TERMS = ("download", "copy", "usb", "external", "export", "transfer", "exfil")


def convert(input_path: Path, output_path: Path) -> pd.DataFrame:
    df = pd.read_csv(input_path, low_memory=False)
    missing = REQUIRED.difference(df.columns)
    if missing:
        raise ValueError(f"Not a recognized SPEDIA CSV; missing columns: {', '.join(sorted(missing))}")

    df = df.loc[df["Activity"].astype(str).str.strip().str.lower().eq("file")].copy()
    if df.empty:
        raise ValueError("No rows with Activity='file' were found in this SPEDIA CSV.")
    df["_ts"] = pd.to_datetime(df["Timestamp"], errors="coerce", utc=True)
    df["_label"] = pd.to_numeric(df["Anomaly"], errors="coerce")
    if df["_ts"].isna().any() or df["_label"].isna().any() or not df["_label"].isin([0, 1]).all():
        raise ValueError("SPEDIA file rows need valid Timestamp values and binary Anomaly labels (0/1).")

    after = pd.to_numeric(df["Size_after"], errors="coerce")
    before = pd.to_numeric(df["Size_before"], errors="coerce")
    observed_bytes = after.where(after > 0, before.where(before > 0))
    df["_size_mb"] = observed_bytes / (1024 * 1024)
    df["_user"] = df["User"].fillna("unknown").astype(str)
    df = df.sort_values(["_user", "_ts"], kind="stable").reset_index(drop=True)

    windows: dict[str, deque] = defaultdict(deque)
    counts, totals = [], []
    for user, stamp, size in df[["_user", "_ts", "_size_mb"]].itertuples(index=False, name=None):
        window = windows[user]
        while window and (stamp - window[0][0]).total_seconds() > 3600:
            window.popleft()
        window.append((stamp, 0.0 if pd.isna(size) else float(size)))
        counts.append(sum(1 for when, _ in window if (stamp - when).total_seconds() <= 600))
        totals.append(sum(value for _, value in window))
    df["_files_10m"] = counts
    df["_mb_1h"] = totals

    output = df.loc[df["_size_mb"].notna()].copy()
    if output.empty:
        raise ValueError("No file records have a positive Size_after or Size_before value.")
    actions = output["Action"].fillna("").astype(str).str.lower()
    descriptions = output.get("Description", pd.Series("", index=output.index)).fillna("").astype(str).str.lower()

    output["sensitivity"] = 1
    output["is_download"] = (
        actions.str.contains("added", regex=False)
        | actions.str.contains("download|copy|usb|external|export|transfer|exfil", regex=True)
        | descriptions.str.contains("download|copy|usb|external|export|transfer|exfil", regex=True)
    ).astype("int8")
    output["hour"] = output["_ts"].dt.hour.astype("int8")
    output["size_mb"] = output["_size_mb"].astype(float)
    output["files_last_10min"] = output["_files_10m"].astype("int32")
    output["mb_last_hour"] = output["_mb_1h"].astype(float)
    output["y"] = output["_label"].astype("int8")
    result = output[OUTPUT_COLUMNS].reset_index(drop=True)
    if result["y"].nunique() != 2 or result["y"].value_counts().min() < 2:
        raise ValueError("Converted data must contain at least two rows for each Anomaly class.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False, float_format="%.6f")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv", type=Path, help="Path to logs_SPEDIA_annotated_en.csv")
    parser.add_argument("-o", "--output", type=Path, default=Path("spedia_leakguard_compatible.csv"))
    args = parser.parse_args()
    result = convert(args.input_csv, args.output)
    print(f"Saved {len(result):,} rows to {args.output.resolve()}")
    print("Columns:", ", ".join(result.columns))
    print("SPEDIA anomaly label counts:", result["y"].value_counts().sort_index().to_dict())
    print("Note: y is SPEDIA's general Anomaly label; sensitivity=1 is a placeholder and is_download is a heuristic proxy.")


if __name__ == "__main__":
    main()
