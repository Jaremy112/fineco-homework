# HW02-1 数据目录说明

用途：列出本目录全部数据文件的文件名、用途、大小、访问地址与本地存放路径（作业第 4/5 节要求）。
复现使用**本次分析的数据快照**，不依赖未来重新调用接口。

## 1. 仓库内的文件（允许共享，已入库）

`data/raw/akshare/` —— 原始返回快照，只读，含 SHA256 清单（`../audit/source_manifest_akshare.csv`）

| 子目录 | 内容 | 大小 | 来源与获取方式 |
|---|---|---:|---|
| `sina_unadjusted/` | 新浪财经**不复权**日行情（13 只） | 1.7 MB | AKShare `stock_zh_a_daily`，见 `code/download_akshare_hw02_1.py` |
| `sina_hfq/` | 新浪财经**后复权**日行情（13 只） | 1.7 MB | 同上（`adjust="hfq"`） |
| `cninfo_share_capital/` | 巨潮资讯股本变动历史（13 只） | 256 KB | AKShare `stock_share_change_cninfo` |

`data/processed/` —— 派生数据，可由 raw 重算（**已入库，复现直接读取**）

| 文件 | 用途 | 大小 |
|---|---|---:|
| `daily_stock_data_20201231_20260916.csv` | 主数据：日期×股票的不复权收盘价、hfq 收盘价、成交额、总市值（亿元） | 2.2 MB |
| `daily_returns_20210104_20260916.csv` | 日简单收益率与跨期标记 | 2.1 MB |
| `share_capital_history.csv` | 巨潮有效总股本生效日历史（用于构造历史总市值） | 120 KB |
| `stock_selection_master.csv` | 选股表（代码、简称、行业、上市日期、选股理由） | 3.5 KB |
| `stock_selection_master_README.md` | 选股表字段说明 | 1.7 KB |

## 2. 未入库的本地文件（受限或临时）

| 文件 | 用途 | 本地存放路径 | 访问方式 |
|---|---|---|---|
| Wind MCP 市值交叉核验结果 | 单点核验茅台总市值 | `audit/market_cap_crosscheck.json`（已入库） | 需 Wind 权限，非必需 |

本目录不含 CSMAR 等受限数据。CSMAR 数据全部位于 `../hw02-2/data/raw/`，见该题 `data/README.md`。

## 3. 获取日期与版本

| 项 | 值 |
|---|---|
| 数据获取日期 | 2026-09-24（AKShare 下载与审计，见 `../CHANGELOG.md`） |
| AKShare 版本 | 1.18.39（见 `../requirements.txt`） |
| 样本期间 | 2021-01-01 ~ 2026-09-16；支持日 2020-12-31（用于首日收益） |
| 数据快照方式 | 原始返回 + 派生 CSV 一并入库，复现无需联网 |

## 4. 复现时的本地路径约定

所有脚本与 Notebook 使用相对路径，从仓库根目录进入 `hw02-1/` 后运行：

```
hw02-1/
├── data/raw/akshare/...     原始快照（只读）
├── data/processed/*.csv     分析直接读取的快照
├── audit/                   下载与核验审计（coverage、missing_days、source_manifest、market_cap_crosscheck）
└── code/                    下载、核验与 Notebook 构建脚本
```
