#!/usr/bin/env python3
"""在 hw_02-1.ipynb 中追加第 3 节「不复权价格、累计收益和日收益图形」。

对应作业必做要求表中的三行：收盘价时序、起点为 1 的累计表现、日收益率时序及异常波动检查。

用法：
    cd hw-02 && python scripts/build_hw02_1_section03.py
    python scripts/run_notebook.py
"""
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "hw_02-1.ipynb"

nb = nbf.read(NB, as_version=4)
# 幂等：若已存在第 3 节或原占位单元，从其起始位置截断后重新写入
CUT_MARKERS = ("## 3. 不复权价格", "## 后续分析结构")
cut = len(nb["cells"])
for i, c in enumerate(nb["cells"]):
    if "".join(c["source"]).lstrip().startswith(CUT_MARKERS):
        cut = i
        break
nb["cells"] = nb["cells"][:cut]

cells = []

cells.append(nbf.v4.new_markdown_cell("""## 3. 不复权价格、累计收益和日收益图形

### Step 1：Markdown分析说明

本节要回答三个问题：第一，10只股票的价格在样本期内怎么走；第二，以同一起点计算，各股票累计赚了多少；第三，日收益的波动是否出现异常，异常集中在什么时候。

三张图分别对应这三个问题。需要特别说明两点口径。其一，**价格图用不复权收盘价，收益图用后复权价**：不复权价是当时市场上真实的成交价格，适合看价格水平；但送转股和现金分红会造成价格机械下调，用不复权价判断盈亏会得到错误结论，因此累计收益必须用后复权价构造。其二，**累计净值以2020-12-31的后复权价为基准**（净值=1），该日是计算首个日收益率所需的支持日，正式样本从2021-01-04开始；这样既不丢掉首个交易日的收益，又能让曲线起点严格等于1。

分析要点与检查事项：

- 价格图：分面展示10只股票，标注日期范围与单位（元），观察价格水平与趋势差异；
- 累计收益：以共同起点比较10只股票，观察分化程度与首尾差距；
- 日收益图：分面展示，叠加±10%参考线（10只股票均为主板，涨跌幅限制±10%），检查是否有越界观测；
- 异常波动：分年统计日收益标准差与极端值个数，识别波动的时间聚集；
- 停牌与跨期收益在主口径中为缺失，图上表现为曲线缺口，不填零、不跨日连乘；
- 图表统一标明标题、日期范围、单位与图例，并设置中文字体与负号显示。"""))

cells.append(nbf.v4.new_markdown_cell("""### Step 2：代码与实际输出

下面先配置中文与负号显示，再依次绘制不复权收盘价分面图、起点为1的累计收益曲线、日收益率分面图，最后给出异常波动的分年统计与极值清单。"""))

cells.append(nbf.v4.new_code_cell("""# 配置中文字体与负号显示（作业要求图表中文和负号正常）
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

plt.rcParams["font.sans-serif"] = ["PingFang SC", "Hiragino Sans GB", "Arial Unicode MS", "Heiti TC"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 110

# 复用以第 2 节构造好的收益率数据（d 含 ret、ret_raw、cross_period）
names = d.drop_duplicates("stock_code").set_index("stock_code")["stock_name"].to_dict()
order = sorted(names.keys())
colors = {code: plt.cm.tab10(i % 10) for i, code in enumerate(order)}
print("绘图股票数:", len(order))
print("数据日期范围:", d["date"].min().date(), "至", d["date"].max().date())"""))

cells.append(nbf.v4.new_code_cell("""# 图1：各股票不复权收盘价时序（分面）
fig, axes = plt.subplots(5, 2, figsize=(14, 13), sharex=True)
for ax, code in zip(axes.ravel(), order):
    sub = d[d["stock_code"] == code]
    ax.plot(sub["date"], sub["close_unadjusted"], color=colors[code], linewidth=1)
    ax.set_title(f"{names[code]} {code}", fontsize=11)
    ax.set_ylabel("元")
    ax.grid(alpha=0.3)
axes[0, 0].xaxis.set_major_locator(mdates.YearLocator())
axes[0, 0].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
fig.suptitle("图1  10只A股不复权收盘价时序（2020-12-31 至 2026-09-16，单位：元）",
             fontsize=13, y=0.995)
fig.tight_layout()
plt.show()

# 价格区间表
display(d.groupby("stock_code").agg(
    股票=("stock_name", "first"), 最低价=("close_unadjusted", "min"), 最高价=("close_unadjusted", "max"),
    起点价=("close_unadjusted", "first"), 末价=("close_unadjusted", "last")
).reindex(order))"""))

