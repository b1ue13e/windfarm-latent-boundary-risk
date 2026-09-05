"""Download and validate UK Elexon BMRS 2016-2024 System Buy/Imbalance Prices.

Fetches half-hourly settlement prices from the Elexon Insights Solution API:
https://data.elexon.co.uk/bmrs/api/v1/balancing/settlement/system-prices/{date}
"""
from __future__ import annotations

import argparse
import concurrent.futures
import datetime
import json
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = ROOT / "artifacts" / "elexon_bmrs_imbalance"


def fetch_single_day(date_str: str, max_retries: int = 4) -> tuple[str, list[dict[str, Any]]]:
    url = f"https://data.elexon.co.uk/bmrs/api/v1/balancing/settlement/system-prices/{date_str}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }
    req = urllib.request.Request(url, headers=headers)
    
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                if resp.status == 200:
                    payload = json.loads(resp.read().decode("utf-8"))
                    data = payload.get("data", [])
                    return date_str, data
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"[ERROR] Failed {date_str} after {max_retries} attempts: {e}", file=sys.stderr)
                return date_str, []
            time.sleep(1.0 + attempt * 1.5)
            
    return date_str, []


def download_year(year: int, out_dir: Path, workers: int = 24) -> pd.DataFrame:
    year_file = out_dir / f"elexon_prices_{year}.csv"
    if year_file.exists():
        print(f"Loading cached {year_file.name}...")
        df_cached = pd.read_csv(year_file)
        if len(df_cached) > 17000: # Typical year has ~17,520 half-hours
            return df_cached
        print(f"Cached {year_file.name} seems incomplete ({len(df_cached)} rows), re-downloading...")

    start_date = datetime.date(year, 1, 1)
    end_date = datetime.date(year, 12, 31)
    n_days = (end_date - start_date).days + 1
    dates = [(start_date + datetime.timedelta(days=i)).isoformat() for i in range(n_days)]

    print(f"Fetching {year} ({n_days} days) with {workers} threads...")
    t0 = time.time()
    
    results: list[tuple[str, list[dict[str, Any]]]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(fetch_single_day, d): d for d in dates}
        for fut in concurrent.futures.as_completed(futures):
            results.append(fut.result())

    rows: list[dict[str, Any]] = []
    failed_dates: list[str] = []
    for d, items in results:
        if not items:
            failed_dates.append(d)
            continue
        for item in items:
            rows.append({
                "settlementDate": item.get("settlementDate"),
                "settlementPeriod": int(item.get("settlementPeriod", 0)),
                "startTime": item.get("startTime"),
                "systemBuyPrice": float(item.get("systemBuyPrice")) if item.get("systemBuyPrice") is not None else np.nan,
                "systemSellPrice": float(item.get("systemSellPrice")) if item.get("systemSellPrice") is not None else np.nan,
                "netImbalanceVolume": float(item.get("netImbalanceVolume")) if item.get("netImbalanceVolume") is not None else np.nan,
                "priceDerivationCode": item.get("priceDerivationCode", ""),
            })

    if failed_dates:
        print(f"[WARN] Retrying {len(failed_dates)} failed dates for {year}...")
        time.sleep(2.0)
        for fd in failed_dates:
            _, items = fetch_single_day(fd, max_retries=6)
            for item in items:
                rows.append({
                    "settlementDate": item.get("settlementDate"),
                    "settlementPeriod": int(item.get("settlementPeriod", 0)),
                    "startTime": item.get("startTime"),
                    "systemBuyPrice": float(item.get("systemBuyPrice")) if item.get("systemBuyPrice") is not None else np.nan,
                    "systemSellPrice": float(item.get("systemSellPrice")) if item.get("systemSellPrice") is not None else np.nan,
                    "netImbalanceVolume": float(item.get("netImbalanceVolume")) if item.get("netImbalanceVolume") is not None else np.nan,
                    "priceDerivationCode": item.get("priceDerivationCode", ""),
                })

    df = pd.DataFrame(rows)
    df.sort_values(by=["settlementDate", "settlementPeriod"], inplace=True)
    df.drop_duplicates(subset=["settlementDate", "settlementPeriod"], inplace=True)
    df.to_csv(year_file, index=False)
    t1 = time.time()
    print(f"Saved {year_file.name}: {len(df)} settlement periods in {t1 - t0:.1f}s. SBP mean: GBP {df['systemBuyPrice'].mean():.2f}/MWh (min: GBP {df['systemBuyPrice'].min():.2f}, max: GBP {df['systemBuyPrice'].max():.2f})")
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Download Elexon BMRS prices 2016-2024")
    parser.add_argument("--start-year", type=int, default=2016)
    parser.add_argument("--end-year", type=int, default=2024)
    parser.add_argument("--workers", type=int, default=24)
    parser.add_argument("--output-dir", type=str, default=str(DEFAULT_OUT_DIR))
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_dfs = []
    for y in range(args.start_year, args.end_year + 1):
        df_y = download_year(y, out_dir, workers=args.workers)
        all_dfs.append(df_y)

    combined = pd.concat(all_dfs, ignore_index=True)
    combined.sort_values(by=["settlementDate", "settlementPeriod"], inplace=True)
    combined.drop_duplicates(subset=["settlementDate", "settlementPeriod"], inplace=True)

    full_csv = out_dir / "elexon_system_prices_2016_2024.csv"
    combined.to_csv(full_csv, index=False)
    print(f"\n=======================================================")
    print(f"All years {args.start_year}-{args.end_year} successfully processed!")
    print(f"Total half-hour settlement periods: {len(combined):,}")
    print(f"Total days covered: {combined['settlementDate'].nunique():,}")
    print(f"System Buy Price Summary (GBP/MWh):")
    print(combined["systemBuyPrice"].describe())
    print(f"Output saved to: {full_csv}")
    print(f"=======================================================\n")


if __name__ == "__main__":
    main()
