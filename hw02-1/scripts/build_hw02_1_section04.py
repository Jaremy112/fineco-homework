#!/usr/bin/env python3
"""在 hw02-1.ipynb 中追加第 4 节「20 日滚动年化波动率」。

对应作业必做要求表第 4 行：20 个交易日滚动年化波动率；年化用日收益样本标准差乘 √252，
窗口不足 20 个观测时不计算。

用法：
    cd hw-02 && python scripts/build_hw02_1_section04.py
    python scripts/run_notebook.py
"""
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "hw02-1.ipynb"

nb = nbf.read(NB, as_version=4)
CUT_MARKERS = ("## 4. 20日滚动年化波动率", "## 后续分析结构")
cut = len(nb["cells"])
for i, c in enumerate(nb["cells"]):
    if "".join(c["source"]).lstrip().startswith(CUT_MARKERS):
        cut = i
        break
nb["cells"] = nb["cells"][:cut]

cells = []

cells.append(nbf.v4.new_markdown_cell("""## 4. 20日滚动年化波动率

### Step 1：Markdown分析说明

本节要回答三个问题：第一，各股票的波动水平有多高、谁最稳定；第二，波动在时间上如何变化、是否与市场事件同步；第三，把10只股票放在一起后，组合的波动为什么明显低于个股。

计算口径严格按作业要求：年化波动率等于日收益率样本标准差乘以 $\\sqrt{252}$；滚动窗口包含20个交易日；不足20个观测时不计算。在此基础上补充一条处理规则：**若窗口内含有第2节剔除的跨期收益，则该窗口不计算**。原因是这类窗口的价格变化跨越了停牌期，把它混入20日标准差会高估真实的日内波动。顺丰控股和中信证券因此各少20个窗口，合计40个，代价可量化。

分析要点与检查事项：

- 水平比较：滚动年化波动率的均值、中位数与期末值，横向排序；
- 时点比较：各股票波动率峰值及其出现日期，识别共同的波动高发期；
- 分散化：把10只股票按等权合成组合，比较组合波动率与个股波动率均值；
- 收益与风险：结合第3节的累计净值，观察高波动是否对应高收益；
- 单位统一用百分比，图表标明标题、日期范围、单位与图例。"""))

cells.append(nbf.v4.new_markdown_cell("""### Step 2：代码与实际输出

下面先计算各股票的20日滚动年化波动率，再绘制个股波动率时序、组合与个股均值对比，最后给出汇总统计与峰值时点。"""))

cells.append(nbf.v4.new_code_cell("""# 20日滚动年化波动率：日收益样本标准差 × sqrt(252)，窗口不足 20 个观测时不计算
import numpy as np

ANN = np.sqrt(252)
d["vol20"] = d.groupby("stock_code", group_keys=False)["ret"].apply(
    lambda s: s.rolling(20, min_periods=20).std() * ANN
)
vol = d.loc[d["date"] >= "2021-01-01"]

summary = vol.groupby("stock_code").agg(
    简称=("stock_name", "first"),
    滚动均值=("vol20", "mean"), 滚动中位=("vol20", "median"),
    滚动最大=("vol20", "max"), 滚动最小=("vol20", "min"),
    期末值=("vol20", "last"), 有效窗口数=("vol20", "count"),
    全期年化=("ret", lambda s: s.std() * ANN),
)
# 峰值出现日期
peak_date = vol.loc[vol.groupby("stock_code")["vol20"].idxmax(), ["stock_code", "date"]].set_index("stock_code")["date"]
summary["峰值日期"] = peak_date
summary_pct = summary.assign(**{c: summary[c] * 100 for c in
                                ["滚动均值", "滚动中位", "滚动最大", "滚动最小", "期末值", "全期年化"]})
display(summary_pct.sort_values("全期年化", ascending=False).round(2))

# 因窗口内含跨期收益而无法计算的窗口数
expected = vol.groupby("stock_code")["ret"].apply(lambda s: max(len(s) - 19, 0))
lost = (expected - summary["有效窗口数"]).astype(int)
print("各股票预期窗口数与实际有效窗口数之差（跨期收益导致的窗口损失）:")
print(lost[lost > 0].to_string())
print("合计损失窗口数:", int(lost.sum()))"""))

cells.append(nbf.v4.new_code_cell("""# 图4：各股票 20 日滚动年化波动率时序
fig, ax = plt.subplots(figsize=(14, 7))
for code in order:
    sub = vol[vol["stock_code"] == code]
    ax.plot(sub["date"], sub["vol20"] * 100, label=names[code], color=colors[code], linewidth=1.1)
ax.set_title("图4  20个交易日滚动年化波动率（2021-01-04 至 2026-09-16，单位：%）", fontsize=13)
ax.set_xlabel("日期")
ax.set_ylabel("年化波动率（%）")
ax.legend(ncol=5, fontsize=9, loc="upper left")
ax.grid(alpha=0.3)
fig.tight_layout()
plt.show()"""))

