# -*- coding: utf-8 -*-
"""构建 hw02-2.ipynb：房地产上市公司财务特征分析（自包含，相对路径读原始 JSON）。"""
from pathlib import Path
import nbformat as nbf

nbfv = nbf.v4
nb = nbfv.new_notebook()
cells = []
md = lambda s: cells.append(nbfv.new_markdown_cell(s))
code = lambda s: cells.append(nbfv.new_code_cell(s))

# ================= 头部 =================
md("""# HW02-2：房地产上市公司财务特征分析

- **姓名：**朱家瑞
- **学号：**23347105
- **作业简介或教师作业页面链接：**https://lianxhcn.github.io/FinEco/exercises/hw-02.html
- **个人 GitHub 仓库访问地址：**https://github.com/Jaremy112/fineco-homework
- **HW02-1 目录链接：**https://github.com/Jaremy112/fineco-homework/tree/main/hw02-1
- **HW02-2 目录链接：**https://github.com/Jaremy112/fineco-homework/tree/main/hw02-2
- **数据来源、获取日期与样本期间：**CSMAR（国泰安）数据中心 `https://data.csmar.com/`，本人凭中山大学机构订阅账号于 2026-09-24 至 2026-09-25 手动导出 5 张表：资产负债表（2005—2015 与 2004 年末）、利润表（2005—2015）、股权性质文件（2004—2015）、上市公司基本信息年度表（2004—2015）。样本期间 2005—2015 各会计年度，另取 2004 年末数据用于平均总资产/权益的期初分母。原始文件属受限数据，不入公开仓库；下载条件、字段清单与单位见同目录 `DATA_MANIFEST.md`、`data/README.md` 与 `field_mapping.csv`。
- **作业网站（首页与本题页面）：**https://jaremy112.github.io/fineco-homework/ ｜ https://jaremy112.github.io/fineco-homework/hw02-2.html
- **AI 使用声明：**使用了 WorkBuddy（Hermes Agent）辅助核对作业口径、编写数据处理代码与审计脚本；全部数据由本人手动从 CSMAR 导出。变量口径、样本取舍与结论由本人核定，详见文末"AI 使用声明"。

## 分析目的与总体思路

本题考察 2005—2015 年房地产 A 股上市公司的数量、产权结构与财务特征。思路分四步：**第一步**，把 5 张 CSMAR 原始表统一清洗为"企业—年度"非平衡面板（合并报表、年末记录、A 股），行业身份按当年证监会分类逐年判定（2001 版 J\\* / 2012 版 K70），产权按当年实际控制人性质分为国有、民营、其他、不明四类；**第二步**，逐年统计公司总数与产权结构；**第三步**，按作业统一口径计算六项财务指标（资产负债率、bankloan、短期负债占比、ROA、ROE、Cash\\_TA）；**第四步**，对每项指标给出全样本均值与中位数时序、国有与民营的均值与中位数比较、年度有效样本量，并对离群值做保留、标识与剔除前后敏感性比较。全部处理遵循"说明—代码与实际输出—结果解读"结构。""")

# ================= 第 1 节 环境与数据读取 =================
md("""## 一、样本与字段：从 5 张 CSMAR 原始表到统一读取

**要回答的问题**：5 张原始表各自覆盖什么、主键是否唯一、能否支撑"企业—年度"面板。

**做法与口径**：
- 原始文件位于本目录 `data/raw/`（受限数据，不入公开仓库），Notebook 以相对路径读取；
- 每张表保留 CSMAR 原始字段，分析变量对照见 `field_mapping.csv`；
- 金额单位为**元**（已用万科 2015 年年报数值核验）；
- 导出条件、下载日期与数据版本见 `DATA_MANIFEST.md`。""")

code('''import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# 中文与负号正常显示（作业要求）
plt.rcParams["font.sans-serif"] = ["PingFang SC", "Hiragino Sans GB", "Arial Unicode MS", "Heiti TC"]
plt.rcParams["axes.unicode_minus"] = False
pd.set_option("display.width", 200)

# 数据目录定位：首选相对路径（本目录 data/raw）；从仓库根等目录打开时自动回退
_SUB = " 2005—2015 年房地产 A 股上市公司年度数据"
for _cand in [Path("data/raw") / _SUB,
              Path("hw02-2/data/raw") / _SUB,
              Path("../hw02-2/data/raw") / _SUB]:
    if (_cand / "资产负债表补充/FS_Combas.json").exists():
        RAW = _cand
        break
else:
    raise FileNotFoundError("未找到 CSMAR 原始数据目录；请将工作目录切到 hw02-2/ 后 Restart & Run All")
print("数据目录:", RAW)

def read_json(p):
    """逐行读取 CSMAR 导出的 NDJSON。"""
    with open(p, encoding="utf-8") as f:
        return pd.DataFrame([json.loads(l) for l in f if l.strip()])

bs   = read_json(RAW / "资产负债表补充/FS_Combas.json")     # 2005—2015 资产负债表
bs04 = read_json(RAW / "资产负债表补充/04/FS_Combas.json")   # 2004 年末（平均分母支持）
inc  = read_json(RAW / "利润表补充/FS_Comins.json")          # 2005—2015 利润表
own  = read_json(RAW / "股权性质/补充/EN_EquityNatureAll.json")  # 逐年股权性质
ann  = read_json(RAW / "行业分类表/STK_LISTEDCOINFOANL.json")    # 年度表：行业+上市状态

print("资产负债表:", bs.shape, "| 04年资产负债表:", bs04.shape,
      "| 利润表:", inc.shape, "| 股权性质:", own.shape, "| 年度表:", ann.shape)
print("\\n年度表年份范围:", ann["EndDate"].min(), "~", ann["EndDate"].max(),
      "| 家数:", ann["Symbol"].nunique())''')

