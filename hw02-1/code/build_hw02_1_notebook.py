#!/usr/bin/env python3
from pathlib import Path
import nbformat as nbf

root = Path(__file__).resolve().parents[1]
out = root / "hw02-1.ipynb"
nb = nbf.v4.new_notebook()
nb["metadata"]["kernelspec"] = {"display_name": "Python (FinEco)", "language": "python", "name": "fineco"}
nb["metadata"]["language_info"] = {"name": "python", "version": "3.12.12"}

cells = []
cells.append(nbf.v4.new_markdown_cell("""# HW02-1：股票收益与组合风险分析

- **姓名：**朱家瑞
- **学号：**待填写（坚果云提交前补充完整学号）
- **作业简介或教师作业页面链接：**https://lianxhcn.github.io/FinEco/exercises/hw-02.html
- **个人 GitHub 仓库访问地址：**https://github.com/Jaremy112/fineco-homework
- **HW02-1 目录链接：**https://github.com/Jaremy112/fineco-homework/tree/main/hw-02
- **HW02-2 目录链接：**待完成HW02-2后补充
- **数据来源、获取日期与样本期间：**AKShare 1.18.39（新浪财经日行情、巨潮资讯股本变动）为主要数据源，CSMAR上市公司基本信息年度表用于统一简称、上市日期及2025年末行业分类，Wind金融数据服务用于关键字段交叉核验；获取日期为2026-09-18；正式样本为2021-01-01至2026-09-16，并补充每只股票在2021年前最后一个有效交易日用于计算首个日收益率。
- **AI 使用声明：**使用了Hermes Agent（Codex）辅助读取教师作业要求、设计数据获取与审计流程、编写和检查Python代码；使用Wind MCP调用万得金融数据服务。股票池、字段口径、异常处理和结论由本人核对，Notebook保留数据来源、参数、实际输出和局限说明。

## 分析目的与总体思路

本文选择10只至少覆盖5个CSMAR行业、且均在样本开始前上市的A股，先取得不复权收盘价、经公司行为调整的复权收盘价、成交量、成交额和历史总市值，再检查主键、日期、覆盖、缺失、停牌和异常收益。在统一的数据口径上，依次完成价格与累计收益图、日收益及滚动波动率、描述统计、相关性分析，并比较每日等权与使用上一交易日总市值确定权重的市值加权组合。分析遵循“说明—代码与实际输出—结果解读”的结构。"""))

