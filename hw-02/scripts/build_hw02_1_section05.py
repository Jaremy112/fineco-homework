#!/usr/bin/env python3
"""在 hw_02-1.ipynb 中追加第 5 节「描述统计与异常收益检查」。

对应作业必做要求表第 5 行：有效观测数、均值、标准差、最小值、中位数、最大值、偏度、超额峰度；
以及"检查离群值是必做、缩尾不是必做"和"影响结论的处理须比较处理前后"两条要求。

用法：
    cd hw-02 && python scripts/build_hw02_1_section05.py
    python scripts/run_notebook.py
"""
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "hw_02-1.ipynb"

nb = nbf.read(NB, as_version=4)
CUT_MARKERS = ("## 5. 描述统计与异常收益检查", "## 后续分析结构")
cut = len(nb["cells"])
for i, c in enumerate(nb["cells"]):
    if "".join(c["source"]).lstrip().startswith(CUT_MARKERS):
        cut = i
        break
nb["cells"] = nb["cells"][:cut]

cells = []

cells.append(nbf.v4.new_markdown_cell("""## 5. 描述统计与异常收益检查

### Step 1：Markdown分析说明

本节要回答三个问题：第一，10只股票日收益率的分布形态如何；第二，哪些观测算异常值、它们是否合理；第三，如果把这些异常观测删掉或缩尾，主要结果会不会变。

先说明分工：重复记录、缺失值、单位、日期和分母有效性已在第2节核对完毕，本节聚焦**离群值与分布形态**。异常值的作用按作业要求理解为"定位需要解释的记录"，不是"自动生成删除名单"；检查离群值是必做项，缩尾不是必做项。

因此本节的做法是：先给出完整描述统计，再用两种口径识别异常，最后做一次处理前后的敏感性比较，用数字说明"删或不删"对结论的影响，再决定保留。

判定口径与检查事项：

- 描述统计：有效观测数、均值、标准差、最小值、中位数、最大值、偏度、超额峰度，逐只股票给出；
- 异常口径一：个股内部标准化，$|z|>4$、$>5$、$>6$，用于看极端观测有多少；
- 异常口径二：绝对值达到9.5%，即接近主板±10%涨跌幅限制，用于看涨跌停级别的观测有多少；
- 分布形态：偏度与超额峰度是否为正，判断是否存在尖峰厚尾；
- 敏感性：剔除绝对值9.5%以上的观测后，比较各股票均值与标准差的变化；
- 决策依据：若处理后主要统计量与股票间排序基本不变，就保留原观测，只作解释，不做缩尾或删除。"""))

cells.append(nbf.v4.new_markdown_cell("""### Step 2：代码与实际输出

下面先给出按作业要求逐项列明的描述统计，再用箱线图比较10只股票的分布与离群点，最后识别异常观测并做处理前后的敏感性比较。"""))

cells.append(nbf.v4.new_code_cell("""# 描述统计：作业要求逐项列明的 8 个统计量
ret_stats = d.loc[d["date"] >= "2021-01-01"].dropna(subset=["ret"])
desc = ret_stats.groupby("stock_code").agg(
    简称=("stock_name", "first"),
    有效观测数=("ret", "size"),
    均值=("ret", "mean"),
    标准差=("ret", "std"),
    最小值=("ret", "min"),
    中位数=("ret", "median"),
    最大值=("ret", "max"),
    偏度=("ret", "skew"),
    超额峰度=("ret", lambda s: s.kurt()),   # pandas 的 kurt 已是超额峰度（减 3）
)
display(desc.round({c: 6 for c in ["均值", "标准差", "最小值", "中位数", "最大值"]}
                   | {c: 4 for c in ["偏度", "超额峰度"]}))

print("全部股票合计有效观测数:", len(ret_stats))
print("池化日收益均值:", round(float(ret_stats["ret"].mean()), 6),
      " 池化日收益标准差:", round(float(ret_stats["ret"].std()), 6))
print("池化偏度:", round(float(ret_stats["ret"].skew()), 4),
      " 池化超额峰度:", round(float(ret_stats["ret"].kurt()), 4))
print("正收益观测占比:", round(float((ret_stats["ret"] > 0).mean()), 4))"""))

