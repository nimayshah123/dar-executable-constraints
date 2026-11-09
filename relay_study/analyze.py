"""Analysis for the relay experiment. Reads a results folder, writes results.md and figures.

All rates come with 95% intervals from a cluster bootstrap over tasks (resampling task
seeds, 2,000 draws), because samples and requirements within a task are not independent.

Usage: python analyze.py results/summary_s4
"""
from __future__ import annotations

import json
import random
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

B_ITERS = 2000


def load(folder: Path):
    tasks = {t["seed"]: t for t in json.loads((folder / "tasks.json").read_text())}
    chains = [json.loads(l) for l in open(folder / "chains.jsonl", encoding="utf-8")]
    runs_path = folder / "runs.jsonl"
    runs = [json.loads(l) for l in open(runs_path, encoding="utf-8")] if runs_path.exists() else []
    return tasks, chains, runs


def boot(pairs, iters=B_ITERS, seed=0):
    """pairs: list of (cluster, numerator, denominator). Returns (rate, lo, hi) or None."""
    by = defaultdict(lambda: [0.0, 0.0])
    for c, n, d in pairs:
        by[c][0] += n
        by[c][1] += d
    keys = sorted(by)  # fixed order so intervals do not depend on file order
    tot_d = sum(v[1] for v in by.values())
    if not keys or tot_d == 0:
        return None
    est = sum(v[0] for v in by.values()) / tot_d
    rng, draws = random.Random(seed), []
    for _ in range(iters):
        s = [by[rng.choice(keys)] for _ in keys]
        dd = sum(x[1] for x in s)
        if dd:
            draws.append(sum(x[0] for x in s) / dd)
    draws.sort()
    return est, draws[int(0.025 * len(draws))], draws[int(0.975 * len(draws)) - 1]


def fmt(r, pct=True):
    if r is None:
        return "n/a"
    e, lo, hi = r
    if pct:
        return f"{100 * e:.0f}% [{100 * lo:.0f}, {100 * hi:.0f}]"
    return f"{e:.2f} [{lo:.2f}, {hi:.2f}]"


def meta(tasks):
    return {s: {r["id"]: r for r in t["reqs"]} for s, t in tasks.items()}


def table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def free_vector(plan, task):
    f = task["free"]
    mods = plan.get("modules", {}) if isinstance(plan, dict) else {}
    vec = []
    for slot in f["settings"]:
        m, k = slot.split(".")
        s = mods.get(m, {}).get("settings", {}) if isinstance(mods.get(m), dict) else {}
        vec.append(s.get(k) if isinstance(s, dict) else None)
    for fl in f["files"]:
        vec.append(next((m for m, e in mods.items() if isinstance(e, dict)
                         and isinstance(e.get("files"), list) and fl in e["files"]), None))
    for m in f["workers"]:
        vec.append(mods.get(m, {}).get("worker") if isinstance(mods.get(m), dict) else None)
    return vec


def disagreement(u, v):
    return sum(a != b for a, b in zip(u, v)) / max(1, len(u))


