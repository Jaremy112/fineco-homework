# -*- coding: utf-8 -*-
"""
HW02-2 第一步：企业—年度面板与六项财务指标构造（不依赖行业分类表）

输入（授权本地路径，受限数据，不入库）：
  RAW/资产负债表/FS_Combas.json       2005—2015 合并资产负债表
  RAW/04年资产负债表/FS_Combas.json   2004 年合并资产负债表（平均分母支持）
  RAW/利润表/FS_Comins.json           2005—2015 合并利润表
  RAW/股权性质/EN_EquityNatureAll.json 2004—2015 逐年股权性质

输出：
  PROCESSED/firm_year_panel.csv       企业—年度面板（含六指标、产权分组）
  PROCESSED/sample_flow.csv           样本处理表（各阶段公司数与企业—年度观测数）
  PROCESSED/audit_indicators.csv      六指标逐年有效样本量与描述统计

口径决策（见 DECISIONS.md）：
  - 只保留合并报表（Typrep=A）、年末（Accper=12-31）、A 股（剔除 200/900 前缀 B 股）
  - 平均总资产/权益 = (t 年末 + t-1 年末)/2，t-1 缺失则返回缺失（2005 年用 2004 年末文件）
  - 零/负分母返回缺失并计数，不删除观测
  - 净利润用合并口径 B002000000，不混用归母
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd

RAW = Path("/Users/macbookairzhu/Documents/fineco-homework/hw02-2/data/raw/"
           " 2005—2015 年房地产 A 股上市公司年度数据")
OUT = Path("/Users/macbookairzhu/Documents/fineco-homework/hw02-2/data/processed")
OUT.mkdir(parents=True, exist_ok=True)

# 关键科目编码（来自各表 DES 字段说明，已逐条比对）
BS_FIELDS = {
    "A001000000": "assets",          # 资产总计
    "A002000000": "liabilities",     # 负债合计
    "A002100000": "cur_liabilities", # 流动负债合计
    "A002101000": "st_borrow",       # 短期借款
    "A002201000": "lt_borrow",       # 长期借款
    "A003000000": "equity",          # 所有者权益合计
    "A001101000": "cash",            # 货币资金
}
IS_FIELDS = {
    "B002000000": "net_income",      # 净利润（合并）
    "B002000101": "ni_parent",       # 归母净利润（2007 起，仅备核对）
}

def read_json(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return pd.DataFrame(rows)

def is_a_share(code: str) -> bool:
    # B 股：深市 200xxx、沪市 900xxx
    return not (str(code).startswith("200") or str(code).startswith("900"))

# ---------- 阶段 0：原始读取 ----------
flow = []  # 样本处理表

def pick(*cands):
    """按优先级返回第一个存在的路径。"""
    for c in cands:
        p = RAW / c
        if p.exists():
            return p
    raise FileNotFoundError(f"未找到任一候选: {cands}")

BS_DIR   = pick("资产负债表补充", "资产负债表")          # 2005—2015
IS_DIR   = pick("利润表补充", "利润表")                   # 2005—2015
BS04_P   = pick("资产负债表补充/04", "04年资产负债表补充", "04年资产负债表")  # 2004 年末
EN_P     = pick("股权性质/补充/EN_EquityNatureAll.json",
                "股权性质补充/EN_EquityNatureAll.json",
                "股权性质/EN_EquityNatureAll.json")

bs_raw   = read_json(BS_DIR / "FS_Combas.json")
bs04_raw = read_json(BS04_P / "FS_Combas.json")
inc_raw  = read_json(IS_DIR / "FS_Comins.json")
en_raw   = read_json(EN_P)
flow.append((f"0-0 资产负债表原始行 [{BS_DIR.name}]", len(bs_raw), bs_raw["Stkcd"].nunique()))
flow.append((f"0-1 资产负债表原始行(2004) [{BS04_P.name}]", len(bs04_raw), bs04_raw["Stkcd"].nunique()))
flow.append((f"0-2 利润表原始行 [{IS_DIR.name}]", len(inc_raw), inc_raw["Stkcd"].nunique()))
flow.append(("0-3 股权性质原始行（2004—2015）", len(en_raw), en_raw["Symbol"].nunique()))

# ---------- 阶段 1：合并报表 + 年末 + A 股 ----------
def prep_bs(df, tag):
    d = df[df["Typrep"] == "A"].copy()
    flow.append((f"1-{tag} 筛合并报表(Typrep=A)", len(d), d["Stkcd"].nunique()))
    d = d[d["Accper"].astype(str).str.endswith("12-31")].copy()
    flow.append((f"1-{tag} 筛年末(Accper=12-31)", len(d), d["Stkcd"].nunique()))
    d = d[d["Stkcd"].map(is_a_share)].copy()
    flow.append((f"1-{tag} 剔除 B 股(200/900 前缀)", len(d), d["Stkcd"].nunique()))
    d["fiscal_year"] = d["Accper"].astype(str).str[:4].astype(int)
    return d

bs = prep_bs(bs_raw, "主表")
bs04 = prep_bs(bs04_raw, "04表")

def prep_is(df):
    d = df[df["Typrep"] == "A"].copy()
    flow.append(("1-利润 筛合并报表(Typrep=A)", len(d), d["Stkcd"].nunique()))
    d = d[d["Accper"].astype(str).str.endswith("12-31")].copy()
    flow.append(("1-利润 筛年末(Accper=12-31)", len(d), d["Stkcd"].nunique()))
    d = d[d["Stkcd"].map(is_a_share)].copy()
    flow.append(("1-利润 剔除 B 股", len(d), d["Stkcd"].nunique()))
    d["fiscal_year"] = d["Accper"].astype(str).str[:4].astype(int)
    return d

inc = prep_is(inc_raw)

# ---------- 阶段 2：字段改名与抽取 ----------
def extract(d, mapping, extra=()):
    cols = {k: v for k, v in mapping.items() if k in d.columns}
    out = d[["Stkcd", "fiscal_year"] + list(cols)].rename(columns=cols)
    for c in mapping.values():
        if c not in out.columns:
            out[c] = np.nan
    return out

bsx = extract(bs, BS_FIELDS)
bs04x = extract(bs04, BS_FIELDS)
incx = extract(inc, IS_FIELDS)

for c in BS_FIELDS.values():
    bsx[c] = pd.to_numeric(bsx[c], errors="coerce")
    bs04x[c] = pd.to_numeric(bs04x[c], errors="coerce")
for c in IS_FIELDS.values():
    incx[c] = pd.to_numeric(incx[c], errors="coerce")

# ---------- 阶段 3：合并为候选面板 ----------
# 主键：证券代码 + 会计年度。先检查唯一性
dup_bs = bsx.duplicated(["Stkcd", "fiscal_year"]).sum()
dup_is = incx.duplicated(["Stkcd", "fiscal_year"]).sum()
print(f"[键检查] 资产负债表重复键 {dup_bs} 行；利润表重复键 {dup_is} 行")

panel = bsx.merge(incx[["Stkcd", "fiscal_year", "net_income", "ni_parent"]],
                  on=["Stkcd", "fiscal_year"], how="left", validate="1:1", indicator=True)
flow.append(("3-0 资产负债表年末合并观测", len(bsx), bsx["Stkcd"].nunique()))
flow.append(("3-1 左连利润表后观测", len(panel), panel["Stkcd"].nunique()))
flow.append(("3-2 利润表未匹配观测", int((panel["_merge"] == "left_only").sum()),
             panel.loc[panel["_merge"] == "left_only", "Stkcd"].nunique()))
panel = panel.drop(columns="_merge")

names = (bs.sort_values("fiscal_year")
           .groupby("Stkcd")["ShortName"].last().to_dict())

# ---------- 阶段 4：上一期分母（2004 年末来自独立文件） ----------
prev = bsx[["Stkcd", "fiscal_year", "assets", "equity"]].copy()
prev["fiscal_year"] = prev["fiscal_year"] + 1
prev = prev.rename(columns={"assets": "assets_prev", "equity": "equity_prev"})
prev04 = bs04x[["Stkcd", "assets", "equity"]].copy()
prev04["fiscal_year"] = 2005
prev04 = prev04.rename(columns={"assets": "assets_prev", "equity": "equity_prev"})
prev_all = pd.concat([prev04, prev[prev["fiscal_year"] > 2005]], ignore_index=True)

panel = panel.merge(prev_all, on=["Stkcd", "fiscal_year"], how="left", validate="1:1")
n_prev_missing = panel["assets_prev"].isna().sum()
flow.append(("4-0 上年末分母缺失观测", int(n_prev_missing),
             panel.loc[panel["assets_prev"].isna(), "Stkcd"].nunique()))

# ---------- 阶段 5：六项指标 ----------
def safe_div(num, den, zero_as_na=True):
    den = pd.to_numeric(den, errors="coerce")
    bad = den.isna() | (den == 0)
    if not zero_as_na:
        bad = den.isna()
    out = num / den.where(~bad)
    return out, int(bad.sum())

panel["leverage"], n0 = safe_div(panel["liabilities"], panel["assets"])
panel["bankloan"], n1 = safe_div(panel["st_borrow"] + panel["lt_borrow"], panel["liabilities"])
panel["st_debt_ratio"], n2 = safe_div(panel["cur_liabilities"], panel["liabilities"])
panel["cash_ta"], n3 = safe_div(panel["cash"], panel["assets"])

avg_assets = (panel["assets"] + panel["assets_prev"]) / 2
avg_equity = (panel["equity"] + panel["equity_prev"]) / 2
panel["roa"], n4 = safe_div(panel["net_income"], avg_assets)
panel["roe"], n5 = safe_div(panel["net_income"], avg_equity)

# bankloan 分子缺失不按零处理：分子任一缺失则结果缺失
bl_missing = panel["st_borrow"].isna() | panel["lt_borrow"].isna()
panel.loc[bl_missing, "bankloan"] = np.nan

den_stats = pd.DataFrame({
    "指标": ["资产负债率", "bankloan", "短期负债占比", "Cash_TA", "ROA", "ROE"],
    "分母": ["总资产", "总负债", "总负债", "总资产", "平均总资产", "平均所有者权益"],
    "分母缺失或为零的观测数": [n0, n1, n2, n3, n4, n5],
})
print("\n=== 分母诊断（零/缺失一律返回缺失，不删观测）===")
print(den_stats.to_string(index=False))

# ---------- 阶段 6：产权分组（逐年） ----------
en = en_raw.copy()
en["year"] = en["EndDate"].astype(str).str[:4].astype(int)
en = en[["Symbol", "year", "EquityNature", "EquityNatureID",
         "ActualControllerName", "ActualControllerNatureID"]].rename(columns={"Symbol": "Stkcd"})

def own_group(x):
    """产权分类规则：非国有 ≠ 民营。
    国企→国有；纯民营→民营；外资/其他/复合→其他；缺失→不明。"""
    if pd.isna(x):
        return "不明"
    x = str(x).strip()
    if x == "国企":
        return "国有"
    if x == "民营":
        return "民营"
    if x in ("外资", "其他"):
        return "其他"
    if "," in x:                     # 复合性质，如"民营,外资"
        parts = [p.strip() for p in x.split(",")]
        if "国企" in parts:
            return "国有"
        if "民营" in parts and len(set(parts)) == 1:
            return "民营"
        return "其他"
    return "其他"

en["ownership"] = en["EquityNature"].map(own_group)
panel = panel.merge(en[["Stkcd", "year", "ownership", "EquityNature", "ActualControllerName"]],
                    how="left", left_on=["Stkcd", "fiscal_year"], right_on=["Stkcd", "year"],
                    validate="1:1").drop(columns="year")
panel["ownership"] = panel["ownership"].fillna("不明")
flow.append(("6-0 产权缺失(归入不明)观测", int((panel["ownership"] == "不明").sum()),
             panel.loc[panel["ownership"] == "不明", "Stkcd"].nunique()))

# ---------- 阶段 5.5：并入年度表的上市状态与行业（逐年，不做覆盖） ----------
ANN = RAW / "行业分类表" / "STK_LISTEDCOINFOANL.json"
if ANN.exists():
    ann = read_json(ANN)
    ann["Symbol"] = ann["Symbol"].astype(str).str.zfill(6)
    ann["year"] = ann["EndDate"].astype(str).str[:4].astype(int)
    ann["IndustryCode"] = ann["IndustryCode"].astype(str).str.upper().str.strip()
    # 分类标准跨年映射：≤2011 用 2001 版(J*=房地产业)；≥2012 用 2012 版(K70=房地产业，J* 已变为金融业)
    ann["is_re"] = np.where(ann["year"] <= 2011,
                            ann["IndustryCode"].str.startswith("J"),
                            ann["IndustryCode"].str.startswith("K70"))
    ann["std_ver"] = np.where(ann["year"] <= 2011, "证监会2001版", "证监会2012版")
    panel = panel.merge(
        ann[["Symbol", "year", "is_re", "std_ver", "IndustryCode", "IndustryName", "LISTINGSTATE"]]
        .rename(columns={"Symbol": "Stkcd", "year": "fiscal_year",
                         "LISTINGSTATE": "listing_state"}),
        on=["Stkcd", "fiscal_year"], how="left", validate="1:1")
    flow.append(("5-0 并入年度表(上市状态/行业/标准版本)", int(panel["is_re"].notna().sum()),
                 panel.loc[panel["is_re"].notna(), "Stkcd"].nunique()))
    flow.append(("5-1 年度表未覆盖(无法判定行业)", int(panel["is_re"].isna().sum()),
                 panel.loc[panel["is_re"].isna(), "Stkcd"].nunique()))
    # 上市状态分布（保留 ST/暂停上市，基础库不提前剔除）
    print("\n=== 各年年末上市状态（并入面板后）===")
    print(pd.crosstab(panel["fiscal_year"], panel["listing_state"]).to_string())
else:
    panel["is_re"] = np.nan
    print("[提示] 未找到年度表，跳过上市状态与行业并入")
flow.append(("7-0 最终企业—年度面板", len(panel), panel["Stkcd"].nunique()))

# ---------- 输出 ----------
panel.to_csv(OUT / "firm_year_panel.csv", index=False, encoding="utf-8-sig")
flow_df = pd.DataFrame(flow, columns=["阶段", "企业—年度观测数", "公司数"])
flow_df.to_csv(OUT / "sample_flow.csv", index=False, encoding="utf-8-sig")

IND = ["leverage", "bankloan", "st_debt_ratio", "roa", "roe", "cash_ta"]
LBL = {"leverage": "资产负债率", "bankloan": "bankloan", "st_debt_ratio": "短期负债占比",
       "roa": "ROA", "roe": "ROE", "cash_ta": "Cash_TA"}
rows = []
for y, g in panel.groupby("fiscal_year"):
    for ind in IND:
        s = g[ind].dropna()
        rows.append({"年度": y, "指标": LBL[ind], "有效样本量": len(s),
                     "均值": s.mean(), "中位数": s.median(), "标准差": s.std(),
                     "最小": s.min(), "最大": s.max()})
audit = pd.DataFrame(rows)
audit.to_csv(OUT / "audit_indicators.csv", index=False, encoding="utf-8-sig")

print("\n=== 样本处理表 ===")
print(flow_df.to_string(index=False))

print("\n=== 逐年公司数与产权结构（尚未按行业筛选）===")
own_tab = (panel.groupby(["fiscal_year", "ownership"])["Stkcd"].nunique()
           .unstack(fill_value=0))
tot = own_tab.sum(axis=1)
own_tab["合计"] = tot
for c in ["国有", "民营", "其他", "不明"]:
    if c in own_tab:
        own_tab[f"{c}占比%"] = (own_tab[c] / tot * 100).round(1)
print(own_tab.to_string())

print("\n=== 六指标逐年均值（预览，前 3 个指标）===")
prev_ = audit[audit["指标"].isin(["资产负债率", "ROA", "ROE"])].copy()
for c in ["均值", "中位数", "标准差", "最小", "最大"]:
    prev_[c] = prev_[c].round(4)
print(prev_.to_string(index=False))

print(f"\n输出已写入: {OUT}")
print(f"面板: {len(panel)} 行 × {panel['Stkcd'].nunique()} 家，年度 {panel['fiscal_year'].min()}—{panel['fiscal_year'].max()}")