cells.append(nbf.v4.new_code_cell("""# 图6：10只股票日收益率箱线图（对比分布与离群点）
fig, ax = plt.subplots(figsize=(13, 6))
data = [ret_stats.loc[ret_stats["stock_code"] == c, "ret"].to_numpy() for c in order]
bp = ax.boxplot(data, tick_labels=[names[c] for c in order], showfliers=True,
                flierprops={"marker": ".", "markersize": 3, "alpha": 0.4})
ax.axhline(0.10, color="red", linestyle="--", linewidth=0.9, label="±10% 涨跌幅限制")
ax.axhline(-0.10, color="green", linestyle="--", linewidth=0.9)
ax.axhline(0, color="gray", linewidth=0.8)
ax.set_title("图6  10只股票日收益率分布箱线图（2021-01-04 至 2026-09-16）", fontsize=13)
ax.set_ylabel("日收益率")
ax.legend(fontsize=9)
ax.grid(alpha=0.3, axis="y")
fig.tight_layout()
plt.show()"""))

cells.append(nbf.v4.new_code_cell("""# 异常观测识别：个股内标准化 z 值 + 接近涨跌停的绝对阈值
ret_stats = ret_stats.assign(
    z=ret_stats.groupby("stock_code")["ret"].transform(lambda s: (s - s.mean()) / s.std())
)
for k in [4, 5, 6]:
    n_k = int((ret_stats["z"].abs() > k).sum())
    print(f"|z| > {k} 的观测数: {n_k}（占有效样本 {n_k / len(ret_stats) * 100:.3f}%）")
print("|r| >= 9% 的观测数:", int((ret_stats["ret"].abs() >= 0.09).sum()))
print("|r| >= 9.5% 的观测数:", int((ret_stats["ret"].abs() >= 0.095).sum()))

print("\\n绝对值最大的 10 个观测及其 z 值:")
display(ret_stats.reindex(ret_stats["ret"].abs().sort_values(ascending=False).index)
        .head(10)[["stock_code", "stock_name", "date", "ret", "z"]].round(4))"""))

cells.append(nbf.v4.new_code_cell("""# 敏感性比较：剔除绝对值 9.5% 以上的观测后，均值与标准差的变化
THRESH = 0.095
kept = ret_stats[ret_stats["ret"].abs() < THRESH]
comp = pd.DataFrame({
    "有效观测数(原)": ret_stats.groupby("stock_code")["ret"].size(),
    "剔除观测数": ret_stats.groupby("stock_code")["ret"].size() - kept.groupby("stock_code")["ret"].size(),
    "均值(原)": ret_stats.groupby("stock_code")["ret"].mean(),
    "均值(剔除后)": kept.groupby("stock_code")["ret"].mean(),
    "标准差(原)": ret_stats.groupby("stock_code")["ret"].std(),
    "标准差(剔除后)": kept.groupby("stock_code")["ret"].std(),
})
comp["均值变化(基点)"] = (comp["均值(剔除后)"] - comp["均值(原)"]) * 1e4
comp["标准差变化(百分点)"] = (comp["标准差(剔除后)"] - comp["标准差(原)"]) * 100
display(comp.round(6))
print("合计剔除观测数:", int(comp["剔除观测数"].sum()))
print("均值变化的最大绝对值(基点):", round(float(comp["均值变化(基点)"].abs().max()), 2))
print("标准差变化的最大绝对值(百分点):", round(float(comp["标准差变化(百分点)"].abs().max()), 4))
print("波动率排序是否改变:",
      list(comp["标准差(原)"].sort_values(ascending=False).index) !=
      list(comp["标准差(剔除后)"].sort_values(ascending=False).index))"""))