cells.append(nbf.v4.new_code_cell("""# 图2：起点为 1 的累计收益曲线（以 2020-12-31 后复权价为基准）
base_price = d.loc[d["date"] == "2020-12-31"].set_index("stock_code")["close_hfq"]
nav = d.copy()
nav["净值"] = nav["close_hfq"] / nav["stock_code"].map(base_price)

fig, ax = plt.subplots(figsize=(14, 7))
for code in order:
    sub = nav[nav["stock_code"] == code]
    ax.plot(sub["date"], sub["净值"], label=f"{names[code]}", color=colors[code], linewidth=1.3)
ax.axhline(1.0, color="gray", linestyle="--", linewidth=1)
ax.set_title("图2  累计收益曲线（起点=1，基准为 2020-12-31 后复权收盘价）", fontsize=13)
ax.set_xlabel("日期")
ax.set_ylabel("累计净值（倍）")
ax.legend(ncol=5, fontsize=9, loc="upper left")
ax.grid(alpha=0.3)
fig.tight_layout()
plt.show()

# 期末累计净值排序
end_nav = nav.loc[nav["date"] == nav["date"].max(), ["stock_code", "stock_name", "净值"]]
end_nav = end_nav.assign(累计收益率=lambda x: x["净值"] - 1).sort_values("净值", ascending=False)
display(end_nav.assign(**{"净值": lambda x: x["净值"].round(4), "累计收益率": lambda x: x["累计收益率"].round(4)}))
print("净值大于1的股票数:", int((end_nav["净值"] > 1).sum()),
      " 净值小于1的股票数:", int((end_nav["净值"] < 1).sum()))

# 不复权价涨跌与后复权净值的对比：说明为什么不能用不复权价判断收益
compare = d.groupby("stock_code").agg(起点不复权价=("close_unadjusted", "first"), 末不复权价=("close_unadjusted", "last"))
compare["不复权涨跌"] = compare["末不复权价"] / compare["起点不复权价"] - 1
compare = compare.join(end_nav.set_index("stock_code")["净值"])
compare["后复权累计 / 不复权累计"] = compare["净值"] / (1 + compare["不复权涨跌"])
display(compare.reindex(order).round(4))"""))

cells.append(nbf.v4.new_code_cell("""# 图3：日收益率时序（分面），叠加 ±10% 涨跌幅限制参考线
fig, axes = plt.subplots(5, 2, figsize=(14, 13), sharex=True, sharey=True)
for ax, code in zip(axes.ravel(), order):
    sub = d[(d["stock_code"] == code) & (d["date"] >= "2021-01-01")]
    ax.plot(sub["date"], sub["ret"], color=colors[code], linewidth=0.6)
    ax.axhline(0.10, color="red", linestyle="--", linewidth=0.8)
    ax.axhline(-0.10, color="green", linestyle="--", linewidth=0.8)
    ax.set_title(f"{names[code]}", fontsize=11)
    ax.set_ylim(-0.12, 0.12)
    ax.grid(alpha=0.3)
axes[0, 0].xaxis.set_major_locator(mdates.YearLocator())
axes[0, 0].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
fig.suptitle("图3  日收益率时序与 ±10% 涨跌幅限制参考线（2021-01-04 至 2026-09-16）",
             fontsize=13, y=0.995)
fig.tight_layout()
plt.show()"""))

