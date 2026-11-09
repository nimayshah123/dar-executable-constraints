"""Report figures, drawn from the tables in data/ and the planted fault results.

Usage (from the repository root): python figures/make_figures.py [<figures dir>] [<planted fault results.json>]
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

SURFACE, INK, INK2, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#e4e3df'
RAMP = {'250': '#86b6ef', '350': '#5598e7', '500': '#256abf', '650': '#104281'}  # ordinal blue, validated light mode
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.edgecolor': GRID, 'axes.labelcolor': INK2,
                     'xtick.color': INK2, 'ytick.color': INK2, 'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE})


REPO = Path(__file__).resolve().parent.parent


def read_csv(rel):
    with open(REPO / rel, encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def finish(ax):
    for side in ('top', 'right', 'left'):
        ax.spines[side].set_visible(False)
    ax.tick_params(length=0)


def inventory(out):
    levels = ['Prompt only', 'Caught at root', 'Field check only', 'Blocked by code']
    found = Counter((r['channel'], r['level_group']) for r in read_csv('data/fbs_logs/supervision_inventory.csv'))
    channels = [(name, [found[(name, level)] for level in levels]) for name in ('Root plan to Workers', 'FBS to Workers', 'FBS to Root')]
    channels.append(('All rules', [sum(counts[i] for _, counts in channels) for i in range(len(levels))]))
    colors = [RAMP['250'], RAMP['350'], RAMP['500'], RAMP['650']]
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    for row, (name, counts) in enumerate(channels):
        total, left = sum(counts), 0.0
        for level, count, color in zip(levels, counts, colors):
            share = 100 * count / total
            if count:
                ax.barh(row, share, left=left, height=0.56, color=color, edgecolor=SURFACE, linewidth=2)
                if share >= 7:
                    ax.text(left + share / 2, row, str(count), ha='center', va='center', fontsize=9.5,
                            color=INK if color in (RAMP['250'], RAMP['350']) else 'white')
            left += share
        ax.text(101.5, row, f'{round(100 * counts[0] / total)}% prompt only', va='center', fontsize=9.5, color=INK)
    ax.set_yticks(range(len(channels)), [f'{n}  ({sum(c)} rules)' for n, c in channels], fontsize=10, color=INK)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xticks([0, 25, 50, 75, 100], ['0%', '25%', '50%', '75%', '100%'])
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    finish(ax)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in colors]
    ax.legend(handles, levels, ncol=4, loc='upper left', bbox_to_anchor=(0, -0.13), frameon=False, fontsize=9.5,
              handlelength=1.2, columnspacing=1.4)
    fig.text(0.01, 0.97, 'The plan reaches Workers almost entirely as prompt text', fontsize=12.5, weight='bold', color=INK, va='top')
    fig.text(0.01, 0.89, 'Each rule in the 3 November FBS run, labeled by the strongest control that enforces it. Numbers are rule counts.',
             fontsize=9.5, color=INK2, va='top')
    fig.subplots_adjust(left=0.27, right=0.84, top=0.80, bottom=0.22)
    fig.savefig(out, dpi=200)
    plt.close(fig)


def relay(out):
    arms = ['B: Root reviews,\nfull notes', 'Bc: Root reviews,\nits own summary', 'C: ledger\nchecked by code']
    # Generic summary, 64 requirements. Bc ran as its own experiment on the same cached handoff chains.
    runs = [r for r in read_csv('data/relay_study/runs.csv')
            if (r['experiment'], r['arm']) in {('summary_s4', 'B'), ('summary_s4_compacted_root', 'Bc'), ('summary_s4', 'C')}]

    def cell(arm, handoffs):
        return [r for r in runs if r['arm'] == arm and r['handoffs'] == str(handoffs)]

    def mean(rows, column):
        return sum(int(r[column]) for r in rows) / len(rows)
    after1, after4 = ([round(mean(cell(arm, h), 'violations_executed_total'), 1) for arm in ('B', 'Bc', 'C')] for h in (1, 4))
    c_total = sum(int(r['violations_executed_total']) for h in (1, 4) for r in cell('C', h))
    c_inside = sum(int(r['violations_executed_formalized']) for h in (1, 4) for r in cell('C', h))
    tokens = {arm: round(mean(cell(arm, 1) + cell(arm, 4), 'input_tokens'), -2) for arm in ('B', 'C')}
    fig, ax = plt.subplots(figsize=(8.6, 4.2))
    width = 0.34
    xs = range(len(arms))
    for offset, values, color, label in ((-width / 2 - 0.01, after1, RAMP['350'], 'After 1 handoff'),
                                        (width / 2 + 0.01, after4, RAMP['650'], 'After 4 handoffs')):
        positions = [x + offset for x in xs]
        ax.bar(positions, values, width=width, color=color, edgecolor=SURFACE, linewidth=2, label=label)
        for x, v in zip(positions, values):
            ax.text(x, v + 0.8, f'{v:g}', ha='center', va='bottom', fontsize=10, color=INK)
    ax.set_xticks(list(xs), arms, fontsize=10, color=INK)
    ax.set_ylim(0, 40)
    ax.set_ylabel('Violations executed per run (of 64)')
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    finish(ax)
    ax.legend(frameon=False, loc='upper right', fontsize=9.5)
    ax.text(2, max(after1[2], after4[2]) + 4, f'{c_total - c_inside} of {c_total} outside\nthe ledger; the other\n{c_inside} are premise bypasses',
            ha='center', va='bottom', fontsize=9, color=INK2)
    fig.text(0.01, 0.97, 'A supervisor working from its own summary lets most violations through', fontsize=12.5, weight='bold', color=INK, va='top')
    fig.text(0.01, 0.905, f'Relay study, generic summary, 64 requirements, {len(cell("B", 1))} runs per cell. '
             f'Input tokens per run: B {tokens["B"]:,.0f}, C {tokens["C"]:,.0f}.', fontsize=9.5, color=INK2, va='top')
    fig.subplots_adjust(left=0.09, right=0.98, top=0.82, bottom=0.17)
    fig.savefig(out, dpi=200)
    plt.close(fig)


def planted(out, results_path):
    data = json.loads(Path(results_path).read_text(encoding='utf-8'))['results']
    order = ['Blocked at plan', 'Blocked at delivery', 'Caught at root', 'Missed']
    colors = {'Blocked at plan': RAMP['650'], 'Blocked at delivery': RAMP['500'], 'Caught at root': RAMP['250'], 'Missed': '#e34948'}
    groups = [('Root plan', 'P'), ('Worker delivery', 'D'), ('Behavior', 'B'), ('Plan rules to Workers', 'C')]
    arms = [('as-run', 'As run on 3 November'), ('formalized', 'Same faults, six host checks added')]
    unexpected = sorted({r['result'] for r in data if r['fault'] not in ('clean', 'fixed')} - set(order))
    if unexpected:
        raise SystemExit(f'results contain {unexpected}; rerun those faults before drawing the figure')
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.2), sharey=True)
    for ax, (arm, title) in zip(axes, arms):
        rows = [r for r in data if r['arm'] == arm and r['fault'] not in ('clean', 'fixed')]
        for gi, (gname, prefix) in enumerate(groups):
            group = [r for r in rows if r['fault'].startswith(prefix)]
            if not group:
                ax.text(0.12, gi, 'not rerun', va='center', fontsize=9, color=INK2)
                continue
            left = 0
            for o in order:
                n = sum(1 for r in group if r['result'] == o)
                if n:
                    ax.barh(gi, n, left=left, height=0.56, color=colors[o], edgecolor=SURFACE, linewidth=2)
                    ax.text(left + n / 2, gi, str(n), ha='center', va='center', fontsize=9.5,
                            color='white' if o in ('Blocked at plan', 'Blocked at delivery', 'Missed') else INK)
                left += n
        ax.set_xlim(0, 6.5)
        ax.set_xticks(range(0, 7))
        ax.xaxis.grid(True, color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.set_title(title, fontsize=10.5, color=INK, loc='left')
        ax.set_xlabel('Planted faults')
        finish(ax)
    # Shared y axis: one set of labels, on the left panel only.
    as_run = [r for r in data if r['arm'] == 'as-run']
    axes[0].set_yticks(range(len(groups)), [f"{g} ({sum(1 for r in as_run if r['fault'].startswith(p))})" for g, p in groups],
                       fontsize=10, color=INK)
    axes[0].invert_yaxis()
    handles = [plt.Rectangle((0, 0), 1, 1, color=colors[o]) for o in order]
    fig.legend(handles, order, ncol=4, loc='lower left', bbox_to_anchor=(0.2, 0.0), frameon=False, fontsize=9.5,
               handlelength=1.2, columnspacing=1.4)
    fig.text(0.01, 0.97, 'Rules the test suite cannot see pass FBS until they become checks', fontsize=12.5, weight='bold', color=INK, va='top')
    fig.text(0.01, 0.905, 'One planted fault per run, replayed through unmodified FBS on the 3 November deliveries. Bars show the first control that stopped each fault.',
             fontsize=9.5, color=INK2, va='top')
    fig.subplots_adjust(left=0.2, right=0.98, top=0.78, bottom=0.22, wspace=0.08)
    fig.savefig(out, dpi=200)
    plt.close(fig)


if __name__ == '__main__':
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / 'figures'
    results = Path(sys.argv[2]) if len(sys.argv) > 2 else REPO / 'planted_faults' / 'results' / 'results.json'
    target.mkdir(parents=True, exist_ok=True)
    inventory(target / 'fig1_inventory.png')
    planted(target / 'fig2_planted_faults.png', results)
    relay(target / 'fig3_relay_supervision.png')
    print('figures written to', target)
