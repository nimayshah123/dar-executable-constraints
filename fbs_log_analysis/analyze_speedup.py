"""Where did the scoped-prompt speedup come from?

Reads the Before/After evidence packs (original long-context run 01, scoped runs 02 and 03),
and answers four questions with numbers taken only from the saved native requests,
responses and scheduler timelines:

  1. Which stages got faster, and are they Root-owned or Worker-owned?
  2. What exactly was removed from the Worker prompts?
  3. Was the "new format" a rewrite, or a selection of the same text?
  4. Could prefix caching or Root reuse explain it?

Usage (stdlib only, Python 3.10+):
  python analyze_speedup.py --before <Before_Modification_EN.zip> --after <After_Modification_EN.zip> \
      --work evidence --out timing_tables.md
The two evidence archives are the recorded 7 November runs shared by the FBS author; they are not in
this repository. Archives are extracted into --work once; later runs reuse the extraction.
"""
import argparse, csv, difflib, glob, json, os, re, sys, zipfile
from datetime import datetime

RUNS = {"01-original-long-context": "before", "02-scoped-round1": "after", "03-scoped-round2": "after"}
LABEL = {"01-original-long-context": "01 original", "02-scoped-round1": "02 scoped r1", "03-scoped-round2": "03 scoped r2"}
UNITS = ["foundation", "merchandising", "fulfillment", "exchange-views", "transports"]
BATCH = ["merchandising", "fulfillment", "exchange-views"]
ROOT_OWNED = {"contract_planning", "transports", "__contract_integration__"}
MARK = re.compile(r"^[A-Z][A-Z0-9 /_-]{7,}( \(.*\))?:?$")

# prompt section header -> component
COMPONENT = [
    ("READ-ONLY PROVIDED MATERIALS", "public test fixtures"),
    ("ORIGINAL TASK SOURCE", "task text"),
    ("SHARED CONTRACT", "interface/verification contract"),
    ("REQUIRED API CONTRACT", "interface/verification contract"),
    ("COMMAND VALIDATION SCHEMAS", "interface/verification contract"),
    ("CURRENT UPSTREAM ARTIFACTS", "dependency code"),
    ("CURRENT EXECUTION CONTRACT", "own work-unit contract"),
    ("CURRENT OWN EXECUTION CONTRACT", "own work-unit contract"),
    ("CURRENT DELIVERY CONTRACT", "own work-unit contract"),
    ("RISK BOUNDARIES", "boundary rules"),
    ("ROUND TWO OWNERSHIP AND ERROR BOUNDARIES", "boundary rules"),
    ("YOUR EXCLUSIVE RESPONSIBILITY", "boundary rules"),
]
ORDER = ["public test fixtures", "task text", "interface/verification contract", "own work-unit contract",
         "dependency code", "boundary rules", "instructions"]


def extract(zpath, dest):
    if os.path.isdir(dest) and os.listdir(dest):
        return
    os.makedirs(dest, exist_ok=True)
    with zipfile.ZipFile(zpath) as z:
        z.extractall(dest)


def prepare(args):
    if args.before:
        extract(args.before, os.path.join(args.work, "before"))
    if args.after:
        extract(args.after, os.path.join(args.work, "after"))
    for run, side in RUNS.items():
        extract(os.path.join(args.work, side, "original-evidence", run + ".zip"), os.path.join(args.work, "raw", run))


def ts(s):
    return datetime.fromisoformat(s)


def sections(prompt):
    out, cur, buf = [], "PREAMBLE", []
    for ln in prompt.split("\n"):
        s = ln.strip()
        if MARK.match(s) and len(s) < 90:
            out.append((cur, "\n".join(buf)))
            cur, buf = s, []
        else:
            buf.append(ln)
    out.append((cur, "\n".join(buf)))
    return out


def load(work):
    req, resp = {}, {}
    for run in RUNS:
        for f in glob.glob(os.path.join(work, "raw", run, "bridge", "*.request.json")):
            q = json.load(open(f, encoding="utf-8"))
            r = json.load(open(f.replace(".request.json", ".response.json"), encoding="utf-8"))
            body = json.loads(r["body"]) if isinstance(r["body"], str) else r["body"]
            req[(run, q["task_id"])] = q
            resp[(run, q["task_id"])] = {"producer": r.get("producer"), "chars": len(r["body"]) if isinstance(r["body"], str) else len(json.dumps(r["body"])),
                                         "files": body.get("files") or {}}
    return req, resp


