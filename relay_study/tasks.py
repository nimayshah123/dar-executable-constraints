"""Procedural task generator for the relay experiment.

Each task is a small engineering work plan. 16 hard requirements are written
into about 1,000 words of dated meeting notes, together with filler, withdrawn
draft values, legacy numbers and non-binding preferences. Every requirement is
a machine-checkable predicate over the JSON plan an executor returns, so
acceptance needs no LLM judge.

Requirement classes
  fact      setting_eq, worker_eq, file_owner             (one entity, one value)
  relation  depends, not_depends, before, diff_worker,
            same_worker, conditional                     (two entities linked)

Two predicates per requirement
  check()   the literal formal predicate the host checker runs in group C
  accept()  independent acceptance. Identical to check() except for
            conditionals: the user's notes pin the antecedent true, so the
            consequent is what the user actually requires.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field, asdict

MODULES = ["ingest", "auth", "billing", "ledger", "notify", "export", "search", "cache",
           "audit", "scheduler", "gateway", "reports", "inventory", "pricing", "sync", "metrics",
           "catalog", "checkout", "shipping", "returns", "profile", "session", "upload", "media",
           "feed", "alerts", "webhooks", "quota", "tenant", "backup", "archive", "indexer"]
WORKERS = ["alpha", "beta", "gamma", "delta"]
SETTINGS = {  # key: (lo, hi, step)
    "retry_limit": (1, 9, 1),
    "batch_size": (100, 900, 50),
    "timeout_s": (5, 120, 5),
    "ttl_s": (30, 600, 30),
    "max_workers": (2, 32, 2),
    "queue_depth": (10, 500, 10),
}
FILES = ["core.py", "handlers.py", "models.py", "jobs.py", "routes.py", "store.py", "client.py",
         "schema.sql", "config.yaml", "worker.py", "views.py", "adapters.py", "codec.py", "policy.py",
         "events.py", "forms.py", "hooks.py", "serial.py", "limits.py", "retry.py", "tokens.py",
         "locks.py", "queues.py", "rules.py", "paths.py", "types.py", "flags.py", "bench.py",
         "fixtures.py", "stubs.py", "specs.py", "loader.py", "mapper.py", "guard.py", "parser.py",
         "render.py"]
PEOPLE = ["Maya", "Tomas", "Priya", "Jonah", "Lena", "Ravi", "Sofia", "Ken"]
PROJECTS = ["Harbor", "Juniper", "Atlas", "Kestrel", "Meridian", "Orchard", "Tundra", "Willow"]
N_MODULES, N_FILES = 6, 9


@dataclass
class Req:
    id: str
    kind: str
    cls: str                 # fact | relation
    p: dict                  # parameters
    formalized: bool = True  # present in the host ledger (group C)
    revised: bool = False    # notes contain a withdrawn earlier value

    # ---- text forms -------------------------------------------------
    def formal(self) -> str:
        p, k = self.p, self.kind
        if k == "setting_eq":
            return f"plan.modules.{p['m']}.settings.{p['k']} == {p['v']}"
        if k == "worker_eq":
            return f'plan.modules.{p["m"]}.worker == "{p["w"]}"'
        if k == "file_owner":
            return f'"{p["f"]}" in plan.modules.{p["m"]}.files'
        if k == "depends":
            return f'"{p["b"]}" in plan.modules.{p["a"]}.depends_on'
        if k == "not_depends":
            return f"not reachable({p['a']} -> {p['b']}) through depends_on, direct or transitive"
        if k == "before":
            return f'index(plan.order, "{p["a"]}") < index(plan.order, "{p["b"]}")'
        if k == "diff_worker":
            return f"plan.modules.{p['a']}.worker != plan.modules.{p['b']}.worker"
        if k == "same_worker":
            return f"plan.modules.{p['a']}.worker == plan.modules.{p['b']}.worker"
        if k == "conditional":
            return (f"plan.modules.{p['a']}.settings.{p['ka']} > {p['t']}  =>  "
                    f"plan.modules.{p['b']}.settings.{p['kb']} {p['op']} {p['u']}")
        raise ValueError(k)

    def plain(self) -> str:
        """Canonical English statement, used only by the brief-retention judge."""
        p, k = self.p, self.kind
        return {
            "setting_eq": lambda: f"{p['m']}.{p['k']} must be exactly {p['v']}",
            "worker_eq": lambda: f"{p['m']} must be assigned to worker {p['w']}",
            "file_owner": lambda: f"file {p['f']} must be owned by module {p['m']}",
            "depends": lambda: f"{p['a']} must depend on {p['b']}",
            "not_depends": lambda: f"{p['a']} must not depend on {p['b']}, directly or transitively",
            "before": lambda: f"{p['a']} must come before {p['b']} in the execution order",
            "diff_worker": lambda: f"{p['a']} and {p['b']} must be on different workers",
            "same_worker": lambda: f"{p['a']} and {p['b']} must be on the same worker",
            "conditional": lambda: (f"if {p['a']}.{p['ka']} is above {p['t']} then {p['b']}.{p['kb']} must be "
                            f"{'at most' if p['op'] == '<=' else 'at least'} {p['u']}"),
        }[k]()

    # ---- predicates -------------------------------------------------
    def check(self, plan) -> tuple[bool, str]:
        return _eval(self, plan, literal=True)

    def accept(self, plan) -> tuple[bool, str]:
        return _eval(self, plan, literal=False)


def _mod(plan, m):
    try:
        v = plan["modules"][m]
        return v if isinstance(v, dict) else {}
    except Exception:
        return {}


def _setting(plan, m, k):
    s = _mod(plan, m).get("settings")
    return s.get(k) if isinstance(s, dict) else None


def _deps(plan, m):
    d = _mod(plan, m).get("depends_on")
    return [x for x in d if isinstance(x, str)] if isinstance(d, list) else []


def reachable(plan, a, b) -> bool:
    seen, stack = set(), list(_deps(plan, a))
    while stack:
        x = stack.pop()
        if x == b:
            return True
        if x not in seen:
            seen.add(x)
            stack.extend(_deps(plan, x))
    return False


def _cmp(x, op, u):
    return isinstance(x, int) and not isinstance(x, bool) and (x <= u if op == "<=" else x >= u)


def _eval(r: Req, plan, literal: bool) -> tuple[bool, str]:
    p, k = r.p, r.kind
    if k == "setting_eq":
        got = _setting(plan, p["m"], p["k"])
        return got == p["v"] and not isinstance(got, bool), f"found {got!r}"
    if k == "worker_eq":
        got = _mod(plan, p["m"]).get("worker")
        return got == p["w"], f"found {got!r}"
    if k == "file_owner":
        files = _mod(plan, p["m"]).get("files")
        ok = isinstance(files, list) and p["f"] in files
        return ok, f"{p['m']}.files = {files!r}"
    if k == "depends":
        d = _deps(plan, p["a"])
        return p["b"] in d, f"{p['a']}.depends_on = {d!r}"
    if k == "not_depends":
        bad = reachable(plan, p["a"], p["b"])
        return not bad, ("a dependency path exists" if bad else "no path")
    if k == "before":
        o = plan.get("order") if isinstance(plan, dict) else None
        if not isinstance(o, list) or p["a"] not in o or p["b"] not in o:
            return False, f"order = {o!r}"
        return o.index(p["a"]) < o.index(p["b"]), f"order = {o!r}"
    if k in ("diff_worker", "same_worker"):
        wa, wb = _mod(plan, p["a"]).get("worker"), _mod(plan, p["b"]).get("worker")
        if wa not in WORKERS or wb not in WORKERS:
            return False, f"workers {wa!r}, {wb!r}"
        ok = (wa != wb) if k == "diff_worker" else (wa == wb)
        return ok, f"workers {wa!r}, {wb!r}"
    if k == "conditional":
        av, bv = _setting(plan, p["a"], p["ka"]), _setting(plan, p["b"], p["kb"])
        cons = _cmp(bv, p["op"], p["u"])
        if literal and isinstance(av, int) and av <= p["t"]:
            return True, f"antecedent false ({p['a']}.{p['ka']} = {av})"
        return cons, f"{p['a']}.{p['ka']} = {av}, {p['b']}.{p['kb']} = {bv}"
    raise ValueError(k)


def schema_problems(plan, task) -> list[str]:
    """Universal validity rules, given to every condition in the skeleton."""
    if not isinstance(plan, dict):
        return ["output is not a JSON object"]
    out = []
    mods = plan.get("modules")
    if not isinstance(mods, dict):
        return ["missing 'modules' object"]
    extra = sorted(set(plan) - {"modules", "order"})
    if extra:
        out.append(f"unexpected top-level keys {extra}; only 'modules' and 'order' are allowed")
    want = set(task["modules"])
    if set(mods) != want:
        out.append(f"modules must be exactly {sorted(want)}; got {sorted(mods)}")
    owners = {}
    for m in task["modules"]:
        e = mods.get(m) if isinstance(mods.get(m), dict) else {}
        if e.get("worker") not in WORKERS:
            out.append(f"{m}.worker invalid: {e.get('worker')!r}")
        d = e.get("depends_on")
        if not isinstance(d, list) or any(x not in want or x == m for x in d):
            out.append(f"{m}.depends_on invalid: {d!r}")
        s = e.get("settings")
        for key in task["settings"][m]:
            lo, hi, _ = SETTINGS[key]
            v = s.get(key) if isinstance(s, dict) else None
            if not (isinstance(v, int) and not isinstance(v, bool) and lo <= v <= hi):
                out.append(f"{m}.settings.{key} must be an integer in {lo}..{hi}; got {v!r}")
        for f in e.get("files", []) if isinstance(e.get("files"), list) else []:
            owners.setdefault(f, []).append(m)
    for f in task["files"]:
        if len(owners.get(f, [])) != 1:
            out.append(f"file {f} must be owned by exactly one module; owners {owners.get(f, [])}")
    for f in owners:
        if f not in task["files"]:
            out.append(f"unknown file {f}")
    o = plan.get("order")
    if not isinstance(o, list) or sorted(o) != sorted(want):
        out.append(f"order must list every module once; got {o!r}")
    else:
        for m in task["modules"]:
            for d in _deps(plan, m):
                if d in o and o.index(d) > o.index(m):
                    out.append(f"{m} depends on {d} but {d} comes later in order")
    return out


# ---------------------------------------------------------------- generator
def _val(rng, key, exclude=()):
    lo, hi, st = SETTINGS[key]
    choices = [v for v in range(lo, hi + 1, st) if v not in exclude]
    return rng.choice(choices)


def make_task(seed: int, scale: int = 1) -> dict:
    """scale multiplies everything: 6*scale modules, 9*scale files, 16*scale requirements."""
    rng = random.Random(seed * 10 + scale)
    mods = rng.sample(MODULES, N_MODULES * scale)
    settings = {m: rng.sample(list(SETTINGS), 2) for m in mods}
    files = rng.sample(FILES, N_FILES * scale)
    people = rng.sample(PEOPLE, 5)
    project = rng.choice(PROJECTS)

    # Hidden reference plan so every requirement set is jointly satisfiable.
    order = mods[:]
    rng.shuffle(order)
    pos = {m: i for i, m in enumerate(order)}
    workers = {m: rng.choice(WORKERS) for m in mods}
    values = {m: {k: _val(rng, k) for k in settings[m]} for m in mods}
    owner = {f: rng.choice(mods) for f in files}

    reqs: list[Req] = []

    # relations on structure
    pairs = [(a, b) for a in mods for b in mods if pos[b] < pos[a]]  # b earlier than a
    rng.shuffle(pairs)
    dep_edges = pairs[:2 * scale]
    ref_deps = {m: [] for m in mods}
    for a, b in dep_edges:
        ref_deps[a].append(b)
        reqs.append(Req("", "depends", "relation", {"a": a, "b": b}))

    def ref_reach(a, b):
        return reachable({"modules": {m: {"depends_on": ref_deps[m]} for m in mods}}, a, b)

    nd = [(a, b) for a in mods for b in mods if a != b and not ref_reach(a, b)
          and (a, b) not in dep_edges and pos[b] < pos[a]]
    for a, b in rng.sample(nd, scale):
        reqs.append(Req("", "not_depends", "relation", {"a": a, "b": b}))
    bf = [(a, b) for a in mods for b in mods if pos[a] < pos[b]
          and not ref_reach(a, b) and not ref_reach(b, a)]
    for a, b in rng.sample(bf, scale):
        reqs.append(Req("", "before", "relation", {"a": a, "b": b}))

    # workers: disjoint same-worker pairs forced, then diff pairs and pins consistent with them
    same = rng.sample(mods, 2 * scale)
    for sa, sb in zip(same[::2], same[1::2]):
        workers[sb] = workers[sa]
        reqs.append(Req("", "same_worker", "relation", {"a": sa, "b": sb}))
    dw = [(a, b) for a in mods for b in mods if a < b and workers[a] != workers[b]]
    for a, b in rng.sample(dw, scale):
        reqs.append(Req("", "diff_worker", "relation", {"a": a, "b": b}))
    for m in rng.sample(mods, 2 * scale):
        reqs.append(Req("", "worker_eq", "fact", {"m": m, "w": workers[m]}))

    # settings: 4*scale pinned facts, 2*scale conditionals hanging off pinned values
    slots = [(m, k) for m in mods for k in settings[m]]
    rng.shuffle(slots)
    pinned, free_slots = slots[:4 * scale], slots[4 * scale:]
    for m, k in pinned:
        lo, hi, st = SETTINGS[k]
        if values[m][k] <= lo + st:          # antecedent needs room below the value
            values[m][k] = lo + st * rng.randint(2, (hi - lo) // st)
    for m, k in pinned:
        reqs.append(Req("", "setting_eq", "fact", {"m": m, "k": k, "v": values[m][k]}))
    for (am, ak), (bm, bk) in zip(pinned[:2 * scale], free_slots[:2 * scale]):
        lo, hi, st = SETTINGS[ak]
        v = values[am][ak]
        t = max(lo, v - st * rng.randint(1, 3))
        blo, bhi, bst = SETTINGS[bk]
        op = rng.choice(["<=", ">="])
        if op == "<=":
            u = blo + bst * rng.randint(0, 2)
            values[bm][bk] = blo
        else:
            u = bhi - bst * rng.randint(0, 2)
            values[bm][bk] = bhi
        reqs.append(Req("", "conditional", "relation",
                        {"a": am, "ka": ak, "t": t, "b": bm, "kb": bk, "op": op, "u": u}))
    for f in rng.sample(files, 2 * scale):
        reqs.append(Req("", "file_owner", "fact", {"f": f, "m": owner[f]}))

    rng.shuffle(reqs)
    for i, r in enumerate(reqs):
        r.id = f"R{i + 1:02d}"
    # two of the pinned settings were revised during the meetings
    for r in rng.sample([r for r in reqs if r.kind == "setting_eq"], 2 * scale):
        r.revised = True
        r.p["old"] = _val(rng, r.p["k"], exclude=(r.p["v"],))
    # formalization gap: some requirements never reach the host ledger
    for r in (rng.sample([r for r in reqs if r.cls == "fact"], 2 * scale)
              + rng.sample([r for r in reqs if r.cls == "relation"], 2 * scale)):
        r.formalized = False

    pinned_slots = {(r.p["m"], r.p["k"]) for r in reqs if r.kind == "setting_eq"}
    cond_slots = {(r.p["b"], r.p["kb"]) for r in reqs if r.kind == "conditional"}
    pinned_workers = ({r.p["m"] for r in reqs if r.kind == "worker_eq"}
                      | {r.p[x] for r in reqs if r.kind in ("same_worker", "diff_worker") for x in "ab"})
    free = {
        "settings": [f"{m}.{k}" for m, k in slots if (m, k) not in pinned_slots | cond_slots],
        "files": [f for f in files if f not in {r.p["f"] for r in reqs if r.kind == "file_owner"}],
        "workers": [m for m in mods if m not in pinned_workers],
    }
    task = {
        "seed": seed, "scale": scale, "project": project, "modules": mods, "settings": settings,
        "files": files, "workers": WORKERS, "reqs": [asdict(r) for r in reqs], "free": free,
    }
    # The hidden reference plan must pass everything, proving joint satisfiability.
    ref = {"modules": {m: {"worker": workers[m], "depends_on": ref_deps[m], "settings": values[m],
                           "files": [f for f in files if owner[f] == m]} for m in mods},
           "order": order}
    assert not schema_problems(ref, task), schema_problems(ref, task)
    assert all(r.accept(ref)[0] and r.check(ref)[0] for r in reqs), seed
    task["reference_plan"] = ref
    task["source"] = _narrative(rng, task, reqs, people, values)
    task["skeleton"] = skeleton(task)
    task["ledger"] = "\n".join(f"{r.id}: {r.formal()}" for r in reqs if r.formalized)
    return task


def reqs_of(task) -> list[Req]:
    return [Req(**r) for r in task["reqs"]]


# ---------------------------------------------------------------- text
def skeleton(task) -> str:
    st = "\n".join(
        f"  {m}: " + ", ".join(f"{k} (integer {SETTINGS[k][0]}..{SETTINGS[k][1]})" for k in task["settings"][m])
        for m in task["modules"])
    return f"""Project {task['project']}: produce the work plan as JSON.
