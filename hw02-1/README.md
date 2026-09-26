# HW02-1：股票收益与组合风险分析

- 姓名：朱家瑞
- 作业页面：<https://lianxhcn.github.io/FinEco/exercises/hw-02.html>
- 截止：2026-09-28 23:59（北京时间）
- 所属仓库：<https://github.com/Jaremy112/fineco-homework>（本目录 `hw02-1/`）
- 进度：Notebook `hw02-1.ipynb` **全部 8 节已完成**（57 单元，9 张图 + 31 张表，已运行并保存输出）

本目录保存 HW02-1 的全部输入快照、下载脚本、审计文件和分析 Notebook。所有路径均为相对路径，复现时不依赖重新调用网络接口。

---

## 1. 目录结构

```
hw02-1/
├── README.md                        本文件：来源、口径、运行顺序、预期输出
├── CHANGELOG.md                     操作日志：每步做了什么、依据、产出、样本流
├── DECISIONS.md                     口径决定记录与待裁定事项
├── requirements.txt                 复现依赖（含版本）
├── hw02-1.ipynb                    主分析 Notebook（已运行，含输出）
├── code/
│   ├── download_akshare_hw02_1.py   正式下载与审计脚本（本次数据由它生成）
│   ├── locate_missing_days.py       定位各股票缺失交易日并输出证据
│   ├── build_hw02_1_section02.py    写入 Notebook 第 2 节单元
│   ├── build_hw02_1_section03.py    写入 Notebook 第 3 节单元
│   ├── build_hw02_1_section04.py    写入 Notebook 第 4 节单元
│   ├── build_hw02_1_section05.py    写入 Notebook 第 5 节单元
│   ├── build_hw02_1_section06.py    写入 Notebook 第 6 节单元
│   ├── build_hw02_1_section07.py    写入 Notebook 第 7 节单元
│   ├── build_hw02_1_section08.py    写入 Notebook 第 8 节单元
│   └── run_notebook.py              用 fineco 内核原地执行 Notebook 并保存输出
│   ├── download_wind_hw02_1.py      Wind 方案脚本（仅尝试，未采用，保留存档）
│   └── build_hw02_1_notebook.py     Notebook 骨架构建脚本
├── data/
│   ├── raw/akshare/                 原始返回快照，只读，含 SHA256 清单
│   │   ├── sina_unadjusted/         新浪财经不复权日行情（13 只）
│   │   ├── sina_hfq/                新浪财经后复权日行情（13 只）
│   │   └── cninfo_share_capital/    巨潮资讯股本变动历史（13 只）
│   └── processed/                   派生数据，可由 raw 重算
│       ├── stock_selection_master.csv      股票池主表（唯一维护来源）
│       ├── stock_selection_master_README.md 主表字段字典
│       ├── daily_stock_data_20201231_20260916.csv  统一日度分析底表
│       └── daily_returns_20210104_20260916.csv     含日收益率与跨期标记的派生表
│       └── share_capital_history.csv        总股本变动历史
└── audit/                           审计证据
    ├── source_manifest_akshare.csv  原始文件清单：kind、路径、行数、SHA256
    ├── coverage_akshare.csv         各股票实际覆盖期间、有效观测数与零成交日
    ├── execution_akshare.json       执行环境：包版本、上游、样本期、单位
    ├── market_cap_crosscheck.json   贵州茅台 2020-12-31 总市值 Wind 交叉核验
    └── missing_days_akshare.csv     缺失交易日清单与"其余股票当日是否有行情"证据
```

---

## 2. 数据来源与快照

| 数据 | 接口与上游 | 下载/读取日期 | 单位与口径 | 文件位置 |
|---|---|---|---|---|
| 不复权日收盘价、成交量、成交额 | AKShare 1.18.39 `stock_zh_a_daily(symbol, adjust="")`，上游新浪财经 | 2026-09-20 下载 | 价格元；成交量股；成交额元→亿元 | `data/raw/akshare/sina_unadjusted/` |
| 后复权日收盘价 | AKShare 1.18.39 `stock_zh_a_daily(..., adjust="hfq")`，上游新浪财经 | 2026-09-20 下载 | 元；仅作连续收益尺度，非历史成交价 | `data/raw/akshare/sina_hfq/` |
| 总股本及变动日期 | AKShare 1.18.39 `stock_share_change_cninfo(symbol)`，上游巨潮资讯 | 2026-09-20 下载 | 原始单位为万股 | `data/raw/akshare/cninfo_share_capital/` |
| 证券简称、上市日期、行业分类 | CSMAR 上市公司基本信息年度表（2025-12-31 记录） | 2026-09-18 读取 | 统一 CSMAR 行业分类，不倒填历史 | `data/processed/stock_selection_master.csv` |
| 档案与关键日期交叉核验 | Wind 金融数据服务 | 2026-09-22 读取 | 仅用于核验，不作主数据源 | `audit/market_cap_crosscheck.json` |

