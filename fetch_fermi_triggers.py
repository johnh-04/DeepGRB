"""
Fetch official Fermi GBM Trigger Catalog (fermigtrig) from HEASARC
for a specified time window and save to CSV.
"""

from pathlib import Path
import pandas as pd
from gbm.finder import TriggerCatalog


def decode_bytes(val):
    if isinstance(val, (bytes, bytearray)):
        return val.decode("utf-8", errors="ignore").strip()
    return str(val).strip()


def fetch_triggers(start_utc: str, end_utc: str, output_csv: Path) -> pd.DataFrame:
    print(f"[INFO] Fetching official Fermi-GBM triggers from {start_utc} to {end_utc}...")
    cat = TriggerCatalog()
    
    # cat.get_table() returns a numpy.recarray
    raw_df = pd.DataFrame(cat.get_table())
    
    # Standardize column names to uppercase
    raw_df.columns = [str(c).upper() for c in raw_df.columns]
    
    # Decode string columns (bytes -> str)
    for col in raw_df.columns:
        if raw_df[col].dtype == object or hasattr(raw_df[col].iloc[0], "decode"):
            raw_df[col] = raw_df[col].apply(decode_bytes)

    # Identify trigger time column (typically TRIGGER_TIME)
    time_col = "TRIGGER_TIME" if "TRIGGER_TIME" in raw_df.columns else "TIME"
    raw_df["dt_parsed"] = pd.to_datetime(raw_df[time_col], errors="coerce")
    
    t_start = pd.to_datetime(start_utc)
    t_end = pd.to_datetime(end_utc)
    
    # Time filtering
    mask = (raw_df["dt_parsed"] >= t_start) & (raw_df["dt_parsed"] <= t_end)
    filtered = raw_df[mask].copy()
    
    print(f"[INFO] Found {len(filtered)} official trigger(s) in this timeframe.")
    
    if filtered.empty:
        print("[WARNING] No events found in this timeframe.")
        return pd.DataFrame()

    df_out = pd.DataFrame({
        "trig_ids": filtered.get("TRIGGER_NAME", filtered.index),
        "datetime": filtered[time_col],
        "catalog_triggers": filtered.get("TRIGGER_TYPE", "UNKNOWN"),
        "ra": filtered.get("RA", None),
        "dec": filtered.get("DEC", None)
    })
    
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    df_out.to_csv(output_csv, index=False)
    print(f"[SUCCESS] Saved triggers to: {output_csv}\n")
    print("Trigger list:")
    print(df_out.to_string(index=False))
    return df_out


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    out_path = base_dir / "data" / "fermi_triggers_sandbox_jan2019.csv"
    
    fetch_triggers("2019-01-12T00:00:00", "2019-01-19T00:00:00", out_path)