cells.append(nbf.v4.new_markdown_cell("""## 1. 选股与获取数据

### Step 1：Markdown分析说明

本节要回答两个问题：第一，所选10只股票是否满足至少覆盖5个行业、在2021年以前上市且不依据样本期事后涨幅选取；第二，取得的数据是否覆盖作业要求的价格、收益率、流动性和历史总市值口径。先冻结股票池再下载，可以避免根据2021—2026年的实际表现替换股票而产生事后选择。

本作业优先使用AKShare获取行情：不复权和后复权日行情来自新浪财经接口，股本变动来自巨潮资讯接口。由于本题要求历史**总市值**，而新浪行情接口只直接提供流通股本，本文用巨潮资讯按变动日期记录的总股本与同日不复权收盘价构造历史总市值；不使用流通市值，也不使用复权价格乘股本。Wind用于股票档案、统一行业分类和关键日期的总市值交叉核验，以减少代码、日期、单位和口径误判。复权价格仅作为连续收益分析尺度，不视为历史实际成交价。

分析要点和口径如下：

- 股票池：10只A股，统一采用CSMAR上市公司基本信息年度表中的2025年末行业分类，数据读取日期为2026-09-18；
- 选股依据：行业、商业模式和代表性，不以样本期事后涨幅为依据；
- 样本：2021-01-01至2026-09-16，并补充2020年最后一个有效交易日；
- 价格：新浪财经不复权收盘价用于价格时序图；新浪财经后复权收盘价用于日简单收益率；
- 流动性：新浪财经成交量原始单位为股；成交额由元转换为亿元；
- 市值：巨潮资讯总股本原始单位为万股，按变动日期向后匹配；历史总市值（亿元）=`不复权收盘价×总股本（万股）/10000`；
- 组合权重：交易日 $t$ 的市值权重只使用 $t-1$ 日历史总市值；
- 获取审计：保留原始CSV、接口参数、字段单位、覆盖、SHA-256和处理后数据；
- 交叉核验：以贵州茅台2020-12-31为例，将构造总市值与Wind同日历史总市值比较。

### 选股表

| 代码 | 简称 | 行业 | 上市日期 | 选股理由 |
|---|---|---|---|---|
| 600519.SH | 贵州茅台 | 酒、饮料和精制茶制造业 | 2001-08-27 | 消费品牌代表，覆盖品牌型商业模式 |
| 600036.SH | 招商银行 | 货币金融服务 | 2002-04-09 | 银行业代表，覆盖金融中介业务 |
| 600276.SH | 恒瑞医药 | 医药制造业 | 2000-10-18 | 医药制造代表，覆盖研发驱动模式 |
| 000333.SZ | 美的集团 | 电气机械和器材制造业 | 2013-09-18 | 家电制造代表，覆盖耐用消费与制造 |
| 002594.SZ | 比亚迪 | 汽车制造业 | 2011-06-30 | 汽车制造代表，覆盖技术投入与产业链 |
| 600309.SH | 万华化学 | 化学原料和化学制品制造业 | 2001-01-05 | 化工材料代表，覆盖周期制造与研发投入 |
| 002352.SZ | 顺丰控股 | 邮政业 | 2010-02-05 | 物流服务代表，覆盖网络型服务商业模式 |
| 600030.SH | 中信证券 | 资本市场服务 | 2003-01-06 | 证券业代表，补充非银行金融模式 |
| 601012.SH | 隆基绿能 | 电气机械和器材制造业 | 2012-04-11 | 新能源设备代表，覆盖制造周期 |
| 002475.SZ | 立讯精密 | 计算机、通信和其他电子设备制造业 | 2010-09-15 | 电子制造代表，覆盖消费电子供应链 |

上述10只股票覆盖9个CSMAR行业，全部在2021-01-01之前上市。股票池不是依据2021—2026年已实现涨幅事后筛选，而是依据行业、商业模式和代表性事先确定。

### 数据来源与接口说明

本题的数据源可以使用，但实际获取采用分工明确的组合，而不是把所有数据强行交给单一数据库：

- **AKShare 1.18.39 / 新浪财经 `stock_zh_a_daily`**：获取不复权日收盘价、后复权日收盘价、成交量和成交额；
- **AKShare 1.18.39 / 巨潮资讯 `stock_share_change_cninfo`**：获取总股本及股本变动日期，用于构造历史总市值；
- **CSMAR上市公司基本信息年度表**：统一获取简称、上市日期和2025年末行业分类；
- **Wind金融数据服务**：用于股票档案和贵州茅台关键日期总市值交叉核验。Wind全量行情调用因账户积分余额不足未采用，不影响本题使用AKShare完成数据获取。

因此，本题并不是“AKShare或CSMAR不能用”，而是：AKShare负责行情和股本，CSMAR负责统一选股信息，Wind负责交叉核验。所有原始返回和处理后数据均已保存到本Notebook同目录的`data/raw/akshare/`和`data/processed/`。
"""))

cells.append(nbf.v4.new_markdown_cell("""### Step 2：代码与实际输出

下面先显示本次运行环境，再展示冻结后的选股表、数据来源清单、各股票覆盖情况、主键检查和历史总市值交叉核验。"""))

cells.append(nbf.v4.new_code_cell("""# 导入本节所需包并设置显示选项
from pathlib import Path
import json
import platform
import pandas as pd
from IPython.display import display

PROJECT = Path.cwd()
if not (PROJECT / "audit" / "source_manifest_akshare.csv").exists():
    # 允许从个人仓库根目录启动Notebook
    candidate = Path.cwd() / "hw-02"
    if (candidate / "audit" / "source_manifest_akshare.csv").exists():
        PROJECT = candidate
    else:
        raise FileNotFoundError("未找到HW02-1审计文件，请先运行数据下载脚本。")

pd.set_option("display.max_colwidth", 60)
print("Python:", platform.python_version())
print("pandas:", pd.__version__)
print("项目目录:", PROJECT.resolve())"""))

cells.append(nbf.v4.new_code_cell("""# 从唯一股票池主表读取10只股票及统一的CSMAR 2025年末行业分类
selection_master_path = PROJECT / "data" / "processed" / "stock_selection_master.csv"
selection_master = pd.read_csv(
    selection_master_path,
    dtype={"stock_code": "string", "symbol": "string"},
    parse_dates=["listing_date", "industry_classification_date", "industry_source_read_date", "sample_start", "sample_end"],
)

required_columns = [
    "stock_code", "stock_name", "industry", "listing_date", "selection_reason",
    "industry_standard", "industry_classification_date", "industry_source",
    "industry_source_read_date", "listed_before_sample",
]
missing_columns = sorted(set(required_columns) - set(selection_master.columns))
if missing_columns:
    raise ValueError(f"股票池主表缺少字段: {missing_columns}")
if len(selection_master) != 10 or selection_master["stock_code"].duplicated().any():
    raise ValueError("股票池主表必须恰好包含10只不重复股票")

selection = selection_master[[
    "stock_code", "stock_name", "industry", "listing_date", "selection_reason",
    "listed_before_sample", "industry_standard", "industry_classification_date",
    "industry_source", "industry_source_read_date",
]].rename(columns={
    "stock_code": "股票代码",
    "stock_name": "股票简称",
    "industry": "CSMAR行业（2025年末）",
    "listing_date": "上市日期",
    "selection_reason": "选股理由",
    "listed_before_sample": "2021年前上市",
    "industry_standard": "行业分类标准",
    "industry_classification_date": "行业分类日期",
    "industry_source": "行业分类来源",
    "industry_source_read_date": "来源读取日期",
})

display(selection)
print("股票池主表:", selection_master_path.resolve())
print("股票数:", len(selection))
print("CSMAR行业数量:", selection["CSMAR行业（2025年末）"].nunique())
print("全部在样本前上市:", bool(selection["2021年前上市"].all()))"""))