def timeline(work, run):
    side = RUNS[run]
    rows = list(csv.DictReader(open(os.path.join(work, side, "runs", run, "timeline.en.csv"), encoding="utf-8-sig")))
    start, end = {}, {}
    for r in rows:
        if r["type"] == "api_request_started":
            start[r["task_id"]] = ts(r["timestamp"])
        if r["type"] == "artifact_created":
            end[r["task_id"]] = ts(r["timestamp"])
        if r["type"] == "acceptance_passed" and r["task_id"] == "__contract_composition__":
            end["final_acceptance"] = ts(r["timestamp"])
        if r["type"] == "run_created":
            start["run"] = ts(r["timestamp"])
    start["final_acceptance"] = start["__contract_composition__"]
    summary = json.load(open(os.path.join(work, side, "runs", run, "run-summary.en.json"), encoding="utf-8"))
    return start, end, summary["elapsed_seconds"]


def stages(work, run, req):
    start, end, total = timeline(work, run)
    d = lambda t: (end[t] - start[t]).total_seconds()
    st = {}
    plan = req.get((run, "contract_planning"))
    st["plan (Root)"] = (start["run"] - ts(plan["started_at"])).total_seconds() if plan else 0.0
    st["foundation (Worker)"] = d("foundation")
    st["business batch x3 (Workers)"] = (max(end[t] for t in BATCH) - min(start[t] for t in BATCH)).total_seconds()
    st["transports (Root)"] = d("transports")
    st["integration (Root)"] = d("__contract_integration__")
    st["final acceptance (host, no model)"] = d("final_acceptance")
    st["scheduler overhead"] = total - sum(st.values())
    return st, total, {t: d(t) for t in UNITS + ["__contract_integration__"]}


def components(prompt, srclines):
    c = {k: 0 for k in ORDER}
    for name, body in sections(prompt):
        comp = next((v for k, v in COMPONENT if name.startswith(k)), None)
        if comp:
            c[comp] += len(body)
        else:  # PREAMBLE: in scoped prompts this is verbatim task excerpts plus a short instruction line
            for ln in body.split("\n"):
                c["task text" if ln.strip() and ln.strip() in srclines else "instructions"] += len(ln) + 1
    return c


def line_sim(a, b):
    la = [l.strip() for l in a.splitlines() if l.strip()]
    lb = [l.strip() for l in b.splitlines() if l.strip()]
    return difflib.SequenceMatcher(None, la, lb, autojunk=False).ratio()


