# HW02-1 股票池主表字段说明

主表文件：`data/processed/stock_selection_master.csv`

该文件是HW02-1股票池的唯一维护来源。每只股票一行，不含逐日行情。下载脚本和Notebook均应读取该文件，避免在多个程序中重复维护代码、简称、行业、上市日期和选股理由。

| 字段 | 含义 | 口径 |
|---|---|---|
| `stock_code` | 股票代码 | Wind格式，含交易所后缀，如`600519.SH` |
| `symbol` | 六位股票代码 | 用于AKShare等接口，如`600519` |
| `exchange` | 交易所 | `SSE`或`SZSE` |
| `stock_name` | 当前证券简称 | 选股表展示字段 |
| `industry` | 行业 | CSMAR上市公司基本信息年度表中的统一行业分类 |
| `industry_standard` | 行业分类标准 | 本作业统一写为`CSMAR上市公司行业分类` |
| `industry_classification_date` | 行业分类日期 | 2025-12-31 |
| `industry_source` | 行业来源表 | CSMAR上市公司基本信息年度表 |
| `industry_source_read_date` | 来源读取日期 | 2026-09-18 |
| `listing_date` | 当前A股证券上市日期 | CSMAR，使用Wind基本档案交叉核验 |
| `listing_date_source` | 上市日期来源 | 记录主来源与交叉核验日期 |
| `selection_reason` | 选股理由 | 依据行业、商业模式和代表性，不以样本期事后涨幅筛选 |
| `listed_before_sample` | 是否在样本开始前上市 | `listing_date < 2021-01-01` |
| `sample_start` | 正式样本开始日 | 2021-01-01 |
| `sample_end` | 正式样本结束日 | 2026-09-16 |

注意：比亚迪`002594.SZ`采用A股上市日期`2011-06-30`。此前的`2002-07-31`是H股上市日期，不适用于本作业所选A股证券。