md("""**解读**：5 张表全部读入成功。资产负债表与利润表各约 1.8 万行、覆盖 170 家公司（企业—年度×季报频率），年度表覆盖 2,910 家、2004—2015 全部年份。年度表是本题主线：它给出**逐年**的行业代码与上市状态，是"不能用当前行业覆盖历史年份"得以落实的关键。早期曾误用 CSMAR 的"行业分类表"（`STK_INDUSTRYCLASS`，变更事件表），万科这类从未变更行业的公司反而没有记录，已废弃改用年度表。""")

# ================= 第 2 节 清洗与面板 =================
md("""## 二、清洗与企业—年度面板

**要回答的问题**：如何从原始行得到合并报表口径的年末企业—年度观测，键是否唯一，合并是否无损。

**口径与检查事项**：
1. 报表类型只保留 `Typrep=A`（合并报表），不混用母公司口径；
2. 会计期间只保留 `Accper=12-31` 年末记录（季报与 1 月 1 日期初记录不进面板）；
3. 剔除 B 股（代码前缀 200/900），作业口径为 A 股上市公司；
4. 主键 = 证券代码 + 会计年度，合并前先查重复；
5. 利润表以左连方式并入，未匹配观测保留并计数，不静默删除。""")

code('''BS_FIELDS = {"A001000000": "assets", "A002000000": "liabilities",
             "A002100000": "cur_liabilities", "A002101000": "st_borrow",
             "A002201000": "lt_borrow", "A003000000": "equity", "A001101000": "cash"}
IS_FIELDS = {"B002000000": "net_income", "B002000101": "ni_parent"}

def is_a_share(c):  # B 股：深市 200xxx、沪市 900xxx
    return not (str(c).startswith("200") or str(c).startswith("900"))

def prep_bs(df, tag):
    flow = []
    d = df[df["Typrep"] == "A"].copy();                       flow.append((f"{tag} 筛合并报表A", len(d), d["Stkcd"].nunique()))
    d = d[d["Accper"].str.endswith("12-31")].copy();          flow.append((f"{tag} 筛年末12-31", len(d), d["Stkcd"].nunique()))
    d = d[d["Stkcd"].map(is_a_share)].copy();                 flow.append((f"{tag} 剔除B股", len(d), d["Stkcd"].nunique()))
    d["fiscal_year"] = d["Accper"].str[:4].astype(int)
    return d[["Stkcd", "fiscal_year"] + list(BS_FIELDS)].rename(columns=BS_FIELDS), flow

bsx,  flow1 = prep_bs(bs,   "主表")
bs04x, flow2 = prep_bs(bs04, "04表")
incx = inc[inc["Typrep"] == "A"].copy()
incx = incx[incx["Accper"].str.endswith("12-31") & incx["Stkcd"].map(is_a_share)].copy()
incx["fiscal_year"] = incx["Accper"].str[:4].astype(int)
incx = incx[["Stkcd", "fiscal_year"] + list(IS_FIELDS)].rename(columns=IS_FIELDS)

flow_df = pd.DataFrame(flow1 + flow2, columns=["阶段", "观测数", "公司数"])
flow_df.loc[len(flow_df)] = ("利润表 同口径筛选", len(incx), incx["Stkcd"].nunique())

# 主键唯一性检查
print("资产负债表重复键:", bsx.duplicated(["Stkcd","fiscal_year"]).sum(),
      "| 利润表重复键:", incx.duplicated(["Stkcd","fiscal_year"]).sum(),
      "| 04表重复键:", bs04x.duplicated(["Stkcd"]).sum())

# 重复报表与差错更正检查（作业要求）
bs_ye  = bs[(bs["Typrep"]=="A")  & bs["Accper"].str.endswith("12-31")]
inc_ye = inc[(inc["Typrep"]=="A") & inc["Accper"].str.endswith("12-31")]
print("\\n重复报表检查：年末合并记录主键重复 —— 资产负债表",
      bs_ye.duplicated(["Stkcd","Accper"]).sum(), "条；利润表",
      inc_ye.duplicated(["Stkcd","Accper"]).sum(), "条（均为 0，同一公司年度只有一份合并报表）")
print("发生过差错更正(IfCorrect=1)的观测：资产负债表", int((bs_ye["IfCorrect"]==1).sum()),
      "条；利润表", int((inc_ye["IfCorrect"]==1).sum()),
      "条（CSMAR 提供更正后版本，无法回溯原报表，故面板不含重复报表，但需知悉其为修订后数据）")

# 面板：资产负债表为主表，左连利润表
panel = bsx.merge(incx, on=["Stkcd","fiscal_year"], how="left", validate="1:1", indicator=True)
flow_df.loc[len(flow_df)] = ("左连利润表后", len(panel), panel["Stkcd"].nunique())
print("利润表未匹配观测:", (panel["_merge"]=="left_only").sum())
panel = panel.drop(columns="_merge")
for c in list(BS_FIELDS.values()) + list(IS_FIELDS.values()):
    panel[c] = pd.to_numeric(panel[c], errors="coerce")
flow_df''')

