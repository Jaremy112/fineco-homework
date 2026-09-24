#!/usr/bin/env python3
"""Download and audit HW02-1 inputs from AKShare public upstreams.

Prices come from Sina Finance via AKShare. Share-capital history comes from CNINFO
via AKShare. Wind is used only for security metadata and cross-checks already
recorded in the notebook; no credential is read or stored here.
"""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime
from pathlib import Path

import akshare as ak
import pandas as pd

PROJECT = Path(__file__).resolve().parents[1]
RAW = PROJECT / "data" / "raw" / "akshare"
PROCESSED = PROJECT / "data" / "processed"
AUDIT = PROJECT / "audit"

SELECTION_MASTER = PROCESSED / "stock_selection_master.csv"
if not SELECTION_MASTER.exists():
    raise FileNotFoundError(f"Missing stock-pool master: {SELECTION_MASTER}")

_selection = pd.read_csv(
    SELECTION_MASTER,
    dtype={"stock_code": "string", "symbol": "string"},
)
_required_selection_columns = {
    "stock_code", "symbol", "stock_name", "industry", "listing_date",
    "selection_reason", "industry_standard", "industry_classification_date",
}
_missing_selection_columns = _required_selection_columns - set(_selection.columns)
if _missing_selection_columns:
    raise ValueError(f"Stock-pool master missing columns: {sorted(_missing_selection_columns)}")
if len(_selection) != 10 or _selection["stock_code"].duplicated().any():
    raise ValueError("Stock-pool master must contain exactly 10 unique stocks")

STOCKS = list(_selection[["stock_code", "symbol", "stock_name", "industry"]].itertuples(index=False, name=None))
START = "20201201"  # enough support to identify the final 2020 trading day
END = "20260916"


def retry(fn, attempts=4):
    last = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as exc:
            last = exc
            if i + 1 < attempts:
                time.sleep(2 ** i)
    raise last


