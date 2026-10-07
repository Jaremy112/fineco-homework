#!/usr/bin/env python3
"""在 hw02-1.ipynb 中追加第 6 节「日收益率 Pearson 相关性」。

对应作业必做要求表第 6 行：日收益率 Pearson 相关系数矩阵或热力图（二选一，本节两者都给），
并注明日期对齐方式、缺失处理和实际样本量；解释同行业股票是否更相关。

用法：
    cd hw-02 && python scripts/build_hw02_1_section06.py
    python scripts/run_notebook.py
"""
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "hw02-1.ipynb"

nb = nbf.read(NB, as_version=4)
CUT_MARKERS = ("## 6. 日收益率Pearson相关性", "## 后续分析结构")
cut = len(nb["cells"])
for i, c in enumerate(nb["cells"]):
    if "".join(c["source"]).lstrip().startswith(CUT_MARKERS):
        cut = i
        break
nb["cells"] = nb["cells"][:cut]

cells = []

cells.append(nbf.v4.new_markdown_cell("""## 6. 日收益率Pearson相关性

### Step 1：Markdown分析说明

本节要回答三个问题：第一，10只股票的日收益率彼此相关到什么程度；第二，同行业的股票是否更相关；第三，相关性结构如何解释第4节观察到的分散化效果。

先把三个口径交代清楚。日期对齐 采用成对完整观测（pairwise）：两只股票在同一天都有有效收益时才计入这一对的计算。 缺失处理 沿用第2节的规则——停牌日不生成收益、跨期收益置为缺失，两者都不填零，因此不同股票对的可用天数略有差别。 实际样本量 逐对报告：最少1,373天、最多1,384天。为检验对齐方式是否影响结论，本节同时给出共同样本口径（只保留10只股票都有收益的1,373天）的结果作对照。

分析要点与检查事项：

- 相关系数矩阵与热力图同时给出，矩阵看数值、热力图看结构；
- 报告45对组合的平均、最高与最低相关系数；
- 同行业检验：本样本中唯一同属一个CSMAR行业的两只股票是美的集团与隆基绿能（电气机械和器材制造业），剔除该对与金融板块对后剩43对作为对照；另把金融板块的招商银行与中信证券单独列出；
- 与第4节的分散化结果交叉验证：用平均相关系数推算等权组合波动率的理论值，与实际值对比；
- 相关系数只度量线性共动，不等于因果关系，也不区分"共同因子驱动"与"相互传染"。"""))

cells.append(nbf.v4.new_markdown_cell("""### Step 2：代码与实际输出

下面先把收益率整理成"日期 × 股票"矩阵，再给出相关矩阵、热力图、成对样本量与同行业对照。"""))

cells.append(nbf.v4.new_code_cell("""# 整理为 日期 × 股票 的日收益矩阵
ret_wide = d.loc[d["date"] >= "2021-01-01"].pivot(index="date", columns="stock_code", values="ret")
ret_wide = ret_wide.reindex(columns=order)
print("矩阵形状:", ret_wide.shape)
print("各股票有效收益观测数:")
print(ret_wide.notna().sum().to_string())

# 成对完整观测的相关系数矩阵（pairwise）
corr = ret_wide.corr(method="pearson")
display(corr.round(4))"""))

cells.append(nbf.v4.new_code_cell("""# 图7：Pearson 相关系数热力图
fig, ax = plt.subplots(figsize=(9.5, 8))
im = ax.imshow(corr.values, cmap="coolwarm", vmin=0.10, vmax=0.50)
ax.set_xticks(range(len(order)))
ax.set_yticks(range(len(order)))
ax.set_xticklabels([names[c] for c in order], rotation=45, ha="right")
ax.set_yticklabels([names[c] for c in order])
for i in range(len(order)):
    for j in range(len(order)):
        ax.text(j, i, f"{corr.values[i, j]:.2f}", ha="center", va="center",
                color="white" if abs(corr.values[i, j] - 0.30) > 0.12 else "black", fontsize=8)
cb = fig.colorbar(im, ax=ax, shrink=0.8)
cb.set_label("Pearson 相关系数")
ax.set_title("图7  10只股票日收益率 Pearson 相关系数热力图（2021-01-04 至 2026-09-16）", fontsize=12)
fig.tight_layout()
plt.show()"""))

