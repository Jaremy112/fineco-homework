#!/usr/bin/env python3
"""在 hw02-1.ipynb 中追加第 2 节「数据检查与收益率构造」。

用法：
    cd hw-02 && python scripts/build_hw02_1_section02.py
    python scripts/run_notebook.py          # 执行并保存输出
"""
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "hw02-1.ipynb"

nb = nbf.read(NB, as_version=4)

# 移除原有的"后续分析结构"占位单元，稍后在末尾写回更新版
nb["cells"] = [c for c in nb["cells"] if not "".join(c["source"]).lstrip().startswith("## 后续分析结构")]

cells = []

cells.append(nbf.v4.new_markdown_cell("""## 2. 数据检查与收益率构造

### Step 1：Markdown分析说明

本节要回答四个问题：第一，主键、日期排序和各股票覆盖是否可靠；第二，相比共同交易日历缺失的观测为什么不填零；第三，日收益率用什么口径，停牌日与复牌日分别怎么处理；第四，单位、数量和涨跌幅限制是否与A股实际相符。

上一节已发现顺丰控股和中信证券的观测日少于其余股票，本节先把它与共同交易日历比较，区分停牌与接口缺口，再构造收益率。关键风险是：若直接按组内相邻行计算收益，停牌后复牌当日的收益实际跨越了整个停牌期，把它当作单日收益会夸大波动并污染描述统计与相关性。

分析要点与处理规则如下：

- 主键：检查 `(股票代码, 日期)` 是否唯一，并按代码、日期升序排列；
- 覆盖：以10只股票交易日的并集作为共同交易日历，逐只股票比较缺失日；
- 缺失成因：若某日其余9只股票均有行情而该股无行情，且缺口连续，则为个股停牌，不是接口返回缺口；
- 停牌日：不生成收益率，也不填0，观测直接缺失；
- 收益率：按股票内相邻观测用后复权收盘价计算，$r_{i,t}=P^{hfq}_{i,t}/P^{hfq}_{i,t-1}-1$；
- 跨期收益：若某观测的前一观测不是共同日历上的前一个交易日，则标记为跨期收益，主口径置为缺失，原始值保留在 `ret_raw` 供敏感性比较；
- 单位检查：核对价格、成交量、成交额和总市值的数量级，检查非正价格与零成交量日；
- 合理性核对：10只股票均为主板（000/002/600/601），日涨跌幅限制为±10%，据此判断极端收益是否越界。"""))

cells.append(nbf.v4.new_markdown_cell("""### Step 2：代码与实际输出

下面依次展示主键与覆盖检查、单位与数量级检查、缺失日与停牌证据、收益率构造与样本流，以及异常收益与涨跌幅限制核对。"""))

cells.append(nbf.v4.new_code_cell("""# 主键、排序、覆盖与单位检查
daily = daily.sort_values(["stock_code", "date"]).reset_index(drop=True)

print("股票—日期主键重复数:", int(daily.duplicated(["stock_code", "date"]).sum()))
print("每只股票日期单调递增:", bool(
    daily.groupby("stock_code")["date"].apply(lambda s: s.is_monotonic_increasing).all()
))

# 共同交易日历取正式样本期内10只股票交易日的并集
calendar = sorted(daily.loc[daily["date"] >= "2021-01-01", "date"].unique())
n_sample = int((daily["date"] >= "2021-01-01").sum())
print("共同交易日历交易日数:", len(calendar))
print("正式样本期理论观测数:", len(calendar) * daily["stock_code"].nunique(), " 实际观测数:", n_sample)

# 单位与数量级检查
display(daily[["close_unadjusted", "close_hfq", "volume_shares",
               "turnover_100m_cny", "market_cap_100m_cny"]].describe().T)
print("非正后复权收盘价:", int((daily["close_hfq"] <= 0).sum()),
      " 零成交量交易日:", int((daily["volume_shares"] == 0).sum()))"""))

