# Data

Every table behind the report, as CSV with one header row. `python data/export_data.py` rebuilds all of them from the recorded results in this repository; it makes no model calls and runs nothing.

| Folder | What it is | Source |
|---|---|---|
| `relay_study/` | Requirement loss across handoffs under four kinds of supervision | New runs, every model call cached in `relay_study/results/cache` |
| `planted_faults/` | One planted fault per run, replayed through unmodified FBS on the 3 November deliveries | New runs on FBS, no model calls |
| `fbs_logs/` | Rule inventory of the 3 November run and timing of the 7 November rounds | Readings of the recorded logs, not new runs |

## relay_study

8 tasks with 2 samples each, 16 or 64 requirements per task, briefs written as a task aware brief or a generic summary, supervision at 0, 1 or 4 handoffs. See `relay_study/README.md` for the design.

| Arm | Executor sees | Supervision |
|---|---|---|
| B at 0 handoffs | The full notes | Its first attempt is the single agent baseline (A) |
| B | The brief | Root reviews in natural language, holding the full notes |
| Bc | The brief | Root reviews holding only its own compacted notes |
| C | The brief plus a ledger of formal requirements | A code checker returns the failing rows |

A quarter of the requirements are left out of the ledger on purpose (`formalized = 0`).

* `runs.csv`: one row per run. Violations count only when the plan was delivered. Columns: experiment, brief_style, requirements, arm, task_seed, sample, handoffs, outcome, delivered_fully_compliant, violations_executed_formalized, violations_executed_unformalized, violations_executed_total, premise_bypasses_executed, first_attempt_violations, nl_corrections, programmatic_rejections, model_calls, input_tokens, output_tokens.
* `attempts.csv`: one row per plan attempt. flawed = any violation or schema problem; checker_pass for C; root_approved for B and Bc.
* `requirements.csv`: one row per run and requirement: kind, class (fact or relation), formalized, brief_label (judge label for that requirement in the brief the executor saw: kept, distorted or lost; "full notes" at 0 handoffs), satisfied in the first and final attempt, and flagged_by_checker_final.
* `brief_retention.csv`: one row per brief and requirement, with the judge label.
* `premise_bypass_cases.csv`, `premise_bypass_control.csv`: the check below.

`summary_s4_compacted_root` reran B from the same cache as `summary_s4` (identical rows) and adds Bc; `brief_retention.csv` lists those briefs once. The raw JSON per experiment is in `relay_study/results/`, and `relay_study/tasks.py` defines every requirement predicate.

**Headline numbers**

| Number | Value | How to get it |
|---|---|---|
| Violations executed per run, generic summary, 64 requirements, after 1 / 4 handoffs | B 0 / 0, Bc 31.3 / 30.6, C 8.1 / 10.2 | runs.csv: summary_s4 for B and C, summary_s4_compacted_root for Bc; mean of violations_executed_total |
| Flawed plans approved by Root, same condition | B 0% of 36, Bc 71% of 45 | attempts.csv: flawed = 1, mean of root_approved |
| Model calls and input tokens per run, same condition | B 4.25 and 22,900; C 1.0 and 3,600 | runs.csv: summary_s4, handoffs 1 and 4 |
| C runs with any programmatic rejection, whole study | 5 | runs.csv: arm C, programmatic_rejections above 0 |
| Violations C let through, whole study, on requirements outside the ledger | 300 of 305; the other 5 are the premise bypasses | runs.csv: arm C, sum of violations_executed_unformalized and violations_executed_formalized |

C's remaining violations are a coverage gap, not a checker failure. Every one traces to something left out of the ledger: either the requirement itself, or the fact a conditional's premise depends on.

**Premise bypass check.** Do the five bypasses happen because a conditional is in the ledger but the fact its premise depends on is not? Yes, in all five, and in no other case. All five are in summary_s4 after 4 handoffs, all were first attempts, and all five plans were delivered. In each, the premise fact was outside the ledger and the summary had lost it; the executor picked a premise value below the threshold (for example 300 where the notes say 600 and the threshold is 540), so the condition was false and the check passed without looking at the consequent.

Control, every formalized conditional check across all C attempts:

| Premise | Premise in the brief | Checks | Premise set at or below threshold | Violated | Caught by checker | Passed vacuously |
|---|---|---|---|---|---|---|
| In ledger | Kept | 414 | 0 | 0 | 0 | 0 |
| In ledger | Lost or distorted | 65 | 0 | 0 | 0 | 0 |
| Not in ledger | Kept | 170 | 0 | 0 | 0 | 0 |
| Not in ledger | Lost or distorted | 13 | 11 | 5 | 0 | 5 |

A bypass needs both at once: the premise is outside the ledger, and a handoff loses it. The fix is to formalize the facts a premise depends on whenever a conditional is formalized.

## planted_faults

`results.csv`: one row per run (29). Columns: arm, fault, group, planted_change, expected_control_nov3, result, evidence, checks_fired_at_root, suite cases passed and failed, failing case names, run_accepted, fault_in_final_workspace, file_written_outside_workspace, elapsed_s. Results and the fault list are in `planted_faults/README.md`; per run evidence is in `planted_faults/results/outcomes/`.

## fbs_logs

* `supervision_inventory.csv`: the 84 rules given to an agent in the 3 November run, by channel, with the strongest control that enforces each. level_group is one of Blocked by code, Field check only, Caught at root, Prompt only.
* `stage_timing.csv`, `request_timing.csv`, `worker_prompt_composition.csv`: where the 7 November speedup came from. In total the Workers took 32 s longer, while Root's own steps fell from 195 s to 14 s.

The run drivers in the FBS author's evidence (not included) answer each request by submitting files already written to a drafts folder. A step's time therefore records when an answer was submitted, not how long a model took to write it, which is why the transports module could return 8,400 characters of code 5.6 s after release. See `fbs_log_analysis/timing_findings.md`.