cells.append(nbf.v4.new_code_cell("""# 相关系数分布：45 对组合的平均、最高与最低
iu = np.triu_indices_from(corr.values, k=1)
pair_r = corr.values[iu]
pairs = pd.DataFrame({
    "股票A": [names[corr.index[i]] for i in iu[0]],
    "股票B": [names[corr.index[j]] for j in iu[1]],
    "相关系数": pair_r,
})
print("配对数:", len(pairs))
print("平均相关系数:", round(float(pairs["相关系数"].mean()), 4))
print("最高相关系数:", round(float(pairs["相关系数"].max()), 4))
print("最低相关系数:", round(float(pairs["相关系数"].min()), 4))
print("相关系数标准差:", round(float(pairs["相关系数"].std()), 4))
print("\\n最相关的 6 对:")
display(pairs.sort_values("相关系数", ascending=False).head(6).round(4))
print("最不相关的 5 对:")
display(pairs.sort_values("相关系数").head(5).round(4))"""))

cells.append(nbf.v4.new_code_cell("""# 成对有效样本量：确认 pairwise 口径下每对实际用了多少天
valid = ret_wide.notna().astype(int)
pair_n = valid.T.dot(valid)
pn = pair_n.values[np.triu_indices_from(pair_n.values, k=1)]
print("成对有效样本量: 最小", int(pn.min()), " 最大", int(pn.max()), " 中位数", int(np.median(pn)))

# 共同样本口径（listwise）作对照，检验日期对齐方式是否影响结论
common = ret_wide.dropna()
corr_common = common.corr()
print("共同样本行数:", len(common))
print("平均相关系数: pairwise", round(float(pairs['相关系数'].mean()), 4),
      " 共同样本", round(float(corr_common.values[iu].mean()), 4))
print("两种口径下单个相关系数差异的最大绝对值:",
      round(float(np.nanmax(np.abs(corr.values - corr_common.values))), 4))"""))

cells.append(nbf.v4.new_code_cell("""# 同行业与板块对照：检验"同行业是否更相关"
industry_map = d.drop_duplicates("stock_code").set_index("stock_code")["industry"].to_dict()
print("各行业包含的股票数:")
print(pd.Series({names[c]: industry_map[c] for c in order}).value_counts().to_string())

same_industry = [("000333.SZ", "601012.SH")]   # 美的集团、隆基绿能：电气机械和器材制造业
financial = [("600036.SH", "600030.SH")]       # 招商银行、中信证券：金融板块
rows = []
for a, b in same_industry:
    rows.append({"分组": "同行业（电气机械和器材制造业）", "股票A": names[a], "股票B": names[b],
                 "相关系数": corr.loc[a, b]})
for a, b in financial:
    rows.append({"分组": "金融板块（银行+证券）", "股票A": names[a], "股票B": names[b],
                 "相关系数": corr.loc[a, b]})
rows.append({"分组": "其余43对照", "股票A": "—", "股票B": "—",
             "相关系数": float(pd.Series(pair_r).drop(
                 [list(zip(iu[0], iu[1])).index((order.index("000333.SZ"), order.index("601012.SH")))]
             ).mean())})
display(pd.DataFrame(rows).round(4))
print("同行业对在45对中的分位数:",
      round(float((pd.Series(pair_r) < corr.loc["000333.SZ", "601012.SH"]).mean()), 3))

# 用平均相关系数推算等权组合波动率的理论值，与第 4 节实测值对照
n_assets = len(order)
rho_bar = float(pairs["相关系数"].mean())
theory = np.sqrt(1 / n_assets + (1 - 1 / n_assets) * rho_bar)
print("\\n等方差近似下组合/个股波动率理论值:", round(float(theory), 4))
print("第4节实测值（组合标准差 / 个股标准差均值）: 0.618") """))