cells.append(nbf.v4.new_code_cell("""# 异常波动检查：分年统计与极值清单
ret_all = d.loc[d["date"] >= "2021-01-01", ["stock_code", "stock_name", "date", "ret"]].dropna(subset=["ret"])
by_year = ret_all.assign(年份=ret_all["date"].dt.year).groupby("年份").agg(
    有效观测数=("ret", "size"), 日收益标准差=("ret", "std"),
    最大单日涨幅=("ret", "max"), 最大单日跌幅=("ret", "min"),
)
# 阈值 9% 用于识别接近涨跌停的大幅波动观测
by_year["绝对值9pct以上个数"] = ret_all.assign(
    年份=ret_all["date"].dt.year).groupby("年份")["ret"].apply(lambda s: int((s.abs() >= 0.09).sum()))
display(by_year.round(4))

print("|r| >= 10% 的观测数:", int((ret_all["ret"].abs() >= 0.10).sum()),
      " |r| > 11% 的观测数:", int((ret_all["ret"].abs() > 0.11).sum()))
print("\\n单日收益绝对值前 8 名:")
display(ret_all.reindex(ret_all["ret"].abs().sort_values(ascending=False).index)
        .head(8).assign(ret=lambda x: x["ret"].round(6)))"""))

cells.append(nbf.v4.new_markdown_cell("""### Step 3：Markdown结果解读

图1显示，10只股票的**不复权**价格水平差异极大：贵州茅台在1,168.63—2,601元之间波动，隆基绿能从最高123元跌到11元，比亚迪从194.30元降到83.96元。这张图只用于观察价格水平与走势，不能据此判断盈亏——送转股和现金分红会造成价格机械下调。

图2以2020-12-31的后复权收盘价为基准（净值=1）重算累计表现，结论与图1明显不同：截至2026-09-16，10只股票中**4只净值大于1、6只小于1**。比亚迪最高，累计净值1.3399（+33.99%）；招商银行1.2259、美的集团1.1031、中信证券1.0900次之；立讯精密0.9699接近持平；万华化学0.8841、贵州茅台0.7353、恒瑞医药0.4792、顺丰控股0.3824下跌；隆基绿能最低，仅0.2412，5年多累计亏损约75.9%。首尾差距接近5.6倍（1.3399 对 0.2412），分化极其悬殊。

比亚迪是最能说明复权必要性的例子：不复权价下跌56.8%，按后复权价计算的净值却上涨34.0%，两者相差约3.1倍，差额来自期间的送转股与现金分红。若只看不复权价，会把一只上涨的股票误判为大幅亏损。这也印证了第1节的口径设定：后复权价只是连续收益的尺度，不代表当时可成交的价格，但只有它才能用于计算收益。

图3显示，各股票日收益基本落在±10%以内。分年统计进一步给出波动的时间分布：日收益标准差2021年最高（0.0266），2023年最低（0.0171），2024年回升至0.0209；日收益绝对值达到9%以上的观测，2021年有19个、2024年13个、2025年12个，而2022年和2023年各只有5个。极端波动明显集中在2021年与2024—2025年两段，具有时间聚集特征。单日极值前三名均来自隆基绿能：2024-09-30 +10.03%、2025-04-07 −10.02%、2023-12-28 +10.01%；该股同时是累计净值最低的一只，"收益最低、波动最大"两项特征相互一致。

需要说明的是，这些时点与市场事件（2021年春节后核心资产调整、2024年9月政策转向、2025年4月外部关税冲击）在时间上吻合，但本节图形只能说明波动在何时聚集，**不能证明因果关系**；要确认具体成因还需对照公司公告与宏观信息，这超出本题数据范围。

核心发现：

- 4只上涨、6只下跌，首尾累计净值相差约5.6倍，样本期内分化极大；
- 不复权价与后复权净值可能方向相反（比亚迪：−56.8% 对 +34.0%），收益判断必须使用后复权价；
- 日收益全部落在主板±10%涨跌幅限制内，|r| > 11% 的观测为0，未发现越界或单位错误；
- 波动具有明显时间聚集：2021年与2024—2025年是两段高波动期，隆基绿能是单日极值最集中的股票。"""))

cells.append(nbf.v4.new_markdown_cell("""## 后续分析结构

后续各节继续严格采用“Step 1分析说明—Step 2代码与实际输出—Step 3结果解读”：

4. 20日滚动年化波动率  
5. 描述统计与异常收益检查  
6. 日收益率Pearson相关性  
7. 等权组合与滞后总市值加权组合  
8. 总体结论、局限与AI使用说明
"""))

nb["cells"].extend(cells)
nbf.write(nb, NB)
print("已写入:", NB, "单元数:", len(nb["cells"]))
