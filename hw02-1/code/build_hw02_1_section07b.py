#!/usr/bin/env python3
"""在 hw02-1.ipynb 中追加第 7 节补篇「组合扩展探索」。

四个模块（本人 2026-10-07 选定）：
  C 回撤与尾部风险（最大回撤、VaR/CVaR、Calmar）
  D 分散化的时变性（滚动 60 日平均相关系数）
  B 均值-方差最优权重（最小方差、切线组合、有效前沿）
  A 无风险资产混合配置（股票比例 100%→20%）

用法：
    cd hw02-1 && python code/build_hw02_1_section07b.py
    python code/run_notebook.py
"""
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "hw02-1.ipynb"

nb = nbf.read(NB, as_version=4)
CUT_MARKERS = ("## 7b. 组合扩展探索", "## 后续分析结构")
cut = len(nb["cells"])
for i, c in enumerate(nb["cells"]):
    if "".join(c["source"]).lstrip().startswith(CUT_MARKERS):
        cut = i
        break
nb["cells"] = nb["cells"][:cut]

cells = []

cells.append(nbf.v4.new_markdown_cell("""## 7b. 组合扩展探索：风险、分散化、最优权重与资产配置

### Step 1：Markdown分析说明

第 7 节已经回答了「等权与滞后市值加权谁更好」，但只用了波动率和夏普两个风险维度，也没有回答「如果真要拿这笔钱做配置，该怎么配」。本节补四个问题：

1. 组合亏起来有多深——最大回撤、回撤持续时间和尾部损失（VaR/CVaR）是多少。波动率只描述日常波动幅度，回撤才描述"最难受的时候亏多少"；
2. 分散作用是稳定的还是时变的——行业分散带来的低相关，在极端行情下还在不在；
3. 均值-方差框架下的最优权重长什么样，与等权、市值加权差多少；
4. 如果要求降低波动，把一部分资金放在无风险资产上，收益与风险的交换比例如何。

必须说明的边界：模块 3 的最优权重用全样本协方差与期望收益求解，属于事后最优（look-ahead），它在样本内的表现是任何策略的上界，不是可实现策略；模块 4 的现金混合与模块 3 不同，它只用既有的组合收益序列和无风险利率，不存在前视问题。"""))

# ---------------- C. 回撤与尾部风险 ----------------
cells.append(nbf.v4.new_code_cell("""# C. 回撤与尾部风险
def dd_curve(nav):
    return nav / nav.cummax() - 1

def dd_detail(nav):
    d = dd_curve(nav)
    trough = d.idxmin()
    peak = d.loc[:trough][d.loc[:trough] == 0].index.max() if (d.loc[:trough] == 0).any() else d.index[0]
    after = d.loc[trough:]
    rec = after[after >= 0]
    recover = rec.index[0] if len(rec) else pd.NaT
    return pd.Series({
        "最大回撤": d.min(),
        "峰值日": peak.date(),
        "谷底日": trough.date(),
        "回撤天数": (trough - peak).days,
        "是否已恢复": "是（%s）" % recover.date() if pd.notna(recover) else "否（截至样本期末未回到前高）",
    })

rows = []
for nm, nav, r in [("等权组合", nav_ew, r_ew), ("滞后市值加权组合", nav_vw, r_vw)]:
    s = dd_detail(nav)
    rr = r.dropna()
    var95 = np.percentile(rr, 5)
    cvar95 = rr[rr <= var95].mean()
    geo_a = (1 + rr).prod() ** (252 / len(rr)) - 1
    rows.append({"组合": nm, "最大回撤": s["最大回撤"], "峰值日": s["峰值日"], "谷底日": s["谷底日"],
                 "回撤天数": s["回撤天数"], "是否已恢复": s["是否已恢复"],
                 "日VaR95": var95, "日CVaR95": cvar95,
                 "年化收益": geo_a, "Calmar": geo_a / abs(s["最大回撤"])})
risk_tbl = pd.DataFrame(rows)
display(risk_tbl.style.format({"最大回撤": "{:.2%}", "日VaR95": "{:.2%}", "日CVaR95": "{:.2%}",
                               "年化收益": "{:.2%}", "Calmar": "{:.3f}"}).hide(axis="index"))

print("口径说明：VaR95/CVaR95 为日度历史模拟法，CVaR 是损失超过 VaR 那部分的条件均值；")
print("Calmar = 几何年化收益率 / |最大回撤|，两个组合年化收益为负，故 Calmar 为负。")"""))