**快照说明**

- 原始层每个文件都登记了 SHA256，清单见 `audit/source_manifest_akshare.csv`（30 行，覆盖最终 10 只股票 × 3 类来源）。
- **原始层实际存有 13 只股票的行情文件**：除最终 10 只外，还有初始候选池中的中国神华（601088.SH）、中国石化（600028.SH）、中国联通（600050.SH）。这 3 只已被替换出研究样本，其文件保留在 `raw/` 以保持原始层不可回改，但不进入任何分析；研究样本严格为 `stock_selection_master.csv` 中的 10 只。
- Wind 全量行情调用因账户积分余额不足未采用，其脚本 `download_wind_hw02_1.py` 及部分中间产出已清理，仅保留脚本存档；本题数据不由 Wind 生成。
- 日期在 CSV 中以 `YYYY/M/D` 文本存储，读入时用 `parse_dates` 解析，覆盖区间以 `audit/coverage_akshare.csv` 为准。

---

## 3. 关键口径决定

| 决定 | 口径 | 理由 |
|---|---|---|
| 股票池冻结 | 10 只 A 股，按 CSMAR 2025 年末分类覆盖 9 个行业，全部 2021 年前上市 | 先冻结再下载，避免依据 2021—2026 年已实现涨幅事后替换（幸存者与事后选择） |
| 比亚迪上市日期 | 采用 A 股上市日 2011-06-30（2002-07-31 为 H 股上市日，不适用） | 研究标的为 A 股证券 |
| 价格用途 | 不复权价画图与构造市值；后复权价仅用于日收益 | 后复权是价格标度，不是当时可成交价格 |
| 日收益率 | `r_t = close_hfq_t / close_hfq_{t-1} − 1` | 作业指定日简单收益率 |
| 历史总市值 | `market_cap = close_unadjusted × total_shares_10k / 1e4`（亿元） | 用总股本不用流通股本；不用复权价乘股本；不用当前市值回填历史 |
| 市值权重 | 交易日 t 的权重只用 t−1 日历史总市值 | 避免前视偏误 |
| 支持日规则 | 每只股票保留 2021-01-01 前最后一个有效交易日，仅用于生成首个日收益率 | 该日不进入收益率样本，只作前置价格 |

---

## 4. 处理后数据字段（`daily_stock_data_20201231_20260916.csv`）

粒度：股票 × 交易日。共 13,841 行、10 只股票，`(stock_code, date)` 主键重复数为 0。

| 字段 | 含义 | 单位/口径 |
|---|---|---|
| `stock_code` / `stock_name` | Wind 格式代码与简称 | 字符串 |
| `date` | 交易日 | `YYYY/M/D`，读入时解析为日期 |
| `close_unadjusted` | 不复权收盘价 | 元 |
| `close_hfq` | 后复权收盘价 | 元，仅用于收益计算 |
| `volume_shares_unadjusted` / `volume_shares` | 成交量 | 股 |
| `turnover_cny_unadjusted` / `turnover_100m_cny` | 成交额 | 元 / 亿元 |
| `outstanding_shares_unadjusted` | 流通股本 | 股（不用作市值） |
| `effective_date` / `total_shares_10k` | 当日有效总股本的变动生效日与总股本 | 万股（巨潮口径，按变动日后向匹配） |
| `market_cap_100m_cny` | 构造的历史总市值 | 亿元 |
| `industry` | 行业 | CSMAR 2025 年末分类 |

