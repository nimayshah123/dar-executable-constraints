"""Builds the tidy CSV tables in data/ from the recorded results in this repository.

Usage (from the repository root): python data/export_data.py

Reads only recorded results; makes no model calls and runs nothing.
"""
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / 'data'
RELAY = REPO / 'relay_study' / 'results'
EXPERIMENTS = {  # results folder: (brief style, requirements per task)
    'brief_s1': ('task aware brief', 16),
    'brief_s4': ('task aware brief', 64),
    'summary_s1': ('generic summary', 16),
    'summary_s4': ('generic summary', 64),
    'summary_s4_compacted_root': ('generic summary', 64),
}
GROUPS = {'P': 'Root plan', 'D': 'Worker delivery', 'B': 'Behavior', 'C': 'Plan rule given to Workers'}


def write_csv(path, rows, fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or list(rows[0].keys())
    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def load(folder):
    tasks = {t['seed']: t for t in json.loads((folder / 'tasks.json').read_text(encoding='utf-8'))}
    with open(folder / 'chains.jsonl', encoding='utf-8') as f:
        chains = {(c['seed'], c['sample']): c for c in map(json.loads, f)}
    with open(folder / 'runs.jsonl', encoding='utf-8') as f:
        runs = [json.loads(line) for line in f]
    return tasks, chains, runs


def setting(plan, m, k):
    mod = plan.get('modules', {}).get(m) if isinstance(plan, dict) and isinstance(plan.get('modules'), dict) else None
    s = mod.get('settings') if isinstance(mod, dict) else None
    return s.get(k) if isinstance(s, dict) else None


def brief_label(chains, run, rid):
    if run['depth'] == 0:
        return 'full notes'
    return chains[(run['seed'], run['sample'])]['briefs'][run['depth'] - 1]['judge'].get(rid, 'unlabeled')


def plain(q):
    p, k = q['p'], q['kind']
    if k == 'setting_eq':
        return f"{p['m']}.{p['k']} must be exactly {p['v']}"
    if k == 'conditional':
        return (f"if {p['a']}.{p['ka']} is above {p['t']} then {p['b']}.{p['kb']} must be "
                f"{'at most' if p['op'] == '<=' else 'at least'} {p['u']}")
    return json.dumps(p)


def flagged(attempt, rid):
    return any(x.startswith(rid + ' ') for x in attempt['check_failed'])


def premise_of(task, cond):
    a, ka = cond['p']['a'], cond['p']['ka']
    found = [q for q in task['reqs'] if q['kind'] == 'setting_eq' and q['p']['m'] == a and q['p']['k'] == ka]
    assert len(found) == 1, (task['seed'], cond['id'], len(found))
    return found[0]


def export_relay():
    out = OUT / 'relay_study'
    run_rows, attempt_rows, req_rows, ret_rows, case_rows = [], [], [], [], []
    control = defaultdict(Counter)
    chain_hashes = {}
    for name, (style, nreq) in EXPERIMENTS.items():
        folder = RELAY / name
        tasks, chains, runs = load(folder)
        chain_hashes[name] = hashlib.sha256((folder / 'chains.jsonl').read_bytes()).hexdigest()
        base = {'experiment': name, 'brief_style': style, 'requirements': nreq}
        for r in runs:
            task = tasks[r['seed']]
            M = {q['id']: q for q in task['reqs']}
            first, last = r['attempts'][0], r['attempts'][-1]
            delivered = r['outcome'] == 'delivered'
            bad_last = [rid for rid, ok in last['accept'].items() if not ok]
            vac_last = [q['id'] for q in task['reqs'] if r['cond'] == 'C' and q['kind'] == 'conditional' and q['formalized']
                        and not last['accept'][q['id']] and not flagged(last, q['id'])]
            key = {**base, 'arm': r['cond'], 'task_seed': r['seed'], 'sample': r['sample'], 'handoffs': r['depth']}
            run_rows.append({
                **key, 'outcome': r['outcome'], 'attempts': len(r['attempts']),
                'delivered_fully_compliant': int(delivered and not bad_last and not last['schema']),
                'violations_executed_formalized': sum(1 for x in bad_last if M[x]['formalized']) if delivered else 0,
                'violations_executed_unformalized': sum(1 for x in bad_last if not M[x]['formalized']) if delivered else 0,
                'violations_executed_total': len(bad_last) if delivered else 0,
                'premise_bypasses_executed': len(vac_last) if delivered else 0,
                'first_attempt_violations': sum(1 for ok in first['accept'].values() if not ok),
                'nl_corrections': r['nl_corrections'], 'programmatic_rejections': r['prog_rejections'],
                'model_calls': r['calls'], 'input_tokens': r['in_tokens'], 'output_tokens': r['out_tokens'],
            })
            for i, a in enumerate(r['attempts']):
                bad = [rid for rid, ok in a['accept'].items() if not ok]
                attempt_rows.append({
                    **key, 'attempt': i + 1, 'final_attempt': int(i == len(r['attempts']) - 1),
                    'violations': len(bad), 'violations_formalized': sum(1 for x in bad if M[x]['formalized']),
                    'violations_unformalized': sum(1 for x in bad if not M[x]['formalized']),
                    'schema_problems': len(a['schema']), 'flawed': int(bool(bad) or bool(a['schema'])),
                    'checker_pass': '' if r['cond'] != 'C' else int(a['checker_pass']),
                    'root_approved': '' if r['cond'] == 'C' else int(a['approved']),
                    'feedback_kind': a['feedback_kind'] or '',
                })
                if r['cond'] != 'C':
                    continue
                for q in task['reqs']:
                    if q['kind'] != 'conditional' or not q['formalized']:
                        continue
                    prem = premise_of(task, q)
                    lab = brief_label(chains, r, prem['id'])
                    violated = not a['accept'][q['id']]
                    caught = violated and flagged(a, q['id'])
                    vacuous = violated and not caught
                    av, bv = setting(a['plan'], q['p']['a'], q['p']['ka']), setting(a['plan'], q['p']['b'], q['p']['kb'])
                    group = ('premise formalized' if prem['formalized'] else 'premise not formalized',
                             'premise kept in brief' if lab in ('kept', 'full notes') else 'premise lost or distorted in brief')
                    c = control[group]
                    c['conditional checks'] += 1
                    c['violated'] += violated
                    c['caught by checker'] += caught
                    c['passed vacuously'] += vacuous
                    c['premise value set at or below threshold'] += int(isinstance(av, int) and av <= q['p']['t'])
                    if vacuous:
                        case_rows.append({
                            **key, 'attempt': i + 1, 'delivered_with_this_plan': int(delivered and i == len(r['attempts']) - 1),
                            'conditional_id': q['id'], 'conditional': plain(q),
                            'premise_id': prem['id'], 'premise': plain(prem), 'premise_formalized': int(prem['formalized']),
                            'premise_in_brief': lab, 'premise_required_value': prem['p']['v'], 'premise_value_in_plan': av,
                            'threshold': q['p']['t'], 'consequent_required': f"{q['p']['op']} {q['p']['u']}",
                            'consequent_value_in_plan': bv,
                            'other_violations_in_plan': sum(1 for x, ok in a['accept'].items() if not ok and x != q['id']),
                            'checker_pass': int(a['checker_pass']),
                        })
            for rid, q in M.items():
                req_rows.append({
                    **key, 'req_id': rid, 'kind': q['kind'], 'class': q['cls'], 'formalized': int(q['formalized']),
                    'revised_in_notes': int(q['revised']), 'brief_label': brief_label(chains, r, rid),
                    'satisfied_first_attempt': int(first['accept'][rid]), 'satisfied_final_attempt': int(last['accept'][rid]),
                    'flagged_by_checker_final': '' if r['cond'] != 'C' else int(flagged(last, rid)),
                    'run_delivered': int(delivered),
                })
        if name == 'summary_s4_compacted_root' and chain_hashes[name] == chain_hashes['summary_s4']:
            continue  # same recorded chains as summary_s4; do not count them twice
        for (seed, sample), c in sorted(chains.items()):
            M = {q['id']: q for q in tasks[seed]['reqs']}
            for b in c['briefs']:
                for rid, q in M.items():
                    ret_rows.append({**base, 'task_seed': seed, 'sample': sample, 'handoffs': b['depth'], 'req_id': rid,
                                     'kind': q['kind'], 'class': q['cls'], 'formalized': int(q['formalized']),
                                     'revised_in_notes': int(q['revised']), 'label': b['judge'].get(rid, 'unlabeled'),
                                     'brief_words': b['words']})
    counts = {
        'runs.csv': write_csv(out / 'runs.csv', run_rows),
        'attempts.csv': write_csv(out / 'attempts.csv', attempt_rows),
        'requirements.csv': write_csv(out / 'requirements.csv', req_rows),
        'brief_retention.csv': write_csv(out / 'brief_retention.csv', ret_rows),
    }
    case_fields = list(case_rows[0].keys()) if case_rows else ['experiment']
    counts['premise_bypass_cases.csv'] = write_csv(out / 'premise_bypass_cases.csv', case_rows, case_fields)
    summary = []
    for (pf, pk), c in sorted(control.items()):
        summary.append({'premise': pf, 'premise_in_brief': pk, **{k: c[k] for k in (
            'conditional checks', 'premise value set at or below threshold', 'violated', 'caught by checker', 'passed vacuously')}})
    counts['premise_bypass_control.csv'] = write_csv(out / 'premise_bypass_control.csv', summary)
    return counts, case_rows, summary


def export_planted():
    data = json.loads((REPO / 'planted_faults' / 'results' / 'results.json').read_text(encoding='utf-8'))
    rows = []
    for r in data['results']:
        suite = (r.get('suite_runs') or [{}])[-1]
        fid = r['fault']
        rows.append({
            'arm': r['arm'], 'fault': fid, 'group': 'Baseline' if fid in ('clean', 'fixed') else GROUPS[fid[0]],
            'planted_change': r['rule'], 'expected_control_nov3': r.get('nov3_level') or '', 'result': r['result'],
            'evidence': r['evidence'], 'checks_fired_at_root': ' '.join(r.get('checks_fired_at_root', [])),
            'suite_cases_passed': suite.get('passed', ''), 'suite_cases_failed': suite.get('failed', ''),
            'suite_failing_cases': ' '.join(suite.get('failing_cases') or []), 'run_accepted': int(bool(r.get('run_accepted'))),
            'fault_in_final_workspace': '' if r.get('fault_in_final_workspace') is None else int(r['fault_in_final_workspace']),
            'file_written_outside_workspace': int(bool(r.get('escape_file_written'))), 'elapsed_s': r.get('elapsed_s', ''),
        })
    return write_csv(OUT / 'planted_faults' / 'results.csv', rows), data


def md_table_after(text, heading):
    """Rows of the first markdown table after the line that starts with `heading`."""
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(heading))
    i = next(j for j in range(start + 1, len(lines)) if lines[j].startswith('|'))
    block = []
    while i < len(lines) and lines[i].startswith('|'):
        block.append(lines[i])
        i += 1

    def split(line):
        return [c.strip().replace('**', '').replace('\\|', '|') for c in re.split(r'(?<!\\)\|', line.strip())[1:-1]]
    header = split(block[0])
    return [dict(zip(header, split(line))) for line in block[2:]]


