"""Cross-condition figures. Usage: python figures.py results
Reads results/{brief,summary}_s{1,4}/ and writes results/fig1_retention.png, fig2_supervision.png.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from analyze import boot, load, meta

SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
S1, S2 = "#2a78d6", "#eb6834"          # validated categorical slots 1 and 2
CONFIGS = [("brief", 1), ("summary", 1), ("brief", 4), ("summary", 4)]
TITLE = {"brief": "Task-aware handoff brief", "summary": "Generic summary"}


def style(ax):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=9, length=0)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def series(ax, xs, stats, color, label, dx=0.0, label_dy=0):
    """dx dodges overlapping series sideways; label_dy (points) keeps end labels apart."""
    xs = [x + dx for x in xs]
    ys = [s[0] * 100 for s in stats]
    lo = [s[1] * 100 for s in stats]
    hi = [s[2] * 100 for s in stats]
    ax.fill_between(xs, lo, hi, color=color, alpha=0.12, linewidth=0)
    ax.plot(xs, ys, color=color, linewidth=2, marker="o", markersize=7,
            markeredgecolor=SURFACE, markeredgewidth=2, label=label)
    ax.annotate(f"{ys[-1]:.0f}%", (xs[-1], ys[-1]), xytext=(7, label_dy), textcoords="offset points",
                va="center", fontsize=9, color=INK)


def _apart(a, b, gap=0.07):
    """Vertical label offset (points) when two end values sit within 7 points of each other."""
    if abs(a - b) >= gap:
        return 0
    return 6 if a >= b else -6


def fig_retention(root: Path):
    fig, axes = plt.subplots(1, 4, figsize=(13, 3.6), sharey=True, facecolor=SURFACE)
    for ax, (mode, sc) in zip(axes, CONFIGS):
        folder = root / f"{mode}_s{sc}"
        style(ax)
        if not (folder / "chains.jsonl").exists():
            ax.set_title(f"{TITLE[mode]}, {16 * sc} reqs\n(not run)", fontsize=10, color=INK2)
            continue
        tasks, chains, _ = load(folder)
        M = meta(tasks)
        depths = sorted({b["depth"] for c in chains for b in c["briefs"]})
        st = {cls: [(1.0, 1.0, 1.0)] + [boot([(c["seed"], c["briefs"][d - 1]["judge"].get(rid) == "kept", 1)
                                              for c in chains for rid, r in M[c["seed"]].items() if r["cls"] == cls])
                                        for d in depths] for cls in ("fact", "relation")}
        dy = _apart(st["fact"][-1][0], st["relation"][-1][0])
        series(ax, [0] + depths, st["fact"], S1, "Facts", dx=-0.07, label_dy=dy)
        series(ax, [0] + depths, st["relation"], S2, "Relations", dx=0.07, label_dy=-dy)
        ax.set_xlim(-0.4, depths[-1] + 0.9)
        ax.set_title(f"{TITLE[mode]}, {16 * sc} requirements", fontsize=10, color=INK, loc="left")
        ax.set_xticks([0] + depths)
        ax.set_xlabel("Handoffs", fontsize=9, color=INK2)
        ax.set_ylim(0, 105)
    axes[0].set_ylabel("Requirements kept in the brief (%)", fontsize=9, color=INK2)
    axes[0].legend(frameon=False, fontsize=9, loc="lower left")
    fig.suptitle("What survives each handoff", x=0.01, ha="left", fontsize=12, color=INK, fontweight="bold")
    fig.tight_layout()
    fig.savefig(root / "fig1_retention.png", dpi=160, facecolor=SURFACE)


def fig_supervision(root: Path):
    fig, axes = plt.subplots(2, 4, figsize=(13, 6.4), sharey="row", facecolor=SURFACE)
    for j, (mode, sc) in enumerate(CONFIGS):
        folder = root / f"{mode}_s{sc}"
        for i in range(2):
            style(axes[i, j])
        if not (folder / "runs.jsonl").exists():
            axes[0, j].set_title(f"{TITLE[mode]}, {16 * sc} reqs (not run)", fontsize=10, color=INK2)
            continue
        tasks, _, runs = load(folder)
        depths = sorted({r["depth"] for r in runs})
        ok, bad = {}, {}
        for cond in ("B", "C"):
            R = {d: [r for r in runs if r["cond"] == cond and r["depth"] == d] for d in depths}
            ok[cond] = [boot([(r["seed"], r["outcome"] == "delivered" and all(r["attempts"][-1]["accept"].values())
                               and not r["attempts"][-1]["schema"], 1) for r in R[d]]) for d in depths]
            bad[cond] = [boot([(r["seed"], r["outcome"] == "delivered" and (not all(r["attempts"][-1]["accept"].values())
                                                                         or bool(r["attempts"][-1]["schema"])), 1)
                               for r in R[d]]) for d in depths]
        for row, data in ((0, ok), (1, bad)):
            dy = _apart(data["B"][-1][0], data["C"][-1][0])
            series(axes[row, j], depths, data["B"], S2, "B: Root reviews in natural language", dx=-0.07, label_dy=dy)
            series(axes[row, j], depths, data["C"], S1, "C: programmatic ledger and checker", dx=0.07, label_dy=-dy)
            axes[row, j].set_xlim(-0.4, depths[-1] + 0.9)
        axes[0, j].set_title(f"{TITLE[mode]}, {16 * sc} requirements", fontsize=10, color=INK, loc="left")
        for i in range(2):
            axes[i, j].set_xticks(depths)
            axes[i, j].set_ylim(-3, 105)
        axes[1, j].set_xlabel("Handoffs before the executor", fontsize=9, color=INK2)
    axes[0, 0].set_ylabel("Delivered and fully\ncompliant (%)", fontsize=9, color=INK2)
    axes[1, 0].set_ylabel("Delivered with at least\none violation (%)", fontsize=9, color=INK2)
    axes[0, 0].legend(frameon=False, fontsize=8.5, loc="lower left")
    fig.suptitle("Supervision outcomes: natural-language review vs programmatic constraints",
                 x=0.01, ha="left", fontsize=12, color=INK, fontweight="bold")
    fig.tight_layout()
    fig.savefig(root / "fig2_supervision.png", dpi=160, facecolor=SURFACE)


if __name__ == "__main__":
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "results")
    fig_retention(root)
    fig_supervision(root)
    print("wrote", root / "fig1_retention.png", root / "fig2_supervision.png")
