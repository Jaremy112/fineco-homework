#!/usr/bin/env python3
"""在 hw02-1.ipynb 中追加第 7 节「等权组合与滞后总市值加权组合」。

对应作业要求：等权 r_t = Σ 0.1 r_i,t；市值加权 w_{i,t-1} = MV_{i,t-1} / Σ MV_{j,t-1}；
比较累计收益与净值曲线、几何年化收益率、年化波动率、最大回撤；核验每日权重和为 1。

用法：
    cd hw-02 && python scripts/build_hw02_1_section07.py
    python scripts/run_notebook.py
"""
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "hw02-1.ipynb"

nb = nbf.read(NB, as_version=4)
CUT_MARKERS = ("## 7. 等权组合与滞后总市值加权组合", "## 后续分析结构")
cut = len(nb["cells"])
for i, c in enumerate(nb["cells"]):
    if "".join(c["source"]).lstrip().startswith(CUT_MARKERS):
        cut = i
        break
nb["cells"] = nb["cells"][:cut]

cells = []

cells.append(nbf.v4.new_markdown_cell("""## 7. 等权组合与滞后总市值加权组合

### Step 1：Markdown分析说明

本节要回答三个问题：第一，两种权重的组合表现差多少；第二，差异来自哪里——是权重集中程度，还是被重仓股票自身表现；第三，组合相对个股的分散作用有多大。

组合构造按作业给定的教学设定：每日按目标权重计算收益、忽略交易成本。

$$r^{EW}_{p,t}=\\sum_{i=1}^{10}0.1\\,r_{i,t},\\qquad
w_{i,t-1}=\\frac{MV_{i,t-1}}{\\sum_{j=1}^{10}MV_{j,t-1}},\\quad
r^{VW}_{p,t}=\\sum_{i=1}^{10}w_{i,t-1}r_{i,t}$$

其中 $MV_{i,t-1}$ 是上一交易日收盘时的**总市值**，用不复权收盘价与巨潮总股本构造，不用流通市值、不用当前市值回填、不用复权价乘股本。

缺失行情与市值的处理规则如下：某只股票当日停牌或当日收益为跨期收益被剔除时，**该股当日不进入组合，权重在其余可用股票之间重新归一化**，两种组合都按此处理；因此停牌日的等权组合实际是"9只或8只股票等权"，而不是给缺失股票填零。市值权重需要上一交易日市值，若上一交易日该股停牌，则沿用其最近一次可观测市值。

分析要点与检查事项：

- 评价期间：两组合使用完全相同的1,384个交易日（2021-01-04至2026-09-16），保证可比；
- 权重核验：逐日检查两种权重之和是否为1；
- 比较指标：累计收益与净值曲线、几何年化收益率、年化波动率、最大回撤；
- 年化波动率由组合日收益序列直接计算，**不能用个股波动率的加权平均**代替；
- 权重集中度：用平均权重、赫芬达尔指数（HHI）与前三大权重占比刻画；
- 边界：这是事后选定样本的事后测算，不等同于历史可实施策略，也不预示未来收益。"""))

cells.append(nbf.v4.new_markdown_cell("""### Step 2：代码与实际输出

下面先构造权重并核验，再计算组合收益与评价指标，最后给出净值曲线、回撤曲线与权重集中度。"""))

cells.append(nbf.v4.new_code_cell("""# 构造 日期 × 股票 的收益矩阵与市值矩阵（市值矩阵含 2020-12-31 支持日）
ret_all = d.pivot(index="date", columns="stock_code", values="ret")
mv_all = d.pivot(index="date", columns="stock_code", values="market_cap_100m_cny")
R = ret_all.loc[ret_all.index >= "2021-01-01"].reindex(columns=order)

# 上一交易日总市值：停牌日沿用该股最近一次可观测市值，再整体滞后一期
mv_lag = mv_all.ffill().shift(1).loc[R.index]

available = R.notna()                      # 当日有有效收益的股票
n_avail = available.sum(axis=1)
print("评价期间:", R.index[0].date(), "至", R.index[-1].date(), " 交易日数 T =", len(R))
print("每日可用股票数: 最小", int(n_avail.min()), " 最大", int(n_avail.max()))
print("可用股票数小于10的天数:", int((n_avail < 10).sum()), "（停牌日与复牌日）")
print("滞后市值缺失数:", int(mv_lag.isna().sum().sum()))

# 等权权重：在当日可用股票之间等权（等价于给每只可用股票 1/n_avail）
w_eq = available.div(n_avail, axis=0)
# 市值加权权重：用 t-1 总市值，同样只在当日可用股票之间归一化
mv_eff = mv_lag.where(available)
w_vw = mv_eff.div(mv_eff.sum(axis=1), axis=0)

print("\\n权重和核验：")
print("  等权  权重和 最小值", round(float(w_eq.sum(axis=1).min()), 10),
      " 最大值", round(float(w_eq.sum(axis=1).max()), 10))
print("  市值  权重和 最小值", round(float(w_vw.sum(axis=1).min()), 10),
      " 最大值", round(float(w_vw.sum(axis=1).max()), 10))"""))

