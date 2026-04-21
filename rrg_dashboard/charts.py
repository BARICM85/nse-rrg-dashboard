from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd


QUADRANT_COLORS = {
    "Leading": "#16a34a",
    "Weakening": "#f59e0b",
    "Lagging": "#ef4444",
    "Improving": "#0ea5e9",
}


def to_rrg100(values):
    return [100 + float(value) * 4.0 for value in values]


def build_rrg_figure(
    snapshot: pd.DataFrame,
    title: str,
    tail_periods: int = 10,
    zone_shading: bool = True,
    scale_mode: str = "normalized",
):
    fig, ax = plt.subplots(figsize=(10.8, 7.2))
    ax.set_facecolor("#ffffff")

    if scale_mode == "rrg100":
        center = 100
        span = 9
    else:
        center = 0
        span = 5

    x_min, x_max = center - span, center + span
    y_min, y_max = center - span, center + span

    if zone_shading:
        ax.axvspan(center, x_max, 0.5, 1, alpha=0.16, color="#dff4e2")
        ax.axvspan(center, x_max, 0, 0.5, alpha=0.16, color="#fff4cc")
        ax.axvspan(x_min, center, 0, 0.5, alpha=0.16, color="#ffdede")
        ax.axvspan(x_min, center, 0.5, 1, alpha=0.16, color="#dde3ff")

    ax.axhline(center, color="#94a3b8", linewidth=1)
    ax.axvline(center, color="#94a3b8", linewidth=1)

    for _, row in snapshot.iterrows():
        color = QUADRANT_COLORS.get(row["quadrant"], "#334155")
        if scale_mode == "rrg100":
            tail_x = to_rrg100(row["tail_x"][-tail_periods:])
            tail_y = to_rrg100(row["tail_y"][-tail_periods:])
            latest_x = 100 + float(row["rs_ratio"]) * 4.0
            latest_y = 100 + float(row["rs_momentum"]) * 4.0
        else:
            tail_x = row["tail_x"][-tail_periods:]
            tail_y = row["tail_y"][-tail_periods:]
            latest_x = float(row["rs_ratio"])
            latest_y = float(row["rs_momentum"])
        ax.plot(tail_x, tail_y, color=color, linewidth=1.5, alpha=0.55)
        ax.scatter(tail_x, tail_y, color=color, s=18, alpha=0.35)
        ax.scatter(latest_x, latest_y, color=color, s=86, edgecolor="#ffffff", linewidth=0.8)
        ax.annotate(
            row["label"],
            (latest_x, latest_y),
            textcoords="offset points",
            xytext=(6, 6),
            fontsize=9,
            color="#0f172a",
        )

    ax.text(center + span - 2.4, center + span - 1.1, "Leading", color="#16a34a", fontsize=10, weight="bold")
    ax.text(center + span - 2.8, center - span + 0.8, "Weakening", color="#d97706", fontsize=10, weight="bold")
    ax.text(center - span + 0.6, center - span + 0.8, "Lagging", color="#dc2626", fontsize=10, weight="bold")
    ax.text(center - span + 0.6, center + span - 1.1, "Improving", color="#2563eb", fontsize=10, weight="bold")
    ax.text(
        center,
        center + span - 1.2,
        "Thanks to Sharpely for the inspiration",
        ha="center",
        va="center",
        fontsize=9,
        color="#94a3b8",
        alpha=0.8,
        weight="medium",
    )

    if title:
        ax.set_title(title, fontsize=14, weight="bold", color="#0f172a")
    ax.set_xlabel("JdK RS-Ratio" if scale_mode == "rrg100" else "RS Ratio (normalized)", color="#334155")
    ax.set_ylabel("JdK RS-Momentum" if scale_mode == "rrg100" else "RS Momentum (normalized)", color="#334155")
    ax.grid(alpha=0.12, linestyle="-")
    ax.tick_params(colors="#475569")
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)

    fig.tight_layout()
    return fig