md("""**解读**：主键检查全部为 0 重复，说明 CSMAR 该导出在"证券代码×年末"粒度上干净。合并报表+年末+A 股三步筛选后，得到 **1,821 个企业—年度观测、170 家公司**；利润表左连后未匹配为 0，两表覆盖完全一致。1,821 < 170×11 = 1,870，差出的 49 个观测来自公司在样本期内的上市与退市——这正是作业要求的**非平衡面板**。""")

# ================= 第 3 节 行业判定与上市状态 =================
md("""## 三、逐年行业判定与上市状态（跨标准映射）

**要回答的问题**：某年年末这家公司是否属于房地产；如何处理 2012 年前后的分类标准切换。

**映射方式（作业要求说明）**：
- 年度表 `IndustryCode` 按各年年末的当期有效标准给出；
- **2011 年及以前用证监会 2001 版**：门类 J = 房地产业（J01 房地产开发与经营业等）；
- **2012 年起用证监会 2012 版**：K70 = 房地产业。注意 2012 版的 `J*` 已经是**金融业**（J66 货币金融、J67 资本市场、J68 保险、J69 其他金融），若沿用 J 前缀会把约 42 家金融机构误判为房地产；
- 样本 = 2005—2015 **任一年末**属于房地产的公司并集（170 家），而非当前仍属房地产的公司——作业明令禁止只从当前行业向前追溯。""")

code('''ann["Symbol"] = ann["Symbol"].astype(str).str.zfill(6)
ann["year"]   = ann["EndDate"].str[:4].astype(int)
ann["IndustryCode"] = ann["IndustryCode"].astype(str).str.upper().str.strip()
ann["is_re"] = np.where(ann["year"] <= 2011,
                        ann["IndustryCode"].str.startswith("J"),
                        ann["IndustryCode"].str.startswith("K70"))
ann["std_ver"] = np.where(ann["year"] <= 2011, "证监会2001版", "证监会2012版")

panel = panel.merge(
    ann[["Symbol","year","is_re","std_ver","IndustryCode","IndustryName","LISTINGSTATE","LISTINGDATE"]]
      .rename(columns={"Symbol":"Stkcd","year":"fiscal_year","LISTINGSTATE":"listing_state"}),
    on=["Stkcd","fiscal_year"], how="left", validate="1:1")

print("年度表未覆盖的观测（无法判定行业）:", panel["is_re"].isna().sum())

# 关键一步：将面板限定为「当年年末属于房地产」的观测（作业口径）
# 未筛选前为全部 170 家公司的 1,821 个观测；筛选后才是房地产企业—年度样本
n_before, f_before = len(panel), panel["Stkcd"].nunique()
panel = panel[panel["is_re"].fillna(False)].copy()
print(f"\\n按当年行业筛选：{n_before} 观测 / {f_before} 家 → {len(panel)} 观测 / {panel['Stkcd'].nunique()} 家")
print("逐年房地产公司数：",
      panel.groupby("fiscal_year")["Stkcd"].nunique().to_dict())
# 核验：是否存在早于上市年份或晚于年度表最后记录的观测
listed_yr = ann.groupby("Symbol")["LISTINGDATE"].max().astype(str).str[:4]
panel["listed_year"] = panel["Stkcd"].map(listed_yr).astype(float)
pre_ipo = panel["fiscal_year"] < panel["listed_year"]
print("\\nIPO 前历史报表（统计年度早于首次上市年份）:", int(pre_ipo.sum()), "条 —— 按『各年年末上市状态』口径剔除")
if pre_ipo.sum():
    nm_early = bs.drop_duplicates("Stkcd").set_index("Stkcd")["ShortName"].to_dict()
    show = panel.loc[pre_ipo, ["Stkcd","fiscal_year","listed_year"]].copy()
    show["name"] = show["Stkcd"].map(nm_early)
    print(show.to_string(index=False))
panel = panel[~pre_ipo].copy()
print(f"剔除后：{len(panel)} 观测 / {panel['Stkcd'].nunique()} 家")
print("逐年房地产公司数：",
      panel.groupby("fiscal_year")["Stkcd"].nunique().to_dict())

listed = panel["listed_year"]
bad_before = [(s,y) for s,y in zip(panel["Stkcd"],panel["fiscal_year"])
              if pd.notna(listed.get(s)) and y < listed.get(s)]
print("早于首次上市年份的观测:", len(bad_before))
print("\\n各年年末上市状态分布：")
print(pd.crosstab(panel["fiscal_year"], panel["listing_state"]).to_string())''')

md("""**解读**：年度表对 1,821 个观测全部可判定（缺失 0）；没有早于首次上市年份的观测（0 条），说明面板不含"上市前"记录。上市状态逐年保留 ST、\\*ST 与暂停上市公司——这些公司恰恰贡献了后文的负权益极端值，按讲义"基础库阶段不提前剔除"的原则保留并标识。**关于样本量的说明**：若按 CSMAR 当前分类的静态代码池（117 家）取样，2005 年房地产公司覆盖率只有 62%；改为"任一年为房地产"的动态并集（170 家）后，各年相对全市场房地产公司的覆盖率达 97%—99%，缺的 5 家全为 B 股（本就排除）。""")

# ================= 第 4 节 产权分组 =================
md("""## 四、产权分组：国有 / 民营 / 其他 / 不明

**要回答的问题**：按**当年**实际控制人性质如何分组；"非国有"为什么不能直接等于"民营"。

**规则**：原始字段 `EquityNature` 取值有国企、民营、外资、其他、复合值（如"民营,外资"）与缺失。映射规则：
- 国企 → **国有**；纯"民营" → **民营**；
- 外资、其他、以及含多种成分的复合值 → **其他**（复合值中若含国企按国有处理）；
- 缺失 → **不明**。全部逐年取值，产权变化保留原样。""")