Modules: {', '.join(task['modules'])}
Settings each module must define:
{st}
Files to assign (each owned by exactly one module): {', '.join(task['files'])}
Workers: {', '.join(task['workers'])}
Output exactly one JSON object and nothing else:
{{"modules": {{"<module>": {{"worker": "<worker>", "depends_on": ["<module>", ...], "settings": {{"<key>": <int>, ...}}, "files": ["<file>", ...]}}, ...}}, "order": ["<module>", ...]}}
Validity rules: every module appears once; every file is owned by exactly one module; settings are integers in range; "order" lists every module once; every dependency comes earlier in "order"; no dependency cycles.
Follow every hard requirement you were given. Where nothing is required, decide yourself."""


FILLER = [
    "{p} gave an update on the vendor contract; nothing blocking yet.",
    "We spent a while on naming conventions and agreed to revisit them later.",
    "The staging cluster was flaky again on Tuesday, which slowed everyone down.",
    "{p} asked whether we should rewrite {m} in Rust; consensus was not this quarter.",
    "Budget review moved to next Thursday.",
    "{p} shared a dashboard with last month's error rates for the old system.",
    "There is some concern that {m} logs are far too verbose.",
    "We may want a design review for {m} after launch.",
    "{p} will be on leave for part of next week, so expect slower replies.",
    "Someone raised the idea of a shared metrics library; parked for now.",
    "The client said they are happy with progress so far.",
    "Documentation is behind and {p} volunteered to catch up.",
    "We talked about adopting a new linter, but there was no decision.",
    "{p} reminded everyone that the on-call rota changes next month.",
    "Load tests from the old system are not comparable, so nobody should rely on those numbers.",
    "We discussed whether {m} needs its own database and are leaning towards no.",
    "The security review is scheduled for the end of the month.",
    "{p} noted that the CI pipeline takes too long on large branches.",
    "Historically {m} caused most incidents, mostly through configuration drift.",
    "Nobody remembers why {m} was split out originally.",
    "{p} suggested a short demo for the client at the next checkpoint.",
    "There was a long tangent about the office move.",
    "The old runbook for {m} is out of date and needs a rewrite at some point.",
    "{p} is collecting feedback on API naming from the mobile team.",
    "Retro feedback: fewer meetings, more written updates.",
    "{p} will check whether the legacy exporter can finally be retired.",
    "We agreed that code review turnaround should stay under a day.",
    "{p} flagged that two dashboards disagree about weekly active users; unrelated to this plan.",
]


def _say(rng, r: Req, people) -> str:
    p, k, who = r.p, r.kind, rng.choice(people)
    T = {
        "setting_eq": lambda: [
            f"{who} confirmed that {p['m']}'s {p['k']} has to be exactly {p['v']}.",
            f"Hard requirement from the client: {p['k']} on {p['m']} is set to {p['v']}.",
            f"For {p['m']}, {p['k']} = {p['v']} is non-negotiable; ops sized capacity around it.",
        ],
        "worker_eq": lambda: [
            f"{p['m']} must be owned by worker {p['w']}; nobody else has the credentials.",
            f"Only {p['w']} can take {p['m']}, so it has to be assigned there.",
        ],
        "file_owner": lambda: [
            f"The file {p['f']} belongs to {p['m']} and must be owned by that module.",
            f"{who} was firm that {p['f']} has to live under {p['m']}.",
        ],
        "depends": lambda: [
            f"{p['a']} has to declare a dependency on {p['b']}, since it consumes {p['b']}'s output.",
            f"{who} made the point that {p['a']} must depend on {p['b']}.",
        ],
        "not_depends": lambda: [
            f"{p['a']} must not depend on {p['b']}, not even indirectly through another module; legal flagged that coupling.",
            f"Hard rule: no dependency path from {p['a']} to {p['b']}, direct or transitive.",
        ],
        "before": lambda: [
            f"{p['a']} has to run before {p['b']} in the execution order, even though neither depends on the other.",
            f"The rollout sequence needs {p['a']} ahead of {p['b']}; that ordering is required.",
        ],
        "diff_worker": lambda: [
            f"{p['a']} and {p['b']} must go to different workers, for separation of duties.",
            f"Audit insists {p['a']} and {p['b']} are never handled by the same worker.",
        ],
        "same_worker": lambda: [
            f"{p['a']} and {p['b']} must be handled by the same worker because they share a local cache.",
            f"Keep {p['a']} and {p['b']} on one worker; that is a requirement, not a preference.",
        ],
        "conditional": lambda: [
            (f"Because of the load profile, whenever {p['a']}'s {p['ka']} is above {p['t']}, "
             f"{p['b']}'s {p['kb']} must be {'no more than' if p['op'] == '<=' else 'at least'} {p['u']}."),
            (f"{who} explained the coupling: if {p['a']}.{p['ka']} exceeds {p['t']}, then {p['b']}.{p['kb']} "
             f"has to be {'at most' if p['op'] == '<=' else 'at least'} {p['u']}."),
        ],
    }
    return rng.choice(T[k]())


def _narrative(rng, task, reqs: list[Req], people, values) -> str:
    mods = task["modules"]
    days = ["Kickoff (Mon 3 Nov)", "Architecture sync (Tue 4 Nov)", "Ops review (Wed 5 Nov)",
            "Client call (Thu 6 Nov)", "Planning (Fri 7 Nov)", "Wrap-up (Mon 10 Nov)"]
    sections = [[] for _ in days]
    for r in reqs:
        if r.revised:
            i = rng.randint(0, 2)
            sections[i].append(f"{rng.choice(people)}'s first draft put {r.p['m']}'s {r.p['k']} at {r.p['old']}.")
            j = rng.randint(i + 2, len(days) - 1)
            sections[j].append(f"Correction: {r.p['m']}'s {r.p['k']} is {r.p['v']}, not {r.p['old']} as in the "
                               f"earlier draft; the earlier number is withdrawn.")
        else:
            sections[rng.randrange(len(days))].append(_say(rng, r, people))
    # non-binding preferences on unconstrained items
    if task["free"]["workers"]:
        m = rng.choice(task["free"]["workers"])
        sections[rng.randrange(len(days))].append(
            f"{rng.choice(people)} would like {m} on {rng.choice(WORKERS)} if convenient, but that is not a requirement.")
    if task["free"]["settings"]:
        m, k = rng.choice(task["free"]["settings"]).split(".")
        sections[rng.randrange(len(days))].append(
            f"A {k} around {_val(rng, k)} for {m} might be nice; the team can choose.")
    # legacy numbers that look like requirements but are not
    for _ in range(2):
        m = rng.choice(mods)
        k = rng.choice(task["settings"][m])
        sections[rng.randrange(len(days))].append(
            f"In the legacy system {m} ran with {k} {_val(rng, k)}, which is irrelevant for the new plan.")
    for s in sections:
        for _ in range(rng.randint(4, 6)):
            s.append(rng.choice(FILLER).format(p=rng.choice(people), m=rng.choice(mods)))
        for _ in range(task["scale"] - 1):  # a little more filler as load grows
            s.append(rng.choice(FILLER).format(p=rng.choice(people), m=rng.choice(mods)))
        rng.shuffle(s)
    body = "\n\n".join(f"{d}\n" + " ".join(s) for d, s in zip(days, sections))
    head = (f"Running notes from the {task['project']} planning meetings. Attendees rotated between "
            f"{', '.join(people)}. The plan covers modules {', '.join(mods)}.")
    tail = "Anything not stated as required above is left to the team's judgment."
    return f"{head}\n\n{body}\n\n{tail}"


if __name__ == "__main__":  # quick look at one task
    t = make_task(1000, scale=int(__import__("sys").argv[1]) if len(__import__("sys").argv) > 1 else 1)
    print(t["source"])
    print("\n--- words:", len(t["source"].split()))
    print("\n--- ledger\n" + t["ledger"])
    print("\n--- free", t["free"])
