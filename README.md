# Formalize or Lose It

Code, data and results for "Formalize or Lose It: What Executable Constraints Control in an Agent Swarm", the DAR team's report for the Apart Research Swarm Alignment Hackathon (6 to 8 November 2026).

DAR team: Zion, Kyle, Almene, Sam, Nimay.

## Question

When a planner agent (Root) hands work to many Worker agents, every requirement travels as natural language, and every handoff is a lossy rewrite. Can executable constraints take over that supervision without taking planning freedom away from Root? We study FBS, the Feasibility Scheduler ([zionlinne/feasibility-scheduler](https://github.com/zionlinne/feasibility-scheduler), PR #5 head 7630497). It validates Root's plan, releases modules to Workers, checks each delivery and runs an independent test suite.

## What is here

| Folder | Study | Main result |
|---|---|---|
| [`fbs_log_analysis/`](fbs_log_analysis) | Inventory of every rule in a passing FBS run, and a reading of the 7 November timing logs | 84 rules; 46% exist only as prompt text, including 19 of the 23 rules the plan gave Workers |
| [`planted_faults/`](planted_faults) | 19 planted faults replayed through unmodified FBS on the recorded 3 November deliveries; 29 runs, no model calls | FBS blocked all 10 plan and delivery faults. 6 faults passed all 125 suite cases and were accepted. Six host checks, added through FBS's existing extension point, caught 5 of those 6 and a real violation in the 3 November run, with no false positives |
| [`relay_study/`](relay_study) | Controlled study of requirement loss across handoffs under natural language and programmatic supervision; about 1,150 model calls, all cached | A supervisor reviewing from its own compacted notes approved 71% of flawed plans. A ledger checked by code kept formalized requirements intact at every depth at a sixth of the input tokens, and passed every requirement left out of it |
| [`data/`](data) | Every table behind the report as CSV, with a guide to each column | |
| [`figures/`](figures) | The report figures and the script that draws them | |

Constraints control what they formalize, and nothing else.

## Reproduce

Python 3.12 or newer, and `pip install -r requirements.txt` (matplotlib, for the figures only).

| What | Command | Also needs |
|---|---|---|
| Relay study: every result and figure | `bash relay_study/run_all.sh` | Nothing: every model call is replayed from `relay_study/results/cache`, byte for byte |
| CSV tables | `python data/export_data.py` | Nothing |
| Report figures | `python figures/make_figures.py figures planted_faults/results/results.json` | Nothing |
| Planted fault runs | `python -I planted_faults/faults.py --pack <handoff pack> --fbs <feasibility-scheduler>/src --out runs --jobs 3` | Node 24+, FBS at 7630497, the DAR handoff pack v0.2 |
| Timing tables | `python fbs_log_analysis/analyze_speedup.py --before <zip> --after <zip>` | The 7 November evidence archives |

## Not included

* **FBS** is public at the link above.
* **The DAR handoff pack v0.2** (task, recorded 3 November deliveries, official verifier, historical harness) and **the 7 November evidence archives** are the FBS author's prior work and are not redistributed. `faults.py` reads what it needs from the pack at run time; the tables derived from the archives are in `fbs_log_analysis/`.

## Prior work and event work

| Item | When | Who |
|---|---|---|
| FBS, PRs #2 to #5 | Before the event | Zion |
| 3 November baseline run and handoff pack v0.2 | Before the event | Zion |
| Two scoped prompt rounds (7 November) | Event | Zion |
| Evaluation framework and record template | Event | Almene |
| Everything in this repository: supervision inventory, evaluation records for the three runs, timing analysis, FBS unit test run, planted fault driver and runs, relay study, data export, figures | Event | Nimay |

## License

MIT, see [LICENSE](LICENSE).