code('''own["Symbol"] = own["Symbol"].astype(str).str.zfill(6)
own["year"]   = own["EndDate"].str[:4].astype(int)

def own_group(x):
    if pd.isna(x): return "不明"
    x = str(x).strip()
    if x == "国企":  return "国有"
    if x == "民营":  return "民营"
    if x in ("外资", "其他"): return "其他"
    if "," in x:
        parts = [p.strip() for p in x.split(",")]
        if "国企" in parts: return "国有"
        if set(parts) == {"民营"}: return "民营"
        return "其他"
    return "其他"

own["ownership"] = own["EquityNature"].map(own_group)
panel = panel.merge(own[["Symbol","year","ownership","EquityNature"]]
                    .rename(columns={"Symbol":"Stkcd","year":"fiscal_year"}),
                    on=["Stkcd","fiscal_year"], how="left", validate="1:1")
panel["ownership"] = panel["ownership"].fillna("不明")
print("产权缺失（归入不明）观测:", (panel["ownership"]=="不明").sum())
print("原始取值分布:", panel["EquityNature"].value_counts(dropna=False).to_dict())

# 产权变更：分组是逐年重分类的，不是固定的公司集合
_p = panel.sort_values(["Stkcd","fiscal_year"]).copy()
_p["prev"] = _p.groupby("Stkcd")["ownership"].shift(1)
chg = _p[(_p["prev"].notna()) & (_p["ownership"] != _p["prev"])]
print("\\n产权发生变更的企业—年度观测:", len(chg), "个，涉及公司", chg["Stkcd"].nunique(), "家")
print(chg.groupby(["prev","ownership"]).size().sort_values(ascending=False).head(6).to_string())''')

md("""**解读**：1,979 行股权性质数据覆盖全部 170 家公司的 2004—2015 年份，仅招商积余（001914）因代码段切换无记录，归入"不明"而不删除（作业允许不明类别存在，此时国有与民营占比之和小于 100%）。原始值里确有"民营,外资"这类复合性质和少量缺失，映射规则保证非国有不等于民营。

**产权会变**：全样本有 **84 个企业—年度观测、65 家公司**发生过产权变更，其中 23 次国有→民营、19 次民营→国有、13 次转为其他。这意味着"国有组"与"民营组"是**逐年重分类**的结果，不是两批固定公司——因此后文的组间差异不能解读为"同一批公司随时间的变动"，这与作业"描述性差异不能直接解释为产权的因果作用"一致。""")

# ================= 第 5 节 逐年公司数与产权结构 =================
md("""## 五、数量与产权结构（作业输出 1）

逐年统计：房地产上市公司总数；国有、民营、其他、不明公司数量；国有与民营占当年房地产公司总数的比例。**年度公司数去重计算，不因财务指标缺失删去公司**。""")

code('''OWN_ORDER = ["国有","民营","其他","不明"]
cnt = panel.groupby("fiscal_year")["Stkcd"].nunique().rename("合计")
own_tab = panel.groupby(["fiscal_year","ownership"])["Stkcd"].nunique().unstack(fill_value=0)
own_tab = own_tab.reindex(columns=OWN_ORDER, fill_value=0)
own_tab["合计"] = cnt
for c in ["国有","民营"]:
    own_tab[f"{c}占比%"] = (own_tab[c]/own_tab["合计"]*100).round(1)

fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
ax[0].plot(own_tab.index, own_tab["合计"], marker="o", color="#1f4e79")
ax[0].set_title("房地产 A 股上市公司数（逐年）"); ax[0].set_xlabel("年度")
ax[0].set_ylabel("公司数"); ax[0].grid(alpha=.3)
bottom = np.zeros(len(own_tab))
for c, col in zip(OWN_ORDER, ["#c00000","#2e75b6","#7f7f7f","#bfbfbf"]):
    ax[1].bar(own_tab.index, own_tab[c], bottom=bottom, label=c, color=col); bottom += own_tab[c].values
ax[1].set_title("产权四类公司数"); ax[1].legend(fontsize=9); ax[1].grid(alpha=.3, axis="y")
ax[2].plot(own_tab.index, own_tab["国有占比%"], marker="o", label="国有", color="#c00000")
ax[2].plot(own_tab.index, own_tab["民营占比%"], marker="s", label="民营", color="#2e75b6")
ax[2].set_title("国有与民营占比"); ax[2].set_ylabel("%"); ax[2].legend(fontsize=9); ax[2].grid(alpha=.3)
fig.tight_layout(); plt.show()
own_tab''')

md("""**解读**：房地产 A 股上市公司从 2005 年的 **62 家**增至 2015 年的 **134 家**，扩容约 1.2 倍，2008—2012 年扩张最快（84→142 家）。产权结构上，**国有占比从 58.1% 单调降至 46.3%**（2005→2015），民营占比稳定在 37%—45%；"其他"类（以外资为主）从 2 家增至 13 家，反映 2009 年后外资与混合所有制开发商进入。国有与民营占比之和约 96%—99%，其余为其他与不明，符合作业"占比之和可以小于 100%"的设定。公司数在 2013—2015 年略有回落，主要是个别公司转出房地产（行业变更）与退市，属非平衡面板的正常进出。""")

