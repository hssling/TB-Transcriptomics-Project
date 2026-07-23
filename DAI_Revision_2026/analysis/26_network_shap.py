"""Conditional-dependency structure among the features the model relies on.

The node set is the SHAP-ranked panel of each arm, not an independently
derived gene list, so the network describes the internal organisation of the
signal the classifier uses rather than a parallel result that happens to sit
alongside it.

A Gaussian graphical model estimated by the graphical lasso gives partial
correlations: each edge is the association between two transcripts after the
remaining transcripts in the panel are conditioned out, which removes the
indirect links that a marginal correlation network would show. Edges are
undirected and the clinical outcome is not a node, so no regulatory direction
is implied.
"""
import warnings

import common2 as C

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from sklearn.covariance import GraphicalLasso

warnings.filterwarnings("ignore")

N_NODES = 24
# A stronger penalty and a minimum edge weight keep only the partial
# correlations that survive conditioning, which is both the more defensible
# estimate and the readable one.
ALPHAS = [0.35, 0.4, 0.5, 0.6]
EDGE_MIN = 0.12


def estimate(Z):
    for alpha in ALPHAS:
        try:
            prec = GraphicalLasso(alpha=alpha, max_iter=300).fit(Z).precision_
            return prec, alpha
        except Exception:
            continue
    cov = np.corrcoef(Z.T)
    return np.linalg.pinv(cov + 0.4 * np.eye(Z.shape[1])), None


def main():
    ranking = pd.read_csv(f"{C.TAB}/shap_feature_ranking.csv")
    hub_rows = []
    fig, axes = plt.subplots(1, len(C.ARMS), figsize=(5.4 * len(C.ARMS), 5.6))

    for j, arm in enumerate(C.ARMS):
        X, y, meta = C.load_arm(arm)
        panel = ranking[ranking.arm == arm].nsmallest(N_NODES, "rank")
        genes = [g for g in panel["ensembl"] if g in X.columns]
        labels = dict(zip(panel["ensembl"], panel["gene_symbol"]))

        sub = X[genes]
        Z = ((sub - sub.mean()) / (sub.std() + 1e-9)).fillna(0.0).values
        prec, alpha = estimate(Z)
        d = np.sqrt(np.diag(prec))
        pcorr = -prec / np.outer(d, d)
        np.fill_diagonal(pcorr, 0.0)

        G = nx.Graph()
        for g in genes:
            G.add_node(g, label=labels.get(g, g))
        for a in range(len(genes)):
            for b in range(a + 1, len(genes)):
                w = pcorr[a, b]
                if abs(w) >= EDGE_MIN:
                    G.add_edge(genes[a], genes[b], weight=float(w))

        deg = dict(G.degree())
        for g in genes:
            hub_rows.append({
                "arm": arm, "arm_label": C.ARM_LABEL[arm],
                "ensembl": g, "gene_symbol": labels.get(g, g),
                "degree": int(deg.get(g, 0)),
                "mean_abs_partial_correlation": float(
                    np.mean([abs(G[g][n]["weight"]) for n in G[g]]) if deg.get(g) else 0.0),
                "graphical_lasso_alpha": alpha,
            })

        ax = axes[j]
        # Isolated nodes carry no conditional dependency; dropping them keeps
        # the drawing about the structure that was actually estimated.
        G.remove_nodes_from([n for n in list(G.nodes()) if G.degree(n) == 0])
        pos = nx.spring_layout(G, seed=C.SEED, k=1.6, iterations=300)
        if G.number_of_edges():
            weights = [G[a][b]["weight"] for a, b in G.edges()]
            nx.draw_networkx_edges(
                G, pos, ax=ax, width=[1.0 + 5 * abs(w) for w in weights],
                edge_color=["#C44E52" if w > 0 else "#4C72B0" for w in weights],
                alpha=0.65)
        sizes = [220 + 130 * deg.get(g, 0) for g in G.nodes()]
        nx.draw_networkx_nodes(G, pos, ax=ax, node_size=sizes,
                               node_color="#E8E4D9", edgecolors="#4A4A4A",
                               linewidths=0.9)
        nx.draw_networkx_labels(G, pos, ax=ax,
                                labels={g: labels.get(g, g) for g in G.nodes()},
                                font_size=8)
        ax.set_title(f"{C.ARM_LABEL[arm]}\n{G.number_of_edges()} edges"
                     + (f", $\\alpha$ = {alpha}" if alpha else ""),
                     fontsize=11, fontweight="bold")
        ax.axis("off")

    fig.tight_layout()
    fig.savefig(f"{C.FIG}/Figure_network_arms.png", dpi=300)
    plt.close(fig)

    hubs = pd.DataFrame(hub_rows).sort_values(["arm", "degree"],
                                              ascending=[True, False])
    hubs.to_csv(f"{C.TAB}/network_hubs.csv", index=False)
    for arm in C.ARMS:
        top = hubs[hubs.arm == arm].head(6)
        print(f"\n{C.ARM_LABEL[arm]} hubs by degree:")
        print(top[["gene_symbol", "degree",
                   "mean_abs_partial_correlation"]].to_string(index=False))
    print("\nwrote network_hubs.csv and Figure_network_arms.png")


if __name__ == "__main__":
    main()