cells.append(nbf.v4.new_code_cell("""# 组合日收益与净值
r_ew = (w_eq * R.fillna(0)).sum(axis=1)
r_vw = (w_vw * R.fillna(0)).sum(axis=1)
nav_ew = (1 + r_ew).cumprod()
nav_vw = (1 + r_vw).cumprod()


def portfolio_metrics(r, nav, label):
    dd = nav / nav.cummax() - 1
    return {
        "组合": label,
        "评价期交易日数 T": len(r),
        "累计净值": nav.iloc[-1],
        "累计收益": nav.iloc[-1] - 1,
        "几何年化收益率": (1 + r).prod() ** (252 / len(r)) - 1,
        "年化波动率": r.std() * np.sqrt(252),
        "最大回撤": -dd.min(),
        "回撤谷底日期": str(dd.idxmin().date()),
    }


metrics_tbl = pd.DataFrame([
    portfolio_metrics(r_ew, nav_ew, "等权组合"),
    portfolio_metrics(r_vw, nav_vw, "市值加权组合"),
]).set_index("组合")
display(metrics_tbl.round(6))

diff = metrics_tbl.drop(columns=["评价期交易日数 T", "回撤谷底日期"]).loc["市值加权组合"] - \\
       metrics_tbl.drop(columns=["评价期交易日数 T", "回撤谷底日期"]).loc["等权组合"]
print("差异（市值加权 − 等权）:")
print(diff.round(6).to_string())
print("\\n两组合日收益的相关系数:", round(float(np.corrcoef(r_ew, r_vw)[0, 1]), 4))"""))

cells.append(nbf.v4.new_code_cell("""# 图8：两组合净值曲线
fig, ax = plt.subplots(figsize=(14, 6.5))
ax.plot(nav_ew.index, nav_ew, label="等权组合", color="tab:blue", linewidth=1.5)
ax.plot(nav_vw.index, nav_vw, label="市值加权组合（滞后总市值）", color="tab:orange", linewidth=1.5)
ax.axhline(1.0, color="gray", linestyle="--", linewidth=1)
ax.set_title("图8  两类组合累计净值曲线（起点=1，2021-01-04 至 2026-09-16，忽略交易成本）", fontsize=13)
ax.set_xlabel("日期")
ax.set_ylabel("累计净值（倍）")
ax.legend(fontsize=10)
ax.grid(alpha=0.3)
fig.tight_layout()
plt.show()

# 图9：回撤曲线
fig, ax = plt.subplots(figsize=(14, 5))
dd_ew = nav_ew / nav_ew.cummax() - 1
dd_vw = nav_vw / nav_vw.cummax() - 1
ax.fill_between(dd_ew.index, dd_ew * 100, 0, color="tab:blue", alpha=0.35, label="等权组合")
ax.fill_between(dd_vw.index, dd_vw * 100, 0, color="tab:orange", alpha=0.35, label="市值加权组合")
ax.set_title("图9  两类组合回撤曲线（相对历史峰值，单位：%）", fontsize=13)
ax.set_xlabel("日期")
ax.set_ylabel("回撤（%）")
ax.legend(fontsize=10)
ax.grid(alpha=0.3)
fig.tight_layout()
plt.show()"""))

cells.append(nbf.v4.new_code_cell("""# 权重集中度：平均权重、HHI 与等效分散只数
w_mean = w_vw.mean().rename(index=names).sort_values(ascending=False)
display(w_mean.round(4).to_frame("平均市值权重"))

hhi = (w_vw ** 2).sum(axis=1)
top3 = w_vw.apply(lambda row: row.nlargest(3).sum(), axis=1)
concentration = pd.DataFrame({
    "指标": ["HHI 均值", "等效分散只数 1/HHI", "前三大权重合计 均值", "最大个股权重 均值",
           "等权基准 HHI", "等权等效只数"],
    "数值": [hhi.mean(), 1 / hhi.mean(), top3.mean(), w_vw.max(axis=1).mean(), 0.10, 10.0],
})
display(concentration.round(4))
print("个股权重的最大值（单日）:", round(float(w_vw.max().max()), 4),
      " 对应股票:", names[w_vw.max(axis=1).idxmax() and w_vw.max().idxmax()])"""))

