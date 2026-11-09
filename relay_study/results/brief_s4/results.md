# Relay experiment results

Folder: `results/brief_s4`. Tasks: 8. Chains: 16. Supervision loops: 96. Intervals are 95% cluster bootstrap over tasks.

## 1. What survives each handoff (brief audit by judge model)

| class | handoffs | kept | distorted | lost | unlabeled |
|---|---|---|---|---|---|
| fact | 1 | 97% [91, 100] | 0% [0, 0] | 3% [0, 9] | 0 |
| fact | 2 | 97% [91, 100] | 0% [0, 0] | 3% [0, 9] | 0 |
| fact | 3 | 97% [91, 100] | 0% [0, 0] | 3% [0, 9] | 0 |
| fact | 4 | 97% [91, 100] | 0% [0, 0] | 3% [0, 9] | 0 |
| relation | 1 | 98% [94, 100] | 2% [0, 5] | 1% [0, 1] | 0 |
| relation | 2 | 96% [92, 100] | 3% [0, 8] | 1% [0, 1] | 0 |
| relation | 3 | 96% [92, 100] | 3% [0, 8] | 1% [0, 1] | 0 |
| relation | 4 | 95% [90, 98] | 5% [2, 9] | 1% [0, 1] | 0 |

Mean brief length (words) by handoff: 1: 135, 2: 122, 3: 119, 4: 124

Kept rate by requirement kind:

| kind | after 1 | after 2 | after 3 | after 4 |
|---|---|---|---|---|
| before | 100% [100, 100] | 100% [100, 100] | 100% [100, 100] | 100% [100, 100] |
| conditional | 94% [81, 100] | 88% [69, 100] | 88% [69, 100] | 81% [62, 94] |
| depends | 98% [95, 100] | 98% [95, 100] | 98% [95, 100] | 98% [95, 100] |
| diff_worker | 98% [95, 100] | 98% [95, 100] | 98% [95, 100] | 98% [95, 100] |
| file_owner | 94% [81, 100] | 94% [81, 100] | 94% [81, 100] | 94% [81, 100] |
| not_depends | 100% [100, 100] | 100% [100, 100] | 100% [100, 100] | 100% [100, 100] |
| same_worker | 100% [100, 100] | 100% [100, 100] | 100% [100, 100] | 100% [100, 100] |
| setting_eq | 97% [91, 100] | 97% [91, 100] | 97% [91, 100] | 97% [91, 100] |
| worker_eq | 100% [100, 100] | 100% [100, 100] | 100% [100, 100] | 100% [100, 100] |

Revised facts (notes contain a withdrawn draft value) labelled distorted, all depths: 0% [0, 0]

## 2. Requirement satisfaction in the first plan, before any supervision

B first attempt = the executor sees only the brief (depth 0 = full notes = group A). C first attempt = same brief plus the host ledger, before any rejection.

| cond | requirements | depth 0 | depth 1 | depth 4 |
|---|---|---|---|---|
| B | fact | 100% [100, 100] | 97% [91, 100] | 97% [91, 100] |
| B | relation | 100% [100, 100] | 100% [100, 100] | 99% [97, 100] |
| B | unformalized | 100% [100, 100] | 98% [96, 100] | 96% [93, 99] |
| C | fact | 100% [100, 100] | 100% [100, 100] | 100% [100, 100] |
| C | relation | 100% [100, 100] | 100% [100, 100] | 100% [100, 100] |
| C | unformalized | 100% [99, 100] | 98% [95, 100] | 98% [95, 100] |

fact and relation rows cover the 12 formalized requirements; unformalized covers the 4 the ledger never sees.

B first attempt, violation rate when the judge said the brief kept the requirement: 0% [0, 1]; when distorted or lost: 47% [0, 72].

## 3. Supervision outcomes (H1, H2)

delivered = Root approved (B) or the checker passed (C). blocked = no approval after the revision cap, so nothing executes. A violation reaches execution only inside a delivered plan.

| depth | cond | runs | delivered | delivered and fully compliant | delivered with a violation | formalized violations executed per run | unformalized violations executed per run | NL corrections per run | programmatic rejections per run | LLM calls per run |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | B | 16 | 100% [100, 100] | 100% [100, 100] | 0% [0, 0] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 | 0.00 | 2.0 |
| 0 | C | 16 | 100% [100, 100] | 94% [81, 100] | 6% [0, 19] | 0.00 [0.00, 0.00] | 0.06 [0.00, 0.19] | 0.00 | 0.00 | 1.0 |
| 1 | B | 16 | 100% [100, 100] | 100% [100, 100] | 0% [0, 0] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.19 | 0.00 | 2.4 |
| 1 | C | 16 | 100% [100, 100] | 88% [69, 100] | 12% [0, 31] | 0.00 [0.00, 0.00] | 0.31 [0.00, 0.75] | 0.00 | 0.06 | 1.1 |
| 4 | B | 16 | 100% [100, 100] | 100% [100, 100] | 0% [0, 0] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.31 | 0.00 | 2.6 |
| 4 | C | 16 | 100% [100, 100] | 88% [69, 100] | 12% [0, 31] | 0.00 [0.00, 0.00] | 0.31 [0.00, 0.75] | 0.00 | 0.06 | 1.1 |

B Root natural-language review: approved a plan that still had a violation in 0% [0, 0] of flawed plans; withheld approval from a fully correct plan in 0% [0, 0] of correct plans.

Checker detection of formalized non-conditional violations (sanity check, expected 100%): n/a.
Formalized conditionals violated by acceptance but passed by the literal checker (antecedent made false by dropping the pinned value): n/a of conditional violations.

## 4. Planning autonomy (H3)

Free choices = settings, file owners and worker assignments no requirement touches. Diversity = mean share of free choices on which two independent samples of the same task differ. If the constraint layer took over planning, C diversity would collapse relative to A.

| plans | depth | sample pairs | free-choice diversity |
|---|---|---|---|
| A (single agent, first plan) | 0 | 8 | 59% [54, 65] |
| B delivered | 0 | 8 | 59% [54, 65] |
| B delivered | 1 | 8 | 72% [66, 78] |
| B delivered | 4 | 8 | 68% [60, 76] |
| C delivered | 0 | 8 | 59% [53, 65] |
| C delivered | 1 | 8 | 64% [57, 71] |
| C delivered | 4 | 8 | 60% [56, 66] |

Redesign footprint (share of free choices changed between first and last attempt, runs with at least one revision): B 6% [0, 25] over 8 runs; C 4% [2, 7] over 2 runs.
Authorship: every delivered plan is the executor's own JSON output. The checker only returns ledger rows and the values it found; it never writes or edits a plan (see run.py, run_loop).

## Cost

LLM calls: 290. Input tokens: 1,146,551. Output tokens: 1,669,824.
Infrastructure failures (excluded): 0.