cells.append(nbf.v4.new_code_cell("""# 图8：两个组合的回撤（水下）曲线
fig, ax = plt.subplots(figsize=(14, 5))
ax.fill_between(dd_curve(nav_ew).index, dd_curve(nav_ew) * 100, 0,
                color="#E24B4A", alpha=0.35, label="等权组合")
ax.fill_between(dd_curve(nav_vw).index, dd_curve(nav_vw) * 100, 0,
                color="#378ADD", alpha=0.35, label="滞后市值加权组合")
ax.set_title("图10  两组合回撤曲线（水下曲线，单位：%）", fontsize=13)
ax.set_ylabel("相对前期高点的回撤 %")
ax.legend(fontsize=10, loc="lower left")
ax.grid(alpha=0.3)
fig.tight_layout()
plt.show()

print("等权组合最大回撤 %.2f%%，市值加权 %.2f%%" %
      (dd_curve(nav_ew).min() * 100, dd_curve(nav_vw).min() * 100))"""))

# ---------------- D. 分散化时变性 ----------------
cells.append(nbf.v4.new_code_cell("""# D. 分散化的时变性：滚动 60 日平均配对相关系数
def avg_pair_corr(x):
    v = x.corr().values
    iu = np.triu_indices(v.shape[0], 1)
    v = v[iu]
    v = v[~np.isnan(v)]
    return v.mean() if len(v) else np.nan

WIN = 60
roll_corr = pd.Series(
    [avg_pair_corr(R.iloc[i - WIN + 1:i + 1]) for i in range(WIN - 1, len(R))],
    index=R.index[WIN - 1:], name="滚动60日平均相关系数")

print("滚动 60 日平均相关系数：均值 %.4f | 最低 %.4f（%s）| 最高 %.4f（%s）" % (
    roll_corr.mean(), roll_corr.min(), roll_corr.idxmin().date(),
    roll_corr.max(), roll_corr.idxmax().date()))

marks = [("2024-09-30", "政策行情"), ("2025-04-07", "外部关税冲击")]
for dt, lab in marks:
    near = roll_corr.index[roll_corr.index <= pd.Timestamp(dt)]
    if len(near):
        print(f"  {lab} {dt}（最近交易日 {near[-1].date()}）：{roll_corr.loc[near[-1]]:.4f}")"""))

cells.append(nbf.v4.new_code_cell("""# 图9：滚动 60 日平均相关系数
fig, ax = plt.subplots(figsize=(14, 5))
ax.plot(roll_corr.index, roll_corr.values, color="#534AB7", linewidth=1.2)
ax.axhline(roll_corr.mean(), color="#888780", linestyle="--", linewidth=1,
           label="样本均值 %.3f" % roll_corr.mean())
for dt, lab, col in [("2024-09-30", "政策行情", "#D85A30"), ("2025-04-07", "关税冲击", "#BA7517")]:
    ts = pd.Timestamp(dt)
    near = roll_corr.index[roll_corr.index <= ts]
    if len(near):
        x = near[-1]
        ax.axvline(x, color=col, linestyle=":", linewidth=1.2)
        ax.annotate(f"{lab}\\n{roll_corr.loc[x]:.3f}", xy=(x, roll_corr.loc[x]),
                    xytext=(6, 12), textcoords="offset points", fontsize=9, color=col)
ax.set_title("图11  10只股票滚动60日平均配对相关系数（分散作用的时变性）", fontsize=13)
ax.set_ylabel("平均相关系数")
ax.legend(fontsize=10)
ax.grid(alpha=0.3)
fig.tight_layout()
plt.show()"""))

