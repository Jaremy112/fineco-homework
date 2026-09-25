#!/usr/bin/env python3
"""用 fineco 内核原地执行 Notebook 并保存输出（含图表）。

用法：
    cd hw-02 && python scripts/run_notebook.py
"""
from pathlib import Path

import nbformat as nbf
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "hw02-1.ipynb"

nb = nbf.read(NB, as_version=4)
client = NotebookClient(nb, timeout=600, kernel_name="fineco", resources={"metadata": {"path": str(ROOT)}})
client.execute()
nbf.write(nb, NB)

errors = [
    (i, o.get("ename"), o.get("evalue"))
    for i, c in enumerate(nb["cells"])
    for o in c.get("outputs", [])
    if o.get("output_type") == "error"
]
if errors:
    for e in errors:
        print("ERROR cell", e)
    raise SystemExit(1)
print("执行完成并已保存:", NB)
