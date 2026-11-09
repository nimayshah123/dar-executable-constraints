# Relay study: handoff compression vs programmatic constraints

A controlled study of one mechanism behind the report's hypotheses: requirements that travel between agents as natural language can be lost or distorted at each handoff, while requirements held in a host ledger never pass through a summary. It does not use or modify FBS, and its numbers are not evidence about FBS itself. It shows which effects to look for there.

## Design

* **Tasks.** 8 tasks, 2 samples each. Each task is a work plan for 6 or 24 modules: worker assignment, dependencies, execution order, two integer settings per module and file ownership.
* **Requirements.** 16 or 64 per task, half facts (such as `billing.retry_limit == 7`) and half relations (dependencies, forbidden transitive paths, ordering, same or different worker, and conditionals that hang off a fact). They are written into dated meeting notes with filler, withdrawn draft values and legacy numbers.
* **Handoffs.** A relay agent rewrites the notes into a 150 word brief, and each further agent rewrites the brief for the next one at the same budget. Two brief styles: a task aware handoff brief, and a generic summary that does not know what the next agent must do. Supervision runs at 0, 1 and 4 handoffs.
* **Scoring.** Every requirement is a predicate in `tasks.py`, and acceptance is always scored on all requirements by code. A judge model only labels whether each brief kept, distorted or lost each requirement.

| Arm | Executor sees | Supervision |
|---|---|---|
| A (B at 0 handoffs) | The full notes | First attempt, no supervision |
| B | The brief | Root reviews each plan in natural language holding the full notes; a plan executes only on approval |
| Bc | The brief | Root reviews holding only its own compacted notes |
| C | The brief plus a ledger of formal requirements | A code checker rejects violating plans with the failing rows; a plan executes only when it passes |

Each arm allows two revisions after the first attempt and fails closed. A quarter of the requirements are left out of the ledger on purpose, to measure what a formalization gap lets through. Every generated task ships with a hidden reference plan that passes all requirements, so each requirement set is satisfiable.

Models: relay and executor `claude-haiku-5-5`; Root and judge `claude-sonnet-5-5`; through the Claude Code CLI with tools and settings disabled, in an empty working directory.

## Results

Generic summary, 64 requirements:

| Measure | B | Bc | C |
|---|---|---|---|
| Violations executed per run, after 1 / 4 handoffs | 0 / 0 | 31.3 / 30.6 | 8.1 / 10.2 |
| Flawed plans approved by Root | 0% of 36 | 71% of 45 | |
| Model calls and input tokens per run | 4.25 and 22,900 | | 1.0 and 3,600 |

* **Where C's violations come from.** Across the whole study, 300 of the 305 violations C let through were on requirements outside the ledger. The other 5 are premise bypasses: a conditional in the ledger whose premise fact was not, and was lost at the fourth handoff. The executor set the premise below its threshold, so the check passed without looking at the consequent. When the ledger held the premise, losing it from the brief did no harm (65 checks, 0 bypasses).
* **What the briefs keep.** A task aware brief is close to lossless at the first handoff, even at 64 requirements in about 130 words. A generic summary loses relations more than facts.

Full tables with 95% cluster bootstrap intervals are in `results/<experiment>/results.md`, figures in `results/fig1_retention.png` and `results/fig2_supervision.png`, and tidy CSVs in `data/relay_study/`.

## Files

```
tasks.py      procedural tasks and requirement predicates (python tasks.py 4 prints task 1000 at 64 requirements)
llm.py        model wrapper with a disk cache keyed by the sha256 of backend, model, prompts and sample tag
run.py        handoff chains and supervision loops for arms B, Bc and C
analyze.py    tables with cluster bootstrap intervals, written to results/<experiment>/results.md
figures.py    cross condition figures
run_all.sh    reproduces every experiment below
results/      brief_s1, brief_s4, summary_s1, summary_s4 (s1 = 16, s4 = 64 requirements),
              summary_s4_compacted_root (adds Bc), and cache/ with every raw model output
```

## Reproduce

```
bash run_all.sh
```

Every model call is replayed from `results/cache`, so this needs no CLI or API key, makes no model calls, and regenerates every output byte for byte. Python 3.11 or newer; matplotlib for the figures.

To draw fresh samples, point `--cache` at an empty folder or change `--seed0`. Fresh samples will differ, because the CLI exposes no sampling seed; `--backend anthropic --temperature 0` gives a lower variance rerun.