cells.append(nbf.v4.new_code_cell("""# 读取AKShare下载脚本生成的来源清单、覆盖审计和统一日度数据
manifest = pd.read_csv(PROJECT / "audit" / "source_manifest_akshare.csv")
coverage = pd.read_csv(PROJECT / "audit" / "coverage_akshare.csv")
daily = pd.read_csv(
    PROJECT / "data" / "processed" / "daily_stock_data_20201231_20260916.csv",
    parse_dates=["date", "effective_date"], dtype={"stock_code": "string"}
)
execution = json.loads((PROJECT / "audit" / "execution_akshare.json").read_text(encoding="utf-8"))
crosscheck = json.loads((PROJECT / "audit" / "market_cap_crosscheck.json").read_text(encoding="utf-8"))

display(manifest.groupby("kind").agg(
    文件数=("path", "size"), 原始行数=("rows", "sum")
))
display(coverage)
print("AKShare版本:", execution["akshare_version"])
print("价格上游:", execution["price_upstream"])
print("总股本上游:", execution["share_capital_upstream"])
print("正式样本:", " 至 ".join(execution["sample_period"]))
print("股票-日期主键重复数:", int(daily.duplicated(["stock_code", "date"]).sum()))
print("处理后总行数:", len(daily))
print("总市值交叉核验:")
display(pd.DataFrame([crosscheck]))"""))

cells.append(nbf.v4.new_markdown_cell("""### Step 3：Markdown结果解读

本节最终保留10只股票，按CSMAR 2025年末行业分类覆盖酒饮料、银行、医药、家电与电气设备、汽车、化工材料、邮政物流、资本市场和电子制造等9个行业，明显高于作业要求的5个行业；10只股票均在2021年以前上市。选股理由围绕行业、商业模式和代表性事先设定，没有使用2021—2026年的已实现涨幅作为筛选条件。与初始候选方案相比，中国神华、中国石化和中国联通被万华化学、顺丰控股和立讯精密替换，以降低大型国有企业的集中度并扩大商业模式差异。

AKShare 1.18.39实际取得13,841条股票—日期记录。10只股票均从2020-12-31覆盖到2026-09-16，其中8只股票各有1,385个交易日；顺丰控股为1,382日，中信证券为1,379日。所有已返回记录的不复权收盘价、后复权收盘价和构造的历史总市值均非缺失，股票—日期主键重复数为0。两只股票观测日较少并不自动等于数据错误，后续清洗将把它们与共同交易日历比较，区分停牌与接口缺口，且不会把缺失收益直接填为0。

历史总市值使用不复权价格和当日有效总股本构造。以贵州茅台2020-12-31为例，不复权收盘价为1,998元，巨潮资讯总股本为125,619.78万股，得到总市值25,098.832044亿元；Wind同日显示值为25,099.0亿元，两者仅相差0.167956亿元，差异与Wind按万亿元四位小数展示的四舍五入相符。这项核验支持总股本单位和构造公式，但不等于所有股票、所有日期都已由第二来源逐日验证。

核心发现：

- 股票池共10只，按统一CSMAR口径覆盖9个行业，且全部在样本开始前上市；
- 处理后共有13,841条记录，主键无重复，价格和总市值核心字段在已有记录中无缺失；
- 顺丰控股和中信证券分别少于共同上限3日和6日，必须在下一节定位日期后再决定处理；
- 贵州茅台的总市值构造值与Wind交叉核验高度一致，但复权价格仍只用于收益计算，不能视为实际成交价格。
"""))

cells.append(nbf.v4.new_markdown_cell("""## 后续分析结构

后续各节继续严格采用“Step 1分析说明—Step 2代码与实际输出—Step 3结果解读”：

2. 数据清洗与收益率构造  
3. 不复权价格、累计收益和日收益图形  
4. 20日滚动年化波动率  
5. 描述统计与异常收益检查  
6. 日收益率Pearson相关性  
7. 等权组合与滞后总市值加权组合  
8. 总体结论、局限与AI使用说明
"""))

nb["cells"] = cells
nbf.write(nb, out)
print(out)
