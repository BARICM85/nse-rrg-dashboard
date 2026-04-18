from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd


QUADRANT_COLORS = {
    "Leading": "#16a34a",
    "Weakening": "#f59e0b",
    "Lagging": "#ef4444",
    "Improving": "#0ea5e9",
}


def build_rrg_figure(snapshot: pd.DataFrame, title: str, tail_periods: int = 10):
    fig, ax = plt.subplots(figsize=(10.8, 7.4))
    ax.set_facecolor("#ffffff")

    ax.axvspan(0, 5, 0.5, 1, alpha=0.08, color="#16a34a")
    ax.axvspan(0, 5, 0, 0.5, alpha=0.08, color="#f59e0b")
    ax.axvspan(-5, 0, 0, 0.5, alpha=0.08, color="#ef4444")
    ax.axvspan(-5, 0, 0.5, 1, alpha=0.08, color="#0ea5e9")

    ax.axhline(0, color="#94a3b8", linewidth=1)
    ax.axvline(0, color="#94a3b8", linewidth=1)

    for _, row in snapshot.iterrows():
        color = QUADRANT_COLORS.get(row["quadrant"], "#334155")
        tail_x = row["tail_x"][-tail_periods:]
        tail_y = row["tail_y"][-tail_periods:]
        ax.plot(tail_x, tail_y, color=color, linewidth=1.5, alpha=0.55)
        ax.scatter(tail_x, tail_y, color=color, s=18, alpha=0.35)
        ax.scatter(row["rs_ratio"], row["rs_momentum"], color=color, s=86, edgecolor="#ffffff", linewidth=0.8)
        ax.annotate(
            row["label"],
            (row["rs_ratio"], row["rs_momentum"]),
            textcoords="offset points",
            xytext=(6, 6),
            fontsize=9,
            color="#0f172a",
        )

    ax.text(2.8, 2.8, "Leading", color="#166534", fontsize=10, weight="bold")
    ax.text(2.4, -2.8, "Weakening", color="#92400e", fontsize=10, weight="bold")
    ax.text(-4.2, -2.8, "Lagging", color="#991b1b", fontsize=10, weight="bold")
    ax.text(-4.3, 2.8, "Improving", color="#0c4a6e", fontsize=10, weight="bold")

    ax.set_title(title, fontsize=14, weight="bold", color="#0f172a")
    ax.set_xlabel("RS Ratio (normalized)", color="#334155")
    ax.set_ylabel("RS Momentum (normalized)", color="#334155")
    ax.grid(alpha=0.15, linestyle="--")
    ax.tick_params(colors="#475569")

    fig.tight_layout()
    return fig