def main(folder):
    folder = Path(folder)
    tasks, chains, runs = load(folder)
    M = meta(tasks)
    depths = sorted({b["depth"] for c in chains for b in c["briefs"]})
    md = [f"# Relay experiment results\n\nFolder: `{folder.as_posix()}`. Tasks: {len(tasks)}. "
          f"Chains: {len(chains)}. Supervision loops: {len(runs)}. "
          "Intervals are 95% cluster bootstrap over tasks.\n"]
    figs = {}

    # ---------------------------------------------------------------- 1. brief retention (judge)
    md.append("## 1. What survives each handoff (brief audit by judge model)\n")
    rows, fig_ret = [], {}
    for cls in ("fact", "relation"):
        for d in depths:
            kept, dist, lost, unl = [], [], [], 0
            for c in chains:
                b = c["briefs"][d - 1]
                for rid, r in M[c["seed"]].items():
                    if r["cls"] != cls:
                        continue
                    lab = b["judge"].get(rid)
                    if lab not in ("kept", "distorted", "lost"):
                        unl += 1
                        continue
                    kept.append((c["seed"], lab == "kept", 1))
                    dist.append((c["seed"], lab == "distorted", 1))
                    lost.append((c["seed"], lab == "lost", 1))
            k = boot(kept)
            fig_ret[(cls, d)] = k
            rows.append([cls, d, fmt(k), fmt(boot(dist)), fmt(boot(lost)), unl])
    md.append(table(["class", "handoffs", "kept", "distorted", "lost", "unlabeled"], rows))
    words = {d: sum(c["briefs"][d - 1]["words"] for c in chains) / len(chains) for d in depths}
    md.append("\nMean brief length (words) by handoff: " + ", ".join(f"{d}: {w:.0f}" for d, w in words.items()))
    rows = []
    kinds = sorted({r["kind"] for s in M for r in M[s].values()})
    for kind in kinds:
        cells = [kind]
        for d in depths:
            cells.append(fmt(boot([(c["seed"], c["briefs"][d - 1]["judge"].get(rid) == "kept", 1)
                                   for c in chains for rid, r in M[c["seed"]].items() if r["kind"] == kind])))
        rows.append(cells)
    md.append("\nKept rate by requirement kind:\n")
    md.append(table(["kind"] + [f"after {d}" for d in depths], rows))
    rev = [(c["seed"], c["briefs"][d - 1]["judge"].get(rid) == "distorted", 1)
           for c in chains for d in depths for rid, r in M[c["seed"]].items() if r.get("revised")]
    md.append(f"\nRevised facts (notes contain a withdrawn draft value) labelled distorted, all depths: {fmt(boot(rev))}")

    if not runs:
        (folder / "results.md").write_text("\n".join(md), encoding="utf-8", newline="\n")
        print("\n".join(md))
        return

    # ---------------------------------------------------------------- 2. first attempts by depth
    all_depths = sorted({r["depth"] for r in runs})
    md.append("\n## 2. Requirement satisfaction in the first plan, before any supervision\n")
    md.append("B first attempt = the executor sees only the brief (depth 0 = full notes = group A). "
              "C first attempt = same brief plus the host ledger, before any rejection.\n")
    rows, fig_first = [], {}
    conds = sorted({r["cond"] for r in runs})
    for cond in conds:
        for subset in ("fact", "relation", "unformalized"):
            cells = [cond, subset]
            for d in all_depths:
                pairs = []
                for r in runs:
                    if r["cond"] != cond or r["depth"] != d:
                        continue
                    acc = r["attempts"][0]["accept"]
                    for rid, ok in acc.items():
                        q = M[r["seed"]][rid]
                        hit = (not q["formalized"]) if subset == "unformalized" else (q["cls"] == subset and q["formalized"])
                        if hit:
                            pairs.append((r["seed"], ok, 1))
                b = boot(pairs)
                fig_first[(cond, subset, d)] = b
                cells.append(fmt(b))
            rows.append(cells)
    md.append(table(["cond", "requirements", *[f"depth {d}" for d in all_depths]], rows))
    md.append("\nfact and relation rows cover the 12 formalized requirements; unformalized covers the 4 the ledger never sees.")

    # F2 vs F3: lost in the brief vs kept but not applied
    pairs_kept, pairs_lost = [], []
    chain_by = {(c["seed"], c["sample"]): c for c in chains}
    for r in runs:
        if r["cond"] != "B" or r["depth"] == 0:
            continue
        lab = chain_by[(r["seed"], r["sample"])]["briefs"][r["depth"] - 1]["judge"]
        for rid, ok in r["attempts"][0]["accept"].items():
            (pairs_kept if lab.get(rid) == "kept" else pairs_lost).append((r["seed"], not ok, 1))
    md.append(f"\nB first attempt, violation rate when the judge said the brief kept the requirement: "
              f"{fmt(boot(pairs_kept))}; when distorted or lost: {fmt(boot(pairs_lost))}.")

    # ---------------------------------------------------------------- 3. supervision outcomes
    md.append("\n## 3. Supervision outcomes (H1, H2)\n")
    md.append("delivered = Root approved (B) or the checker passed (C). blocked = no approval after the "
              "revision cap, so nothing executes. A violation reaches execution only inside a delivered plan.\n")
    rows, fig_exec = [], {}
    for d in all_depths:
        for cond in conds:
            R = [r for r in runs if r["cond"] == cond and r["depth"] == d]
            if not R:
                continue
            deliv = boot([(r["seed"], r["outcome"] == "delivered", 1) for r in R])
            ok_all = boot([(r["seed"], r["outcome"] == "delivered" and all(r["attempts"][-1]["accept"].values())
                            and not r["attempts"][-1]["schema"], 1) for r in R])
            false_acc = boot([(r["seed"], r["outcome"] == "delivered" and (not all(r["attempts"][-1]["accept"].values())
                                                                          or bool(r["attempts"][-1]["schema"])), 1) for r in R])
            vf = boot([(r["seed"], sum(1 for rid, ok in r["attempts"][-1]["accept"].items()
                                       if not ok and M[r["seed"]][rid]["formalized"]) if r["outcome"] == "delivered" else 0, 1) for r in R])
            vu = boot([(r["seed"], sum(1 for rid, ok in r["attempts"][-1]["accept"].items()
                                       if not ok and not M[r["seed"]][rid]["formalized"]) if r["outcome"] == "delivered" else 0, 1) for r in R])
            nl = sum(r["nl_corrections"] for r in R) / len(R)
            pr = sum(r["prog_rejections"] for r in R) / len(R)
            calls = sum(r["calls"] for r in R) / len(R)
            fig_exec[(cond, d)] = (ok_all, false_acc, vf, vu)
            rows.append([d, cond, len(R), fmt(deliv), fmt(ok_all), fmt(false_acc), fmt(vf, False), fmt(vu, False),
                         f"{nl:.2f}", f"{pr:.2f}", f"{calls:.1f}"])
    md.append(table(["depth", "cond", "runs", "delivered", "delivered and fully compliant",
                     "delivered with a violation", "formalized violations executed per run",
                     "unformalized violations executed per run", "NL corrections per run",
                     "programmatic rejections per run", "LLM calls per run"], rows))

    # Root review quality (B)
    for rc in [c for c in conds if c.startswith("B")]:
        fa, fl = [], []
        for r in runs:
            if r["cond"] != rc:
                continue
            for a in r["attempts"]:
                bad = (not all(a["accept"].values())) or bool(a["schema"])
                (fa if bad else fl).append((r["seed"], a["approved"] if bad else not a["approved"], 1))
        md.append(f"\n{rc} Root natural-language review: approved a plan that still had a violation in {fmt(boot(fa))} "
                  f"of flawed plans; withheld approval from a fully correct plan in {fmt(boot(fl))} of correct plans.")
    # checker detection on formalized rows (sanity: should be 100% by construction)
    det = []
    for r in runs:
        if r["cond"] != "C":
            continue
        for a in r["attempts"]:
            for rid, ok in a["accept"].items():
                q = M[r["seed"]][rid]
                if q["formalized"] and not ok and q["kind"] != "conditional":
                    det.append((r["seed"], any(x.startswith(rid + " ") for x in a["check_failed"]), 1))
    md.append(f"\nChecker detection of formalized non-conditional violations (sanity check, expected 100%): {fmt(boot(det))}.")
    vac = []
    for r in runs:
        if r["cond"] != "C":
            continue
        for a in r["attempts"]:
            for rid, ok in a["accept"].items():
                q = M[r["seed"]][rid]
                if q["formalized"] and q["kind"] == "conditional" and not ok:
                    vac.append((r["seed"], not any(x.startswith(rid + " ") for x in a["check_failed"]), 1))
    md.append(f"Formalized conditionals violated by acceptance but passed by the literal checker (antecedent "
              f"made false by dropping the pinned value): {fmt(boot(vac))} of conditional violations.")

    # ---------------------------------------------------------------- 4. autonomy (H3)
    md.append("\n## 4. Planning autonomy (H3)\n")
    md.append("Free choices = settings, file owners and worker assignments no requirement touches. "
              "Diversity = mean share of free choices on which two independent samples of the same task differ. "
              "If the constraint layer took over planning, C diversity would collapse relative to A.\n")
    groups = defaultdict(list)
    for r in runs:
        t = tasks[r["seed"]]
        first = r["attempts"][0]["plan"]
        last = r["attempts"][-1]["plan"]
        if r["depth"] == 0 and r["cond"] == "B" and first is not None:
            groups[("A (single agent, first plan)", 0, r["seed"])].append(free_vector(first, t))
        if r["outcome"] == "delivered" and last is not None:
            groups[(f"{r['cond']} delivered", r["depth"], r["seed"])].append(free_vector(last, t))
    rows = []
    labels = sorted({(k[0], k[1]) for k in groups})
    for lab, d in labels:
        pairs = []
        for (l2, d2, seed), vecs in groups.items():
            if (l2, d2) != (lab, d) or len(vecs) < 2:
                continue
            for u, v in combinations(vecs, 2):
                pairs.append((seed, disagreement(u, v), 1))
        rows.append([lab, d, len(pairs), fmt(boot(pairs))])
    md.append(table(["plans", "depth", "sample pairs", "free-choice diversity"], rows))
    foot = {c: [] for c in conds}
    for r in runs:
        if len(r["attempts"]) > 1 and r["attempts"][0]["plan"] and r["attempts"][-1]["plan"]:
            t = tasks[r["seed"]]
            foot[r["cond"]].append((r["seed"], disagreement(free_vector(r["attempts"][0]["plan"], t),
                                                            free_vector(r["attempts"][-1]["plan"], t)), 1))
    md.append("\nRedesign footprint (share of free choices changed between first and last attempt, runs with "
              "at least one revision): "
              + "; ".join(f"{c} {fmt(boot(foot[c]))} over {len(foot[c])} runs" for c in conds) + ".")
    md.append("Authorship: every delivered plan is the executor's own JSON output. The checker only returns ledger "
              "rows and the values it found; it never writes or edits a plan (see run.py, run_loop).")

    # ---------------------------------------------------------------- cost
    tot_calls = sum(c["calls"] for c in chains) + sum(r["calls"] for r in runs)
    tot_in = sum(c["in_tokens"] for c in chains) + sum(r["in_tokens"] for r in runs)
    tot_out = sum(c["out_tokens"] for c in chains) + sum(r["out_tokens"] for r in runs)
    md.append(f"\n## Cost\n\nLLM calls: {tot_calls}. Input tokens: {tot_in:,}. Output tokens: {tot_out:,}.")
    errs = folder / "infra_errors.json"
    if errs.exists():
        md.append(f"Infrastructure failures (excluded): {len(json.loads(errs.read_text()))}.")

    (folder / "results.md").write_text("\n".join(md), encoding="utf-8", newline="\n")
    print("\n".join(md))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/summary_s4")
