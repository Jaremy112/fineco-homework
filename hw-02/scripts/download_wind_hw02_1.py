#!/usr/bin/env python3
"""HW02-1 Wind data collector.

The script uses the locally configured Wind MCP CLI. It never reads or writes an
API key. Raw responses are saved before normalized CSV files are produced.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import date, datetime
from pathlib import Path

import pandas as pd

PROJECT = Path(__file__).resolve().parents[1]
RAW = PROJECT / "data" / "raw"
PROCESSED = PROJECT / "data" / "processed"
AUDIT = PROJECT / "audit"
WIND_SKILL = Path.home() / ".hermes" / "skills" / "wind-mcp-skill"
CLI = ["node", "scripts/cli.mjs", "call"]

STOCKS = [
    ("600519.SH", "贵州茅台", "酒、饮料和精制茶制造业"),
    ("600036.SH", "招商银行", "货币金融服务"),
    ("600276.SH", "恒瑞医药", "医药制造业"),
    ("000333.SZ", "美的集团", "电气机械和器材制造业"),
    ("002594.SZ", "比亚迪", "汽车制造业"),
    ("600309.SH", "万华化学", "化学原料和化学制品制造业"),
    ("002352.SZ", "顺丰控股", "邮政业"),
    ("600030.SH", "中信证券", "资本市场服务"),
    ("601012.SH", "隆基绿能", "电气机械和器材制造业"),
    ("002475.SZ", "立讯精密", "计算机、通信和其他电子设备制造业"),
]

# The analytics endpoint returns at most 100 rows. Quarterly windows remain
# safely below that cap and make truncation visible in the audit.
WINDOWS = [
    ("20201231", "20210331"),
    ("20210401", "20210630"),
    ("20210701", "20210930"),
    ("20211001", "20211231"),
    ("20220101", "20220331"),
    ("20220401", "20220630"),
    ("20220701", "20220930"),
    ("20221001", "20221231"),
    ("20230101", "20230331"),
    ("20230401", "20230630"),
    ("20230701", "20230930"),
    ("20231001", "20231231"),
    ("20240101", "20240331"),
    ("20240401", "20240630"),
    ("20240701", "20240930"),
    ("20241001", "20241231"),
    ("20250101", "20250331"),
    ("20250401", "20250630"),
    ("20250701", "20250930"),
    ("20251001", "20251231"),
    ("20260101", "20260331"),
    ("20260401", "20260630"),
    ("20260701", "20260916"),
]


def call_wind(server: str, tool: str, params: dict) -> dict:
    cmd = CLI + [server, tool, json.dumps(params, ensure_ascii=False)]
    result = subprocess.run(
        cmd, cwd=WIND_SKILL, capture_output=True, text=True, timeout=180, check=False
    )
    if result.returncode:
        raise RuntimeError(f"Wind call failed: {result.stdout}\n{result.stderr}")
    outer = json.loads(result.stdout)
    if outer.get("isError"):
        raise RuntimeError(result.stdout)
    return outer


def payload(outer: dict) -> dict:
    return json.loads(outer["content"][0]["text"])


def save_raw(obj: dict, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def kline_frame(obj: dict, code: str, name: str) -> pd.DataFrame:
    data = payload(obj)["data"]
    columns = [c["name"] for c in data["columns"]]
    frame = pd.DataFrame(data["rows"], columns=columns)
    frame["date"] = pd.to_datetime(frame["TIME"], utc=True).dt.tz_convert("Asia/Shanghai").dt.tz_localize(None).dt.normalize()
    for c in ["OPEN", "MATCH", "HIGH", "LOW", "TURNOVER", "VOLUME", "CHANGEHANDRATE", "AVPRICE"]:
        frame[c] = pd.to_numeric(frame[c], errors="raise")
    return frame.assign(stock_code=code, stock_name=name).rename(
        columns={"MATCH": "adj_close", "TURNOVER": "turnover_cny", "VOLUME": "volume_shares"}
    )[["stock_code", "stock_name", "date", "adj_close", "volume_shares", "turnover_cny"]]


def analytics_frame(obj: dict) -> tuple[pd.DataFrame, list[dict]]:
    block = payload(obj)["data"]["data"][0]
    meta = block["columns"]
    cols = [c["name"] for c in meta]
    frame = pd.DataFrame(block["rows"], columns=cols)
    date_col = next(c for c in cols if c == "日期")
    code_col = next(c for c in cols if c == "Wind代码")
    name_col = next(c for c in cols if c == "证券简称")
    close_col = next(c for c in cols if "不复权收盘价" in c and ".复权方式" not in c)
    adjust_col = next(c for c in cols if c.endswith(".复权方式"))
    volume_col = next(c for c in cols if "成交量" in c)
    amount_col = next(c for c in cols if "成交额" in c)
    mv_col = next(c for c in cols if "总市值" in c)
    currency_col = next(c for c in cols if c == "交易币种")
    out = pd.DataFrame({
        "stock_code": frame[code_col].astype("string"),
        "stock_name": frame[name_col].astype("string"),
        "date": pd.to_datetime(frame[date_col], errors="raise"),
        "close_unadjusted": pd.to_numeric(frame[close_col], errors="raise"),
        "adjustment_label": frame[adjust_col].astype("string"),
        "volume_shares": pd.to_numeric(frame[volume_col], errors="raise"),
        "turnover_reported": pd.to_numeric(frame[amount_col], errors="raise"),
        "market_cap_reported": pd.to_numeric(frame[mv_col], errors="raise"),
        "currency": frame[currency_col].astype("string"),
    })
    units = {c["name"]: c.get("unit") for c in meta}
    amount_unit = units.get(amount_col)
    mv_unit = units.get(mv_col)
    amount_factor = {"元": 1 / 1e8, "万元": 1 / 1e4, "亿元": 1.0}[amount_unit]
    mv_factor = {"元": 1 / 1e8, "万元": 1 / 1e4, "亿元": 1.0, "万亿元": 1e4}[mv_unit]
    out["turnover_100m_cny"] = out["turnover_reported"] * amount_factor
    out["market_cap_100m_cny"] = out["market_cap_reported"] * mv_factor
    return out, meta


def main() -> None:
    for d in [RAW, PROCESSED, AUDIT]:
        d.mkdir(parents=True, exist_ok=True)
    manifest = []
    klines = []
    market_parts = []
    field_meta = []

    for code, name, _ in STOCKS:
        obj = call_wind("stock_data", "get_stock_kline", {
            "windcode": code,
            "begin_date": "20201231",
            "end_date": "20260916",
            "period": "1d",
            "aftime": "1",
            "issusp": "1",
        })
        raw_path = RAW / "kline_hfq" / f"{code}.json"
        sha = save_raw(obj, raw_path)
        kf = kline_frame(obj, code, name)
        klines.append(kf)
        manifest.append({"kind": "kline_hfq", "code": code, "path": str(raw_path.relative_to(PROJECT)), "rows": len(kf), "date_min": str(kf.date.min().date()), "date_max": str(kf.date.max().date()), "sha256": sha})

        for begin, end in WINDOWS:
            question = (
                f"{code}在{begin[:4]}年{int(begin[4:6])}月{int(begin[6:])}日至"
                f"{end[:4]}年{int(end[4:6])}月{int(end[6:])}日期间的每日不复权收盘价、"
                "成交量、成交额和历史总市值，返回每个交易日、字段单位与复权口径"
            )
            obj = call_wind("analytics_data", "get_financial_data", {"question": question, "lang": "CNS"})
            raw_path = RAW / "market_unadjusted" / code / f"{begin}_{end}.json"
            sha = save_raw(obj, raw_path)
            mf, meta = analytics_frame(obj)
            if len(mf) >= 100:
                raise RuntimeError(f"Possible truncation: {code} {begin}-{end} returned {len(mf)} rows")
            market_parts.append(mf)
            field_meta.extend({"code": code, "begin": begin, "end": end, **m} for m in meta)
            manifest.append({"kind": "market_unadjusted", "code": code, "begin": begin, "end": end, "path": str(raw_path.relative_to(PROJECT)), "rows": len(mf), "date_min": str(mf.date.min().date()) if len(mf) else None, "date_max": str(mf.date.max().date()) if len(mf) else None, "sha256": sha})

    kline = pd.concat(klines, ignore_index=True).sort_values(["stock_code", "date"])
    market = pd.concat(market_parts, ignore_index=True).sort_values(["stock_code", "date"])
    for label, frame in [("kline", kline), ("market", market)]:
        if frame.duplicated(["stock_code", "date"]).any():
            raise RuntimeError(f"Duplicate stock-date keys in {label}")

    merged = market.merge(
        kline[["stock_code", "date", "adj_close"]],
        on=["stock_code", "date"], how="outer", validate="one_to_one", indicator=True,
    )
    merged.to_csv(PROCESSED / "wind_daily_20201231_20260916.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(manifest).to_csv(AUDIT / "source_manifest.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(field_meta).drop_duplicates().to_csv(AUDIT / "field_metadata.csv", index=False, encoding="utf-8-sig")
    coverage = merged.groupby("stock_code").agg(
        rows=("date", "size"), date_min=("date", "min"), date_max=("date", "max"),
        missing_unadjusted=("close_unadjusted", lambda s: int(s.isna().sum())),
        missing_adjusted=("adj_close", lambda s: int(s.isna().sum())),
        missing_market_cap=("market_cap_100m_cny", lambda s: int(s.isna().sum())),
    ).reset_index()
    coverage.to_csv(AUDIT / "coverage.csv", index=False, encoding="utf-8-sig")
    (AUDIT / "execution.json").write_text(json.dumps({
        "executed_at": datetime.now().astimezone().isoformat(),
        "source": "Wind金融数据服务",
        "sample_start": "2021-01-01",
        "sample_end": "2026-09-16",
        "support_start": "2020-12-31",
        "kline_params": {"period": "1d", "aftime": "1", "issusp": "1"},
        "analytics_note": "Quarterly windows used because a full-range probe returned only 100 rows.",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(coverage.to_string(index=False))
    print("processed_rows=", len(merged), "merge_status=", merged["_merge"].value_counts().to_dict())


if __name__ == "__main__":
    main()