def save_csv(df: pd.DataFrame, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize_hist(df: pd.DataFrame, wind_code: str, name: str, suffix: str) -> pd.DataFrame:
    out = df.rename(columns={
        "date": "date", "close": f"close_{suffix}",
        "volume": f"volume_shares_{suffix}", "amount": f"turnover_cny_{suffix}",
        "outstanding_share": f"outstanding_shares_{suffix}",
    }).copy()
    out["date"] = pd.to_datetime(out["date"], errors="raise")
    for c in [f"close_{suffix}", f"volume_shares_{suffix}", f"turnover_cny_{suffix}"]:
        out[c] = pd.to_numeric(out[c], errors="raise")
    out["stock_code"] = wind_code
    out["stock_name"] = name
    return out[["stock_code", "stock_name", "date", f"close_{suffix}",
                f"volume_shares_{suffix}", f"turnover_cny_{suffix}",
                f"outstanding_shares_{suffix}"]]


def main() -> None:
    for d in [RAW, PROCESSED, AUDIT]:
        d.mkdir(parents=True, exist_ok=True)

    manifest = []
    daily_frames = []
    capital_frames = []

    for wind_code, symbol, name, industry in STOCKS:
        print("downloading", wind_code, name, flush=True)
        sina_symbol = ("sh" if wind_code.endswith(".SH") else "sz") + symbol
        unadj = retry(lambda: ak.stock_zh_a_daily(
            symbol=sina_symbol, start_date=START, end_date=END, adjust=""
        ))
        hfq = retry(lambda: ak.stock_zh_a_daily(
            symbol=sina_symbol, start_date=START, end_date=END, adjust="hfq"
        ))
        capital = retry(lambda: ak.stock_share_change_cninfo(
            symbol=symbol, start_date="19900101", end_date=END
        ))

        if unadj.empty or hfq.empty or capital.empty:
            raise RuntimeError(f"Empty source for {wind_code}")

        p_unadj = RAW / "sina_unadjusted" / f"{wind_code}.csv"
        p_hfq = RAW / "sina_hfq" / f"{wind_code}.csv"
        p_cap = RAW / "cninfo_share_capital" / f"{wind_code}.csv"
        for kind, frame, path in [
            ("sina_unadjusted", unadj, p_unadj),
            ("sina_hfq", hfq, p_hfq),
            ("cninfo_share_capital", capital, p_cap),
        ]:
            sha = save_csv(frame, path)
            manifest.append({
                "kind": kind, "stock_code": wind_code, "path": str(path.relative_to(PROJECT)),
                "rows": len(frame), "sha256": sha,
            })

        u = normalize_hist(unadj, wind_code, name, "unadjusted")
        h = normalize_hist(hfq, wind_code, name, "hfq")
        daily = u.merge(
            h[["stock_code", "date", "close_hfq"]],
            on=["stock_code", "date"], how="outer", validate="one_to_one", indicator=True,
        )
        if not daily["_merge"].eq("both").all():
            raise RuntimeError(f"Adjusted/unadjusted date mismatch for {wind_code}")
        daily = daily.drop(columns="_merge")
        # Sina reports volume in shares and amount in CNY.
        daily["volume_shares"] = daily["volume_shares_unadjusted"]
        daily["turnover_100m_cny"] = daily["turnover_cny_unadjusted"] / 1e8

        cap = capital[["证券代码", "证券简称", "公告日期", "变动日期", "变动原因", "总股本"]].copy()
        cap["effective_date"] = pd.to_datetime(cap["变动日期"], errors="raise")
        cap["announcement_date"] = pd.to_datetime(cap["公告日期"], errors="coerce")
        cap["total_shares_10k"] = pd.to_numeric(cap["总股本"], errors="raise")
        cap = cap.sort_values(["effective_date", "announcement_date"]).drop_duplicates(
            "effective_date", keep="last"
        )
        cap["stock_code"] = wind_code
        cap["stock_name"] = name
        cap["industry"] = industry
        capital_frames.append(cap)

        daily = pd.merge_asof(
            daily.sort_values("date"),
            cap[["effective_date", "total_shares_10k"]].sort_values("effective_date"),
            left_on="date", right_on="effective_date", direction="backward",
        )
        if daily["total_shares_10k"].isna().any():
            raise RuntimeError(f"Missing effective total shares for {wind_code}")
        # CNINFO total shares are reported in 10,000 shares; validated against Wind total market cap.
        daily["market_cap_100m_cny"] = daily["close_unadjusted"] * daily["total_shares_10k"] / 1e4
        daily["industry"] = industry
        daily_frames.append(daily)

    daily = pd.concat(daily_frames, ignore_index=True).sort_values(["stock_code", "date"])
    capital = pd.concat(capital_frames, ignore_index=True).sort_values(["stock_code", "effective_date"])
    if daily.duplicated(["stock_code", "date"]).any():
        raise RuntimeError("Duplicate stock-date keys")

    # Keep the final 2020 trading day plus the requested sample period.
    support = daily[daily["date"] < "2021-01-01"].groupby("stock_code")["date"].max()
    keep = daily["date"].ge("2021-01-01") | daily.set_index("stock_code")["date"].eq(support).to_numpy()
    daily = daily.loc[keep & daily["date"].le("2026-09-16")].copy()

    processed_path = PROCESSED / "daily_stock_data_20201231_20260916.csv"
    daily.to_csv(processed_path, index=False, encoding="utf-8-sig")
    capital.to_csv(PROCESSED / "share_capital_history.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(manifest).to_csv(AUDIT / "source_manifest_akshare.csv", index=False, encoding="utf-8-sig")

    coverage = daily.groupby(["stock_code", "stock_name", "industry"]).agg(
        rows=("date", "size"), date_min=("date", "min"), date_max=("date", "max"),
        unadjusted_nonmissing=("close_unadjusted", "count"),
        hfq_nonmissing=("close_hfq", "count"), market_cap_nonmissing=("market_cap_100m_cny", "count"),
        zero_volume_days=("volume_shares", lambda s: int(s.eq(0).sum())),
    ).reset_index()
    coverage.to_csv(AUDIT / "coverage_akshare.csv", index=False, encoding="utf-8-sig")

    # Cross-check the exact date used in the Wind probe.
    check = daily.query("stock_code == '600519.SH' and date == '2020-12-31'").iloc[0]
    wind_market_cap = 25099.0  # 2.5099 trillion CNY from the saved Wind response
    cross = {
        "stock_code": "600519.SH", "date": "2020-12-31",
        "akshare_close_unadjusted_cny": float(check.close_unadjusted),
        "cninfo_total_shares_10k": float(check.total_shares_10k),
        "constructed_market_cap_100m_cny": float(check.market_cap_100m_cny),
        "wind_market_cap_100m_cny_rounded": wind_market_cap,
        "absolute_difference_100m_cny": abs(float(check.market_cap_100m_cny) - wind_market_cap),
    }
    (AUDIT / "market_cap_crosscheck.json").write_text(
        json.dumps(cross, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    execution = {
        "executed_at": datetime.now().astimezone().isoformat(),
        "akshare_version": ak.__version__,
        "price_upstream": "新浪财经 via AKShare stock_zh_a_daily",
        "share_capital_upstream": "巨潮资讯 via AKShare stock_share_change_cninfo",
        "metadata_and_crosscheck": "Wind金融数据服务",
        "sample_period": ["2021-01-01", "2026-09-16"],
        "support_rule": "Each stock's final observed trading day before 2021-01-01",
        "adjustment": "hfq for return calculation; unadjusted for price chart and market cap",
        "units": {"price": "CNY", "volume_source": "shares", "volume_output": "shares", "turnover_output": "100m CNY", "market_cap_output": "100m CNY", "cninfo_total_shares": "10k shares"},
    }
    (AUDIT / "execution_akshare.json").write_text(
        json.dumps(execution, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(coverage.to_string(index=False))
    print(json.dumps(cross, ensure_ascii=False, indent=2))
    print("processed_rows=", len(daily), "processed_sha256=", hashlib.sha256(processed_path.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