def common_prefix(a, b):
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def md(rows, head):
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join(str(x) for x in r) + " |" for r in rows]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--before"); ap.add_argument("--after")
    ap.add_argument("--work", default=os.path.join(os.path.dirname(__file__), "evidence"))
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "timing_tables.md"))
    args = ap.parse_args()
    prepare(args)
    req, resp = load(args.work)
    runs = list(RUNS)
    o = runs[0]
    src = dict(sections(req[(o, "foundation")]["prompt"]))["ORIGINAL TASK SOURCE"]
    srclines = {l.strip() for l in src.splitlines() if l.strip()}
    rep = ["# Speedup decomposition (generated by analyze_speedup.py)", ""]

    # 1. stage timing
    st = {r: stages(args.work, r, req) for r in runs}
    names = list(st[o][0])
    rows = [[n] + [f"{st[r][0][n]:.1f}" for r in runs] + [f"{st[runs[1]][0][n] - st[o][0][n]:+.1f}"] for n in names]
    rows.append(["**total elapsed**"] + [f"**{st[r][1]:.1f}**" for r in runs] + [f"**{st[runs[1]][1] - st[o][1]:+.1f}**"])
    root = {r: sum(v for k, v in st[r][0].items() if "(Root)" in k) for r in runs}
    work = {r: sum(v for k, v in st[r][0].items() if "Worker" in k) for r in runs}
    rows.append(["sum Root-owned steps"] + [f"{root[r]:.1f}" for r in runs] + [f"{root[runs[1]] - root[o]:+.1f}"])
    rows.append(["sum Worker steps"] + [f"{work[r]:.1f}" for r in runs] + [f"{work[runs[1]] - work[o]:+.1f}"])
    rep += ["## 1. Stage timing (seconds, from scheduler timelines)", "",
            md(rows, ["stage"] + [LABEL[r] for r in runs] + ["02 minus 01"]), ""]

    # 2. prompt components, summed over the five work units
    comp = {r: {k: 0 for k in ORDER} for r in runs}
    for r in runs:
        for t in UNITS:
            for k, v in components(req[(r, t)]["prompt"], srclines).items():
                comp[r][k] += v
    tot = {r: sum(len(req[(r, t)]["prompt"]) for t in UNITS) for r in runs}
    cut = tot[o] - tot[runs[1]]
    rows = [[k] + [f"{comp[r][k]:,}" for r in runs] + [f"{comp[runs[1]][k] - comp[o][k]:+,}", f"{(comp[o][k] - comp[runs[1]][k]) / cut:+.0%}"] for k in ORDER]
    rows.append(["**total Worker prompt chars**"] + [f"**{tot[r]:,}**" for r in runs] + [f"**{-cut:+,}**", "100%"])
    rep += ["## 2. What was removed from the five Worker prompts (characters)", "",
            md(rows, ["component"] + [LABEL[r] for r in runs] + ["02 minus 01", "share of the cut"]), ""]

    # 3. per unit: input, output, duration
    rows = []
    for t in UNITS + ["__contract_integration__"]:
        for r in runs:
            pr = len(req[(r, t)]["prompt"]); out = resp[(r, t)]["chars"]; dur = st[r][2][t]
            rows.append([t, LABEL[r], resp[(r, t)]["producer"], f"{pr:,}", f"{out:,}", f"{dur:.1f}", f"{out / dur:.0f}"])
    if (o, "contract_planning") in req:
        dur = st[o][0]["plan (Root)"]; out = resp[(o, "contract_planning")]["chars"]
        rows.append(["contract_planning", LABEL[o], resp[(o, "contract_planning")]["producer"], f"{len(req[(o, 'contract_planning')]['prompt']):,}", f"{out:,}", f"{dur:.1f}", f"{out / dur:.0f}"])
    rep += ["## 3. Per request: prompt size, output size, wall time", "",
            md(rows, ["unit", "run", "producer", "prompt chars", "output chars", "seconds", "output chars/s"]), ""]

    # 4. format change: selection or rewrite? shared prefixes?
    rows = []
    for t in UNITS:
        r = runs[1]
        pre = dict(sections(req[(r, t)]["prompt"]))["PREAMBLE"]
        ls = [l.strip() for l in pre.splitlines() if l.strip()]
        n = sum(len(l) for l in ls); v = sum(len(l) for l in ls if l in srclines)
        rows.append([t, f"{n:,}", f"{v / n:.0%}", f"{v / len(src):.0%}",
                     common_prefix(req[(o, t)]["prompt"], req[(runs[1], t)]["prompt"]),
                     f"{common_prefix(req[(runs[1], t)]['prompt'], req[(runs[2], t)]['prompt']):,}"])
    rep += ["## 4. Was the new format a rewrite or a selection?", "",
            md(rows, ["unit", "scoped task text chars", "verbatim from original task", "share of original task kept",
                      "shared prefix 01-02", "shared prefix 02-03"]), ""]

    # 5. code similarity across runs (did anyone copy an earlier solution?)
    rows = []
    for t in UNITS:
        for p in sorted(resp[(o, t)]["files"]):
            a, b, c = (resp[(r, t)]["files"].get(p, "") for r in runs)
            owner = "Root" if t in ROOT_OWNED else "Worker"
            rows.append([t, p, owner, f"{line_sim(a, b):.2f}", f"{line_sim(a, c):.2f}", f"{line_sim(b, c):.2f}"])
    same = {r: all(resp[(r, "__contract_integration__")]["files"].get(p) == resp[(r, "transports")]["files"].get(p)
                   for p in resp[(r, "__contract_integration__")]["files"]) for r in runs}
    rep += ["## 5. Output code similarity across runs (line-level difflib ratio)", "",
            md(rows, ["unit", "file", "owner", "01 vs 02", "01 vs 03", "02 vs 03"]), "",
            "Integration response byte-identical to the transports response: " + ", ".join(f"{LABEL[r]}={same[r]}" for r in runs), ""]

    text = "\n".join(rep)
    open(args.out, "w", encoding="utf-8", newline="\n").write(text)
    sys.stdout.reconfigure(encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