cells.append(nbf.v4.new_code_cell("""# 图5：等权组合的滚动波动率与个股波动率均值对比（分散化效应）
# 等权组合日收益：每日对各股票可用收益取平均（停牌日该股缺失，等价于在剩余股票间等权）
eq_ret = vol.groupby("date")["ret"].mean()
eq_vol = eq_ret.rolling(20, min_periods=20).std() * ANN
ind_avg_vol = vol.groupby("date")["vol20"].mean()

fig, ax = plt.subplots(figsize=(14, 6))
ax.plot(eq_vol.index, eq_vol * 100, label="等权组合（10只）", color="black", linewidth=1.6)
ax.plot(ind_avg_vol.index, ind_avg_vol * 100, label="10只个股波动率均值", color="tab:orange", linewidth=1.2)
ax.set_title("图5  等权组合与个股波动率均值：20日滚动年化波动率对比（单位：%）", fontsize=13)
ax.set_xlabel("日期")
ax.set_ylabel("年化波动率（%）")
ax.legend(fontsize=10)
ax.grid(alpha=0.3)
fig.tight_layout()
plt.show()

print("等权组合全期年化波动率(%):", round(float(eq_ret.std() * ANN * 100), 2))
print("个股全期年化波动率均值(%):", round(float(summary["全期年化"].mean() * 100), 2))
print("个股中最低的全期年化波动率(%):", round(float(summary["全期年化"].min() * 100), 2))
print("组合波动率 / 个股均值:", round(float(eq_ret.std() * ANN / summary["全期年化"].mean()), 3))
print("\\n等权组合滚动波动率最高的 10 个日期:")
display((eq_vol * 100).sort_values(ascending=False).head(10).round(2).to_frame("年化波动率(%)"))"""))

cells.append(nbf.v4.new_markdown_cell("""### Step 3：Markdown结果解读

波动水平的分化很明显。按全期年化波动率排序，立讯精密最高（45.79%），隆基绿能42.48%、比亚迪39.11%紧随其后；恒瑞医药33.98%、万华化学33.06%居中；招商银行最低（26.82%），贵州茅台27.25%、美的集团28.24%、中信证券28.35%次之。滚动窗口的均值与中位数给出同样的排序，说明这不是少数极端日造成的假象，而是各股票长期的波动特征。最高与最低相差约1.7倍（45.79% 对 26.82%）。

波动的时点高度集中。个股波动率峰值中，隆基绿能95.75%出现在2024-10-30，中信证券79.53%与恒瑞医药64.36%都出现在2024-10-24，贵州茅台70.56%出现在2024-10-18；等权组合滚动波动率最高的10个日期全部落在2024-10-17至10-30之间。这说明2024年10月是全市场性的高波动期，不是个别股票的特殊事件。另一段高波动期在2021年一季度：万华化学72.18%（2021-03-05）与美的集团60.53%（2021-03-15）的峰值都出现在这一时期。此外立讯精密85.40%（2026-07-03）与比亚迪84.45%（2021-08-05）的峰值更偏个股自身因素。这些时点与市场事件时间吻合，但本节只能说明波动在何时聚集，不能据此认定因果。

图5给出了本节最有价值的一个证据：**等权组合的全期年化波动率为20.70%，不但低于10只个股的均值33.52%，甚至低于个股中波动最小的一只（招商银行26.82%）**，组合波动率仅为个股均值的0.618倍。原因是各股票的日收益不完全同步，涨跌相互抵消，这正是分散投资降低风险的作用；也要注意，这里的"降低"指的是波动率这一风险度量，不等于组合不会亏损。

把第3节的累计净值与本节波动率放在一起看：隆基绿能波动第二高（42.48%）而累计净值最低（0.2412），招商银行波动最低（26.82%）而净值第二高（1.2259），两者方向相反；但比亚迪是个反例——波动第三高（39.11%）却取得最高净值（1.3399）。因此在这个10只股票的样本里，**高波动并没有系统性地换来高收益**，收益与风险的关系更接近"部分股票承担了高波动却没有相应回报"。这只是事后样本的描述性观察：股票池是按行业与商业模式事先选定的，不是按风险因子构建的，且只有10只样本，不能据此推断风险与收益的一般关系，更不涉及因果。

处理规则的代价也已经量化：因窗口内含跨期收益而不计算的窗口共40个（顺丰控股、中信证券各20个），占理论窗口数的0.3%，对整体结论没有实质影响。

核心发现：

- 波动水平分化1.7倍：立讯精密最高45.79%，招商银行最低26.82%；
- 波动有明显的时间聚集，2024年10月是全市场共同的高波动期，2021年一季度是次高；
- 等权组合年化波动率20.70%，低于任何单只个股，分散化把波动降到个股均值的0.617倍；
- 高波动在本样本中并未对应高收益，隆基绿能是"高波动、低收益"的典型。"""))

cells.append(nbf.v4.new_markdown_cell("""## 后续分析结构

后续各节继续严格采用“Step 1分析说明—Step 2代码与实际输出—Step 3结果解读”：

5. 描述统计与异常收益检查  
6. 日收益率Pearson相关性  
7. 等权组合与滞后总市值加权组合  
8. 总体结论、局限与AI使用说明
"""))

nb["cells"].extend(cells)
nbf.write(nb, NB)
print("已写入:", NB, "单元数:", len(nb["cells"]))