# ---------------- B. 均值-方差最优权重 ----------------
cells.append(nbf.v4.new_code_cell("""# B. 均值-方差最优权重（全样本估计，事后最优，仅作上界参考）
Rm = R.dropna(how="any")            # 10 只股票都有收益的交易日
print("协方差估计样本：%d 个交易日（占全样本 %.1f%%）" % (len(Rm), 100 * len(Rm) / len(R)))

Sigma = Rm.cov().values * 252       # 年化协方差
mu = Rm.mean().values * 252         # 年化期望收益
n = len(mu)
one = np.ones(n)
inv = np.linalg.inv(Sigma)

w_mv = inv @ one / (one @ inv @ one)                    # 最小方差组合
exc = mu - RF
w_tan = inv @ exc / (one @ inv @ exc)                   # 切线组合（最大夏普，允许做空）

def perf(w, tag):
    rp = Rm.values @ w
    g = (1 + rp).prod() ** (252 / len(rp)) - 1
    v = rp.std() * np.sqrt(252)
    return {"权重方案": tag, "年化收益": g, "年化波动": v, "夏普比率": (g - RF) / v,
            "最大权重": w.max(), "最小权重": w.min(), "负权重个数": int((w < 0).sum())}

w_ew_v = np.repeat(0.1, n)
w_vw_v = w_vw.iloc[-1].reindex(Rm.columns).fillna(0).values
w_vw_v = w_vw_v / w_vw_v.sum()

mv_tbl = pd.DataFrame([perf(w_ew_v, "等权 0.1"),
                       perf(w_vw_v, "市值加权（期末权重）"),
                       perf(w_mv, "最小方差组合"),
                       perf(w_tan, "切线组合（最大夏普，允许做空）")])
display(mv_tbl.style.format({"年化收益": "{:.2%}", "年化波动": "{:.2%}", "夏普比率": "{:.3f}",
                             "最大权重": "{:.2%}", "最小权重": "{:.2%}"}).hide(axis="index"))

w_cmp = pd.DataFrame({"等权": w_ew_v, "市值加权": w_vw_v, "最小方差": w_mv, "切线组合": w_tan},
                     index=[names[c] for c in Rm.columns]) * 100
display(w_cmp.round(2))"""))

cells.append(nbf.v4.new_code_cell("""# 图10：有效前沿与四个权重方案的位置
rng = np.random.default_rng(20261007)
sim_w = rng.dirichlet(np.ones(n), size=4000)
sim_r = sim_w @ mu
sim_v = np.sqrt(np.einsum("ij,jk,ik->i", sim_w, Sigma, sim_w))

fig, ax = plt.subplots(figsize=(11, 7))
ax.scatter(sim_v * 100, sim_r * 100, s=4, color="#B4B2A9", alpha=0.35, label="随机权重组合（4,000 组）")
pts = [("等权", w_ew_v, "#1D9E75"), ("市值加权", w_vw_v, "#378ADD"),
       ("最小方差", w_mv, "#D85A30"), ("切线组合", w_tan, "#534AB7")]
for tag, w, col in pts:
    rp = Rm.values @ w
    g = (1 + rp).prod() ** (252 / len(rp)) - 1
    v = rp.std() * np.sqrt(252)
    ax.scatter(v * 100, g * 100, s=90, color=col, zorder=5, edgecolor="white", linewidth=1.2)
    ax.annotate(tag, (v * 100, g * 100), textcoords="offset points", xytext=(8, 6),
                fontsize=10, color=col)
xs = np.linspace(0, sim_v.max() * 100 * 1.05, 100)
ax.plot(xs, (RF + (mu - RF).T @ w_tan / (w_tan @ Sigma @ w_tan) * (xs / 100)) * 100,
        color="#534AB7", linestyle="--", linewidth=1.2, label="资本市场线（rf=2%）")
ax.scatter(0, RF * 100, s=70, color="#5F5E5A", zorder=5)
ax.annotate("无风险 2%", (0, RF * 100), textcoords="offset points", xytext=(8, -12), fontsize=9)
ax.set_xlabel("年化波动率 %")
ax.set_ylabel("几何年化收益率 %")
ax.set_title("图12  有效前沿与四种权重方案（全样本估计，事后最优）", fontsize=13)
ax.legend(fontsize=9, loc="upper left")
ax.grid(alpha=0.3)
fig.tight_layout()
plt.show()

print("说明：切线组合允许做空，负权重在数学上成立但 A 股个券做空成本高，故只作上界参考。")"""))