cells.append(nbf.v4.new_markdown_cell("""### Step 3：Markdown结果解读

描述统计显示，10只股票的有效观测数为1,377—1,384个（顺丰控股1,380、中信证券1,377，因停牌与跨期剔除少于其余8只）。日均收益最高的是比亚迪（+0.0513%），最低的是隆基绿能（−0.0671%）与顺丰控股（−0.0586%）；贵州茅台（−0.0076%）与恒瑞医药（−0.0303%）也为负。日收益标准差最高的是立讯精密（2.885%），最低的是招商银行（1.690%），与第4节的年化波动率排序完全一致——两项指标互为印证，不是两套口径各说各话。

最小值和最大值贴近但不超出±10%：多数股票的最大值与最小值落在−10%至+10%之间，只有美的集团（−8.42%至+7.32%）、招商银行（−8.63%至+9.07%）和贵州茅台（−7.56%至+9.50%）在样本期内没有触及涨跌停。这与10只股票均为主板、日涨跌幅限制±10%的制度约束相符。

分布形态上，10只股票的**偏度全部为正**（0.14—0.94），**超额峰度全部为正**（0.95—6.01），池化后偏度0.409、超额峰度2.988。正的偏度说明右侧极端收益略多于左侧；正的超额峰度说明分布比正态更"尖峰厚尾"，极端日的出现频率高于正态分布预期。中信证券的超额峰度最高（6.01），与其在2024年9—10月券商行情中的连续大幅波动一致；顺丰控股（3.43）、招商银行（3.30）、贵州茅台（4.33）次之。这也意味着用正态假设做风险估计会低估尾部风险。池化样本中正收益占比46.44%，略低于一半。

异常观测的识别结果是：按个股内标准化口径，$|z|>4$ 的观测62个（占0.448%），$|z|>5$ 的14个（0.101%），**$|z|>6$ 的0个**；按绝对阈值，日收益绝对值达到9%的58个、达到9.5%的42个。也就是说，无论用哪种口径，极端观测的占比都在0.5%以内，且不存在与整体分布完全脱节的孤立点——最极端的观测也只到$|z|$约5，且它们的绝对值都紧贴10%的涨跌停线。

敏感性比较给出了处理依据：把绝对值9.5%以上的42个观测剔除后（隆基绿能12个、立讯精密9个、比亚迪与恒瑞医药各6个、中信证券5个、万华化学2个、顺丰控股与贵州茅台各1个，美的集团与招商银行为0），标准差变化最大的是隆基绿能（−0.155个百分点，相当于原值的5.8%）与立讯精密（−0.105个百分点）；均值变化最大的是中信证券（−3.64个基点），**其日均收益由+0.0223%转为−0.0141%，说明该股的日均收益主要由少数大幅上涨日贡献**，这一点值得单独留意。

位次上也要如实说明：剔除后标准差排序在两对相邻股票之间发生互换——中信证券与美的集团（原标准差相差0.7个基点）、恒瑞医药与万华化学（相差5.7个基点）。两端的排序不变，立讯精密仍最高、招商银行仍最低；发生互换的两对本身差距就在统计上难以区分的水平，且剔除与否都只影响相邻位次，不改变"高波动组—中波动组—低波动组"的整体梯队。综合看，处理前后的差异集中在个别股票的相邻位次与个别均值符号，**幅度不超过原标准差的6%**。

据此作出处理决定：**不删除、不缩尾，保留全部13,829个有效观测**，只对异常值作出解释。理由是这些观测全部落在涨跌停制度允许的范围内，很可能是真实的市场价格变动而非录入错误；既然剔除与否不改变排序与结论，就没有理由为了减少"不好看的数字"而损失真实信息。需要说明的是，正的超额峰度意味着后续若用正态假设计算风险指标（如在险价值），会低估尾部风险。

核心发现：

- 日均收益最高为比亚迪+0.0513%，最低为隆基绿能−0.0671%；日波动最大为立讯精密2.885%，最小为招商银行1.690%，与第4节年化口径一致；
- 10只股票偏度与超额峰度均为正，池化超额峰度2.988，分布尖峰厚尾，正态假设会低估尾部风险；
- 极端观测占比极低（|z|>5 仅0.101%，|z|>6 为0），且全部紧贴±10%涨跌停线，未见技术错误；
- 剔除42个极端观测后标准差变化不超过原值的6%，仅两对相邻位次互换，故保留全部观测，不做缩尾或删除。"""))

cells.append(nbf.v4.new_markdown_cell("""## 后续分析结构

后续各节继续严格采用“Step 1分析说明—Step 2代码与实际输出—Step 3结果解读”：

6. 日收益率Pearson相关性  
7. 等权组合与滞后总市值加权组合  
8. 总体结论、局限与AI使用说明
"""))

nb["cells"].extend(cells)
nbf.write(nb, NB)
print("已写入:", NB, "单元数:", len(nb["cells"]))
