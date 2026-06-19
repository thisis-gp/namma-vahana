"""Generate solution.ipynb that reproduces the submission end-to-end."""
import nbformat as nbf

intro = ("# Traffic Demand Prediction\n"
         "# Blend of Day-48 lookup ladder (with spatial neighbor fallback)\n"
         "# and a LightGBM structure model.")
imports = ("import numpy as np, pandas as pd, pygeohash as pgh, lightgbm as lgb\n"
           "from sklearn.neighbors import KDTree\n"
           "from sklearn.metrics import r2_score")

def strip_src(code):
    # drop intra-package imports so the notebook runs as flat cells;
    # handles multi-line `from src.x import (...)` by skipping continuation lines
    out, skipping, depth = [], False, 0
    for line in code.splitlines():
        if skipping:
            depth += line.count("(") - line.count(")")
            if depth <= 0:
                skipping = False
            continue
        if line.strip().startswith("from src."):
            depth = line.count("(") - line.count(")")
            skipping = depth > 0
            continue
        out.append(line)
    return "\n".join(out)

cells = [
    intro,
    imports,
    strip_src(open("src/pipeline.py").read()),
    strip_src(open("src/spatial.py").read()),
    strip_src(open("src/model.py").read()),
    strip_src(open("submit.py").read()).replace(
        'if __name__ == "__main__":\n    main()', "main()"),
]

nb = nbf.v4.new_notebook()
nb.cells = [nbf.v4.new_code_cell(c) for c in cells]
with open("solution.ipynb", "w", encoding="utf-8") as f:
    nbf.write(nb, f)
print("wrote solution.ipynb")