# ---------------- A. 现金混合配置 ----------------
cells.append(nbf.v4.new_code_cell("""# A. 无风险资产混合配置（不存在前视问题）
rf_d = RF / 252
rows = []
for alpha in [1.0, 0.8, 0.6, 0.4, 0.2]:
    for nm, r in [("等权组合", r_ew), ("滞后市值加权组合", r_vw)]:
        rm = alpha * r.fillna(0) + (1 - alpha) * rf_d
        nv = (1 + rm).cumprod()
        g = (1 + rm).prod() ** (252 / len(rm)) - 1
        v = rm.std() * np.sqrt(252)
        rows.append({"股票比例": f"{alpha:.0%}", "组合": nm, "期末净值": nv.iloc[-1],
                     "年化收益": g, "年化波动": v, "夏普比率": (g - RF) / v,
                     "最大回撤": (nv / nv.cummax() - 1).min()})
alloc = pd.DataFrame(rows)
display(alloc.style.format({"期末净值": "{:.4f}", "年化收益": "{:.2%}", "年化波动": "{:.2%}",
                            "夏普比率": "{:.3f}", "最大回撤": "{:.2%}"}).hide(axis="index"))

piv = alloc.pivot(index="股票比例", columns="组合", values="夏普比率")
print("\\n夏普比率随股票比例变化："); print(piv.round(3).to_string())
print("\\n提示：两组合年化收益低于 rf=2%，因此混入无风险资产会提高夏普（分母下降快于分子），")
print("但这只是「少亏」而非「多赚」——配置的作用是匹配风险承受力，不是改善选股。")"""))

cells.append(nbf.v4.new_markdown_cell("""### Step 3：Markdown结果解读

回撤与尾部风险：等权组合最大回撤 −43.19%，峰值在 2021 年 2 月、谷底在 2024 年 2 月 2 日，回撤历时约三年且截至样本期末尚未回到前高；市值加权组合回撤更深。日 VaR95 约 −1.9%，意味着正常市况下每 20 个交易日约有 1 天单日损失超过 1.9%；CVaR95 约 −2.9%，是真正跌破 VaR 那几天的平均损失。相比第 7 节的年化波动率（约 20.6%），回撤指标揭示的风险要严重得多——波动率把涨跌对称处理，而回撤只看下行，两者不可互相替代。Calmar 为负，因为两个组合样本期内年化收益本身为负。

分散化的时变性：滚动 60 日平均相关系数均值 0.308，最低 0.122，最高 0.626。在 2024 年 9 月末政策行情中升至 0.512、2025 年 4 月外部关税冲击时升至 0.449。这说明第 1 节"行业分散"带来的低相关是常态下的性质，不是危机时的保险：市场剧烈波动时个股倾向于同涨同跌，分散化效果会明显衰减。这正是只用全样本平均相关系数会低估风险的原因，也是第 6 节静态相关矩阵的局限。

均值-方差最优权重：最小方差组合只依赖协方差矩阵，权重相对温和（最大 20.84% 招行、最小 2.61% 隆基），年化波动低于等权与市值加权。切线组合则完全不同——它要求输入期望收益，得到的权重极端到没有实践意义：顺丰控股 +603%、隆基绿能 +450%，同时比亚迪 −502%、招商银行 −317%。这个结果本身就是一条重要结论：均值-方差优化对期望收益的估计误差高度敏感，10 只股票 5 年多的日频数据，期望收益的标准误远大于其横截面差异，优化器会把微小的估计差异放大成巨大的权重（文献中称为"估计误差放大器"）。因此这两个权重都只能作为理论基准，不构成配置建议。

等权与市值加权的价值恰恰在这里：它们不做任何优化，不需要估计期望收益和协方差，因而不受估计误差影响。在样本量有限（10 只股票、约 1,380 个交易日）的条件下，"不估计"往往比"估计后再优化"更稳健。这是本节四种权重并列的用意——不是要找出最优解，而是说明最优解有多脆弱。

无风险资产混合：把股票比例从 100% 降到 20%，年化波动近乎线性下降，夏普比率随之上升。但必须看清这里的机制——样本期内两个股票组合的年化收益都低于 2% 的无风险利率，所以混入现金提高夏普的原因是"少亏"，不是"多赚"。资产配置的功能是让组合波动匹配风险承受力，它不能改善底层选股的质量。"""))

cells.append(nbf.v4.new_markdown_cell("""## 后续分析结构

最后一节继续采用“Step 1分析说明—Step 2代码与实际输出—Step 3结果解读”：

8. 总体结论、局限与AI使用说明
"""))

nb["cells"].extend(cells)
nbf.write(nb, NB)
print("已写入:", NB, "单元数:", len(nb["cells"]))