各股票交易日数：8 只各 1,385 日，**顺丰控股 1,382 日、中信证券 1,379 日**（均含 2020-12-31 支持日）。两个缺口已定位为**停牌**：顺丰控股 2021-02-05/08/09 筹划收购嘉里物流停牌、2 月 10 日复牌；中信证券 2022-01-19 至 01-26 因 A 股配股缴款与清算全天停牌、1 月 27 日复牌。明细见 `audit/missing_days_akshare.csv`，由此派生的处理规则见 `DECISIONS.md` 第 2 节。

---

## 5. 复现步骤

### 路径 A：用数据快照复现（推荐，也是批改所用路径）

```bash
cd hw02-1
pip install -r requirements.txt
jupyter notebook hw02-1.ipynb     # 内核选择 Python (FinEco)，Restart & Run All
```

Notebook 第 00 个代码单元会自动定位项目目录：若当前目录下找不到 `audit/source_manifest_akshare.csv`，会回退检查 `./hw02-1`。因此从仓库根目录或 `hw02-1/` 目录启动均可。

### 路径 B：重新下载（会覆盖 raw 与 processed，仅在需要更新数据时使用）

```bash
cd hw02-1
python code/download_akshare_hw02_1.py    # 需要 akshare 与网络；会重算 manifest/coverage/crosscheck
python code/build_hw02_1_notebook.py      # 可选：重建 Notebook 骨架
```

注意：路径 B 会重新调用外部接口，结果可能随上游更新而变化；提交与批改以路径 A 的本地快照为准。

---

## 6. 依赖

Python 3.12.12（课程 FinEco 环境），详见 `requirements.txt`：

```
akshare==1.18.39
pandas==2.3.3
numpy==2.4.2
matplotlib==3.10.9
ipython==9.17.1
```

Notebook 内核：`Python (FinEco)`，解释器路径 `/Users/macbookairzhu/Documents/FinEco/.venv/bin/python`。

---

## 7. 预期主要输出

| Notebook 章节 | 主要输出 |
|---|---|
| 1. 选股与获取数据 | 选股表（10 只，含代码/简称/行业/上市日期/选股理由）、来源清单、覆盖审计、主键检查、茅台总市值 Wind 交叉核验 |
| 2. 数据清洗与收益率构造 | 主键与覆盖检查、停牌定位与证据、日收益率构造、跨期收益剔除、样本流、异常收益与涨跌幅限制核对 |
| 3. 价格与累计表现 | 不复权收盘价分面时序图、起点为 1 的累计收益曲线、日收益率分面图（±10% 参考线）、分年波动统计与极值清单 |
| 4. 波动率 | 20 日滚动年化波动率（√252，不足 20 个观测不计算）：个股时序图、组合与个股均值对比、波动率汇总与峰值时点 |
| 5. 描述统计与异常 | 8 项描述统计逐只给出、日收益箱线图、\|z\|>4/5/6 与 \|r\|≥9.5% 双口径异常识别、剔除前后的敏感性比较 |
| 6. 相关性 | Pearson 相关矩阵 + 热力图；成对样本量 1,373—1,384 天；与共同样本口径对照；同行业与金融板块分组检验 |
| 7. 两类组合 | 净值曲线 + 回撤曲线；等权 −9.11%（年化 −1.72%）vs 市值加权 −14.88%（年化 −2.89%）；波动率约 20.6%；权重和恒为 1；HHI 与等效分散只数 |
| 8. 总体结论 | 六条主要发现、7 项关键处理判断、数据/方法/样本三层局限、AI 使用声明（工具、参与环节、关键提示词、核验过程、修正过的问题） |

---

## 8. 已知待办与局限

- 第 3—8 节尚未写入 Notebook；第 2 节采用的停牌与复牌日处理规则见 `DECISIONS.md`，仍需本人复核。
- 复牌日（顺丰 2021-02-10、中信 2022-01-27）的"日收益"为跨期收益，中信当日还叠加配股除权，主结果中不作为单日收益使用。
- 后复权价格只用于收益率计算，不能解释为历史实际成交价；复权序列不消除前视偏误风险，涉及信息可得性时仍须回到公告日。
- 历史总市值由不复权价与巨潮总股本构造，仅以贵州茅台 2020-12-31 与 Wind 做了单点交叉核验，未逐股票逐日双源验证。
- 比亚迪、隆基绿能等存在股本变动或更名的股票，其总股本按变动生效日后向匹配，未做股本变动公告日维度的可得性调整（本题收益率分析不涉及该维度）。