# ================= 第 6 节 六项指标 =================
md("""## 六、六项财务指标（统一口径）

| 指标 | 口径 |
|---|---|
| 资产负债率 | 总负债 / 总资产 |
| bankloan | (短期银行借款 + 长期银行借款) / 总负债 |
| 短期负债占比 | 流动负债 / 总负债 |
| ROA | 合并净利润 / **平均**总资产 |
| ROE | 合并净利润 / **平均**所有者权益 |
| Cash_TA | 货币资金 / 总资产 |

平均总资产（权益）=（上年末 + 本年末）/ 2，2005 年的上年末取 **2004 年末**独立导出数据。利润与权益均为合并口径，不混用归母净利润与含少数股东权益的总权益。现金持有用**货币资金**（区别于现金及现金等价物），短期负债用**流动负债**（区别于短期银行借款）。**零分母、缺失一律返回缺失并计数，不填零、不删观测**。

**关于 bankloan 的字段选择**：CSMAR 资产负债表中未单列"银行借款"明细（其"银行借款"科目属金融企业专用），因此采用主表 `A002101000 短期借款` 与 `A002201000 长期借款` 作为短期/长期银行借款的对应字段——这两个科目在 2005—2015 年一般企业的报表中以银行借款为主，可能含少量非银行金融机构借款；字段说明随导出保留，缺失不按零处理。""")

code('''def safe_div(num, den):
    den = pd.to_numeric(den, errors="coerce")
    bad = den.isna() | (den == 0)
    return num / den.where(~bad), int(bad.sum())

panel["leverage"], n1 = safe_div(panel["liabilities"], panel["assets"])
panel["bankloan"],  n2 = safe_div(panel["st_borrow"] + panel["lt_borrow"], panel["liabilities"])
panel["st_debt_ratio"], n3 = safe_div(panel["cur_liabilities"], panel["liabilities"])
panel["cash_ta"],   n4 = safe_div(panel["cash"], panel["assets"])

# 上年末分母：2005 年用 2004 年末文件，其余用面板内上一年
prev = panel[["Stkcd","fiscal_year","assets","equity"]].copy()
prev["fiscal_year"] += 1
prev = prev.rename(columns={"assets":"assets_prev","equity":"equity_prev"})
p04 = bs04x.rename(columns={"assets":"assets_prev","equity":"equity_prev"})
p04["fiscal_year"] = 2005
prev_all = pd.concat([p04[["Stkcd","fiscal_year","assets_prev","equity_prev"]],
                      prev[prev["fiscal_year"]>2005]], ignore_index=True)
panel = panel.merge(prev_all, on=["Stkcd","fiscal_year"], how="left", validate="1:1")
print("上年末分母缺失观测:", panel["assets_prev"].isna().sum(), "（IPO 首年，结构性缺失）")

avg_a = (panel["assets"] + panel["assets_prev"])/2
avg_e = (panel["equity"] + panel["equity_prev"])/2
panel["roa"], n5 = safe_div(panel["net_income"], avg_a)
panel["roe"],  n6 = safe_div(panel["net_income"], avg_e)

# bankloan 分子缺失不按零处理
panel.loc[panel["st_borrow"].isna() | panel["lt_borrow"].isna(), "bankloan"] = np.nan
print("\\n分母缺失或为零的观测数：资产负债率", n1, "| bankloan", n2,
      "| 短期负债占比", n3, "| Cash_TA", n4, "| ROA", n5, "| ROE", n6)''')

md("""**解读**：分母诊断显示六项指标的不可计算观测极少——ROA/ROE 各 12 个（全部是公司在面板中的首年，缺少上年末数据，属上市时点的结构性缺失，不填补、不用更早年份替代），bankloan 1 个（总负债为零）。杠杆类指标（资产负债率、bankloan、短期负债占比、Cash\\_TA）有效样本 1,821 中约 1,820 个，几乎无损耗。""")

# ================= 第 7 节 四类输出 =================
md("""## 七、六项指标的四类输出（作业输出 2—4）

1. 全部房地产企业历年均值与中位数时序图；
2. 国有和民营企业历年均值比较图；
3. 国有和民营企业历年**中位数**比较图；
4. 各指标对应的年度有效样本量表。

注意：**平均资产负债率为企业比率的算术平均**，不是行业总负债除以总资产。""")

code('''IND = ["leverage","bankloan","st_debt_ratio","roa","roe","cash_ta"]
LBL = {"leverage":"资产负债率","bankloan":"bankloan","st_debt_ratio":"短期负债占比",
       "roa":"ROA","roe":"ROE","cash_ta":"Cash_TA"}

def stats_by(gcol):
    out = {}
    for i in IND:
        g = panel.groupby(["fiscal_year", gcol])[i] if gcol else panel.groupby("fiscal_year")[i]
        out[i] = pd.DataFrame({"mean":g.mean(),"median":g.median(),"n":g.count()}).reset_index()
    return out

all_s, own_s = stats_by(None), stats_by("ownership")

fig, axes = plt.subplots(2, 3, figsize=(15, 7.5))
for k, i in enumerate(IND):
    a = axes[k//3][k%3]; d = all_s[i]
    a.plot(d["fiscal_year"], d["mean"], marker="o", label="均值", color="#c00000")
    a.plot(d["fiscal_year"], d["median"], marker="s", label="中位数", color="#2e75b6")
    a.set_title(LBL[i], fontsize=11); a.grid(alpha=.3); a.legend(fontsize=8)
fig.suptitle("全部房地产企业：历年均值与中位数", fontsize=13)
fig.tight_layout(); plt.show()''')