cells.append(nbf.v4.new_code_cell("""# 缺失交易日与停牌证据（由 scripts/locate_missing_days.py 生成）
missing_days = pd.read_csv(PROJECT / "audit" / "missing_days_akshare.csv")
display(missing_days)
print("缺失观测合计:", len(missing_days))
print("缺失日当日其余9只均有行情的比例:",
      float((missing_days["other_stocks_with_data"] == missing_days["other_stocks_total"]).mean()))

# 公开公告查证结果（来源见解读）
verified = pd.DataFrame([
    {"股票": "顺丰控股 002352.SZ", "停牌区间": "2021-02-05 至 2021-02-09",
     "交易日数": 3, "事由": "筹划收购嘉里物流股权，2月5日开市起临时停牌，2月10日复牌",
     "来源": "证券时报/中证网 2021-02-10；南方都市报 2021-02-05"},
    {"股票": "中信证券 600030.SH", "停牌区间": "2022-01-19 至 2022-01-26",
     "交易日数": 6, "事由": "A股配股缴款期（1/19—1/25）全天停牌，1/26网上清算继续停牌，1/27开市复牌",
     "来源": "中信证券公告 2022-01-13、2022-01-19；中证网 2022-01-13"},
])
display(verified)"""))

cells.append(nbf.v4.new_code_cell("""# 构造日收益率，并标记跨越停牌期的观测
d = daily.copy()
d["ret_raw"] = d.groupby("stock_code")["close_hfq"].pct_change()

# 用共同交易日历的位置差识别跨期：位置差大于1说明中间跳过了交易日
prev_date = d.groupby("stock_code")["date"].shift(1)
cal_pos = {day: i for i, day in enumerate(calendar)}
pos_now, pos_prev = d["date"].map(cal_pos), prev_date.map(cal_pos)
d["skipped_days"] = (pos_now - pos_prev - 1).where(pos_prev.notna() & (pos_now - pos_prev > 1), 0)
d["cross_period"] = pos_prev.notna() & (pos_now - pos_prev > 1)

# 主口径：跨期收益不作为单日收益，置为缺失；原始值保留在 ret_raw
d["ret"] = d["ret_raw"].where(~d["cross_period"])

print("跨期收益明细（跨越交易日数 > 0）:")
display(d.loc[d["cross_period"], ["stock_code", "date", "skipped_days", "close_hfq", "ret_raw", "ret"]])

in_sample = d["date"] >= "2021-01-01"
print("原始日收益数:", int(d.loc[in_sample, "ret_raw"].notna().sum()))
print("其中跨期收益:", int(d["cross_period"].sum()))
print("主口径有效日收益数:", int(d.loc[in_sample, "ret"].notna().sum()))

display(d.loc[in_sample].groupby("stock_code").agg(
    观测数=("date", "size"), 有效收益=("ret", "count"), 跨期剔除=("cross_period", "sum")
))

# 样本流：逐步记录输入、处理与输出
sample_flow = pd.DataFrame([
    {"步骤": "原始记录（含2020年支持日）", "输入": len(d), "输出": len(d), "变化": 0, "原因": "—"},
    {"步骤": "进入正式样本期", "输入": len(d), "输出": int(in_sample.sum()),
     "变化": int(in_sample.sum()) - len(d), "原因": "剔除10条2020-12-31支持日，只用于生成首个收益"},
    {"步骤": "停牌日不生成收益", "输入": len(calendar) * 10, "输出": int(in_sample.sum()),
     "变化": int(in_sample.sum()) - len(calendar) * 10, "原因": "顺丰3日、中信6日停牌，观测缺失且不填0"},
    {"步骤": "剔除跨期收益", "输入": int(in_sample.sum()), "输出": int(d.loc[in_sample, "ret"].notna().sum()),
     "变化": int(d.loc[in_sample, "ret"].notna().sum()) - int(in_sample.sum()),
     "原因": "复牌日收益跨越停牌期，不当作单日收益"},
])
display(sample_flow)

# 保存派生数据供后续各节使用
returns_path = PROJECT / "data" / "processed" / "daily_returns_20210104_20260916.csv"
d.loc[in_sample, ["stock_code", "stock_name", "date", "industry", "close_unadjusted", "close_hfq",
                  "ret", "ret_raw", "cross_period", "skipped_days", "volume_shares",
                  "turnover_100m_cny", "market_cap_100m_cny"]].to_csv(
    returns_path, index=False, encoding="utf-8-sig")
print("已保存派生收益率数据:", returns_path.relative_to(PROJECT))"""))

