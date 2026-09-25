# HW02-2：房地产上市公司财务特征分析

- 姓名：朱家瑞
- 作业页面：<https://lianxhcn.github.io/FinEco/exercises/hw-02.html>
- 所属仓库：<https://github.com/Jaremy112/fineco-homework>（本目录 `hw02-2/`）
- 进度：Notebook `hw02-2.ipynb` **全部完成**（29 单元，4 张图 + 5 张表，已运行、0 报错）

## 1. 数据来源

CSMAR（国泰安）数据中心 <https://data.csmar.com/>，本人凭中山大学机构订阅账号手动导出。
**下载日期**：2026-09-24 至 2026-09-25（逐表日期见 `DATA_MANIFEST.md`）。
**受限数据不入公开仓库**；完整下载条件、数据表清单、字段、单位与日期见 `DATA_MANIFEST.md`，
原始字段与分析变量对应表见 `field_mapping.csv`，数据目录说明见 `data/README.md`。

## 2. 数据版本与文件位置

| 表 | 本地位置（相对本目录） | 覆盖 |
|---|---|---|
| 资产负债表 | `data/raw/ 2005—2015 年房地产 A 股上市公司年度数据/资产负债表补充/FS_Combas.json` | 2005—2015，170 家 |
| 利润表 | `…/利润表补充/FS_Comins.json` | 2005—2015，170 家 |
| 资产负债表（2004 年末） | `…/资产负债表补充/04/FS_Combas.json` | 2004，158 家 |
| 股权性质 | `…/股权性质/补充/EN_EquityNatureAll.json` | 2004—2015，170 家 |
| 上市公司基本信息年度表 | `…/行业分类表/STK_LISTEDCOINFOANL.json` | 2004—2015，2,910 家 |

## 3. 依赖

Python 3.12.12；`pandas 2.3.3`、`numpy 2.4.2`、`matplotlib 3.10.9`（见 `requirements.txt`）。
复现**不需要联网接口**——原始快照已在本地（受限数据需自行按下载条件获取）。

## 4. 运行入口与顺序

```bash
cd hw02-2
# ① 建面板（读原始 JSON → 清洗 → 合并 → 行业/产权/上市状态 → 六指标）
python code/build_panel.py        # 生成 data/processed/firm_year_panel.csv 等
# ② 汇总图表（逐年公司数与产权、四类输出、敏感性）
python code/make_outputs.py       # 生成 outputs/*.png 与 *.csv
# ③ 核心 Notebook（自包含，直接读原始 JSON 完成全部分析；与①②口径一致）
jupyter notebook hw02-2.ipynb     # 或 Restart Kernel 后 Run All
```

## 5. 预期主要输出

- **图 1**：逐年房地产 A 股公司数、产权四类构成、国有/民营占比（62 家 → 134 家；国有 58.1% → 46.3%）
- **图 2**：六指标全样本均值与中位数时序（资产负债率、bankloan、短期负债占比、ROA、ROE、Cash_TA）
- **图 3/4**：国有 vs 民营的均值与中位数比较
- **表**：逐年产权结构、六指标年度有效样本量、样本处理表（1,821 观测 × 170 家）、剔除负权益前后敏感性
- 样本流：18,044 原始行 → 筛合并/年末/A 股 1,821 → 判定房地产 1,176 观测（170 家）

## 6. 复现验证

已于 2026-09-25 从 `/tmp` 新目录按本说明复制材料、配置环境、从头运行核验；
`hw02-1` 同日完成同口径验证（55 单元 / 0 报错 / 9 图）。

## 7. 其他文档

`ASSIGNMENT.md` 题目原文存档 · `DATA_REQUEST.md` 导出清单 · `DATA_MANIFEST.md` 下载条件
· `field_mapping.csv` 字段对应表 · `REPORT.md` 中期分析报告 · `DECISIONS.md` 口径决定
· `CHANGELOG.md` 操作日志 · `audit/` 代码清单与审计