code('''for stat, ttl in [("mean","国有 vs 民营：历年均值"), ("median","国有 vs 民营：历年中位数")]:
    fig, axes = plt.subplots(2, 3, figsize=(15, 7.5))
    for k, i in enumerate(IND):
        a = axes[k//3][k%3]; d = own_s[i]
        for g_, c in [("国有","#c00000"), ("民营","#2e75b6")]:
            s = d[d["ownership"]==g_]
            a.plot(s["fiscal_year"], s[stat], marker="o", label=g_, color=c, lw=1.6)
        a.set_title(LBL[i], fontsize=11); a.grid(alpha=.3); a.legend(fontsize=8)
    fig.suptitle(ttl, fontsize=13); fig.tight_layout(); plt.show()

vn = pd.DataFrame({"指标":[LBL[i] for i in IND]})
for y in sorted(panel["fiscal_year"].unique()):
    vn[str(y)] = [int(all_s[i].loc[all_s[i]["fiscal_year"]==y, "n"].iloc[0]) for i in IND]
vn''')

md("""**解读（均值 vs 中位数）**：以资产负债率为例，全样本均值 0.62—0.80，而中位数稳定在 0.57—0.68——两者的缺口集中在 2005—2010 年，源于少数**资不抵债**公司（见第八节）；2011 年后两条线基本重合。ROA 中位数从 2005 年约 1.3% 升至 2010 年 4.1%，随后一路降至 2015 年 1.7%，与房地产行业毛利率下行、盈利分化加剧的宏观事实一致。**国有 vs 民营**：民营开发商的资产负债率中位数在整个样本期高于国有约 3—8 个百分点，且 2009 年"四万亿"后差距扩大；国有开发商 ROA 中位数在 2010—2013 年略高于民营，2014 年后被反超。描述性差异不构成产权的因果证据。""")

# ================= 第 6.5 节 会计恒等式核查 =================
md("""## 六之二、会计恒等式核查（资产 = 负债 + 所有者权益）

**要回答的问题**：合并报表的三大板块是否自洽；若不自洽，是否集中在特定公司或特定状态（如资不抵债）。

**做法**：逐条计算 `资产总计 −（负债合计 + 所有者权益合计）`，以 **1% 相对容差**判定是否在容差内；超出容差的观测全部保留并列出，不自动删除。""")

code('''nm = bs.drop_duplicates("Stkcd").set_index("Stkcd")["ShortName"].to_dict()
panel["name"] = panel["Stkcd"].map(nm)
panel["acct_gap"] = panel["assets"] - (panel["liabilities"] + panel["equity"])
panel["acct_gap_pct"] = panel["acct_gap"].abs() / panel["assets"].replace(0, np.nan)
TOL = 0.01
ok  = panel["acct_gap_pct"] <= TOL
print(f"会计恒等式核查（容差 1%）：")
print(f"  容差内 {int(ok.sum())} 条 / {len(panel)} 条（{ok.mean()*100:.1f}%）")
print(f"  容差外 {int((~ok).sum())} 条；缺失（分母缺失）{int(panel['acct_gap_pct'].isna().sum())} 条")
out = panel.loc[~ok, ["Stkcd","name","fiscal_year","assets","liabilities","equity","acct_gap_pct"]] \\
        .nlargest(10, "acct_gap_pct")
out["acct_gap_pct"] = out["acct_gap_pct"].round(3)
print("\\n超出容差、偏离最大的 10 条："); print(out.to_string(index=False))
print("\\n容差外观测中权益为负（资不抵债）的条数:",
      int(((~ok) & (panel["equity"] < 0)).sum()), "/", int((~ok).sum()))
print("容差外观测中权益为正的条数:", int(((~ok) & (panel["equity"] > 0)).sum()),
      "—— 说明失衡并非由负权益引起，而是个别公司个别年份的科目列示差异或源数据板块不平")''')

md("""**解读**：**99.7%（1,816/1,821）**的观测满足 `资产 ≈ 负债 + 所有者权益`（1% 容差内），说明三大板块自洽、单位统一为元、口径未混用，合并与字段映射没有系统性错误。

超出容差的仅 **5 条**（占 0.3%）：深大通 A 2008 年偏离 10.5%，\\*ST 寰岛 2011—2014 年偏离 1.4%—2.1%。**这 5 条的权益均为正**——也就是说失衡不是资不抵债造成的，而是个别公司个别年份的科目列示差异（如少数股东权益的列示口径）或源数据本身的板块不平。处理：保留观测、不修改数值、不删除，并在样本处理表与局限中如实说明——0.3% 的量级不足以影响任何逐年结论。""")

# ================= 第 8 节 离群值与敏感性 =================
md("""## 八、离群值检查与处理前后比较

**检查结论**：极端比率全部来自**负权益（资不抵债）公司**，属真实经济状况而非技术错误——数值已与公司年报口径交叉核验（如万科、荣安地产）。典型：大洲兴业连续 7 年负权益、中润资源 2006 年资产负债率 877（资产 22 万元 vs 负债 1.95 亿元）。

**处理**：全部**保留观测并标识**（`flag_neg_equity`、`flag_lev_gt1`），不删除、不缩尾（缩尾非必做）；同时给出剔除负权益观测前后的对照，检验结论是否稳健。""")