def export_fbs_logs():
    """Readings of the recorded FBS runs of 3 and 7 November. No FBS run is repeated here."""
    out = OUT / 'fbs_logs'
    logs = REPO / 'fbs_log_analysis'
    inv = (logs / 'supervision_inventory.md').read_text(encoding='utf-8')
    rows = []
    for heading, channel in (('### A.', 'FBS to Root'), ('### B.', 'FBS to Workers'), ('### C.', 'Root plan to Workers')):
        for r in md_table_after(inv, heading):
            rows.append({'channel': channel, 'row': r.get('#', ''),
                         'rule': r.get('Rule (prompt wording, shortened)') or r.get('Rule (plan wording, shortened)', ''),
                         'level': r.get('Level', ''),
                         'level_group': next(g for p, g in (('Blocked', 'Blocked by code'), ('Field checked only', 'Field check only'),
                                                            ('Caught at root', 'Caught at root'), ('Prompt only', 'Prompt only'))
                                             if r.get('Level', '').startswith(p)),
                         'enforced_at': r.get('Enforced at', ''),
                         'this_run': r.get('This run') or r.get('This run (reading of run/workspace)', ''), 'class': r.get('Class', '')})
    counts = {'supervision_inventory.csv': write_csv(out / 'supervision_inventory.csv', rows)}
    timing = (logs / 'timing_tables.md').read_text(encoding='utf-8')
    counts['stage_timing.csv'] = write_csv(out / 'stage_timing.csv', md_table_after(timing, '## 1.'))
    counts['worker_prompt_composition.csv'] = write_csv(out / 'worker_prompt_composition.csv', md_table_after(timing, '## 2.'))
    counts['request_timing.csv'] = write_csv(out / 'request_timing.csv', md_table_after(timing, '## 3.'))
    return counts


def main():
    for k, v in export_fbs_logs().items():
        print(f'data/fbs_logs/{k}: {v} rows')
    counts, cases, summary = export_relay()
    for k, v in counts.items():
        print(f'data/relay_study/{k}: {v} rows')
    n, data = export_planted()
    print(f'data/planted_faults/results.csv: {n} rows; {dict(Counter(r["result"] for r in data["results"]))}')
    print('\nPremise bypass cases (formalized conditional violated, passed by the checker):')
    for c in cases:
        print(f"  {c['experiment']} seed {c['task_seed']} sample {c['sample']} handoffs {c['handoffs']} attempt {c['attempt']}:"
              f" {c['conditional_id']} premise {c['premise_id']} formalized={c['premise_formalized']}"
              f" in brief={c['premise_in_brief']} value {c['premise_value_in_plan']} vs required {c['premise_required_value']}"
              f" (threshold {c['threshold']})")
    print('\nControl:')
    for s in summary:
        print('  ', s)


if __name__ == '__main__':
    main()
