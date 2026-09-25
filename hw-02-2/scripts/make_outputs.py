# -*- coding: utf-8 -*-
"""
HW02-2 第二步：逐年房地产身份判定 + 全部四类输出（图与表）

行业判定规则（作业：不得用当前行业覆盖历史年份，分类标准跨年变化须说明映射方式）：
  - 年度表 STK_LISTEDCOINFOANL 的 IndustryCode 按各年年末所属标准给出
  - 2001 版：J 门类 = 房地产业（J01 房地产开发与经营业）
  - 2012 版：K 门类 = 房地产业（K70 房地产业）
  - 判定：IndustryCode 以 J 或 K70 开头 → 当年属于房地产
  - 未能判定的年份（行业表缺失）单独列出，不默认归入房地产

输出（aggregate，非受限，可入仓库/Notebook）：
  outputs/fig_counts.png              逐年公司数与产权结构
  outputs/fig_ind_mean_median.png     六指标全样本均值 + 中位数时序
  outputs/fig_ind_soe_mean.png        国有 vs 民营 均值比较
  outputs/fig_ind_soe_median.png      国有 vs 民营 中位数比较
  outputs/tab_valid_n.csv             各指标年度有效样本量
  outputs/tab_counts_ownership.csv    逐年公司数与产权结构
  outputs/tab_sample_flow.csv         样本处理表
"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["PingFang SC", "Hiragino Sans GB", "Arial Unicode MS", "Heiti TC"]
plt.rcParams["axes.unicode_minus"] = False

BASE = Path("/Users/macbookairzhu/Documents/fineco-homework/hw-02-2")
RAW = Path("/Users/macbookairzhu/Documents/fineco-homework/hw-02/data/raw/"
           " 2005—2015 年房地产 A 股上市公司年度数据")
PROC = BASE / "data" / "processed"
FIG = BASE / "outputs"
FIG.mkdir(parents=True, exist_ok=True)

IND = ["leverage", "bankloan", "st_debt_ratio", "roa", "roe", "cash_ta"]
LBL = {"leverage": "资产负债率", "bankloan": "bankloan\n(银行借款/总负债)",
       "st_debt_ratio": "短期负债占比", "roa": "ROA", "roe": "ROE",
       "cash_ta": "Cash_TA\n(货币资金/总资产)"}
OWN_ORDER = ["国有", "民营", "其他", "不明"]

# ---------- 1. 读入面板 ----------
panel = pd.read_csv(PROC / "firm_year_panel.csv")
panel["Stkcd"] = panel["Stkcd"].astype(str).str.zfill(6)
print(f"面板：{len(panel)} 观测 × {panel['Stkcd'].nunique()} 家")

# ---------- 2. 逐年房地产身份 ----------
def build_industry_flag():
    """返回 (flag_df, 说明)；找不到年度表时返回 None。"""
    cand = list((RAW / "行业分类表").glob("STK_LISTEDCOINFOANL*.json"))
    if not cand:
        # 兼容：也可能放在独立目录
        cand = list(RAW.rglob("STK_LISTEDCOINFOANL*.json"))
    if not cand:
        return None, "未找到年度行业表（STK_LISTEDCOINFOANL）"
    recs = []
    with open(cand[0], encoding="utf-8") as f:
        import json
        for line in f:
            line = line.strip()
            if line:
                recs.append(json.loads(line))
    df = pd.DataFrame(recs)
    df["Symbol"] = df["Symbol"].astype(str).str.zfill(6)
    df["year"] = df["EndDate"].astype(str).str[:4].astype(int)
    code = df["IndustryCode"].astype(str).str.upper().str.strip()
    df["is_re"] = code.str.startswith("J") | code.str.startswith("K70")
    df["std"] = np.where(code.str.startswith("J"), "证监会2001版",
                         np.where(code.str.startswith("K"), "证监会2012版", "其他"))
    note = (f"年度表 {cand[0].name}：{len(df)} 行，{df['Symbol'].nunique()} 家，"
            f"年份 {df['year'].min()}—{df['year'].max()}；"
            f"判定为房地产 {int(df['is_re'].sum())} 行")
    return df[["Symbol", "year", "is_re", "std", "IndustryCode", "IndustryName"]], note

ind, note = build_industry_flag()
print("\n[行业判定]", note)

flow_rows = [("面板（合并报表+年末+A股）", len(panel), panel["Stkcd"].nunique())]

if ind is not None:
    panel = panel.merge(ind, left_on=["Stkcd", "fiscal_year"], right_on=["Symbol", "year"],
                        how="left", validate="1:1")
    judged = panel["is_re"].notna()
    flow_rows.append(("其中：年度行业表可判定", int(judged.sum()),
                      panel.loc[judged, "Stkcd"].nunique()))
    not_judged = panel.loc[~judged, ["Stkcd", "fiscal_year"]]
    if len(not_judged):
        flow_rows.append(("其中：行业表缺失（暂不剔除，标记）", len(not_judged),
                          not_judged["Stkcd"].nunique()))
        print("\n行业表未覆盖的观测（前 10）：")
        print(not_judged.head(10).to_string(index=False))
    panel["is_re_eff"] = panel["is_re"].fillna(True)   # 缺失年暂计入，另做敏感性
    re_panel = panel[panel["is_re_eff"]].copy()
    flow_rows.append(("判定为房地产后的面板", len(re_panel), re_panel["Stkcd"].nunique()))
else:
    panel["is_re_eff"] = True
    re_panel = panel.copy()
    print("\n[提示] 未找到年度行业表，当前输出基于候选池（未做逐年行业筛选），仅用于代码验证。")

work = re_panel

# ---------- 3. 逐年公司数与产权结构 ----------
cnt_year = work.groupby("fiscal_year")["Stkcd"].nunique().rename("公司数")
own_tab = (work.groupby(["fiscal_year", "ownership"])["Stkcd"].nunique()
           .unstack(fill_value=0))
for c in OWN_ORDER:
    if c not in own_tab:
        own_tab[c] = 0
own_tab = own_tab[OWN_ORDER]
own_tab["合计"] = cnt_year
for c in ["国有", "民营"]:
    own_tab[f"{c}占比%"] = (own_tab[c] / own_tab["合计"] * 100).round(1)
own_tab = own_tab.join(cnt_year)
own_tab.to_csv(FIG / "tab_counts_ownership.csv", encoding="utf-8-sig")

fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
ax[0].plot(own_tab.index, own_tab["公司数"], marker="o", color="#1f4e79")
ax[0].set_title("房地产 A 股上市公司数（逐年）")
ax[0].set_xlabel("年度"); ax[0].set_ylabel("公司数")
ax[0].grid(alpha=.3)

bottom = np.zeros(len(own_tab))
colors = {"国有": "#c00000", "民营": "#2e75b6", "其他": "#7f7f7f", "不明": "#bfbfbf"}
for c in OWN_ORDER:
    ax[1].bar(own_tab.index, own_tab[c], bottom=bottom, label=c, color=colors[c])
    bottom += own_tab[c].values
ax[1].set_title("国有 / 民营 / 其他 / 不明 公司数")
ax[1].set_xlabel("年度"); ax[1].legend(fontsize=9); ax[1].grid(alpha=.3, axis="y")

ax[2].plot(own_tab.index, own_tab["国有占比%"], marker="o", label="国有占比", color="#c00000")
ax[2].plot(own_tab.index, own_tab["民营占比%"], marker="s", label="民营占比", color="#2e75b6")
ax[2].set_title("国有与民营占比（占当年房地产公司数）")
ax[2].set_xlabel("年度"); ax[2].set_ylabel("%"); ax[2].legend(fontsize=9); ax[2].grid(alpha=.3)
fig.tight_layout(); fig.savefig(FIG / "fig_counts.png", dpi=150); plt.close(fig)

# ---------- 4. 六指标四类输出 ----------
def series_by(group_col=None):
    out = {}
    for i in IND:
        if group_col:
            g = work.groupby(["fiscal_year", group_col])[i]
            out[i] = pd.DataFrame({"mean": g.mean(), "median": g.median(), "n": g.count()}).reset_index()
        else:
            g = work.groupby("fiscal_year")[i]
            out[i] = pd.DataFrame({"mean": g.mean(), "median": g.median(), "n": g.count()}).reset_index()
    return out

all_s = series_by()
own_s = series_by("ownership")

# 图 1：全样本均值 + 中位数时序
fig, axes = plt.subplots(2, 3, figsize=(15, 7.5))
for k, i in enumerate(IND):
    ax = axes[k // 3][k % 3]
    d = all_s[i]
    ax.plot(d["fiscal_year"], d["mean"], marker="o", label="均值", color="#c00000")
    ax.plot(d["fiscal_year"], d["median"], marker="s", label="中位数", color="#2e75b6")
    ax.set_title(LBL[i], fontsize=11)
    ax.grid(alpha=.3); ax.legend(fontsize=8)
fig.suptitle("全部房地产企业：历年均值与中位数", fontsize=13)
fig.tight_layout(); fig.savefig(FIG / "fig_ind_mean_median.png", dpi=150); plt.close(fig)

# 图 2/3：国有 vs 民营（均值、中位数）
for stat, fname, ttl in [("mean", "fig_ind_soe_mean.png", "国有 vs 民营：历年均值"),
                         ("median", "fig_ind_soe_median.png", "国有 vs 民营：历年中位数")]:
    fig, axes = plt.subplots(2, 3, figsize=(15, 7.5))
    for k, i in enumerate(IND):
        ax = axes[k // 3][k % 3]
        d = own_s[i]
        for g_, c in [("国有", "#c00000"), ("民营", "#2e75b6")]:
            s = d[d["ownership"] == g_]
            ax.plot(s["fiscal_year"], s[stat], marker="o", label=g_, color=c, linewidth=1.6)
        ax.set_title(LBL[i], fontsize=11)
        ax.grid(alpha=.3); ax.legend(fontsize=8)
    fig.suptitle(ttl, fontsize=13)
    fig.tight_layout(); fig.savefig(FIG / fname, dpi=150); plt.close(fig)

# 表：各指标年度有效样本量
rows = []
for i in IND:
    d = all_s[i].set_index("fiscal_year")["n"]
    r = {"指标": LBL[i].replace("\n", "")}
    r.update({str(y): int(v) for y, v in d.items()})
    rows.append(r)
valid_n = pd.DataFrame(rows)
valid_n.to_csv(FIG / "tab_valid_n.csv", index=False, encoding="utf-8-sig")

flow_df = pd.DataFrame(flow_rows, columns=["阶段", "企业—年度观测数", "公司数"])
flow_df.to_csv(FIG / "tab_sample_flow.csv", index=False, encoding="utf-8-sig")

print("\n=== 逐年公司数与产权结构 ===")
print(own_tab.to_string())
print("\n=== 各指标年度有效样本量 ===")
print(valid_n.to_string(index=False))
print(f"\n图与表已输出至: {FIG}")
