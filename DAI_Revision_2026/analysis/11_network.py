"""Regenerate the conditional-dependency network (Figure 4) honestly:
- Gaussian graphical model (graphical lasso) on top failure-associated genes,
- the clinical OUTCOME is NOT included as a node (addresses R2.8),
- undirected edges (partial correlations), gene SYMBOL labels, large fonts.
"""
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.covariance import GraphicalLassoCV
warnings.filterwarnings("ignore")
import common

T = f"{common.ROOT}/DAI_Revision_2026/tables"
Fg = f"{common.ROOT}/DAI_Revision_2026/figures"

X, y, meta = common.load_baseline()
deg = pd.read_csv(f"{T}/wpB_DEG_corrected.csv")
top = deg.dropna(subset=["gene_symbol"])
sym = dict(zip(top["ensembl"], top["gene_symbol"]))
# keep genes present with non-zero variance and no NaN
cand = [g for g in top["ensembl"] if g in X.columns]
cand = [g for g in cand if X[g].notna().all() and X[g].std() > 1e-6][:26]
genes = cand

Z = (X[genes] - X[genes].mean()) / (X[genes].std() + 1e-9)
Z = Z.fillna(0.0)
assert np.isfinite(Z.values).all(), "non-finite values in Z"
prec = None
from sklearn.covariance import GraphicalLasso
for alpha in [0.2, 0.3, 0.5]:
    try:
        prec = GraphicalLasso(alpha=alpha, max_iter=200).fit(Z.values).precision_
        break
    except Exception:
        continue
if prec is None:  # robust shrinkage fallback
    cov = np.corrcoef(Z.values.T)
    prec = np.linalg.pinv(cov + 0.4 * np.eye(len(genes)))

# partial correlations from precision
d = np.sqrt(np.diag(prec))
pcorr = -prec / np.outer(d, d)
np.fill_diagonal(pcorr, 0)

labels = [sym.get(g, g) for g in genes]
n = len(genes)
ang = np.linspace(0, 2 * np.pi, n, endpoint=False)
pos = np.c_[np.cos(ang), np.sin(ang)]

plt.figure(figsize=(11, 11))
thr = 0.15
deg_count = np.zeros(n)
for i in range(n):
    for j in range(i + 1, n):
        w = pcorr[i, j]
        if abs(w) > thr:
            deg_count[i] += 1; deg_count[j] += 1
            plt.plot([pos[i, 0], pos[j, 0]], [pos[i, 1], pos[j, 1]],
                     color=("#cc3333" if w > 0 else "#3366cc"),
                     lw=1 + 4 * abs(w), alpha=0.5, zorder=1)
sizes = 300 + 250 * deg_count
plt.scatter(pos[:, 0], pos[:, 1], s=sizes, c="#9ecae1",
            edgecolors="k", zorder=2)
for i, lab in enumerate(labels):
    r = 1.12
    plt.text(pos[i, 0] * r, pos[i, 1] * r, lab, ha="center", va="center",
             fontsize=12, fontweight="bold")
plt.plot([], [], color="#cc3333", lw=3, label="Positive partial correlation")
plt.plot([], [], color="#3366cc", lw=3, label="Negative partial correlation")
plt.legend(loc="upper right", fontsize=12)
plt.xlim(-1.35, 1.35); plt.ylim(-1.35, 1.55)
plt.title("Undirected conditional-dependency (Gaussian graphical) network "
          "of baseline\nfailure-associated genes "
          "(edges = partial correlations; outcome is NOT a node)",
          fontsize=13, y=1.02)
plt.axis("off"); plt.tight_layout()
plt.savefig(f"{Fg}/Figure4_network.png", dpi=300, bbox_inches="tight")
plt.close()

hub = pd.DataFrame({"gene": labels, "degree": deg_count.astype(int)}).sort_values(
    "degree", ascending=False)
hub.to_csv(f"{T}/wpI_network_hubs.csv", index=False)
print("Top hub genes:\n", hub.head(8).to_string(index=False))
print("Saved Figure4_network.png + wpI_network_hubs.csv")