cells.append(nbf.v4.new_markdown_cell("""### Step 3：Markdown结果解读

10只股票的日收益率全部正相关，45对组合的平均相关系数为0.3186，最高的招商银行—贵州茅台为0.4880，最低的立讯精密—招商银行为0.1483，整体处于中等偏低水平。这个水平本身解释了第4节的分散化结果：在等方差近似下，n只资产等权组合的波动率与个股波动率之比为 $\\sqrt{1/n+(1-1/n)\\bar{\\rho}}$，代入 n=10、$\\bar{\\rho}=0.3186$ 得到 理论值0.6219，与第4节实测的0.618几乎一致。也就是说，组合波动率降到个股的六成，完全可以由"10只资产 + 平均相关0.32"解释，不需要额外假设。

 同行业是否更相关——本样本给出的答案是否定的，而且相当明确。 10只股票唯一同属一个CSMAR行业的一对是美的集团与隆基绿能（均为电气机械和器材制造业），其相关系数仅0.1689，在45对中排倒数第二，远低于平均值0.3186；而跨行业的招商银行—贵州茅台反而以0.4880位居第一。金融板块的招商银行与中信证券为0.4588，明显高于平均。

这个结果需要谨慎解释，不能反过来读成"同行业一定不相关"。原因有三：其一，本样本 只有一对同行业股票，单对观测不足以检验行业属性的作用，0.1689 这个数值可能只是这对股票自身的特性；其二，CSMAR的"电气机械和器材制造业"是门类级分类，美的集团是家电终端消费品、隆基绿能是光伏设备制造商，两者的终端需求、产业链位置与驱动因素差别很大，粗分类并不能保证基本面共动；其三，招商银行—贵州茅台的高相关更可能来自"核心资产"与大盘因子的共同驱动，而非行业属性。因此本节的结论是： 在本样本中，粗粒度的行业分类并不能预测日收益率的相关性，行业标签不是分组的充分依据——这一点对第7节的组合构造也有直接含义。

日期对齐方式对结论没有实质影响：pairwise 口径的平均相关系数为0.3186，共同样本（1,373天）口径为0.3183，单个相关系数差异的最大绝对值只有0.0079。这印证了第2节的判断——9个停牌日与2个跨期收益造成的缺失占比极小，任何一种合理的对齐方式都不会改变结论。成对有效样本量最少1,373天、最多1,384天，仍在1,300天以上，估计精度有保障。

最后需要说明相关系数的边界：它只刻画线性共动，不区分"共同因子驱动"与"相互传染"，也不蕴含因果；两个高相关可能只是因为都跟随大盘。此外，相关系数在全样本期是静态的，而第4节显示波动存在时间聚集，危机时期的相关性通常上升，因此用全样本相关估计的风险分散效果在极端行情下可能过于乐观。

核心发现：

- 10只股票日收益全部正相关，平均0.3186，最高0.4880（招行—茅台），最低0.1483（立讯—招行）；
- 平均相关0.32 + 10只资产，理论上把组合波动率降至个股的0.6219倍，与第4节实测0.618吻合；
- 唯一的同行业对（美的—隆基）相关0.1689，排45对中倒数第二，行业粗分类不能预测相关性；
- 日期对齐方式影响极小（两种口径平均相关相差0.0003），结论稳健。"""))

cells.append(nbf.v4.new_markdown_cell("""## 后续分析结构

后续各节继续严格采用“Step 1分析说明—Step 2代码与实际输出—Step 3结果解读”：

7. 等权组合与滞后总市值加权组合  
8. 总体结论、局限与AI使用说明
"""))

nb["cells"].extend(cells)
nbf.write(nb, NB)
print("已写入:", NB, "单元数:", len(nb["cells"]))