cells.append(nbf.v4.new_code_cell("""# 异常收益与涨跌幅限制核对
ret = d.loc[d["date"] >= "2021-01-01", ["stock_code", "stock_name", "date", "ret", "ret_raw", "cross_period"]].dropna(subset=["ret"])

print("|r| > 10% 的观测数:", int((ret["ret"].abs() > 0.10).sum()),
      " |r| > 11% 的观测数:", int((ret["ret"].abs() > 0.11).sum()))
print("日收益极值 top 10（主口径）:")
display(ret.reindex(ret["ret"].abs().sort_values(ascending=False).index).head(10))

print("被剔除的跨期收益原始值（保留在 ret_raw，供敏感性比较）:")
display(d.loc[d["cross_period"], ["stock_code", "stock_name", "date", "skipped_days", "ret_raw"]])"""))

cells.append(nbf.v4.new_markdown_cell("""### Step 3：Markdown结果解读

主键与排序检查通过：`(股票代码, 日期)` 重复数为0，10只股票均按日期升序排列。共同交易日历为1,384个交易日，正式样本期理论观测13,840条，实际13,831条，缺失9条，缺失率0.07%。

这9条缺失全部来自两只股票的停牌，不是接口返回缺口：顺丰控股缺2021-02-05、02-08、02-09共3日，因筹划收购嘉里物流股权于2月5日开市起临时停牌、2月10日复牌；中信证券缺2022-01-19至01-26共6日，因A股配股缴款期（1月19日至25日）全天停牌、1月26日网上清算继续停牌、1月27日开市复牌。判据是这些缺失日连续，且当日其余9只股票全部有行情，说明是这两只证券自身停止交易而非数据未返回；公开公告进一步印证了起止日期。9个缺失观测按规则不填0，直接不生成收益率。

按组内相邻后复权收盘价计算，共得到13,831个原始日收益，其中2个是跨期收益：顺丰控股2021-02-10跨越3个停牌日、原始值+10.0043%；中信证券2022-01-27跨越6个停牌日、原始值−0.3300%。这两个数字刻画的是停牌期加复牌当日的累计价格变化，不是单日收益。顺丰的+10.0043%尤其典型：若直接当单日收益会被读成涨停，实际是4个交易日的累计涨幅。因此主口径把它置为缺失，最终有效日收益13,829个，占理论样本13,840的99.92%；原始值保留在 `ret_raw` 列，后续必要时可做保留该观测的敏感性比较。

中信证券复牌日收益仅−0.33%，也值得单独说明：该日同时是配股除权日（配股价14.43元/股，每10股配售1.5股），后复权序列已包含配股的价格调整，因此价格序列连续，收益没有被除权的机械摊薄扭曲。

单位与合理性核对未发现技术错误。后复权收盘价全部为正，零成交量交易日为0；不复权收盘价区间11—2,601元，后复权价106.16—19,782.65元，成交量103万股—13.51亿股，成交额1.50—421.97亿元，历史总市值833.59—32,673.70亿元，各项数量级与A股实际情况相符。日收益绝对值超过10%的观测共22个，最大为隆基绿能2024-09-30的+10.0257%，超过11%的观测为0。10只股票均为主板（000/002/600/601），日涨跌幅限制为±10%，22个极端值全部紧贴限制边界，说明价格与复权序列没有出现单位错位或字段错配；个别略超10%来自收盘价两位小数的四舍五入，不是数据错误。

核心发现：

- 缺失9个观测全部由公司行为停牌造成，已用共同交易日历与公开公告双重印证，既不填0也不整只删除；
- 识别出2个跨期收益并在主口径中剔除，避免把停牌期累计变化误当单日收益，其中顺丰复牌日的+10.0043%是最容易被误读的一个；
- 主口径有效日收益13,829个，占理论样本的99.92%，样本损失极小且原因可解释；
- 单位、数量级与涨跌幅限制三项核对均通过，未发现需要修正的技术错误。"""))

cells.append(nbf.v4.new_markdown_cell("""## 后续分析结构

后续各节继续严格采用“Step 1分析说明—Step 2代码与实际输出—Step 3结果解读”：

3. 不复权价格、累计收益和日收益图形  
4. 20日滚动年化波动率  
5. 描述统计与异常收益检查  
6. 日收益率Pearson相关性  
7. 等权组合与滞后总市值加权组合  
8. 总体结论、局限与AI使用说明
"""))

nb["cells"].extend(cells)
nbf.write(nb, NB)
print("已写入:", NB, "单元数:", len(nb["cells"]))