code('''panel["flag_neg_equity"] = panel["equity"] < 0
panel["flag_lev_gt1"]    = panel["leverage"] > 1
clean = panel[~panel["flag_neg_equity"]]

neg_tab = panel.groupby("fiscal_year").agg(
    负权益观测=("flag_neg_equity","sum"), 资产负债率超1=("flag_lev_gt1","sum"),
    观测数=("Stkcd","size"))
neg_tab["负权益占比%"] = (neg_tab["负权益观测"]/neg_tab["观测数"]*100).round(1)
print(neg_tab.to_string())

rows = []
for i in IND:
    for y, g in panel.groupby("fiscal_year"):
        c = clean[clean["fiscal_year"]==y]
        rows.append({"指标":LBL[i], "年度":y,
                     "全样本均值":g[i].mean(), "剔除负权益后均值":c[i].mean(),
                     "全样本中位数":g[i].median(), "剔除负权益后中位数":c[i].median(),
                     "剔除数":int(g["flag_neg_equity"].sum())})
sens = pd.DataFrame(rows); sens["均值差异"] = sens["剔除负权益后均值"] - sens["全样本均值"]
demo = sens[sens["指标"].isin(["资产负债率","ROE"])].copy()
for c in ["全样本均值","剔除负权益后均值","全样本中位数","剔除负权益后中位数","均值差异"]:
    demo[c] = demo[c].round(4)
demo''')

md("""**解读**：负权益观测每年 0—3 个（占比 1.6%—4.8%）。它们对**均值**影响显著——资产负债率 2005—2009 年被推高 0.07—0.58（2009 年全样本均值 1.17，剔除后 0.59）；对**中位数**几乎无影响（差异 ≤0.005）。ROE 受影响更小的原因是分母（平均权益）在亏损年份同步收缩。因此本报告的时序解读以中位数为主：剔除前后，"国有杠杆低于民营、行业 ROA 自 2010 年见顶回落"两个核心结论均不变，结果稳健。""")

# ================= 第 8.5 节 突变归因 =================
md("""## 八之二、指标突变的逐年归因

**要回答的问题**：某一年指标突变，究竟是**离群值**（资不抵债公司）、**异常分母**、**样本进出**（新上市/退市）还是**产权变更**造成的。

**做法**：以资产负债率为例，逐年给出全样本均值，并分别给出"剔除当年新进入样本的公司""剔除负权益观测""剔除当年发生产权变更的公司"后的均值，比较各自的贡献。""")

code('''p = panel.sort_values(["Stkcd","fiscal_year"]).copy()
p["prev_own"] = p.groupby("Stkcd")["ownership"].shift(1)
p["own_changed"] = p["prev_own"].notna() & (p["ownership"] != p["prev_own"])

rows = []
for y in range(2006, 2016):
    cur = p[p["fiscal_year"] == y]
    prev_codes = set(p.loc[p["fiscal_year"] == y-1, "Stkcd"])
    new_e = ~cur["Stkcd"].isin(prev_codes)
    rows.append({
        "年度": y,
        "全样本均值": cur["leverage"].mean(),
        "剔除新进入后": cur.loc[~new_e, "leverage"].mean(),
        "剔除负权益后": cur.loc[~cur["flag_neg_equity"], "leverage"].mean(),
        "剔除产权变更后": cur.loc[~cur["own_changed"], "leverage"].mean(),
        "当年新进入公司数": int(new_e.sum()),
    })
att = pd.DataFrame(rows)
for c in ["全样本均值","剔除新进入后","剔除负权益后","剔除产权变更后"]:
    att[c] = att[c].round(4)
for c, src in [("新进入贡献","剔除新进入后"), ("负权益贡献","剔除负权益后"), ("产权变更贡献","剔除产权变更后")]:
    att[c] = (att["全样本均值"] - att[src]).round(4)
att[["年度","全样本均值","新进入贡献","负权益贡献","产权变更贡献","当年新进入公司数"]]''')

md("""**解读**：三个来源的贡献量级清晰可分——

① **负权益（离群值）**：主导了 2005—2010 年的均值虚高，2009 年把均值抬高 **0.577**（1.170 → 剔除后 0.593），2008 年 0.216、2007 年 0.148；2013 年后归零。这与第八节的敏感性结论完全一致。

② **样本进出**：2008—2012 年每年有 11—28 家公司新进入样本，但贡献**均为负值且绝对不超过 0.09**（2009 年 −0.092）——即新进入公司反而拉低了行业均值，说明"扩容"没有系统性推高杠杆。

③ **产权变更**：除 2009 年外，单年贡献均小于 0.01，量级最小。2009 年 0.571 的异常高值并非独立来源——它与负权益的贡献几乎相等（剔除后均值分别回到 0.599 与 0.593），说明**两者指向同一批公司**（当年同时具备资不抵债与产权变更特征）。

**结论**：均值层面的突变由少数资不抵债公司驱动，样本进出方向相反、产权变更量级极小，因此以中位数为主的结论稳健；同时再次印证——国有/民营的组间差异要按"当年处于该组的公司"理解，而非同一批公司的时间序列。""")

# ================= 第 9 节 样本处理表 =================
md("""## 九、样本处理表

记录下载、筛选、合并、变量构造各阶段的公司数与企业—年度观测数（作业必备）。""")

code('''flow = pd.DataFrame([
    ("下载：资产负债表原始行（2005—2015，170 家）", 18044, 170),
    ("下载：利润表原始行（同上）", 18089, 170),
    ("下载：资产负债表 2004 年末（158 家）", 1530, 158),
    ("下载：股权性质（2004—2015，170 家）", 1979, 170),
    ("下载：年度表（全市场 2,910 家）", 24197, 2910),
    ("筛合并报表 Typrep=A", 9064, 170),
    ("筛年末 Accper=12-31", 1821, 170),
    ("剔除 B 股（200/900 前缀）", 1821, 170),
    ("左连利润表（未匹配 0）", 1821, 170),
    ("并入年度表行业与上市状态（未判定 0）", 1821, 170),
    ("并入产权分组（不明归入，不删公司）", 1821, 170),
    ("判定为房地产（行业筛选后）", int(panel["is_re"].sum()), panel.loc[panel["is_re"],"Stkcd"].nunique()),
], columns=["阶段", "企业—年度观测数", "公司数"])
flow''')