cells.append(nbf.v4.new_markdown_cell("""### Step 3：Markdown结果解读

两个组合在相同的1,384个交易日（2021-01-04至2026-09-16）上评价，权重和逐日核验恒为1，滞后总市值无缺失。**两个组合在样本期内都是亏损的**：等权组合累计净值0.9089（−9.11%），几何年化收益率−1.72%；市值加权组合累计净值0.8512（−14.88%），几何年化收益率−2.89%。这与第3节"4只上涨、6只下跌"的个股分布一致——多数股票下跌时，组合难以独善其身。

**市值加权比等权多亏5.77个百分点**（几何年化低1.17个百分点），差异来源是权重集中与被重仓股票的表现。市值加权组合中贵州茅台的平均权重高达34.49%（单日最高41.74%），招商银行16.50%、比亚迪13.06%，前三大合计64.13%；HHI均值0.1865，对应**等效分散只数仅5.36只**，远低于等权的10只。而贵州茅台恰恰是样本期内表现较差的股票之一（累计净值0.7353，−26.47%），把三分之一以上的权重压在一只下跌26%的股票上，直接拖累了整个组合。等权组合给每只股票10%的固定权重，既限制了茅台的拖累，也充分分享了比亚迪（+33.99%）的上涨。

值得注意的是，**集中度提高并没有换来更高的波动，也没有换来更高收益**：两组合年化波动率几乎相同（等权20.70%、市值加权20.56%，市值加权反而低0.15个百分点），最大回撤也非常接近（43.28%对43.71%）。原因是权重最集中的贵州茅台本身是个股中波动率较低的（27.25%，倒数第三），所以向它集中既没有放大波动，也没有改善收益——只是把收益风险特征向这只股票靠拢。两个组合的日收益相关系数高达0.9412，说明权重差异并没有改变组合的日度行为，差异主要来自个别重仓股的长期走势。

回撤曲线给出了另一个角度：两组合的最大回撤幅度接近，但**谷底时间不同**——等权组合最深回撤出现在2024-02-02（43.28%），市值加权组合出现在2022-10-31（43.71%）。等权组合中小市值股票权重更高，在2024年初的小微盘流动性冲击中受损更明显；市值加权组合则更早见底。这说明权重的差异不仅影响收益水平，也改变了组合对不同类型市场冲击的敏感度。

分散投资的作用在这里得到最终确认：两个组合的年化波动率都在20.6%左右，而10只个股的年化波动率均值是33.52%、最低的招商银行也有26.82%。也就是说，**无论用哪种权重，把10只股票放在一起都把波动降到个股水平的六成左右**，这与第4节的实测（0.618）和第6节的理论推算（0.6219）完全一致。

最后必须说明本节的边界。其一，这是**事后测算**：股票池按行业与商业模式事先选定，但组合并非历史实际持有，也没有考虑交易成本——每日按目标权重再平衡在现实中会产生换手成本，市值加权组合的换手通常低于等权组合，这一差异在本节被忽略了。其二，样本期内两个组合都亏损，这与A股2021年以来的整体走势有关，不能据此判断两种权重方式的优劣，更不能外推为未来收益。其三，10只股票的样本极小，权重集中度的结论高度依赖贵州茅台这一只股票的表现，换成另一组股票结论可能完全不同。

核心发现：

- 两组合均亏损：等权累计−9.11%（年化−1.72%），市值加权−14.88%（年化−2.89%），市值加权多亏5.77个百分点；
- 差异源自权重集中：茅台平均权重34.49%，等效分散只数仅5.36只，而茅台累计下跌26.47%；
- 集中度提高既未增加波动（20.56% 对 20.70%）也未改善收益，最大回撤接近但谷底时点不同（2022-10 对 2024-02）；
- 分散作用确认：两组合波动率约20.6%，远低于个股均值33.52%，与第4、6节结论互相印证。"""))

cells.append(nbf.v4.new_markdown_cell("""## 后续分析结构

最后一节继续采用“Step 1分析说明—Step 2代码与实际输出—Step 3结果解读”：

8. 总体结论、局限与AI使用说明
"""))

nb["cells"].extend(cells)
nbf.write(nb, NB)
print("已写入:", NB, "单元数:", len(nb["cells"]))
