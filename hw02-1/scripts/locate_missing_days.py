#!/usr/bin/env python3
"""定位各股票相对共同交易日历缺失的交易日。

背景：新浪日行情只返回该股票实际有交易的日期。若某只股票在某个交易日
没有记录，需要区分两种可能：该股当日停牌（公司行为或重大事项），或者接口
返回缺口。本脚本用"其余股票当日是否有行情"作为判别证据，并输出可复核的
缺失日清单，供 Notebook 第 2 节制定处理规则。

用法：
    cd hw-02 && python scripts/locate_missing_days.py

输出：
    audit/missing_days_akshare.csv  每只股票每个缺失交易日的证据
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT = Path(__file__).resolve().parents[1]
RAW = PROJECT / "data" / "raw" / "akshare" / "sina_unadjusted"
PROCESSED = PROJECT / "data" / "processed"
AUDIT = PROJECT / "audit"

SAMPLE_START = "2021-01-01"
SAMPLE_END = "2026-09-16"


def main() -> None:
    # 研究样本严格取自股票池主表，不使用原始层中的初始候选股票
    master = pd.read_csv(
        PROCESSED / "stock_selection_master.csv", dtype={"stock_code": "string"}
    )
    codes = list(master["stock_code"])

    # 逐只股票读入原始不复权行情，构造各自的交易日集合
    trading_days: dict[str, set[str]] = {}
    for code in codes:
        path = RAW / f"{code}.csv"
        if not path.exists():
            raise FileNotFoundError(f"缺少原始行情文件: {path}")
        frame = pd.read_csv(path)
        trading_days[code] = set(pd.to_datetime(frame["date"]).dt.strftime("%Y-%m-%d"))

    # 共同交易日历 = 全部股票交易日的并集
    calendar: set[str] = set().union(*trading_days.values())
    calendar = {d for d in calendar if SAMPLE_START <= d <= SAMPLE_END}

    rows = []
    for code in codes:
        missing = sorted(calendar - trading_days[code])
        for day in missing:
            others = sum(1 for other in codes if other != code and day in trading_days[other])
            rows.append({
                "stock_code": code,
                "stock_name": master.loc[master["stock_code"] == code, "stock_name"].iloc[0],
                "missing_date": day,
                "other_stocks_with_data": others,
                "other_stocks_total": len(codes) - 1,
                "note": "其余股票当日均有行情，缺口连续时为个股停牌的典型特征",
            })

    out = pd.DataFrame(rows)
    AUDIT.mkdir(parents=True, exist_ok=True)
    out.to_csv(AUDIT / "missing_days_akshare.csv", index=False, encoding="utf-8-sig")

    print(f"共同交易日历（{SAMPLE_START} 至 {SAMPLE_END}）: {len(calendar)} 个交易日")
    for code in codes:
        n = len(calendar & trading_days[code])
        print(f"  {code} 覆盖 {n} 日，缺 {len(calendar) - n} 日")
    print(f"\n缺失日明细已写入: {(AUDIT / 'missing_days_akshare.csv').relative_to(PROJECT)}")
    if not out.empty:
        print(out.to_string(index=False))


if __name__ == "__main__":
    main()