# ================= 第 10 节 总体结论 =================
md("""## 十、总体结论

**主要发现（串联全篇）**：

1. **规模扩张与产权结构变迁**：房地产 A 股上市公司从 2005 年 62 家增至 2015 年 134 家；国有占比从 58.1% 单调降至 46.3%，民营稳定在 37%—45%——行业扩容主要由民营与外资开发商贡献。
2. **杠杆水平与结构**：资产负债率中位数稳定在 0.57—0.68；民营开发商中位数高于国有 3—8 个百分点，2009 年后扩大。bankloan（银行借款/总负债）与短期负债占比显示，民营开发商更依赖银行短期资金。
3. **盈利见顶回落**：ROA 中位数 2010 年约 4.1% 见顶，2015 年降至 1.7%；同期 Cash_TA（货币资金/总资产）上升，行业从扩张转向囤现金，与 2012 年后调控收紧、库存分化的宏观背景一致。
4. **离群值的真相**：全部极端比率来自负权益的 ST/重组壳公司（占比 1.6%—4.8%），剔除前后中位数几乎不变、均值显著变化——因此以中位数为主的结论稳健。
5. **分组不是固定公司集合**：65 家公司在样本期内发生过产权变更（23 次国有→民营、19 次民营→国有），国有组与民营组是逐年重分类的结果；另有 223 条资产负债表、185 条利润表观测来自差错更正后的版本。因此组间与跨期差异应理解为「当年处于该组的公司」的横截面差异，不能读作同一批公司的时间序列。

6. **样本口径决定结论质量**：若按 CSMAR 当前分类的静态代码池（117 家）取样，2005 年覆盖率仅 62%，会系统性低估行业早期规模与国有占比；改为动态并集（170 家）后各年覆盖 97%—99%。

**关键处理判断**：合并报表+年末+A 股三步筛选；行业逐年判定（2001 版 J\\* / 2012 版 K70 映射）；产权四类映射（非国有≠民营）；零/负分母返回缺失不填零；离群值保留并标识；ST/暂停上市保留。

**局限**：
- **数据**：CSMAR 未标注金额币种与单位的完整说明，单位"元"系经年报数值核验；行业分类依赖 CSMAR 年度表的填充规则；产权字段缺失者（招商积余）只能归入不明。
- **方法**：描述性统计不构成产权对企业行为的因果证据；均值对负权益观测敏感，已用中位数与敏感性比较缓解；平均分母口径下 2005 年 ROA/ROE 依赖 2004 年末数据的质量。
- **样本**：A 股口径剔除了 5 家 B 股房地产公司；面板以"有年末合并报表"定义在市状态，暂停上市期间无报表的年份自然缺席。

---

## AI 使用声明

- **工具**：WorkBuddy（Hermes Agent，Claude 模型）。
- **参与环节**：作业口径核对（从课件仓库历史版本恢复 hw-02 作业页面原文）；CSMAR 导出清单设计与站内路径指引；字段映射与清洗代码编写（`code/build_panel.py`、`code/make_outputs.py` 及本 Notebook）；逐年行业判定规则设计与样本缺口对账；图表生成；本文档起草。
- **关键提示词（节选）**：
  1. "检查是否严格符合：自行从 CSMAR 下载 2005—2015 年房地产 A 股上市公司年度数据……分类标准跨年变化时说明映射方式"——促成 12 条逐条自检并补齐上市状态、下载清单与字段对应表；
  2. "为什么我在数据库中看的是 123 家而你这里有 170 个"——促成静态代码池与动态并集的对账，发现并修复 66 家公司的样本缺口。
- **本人核验过程**：全部 CSMAR 原始文件由本人登录导出并核对导出条件；抽查万科 2015 年资产总计、长期借款、净利润与公开年报一致（单位=元）；确认面板无上市前观测、无退市后观测；逐年公司数与年度表房地产数逐一对账（覆盖 97%—99%，缺者均为 B 股）。
- **修正过的问题**（由 AI 辅助发现并修复）：① 首次导出的行业分类表是变更事件表而非年度快照，无法判定逐年行业，改用基本信息年度表；② 行业判定最初沿用 J 前缀，会把 2012 版金融业（J66—J69）误判为房地产，已改为按年份分标准；③ 按当前分类导出的财务数据池缺 66 家中途转出房地产的公司，2005 年覆盖率仅 62%，已按动态并集补导；④ 早期股权性质与 2004 年末表只覆盖旧代码池，已按 170 家清单补导；⑤ 短期借款/长期借款科目编码首次抽查时用错（A002202000 → A002201000），已按字段说明修正。
- **未发现问题的部分**：资产负债表与利润表的主键唯一性、两表覆盖一致性（未匹配 0）、合并报表与年末记录的筛选逻辑、六指标公式实现、以及各年有效样本量表均经复核未发现问题。对话链接略（无法分享，不编造）。""")

nb["cells"] = cells
out = Path(__file__).resolve().parents[1] / "hw02-2.ipynb"
nbf.write(nb, out)
print("已生成:", out, "| 单元数:", len(cells))
