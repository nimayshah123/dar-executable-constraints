# Relay experiment results

Folder: `results/summary_s4_compacted_root`. Tasks: 8. Chains: 16. Supervision loops: 64. Intervals are 95% cluster bootstrap over tasks.

## 1. What survives each handoff (brief audit by judge model)

| class | handoffs | kept | distorted | lost | unlabeled |
|---|---|---|---|---|---|
| fact | 1 | 55% [48, 61] | 0% [0, 0] | 45% [39, 52] | 0 |
| fact | 2 | 41% [32, 48] | 0% [0, 0] | 59% [52, 68] | 0 |
| fact | 3 | 33% [26, 41] | 0% [0, 0] | 67% [59, 74] | 0 |
| fact | 4 | 33% [26, 41] | 0% [0, 0] | 67% [59, 74] | 0 |
| relation | 1 | 35% [30, 39] | 0% [0, 0] | 65% [61, 70] | 0 |
| relation | 2 | 33% [28, 38] | 0% [0, 1] | 66% [61, 72] | 0 |
| relation | 3 | 33% [28, 38] | 0% [0, 1] | 66% [61, 72] | 0 |
| relation | 4 | 33% [28, 38] | 0% [0, 1] | 66% [61, 72] | 0 |

Mean brief length (words) by handoff: 1: 141, 2: 138, 3: 135, 4: 135

Kept rate by requirement kind:

| kind | after 1 | after 2 | after 3 | after 4 |
|---|---|---|---|---|
| before | 73% [61, 86] | 73% [61, 86] | 73% [61, 86] | 73% [61, 86] |
| conditional | 5% [1, 9] | 5% [1, 9] | 5% [1, 9] | 5% [1, 9] |
| depends | 5% [0, 16] | 5% [0, 16] | 5% [0, 16] | 5% [0, 16] |
| diff_worker | 50% [33, 70] | 44% [23, 67] | 44% [23, 67] | 44% [23, 67] |
| file_owner | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] | 0% [0, 0] |
| not_depends | 97% [92, 100] | 97% [92, 100] | 97% [92, 100] | 97% [92, 100] |
| same_worker | 36% [16, 59] | 33% [12, 58] | 33% [12, 58] | 33% [12, 58] |
| setting_eq | 76% [73, 80] | 49% [37, 61] | 33% [25, 42] | 33% [25, 42] |
| worker_eq | 66% [44, 84] | 66% [44, 84] | 66% [44, 84] | 66% [44, 84] |

Revised facts (notes contain a withdrawn draft value) labelled distorted, all depths: 0% [0, 0]

## 2. Requirement satisfaction in the first plan, before any supervision

B first attempt = the executor sees only the brief (depth 0 = full notes = group A). C first attempt = same brief plus the host ledger, before any rejection.

| cond | requirements | depth 1 | depth 4 |
|---|---|---|---|
| B | fact | 58% [51, 64] | 40% [32, 46] |
| B | relation | 47% [43, 51] | 45% [42, 49] |
| B | unformalized | 47% [43, 52] | 39% [34, 43] |
| Bc | fact | 58% [51, 64] | 40% [32, 46] |
| Bc | relation | 47% [43, 51] | 45% [42, 49] |
| Bc | unformalized | 47% [43, 52] | 39% [34, 43] |

fact and relation rows cover the 12 formalized requirements; unformalized covers the 4 the ledger never sees.

B first attempt, violation rate when the judge said the brief kept the requirement: 1% [0, 1]; when distorted or lost: 88% [85, 90].

## 3. Supervision outcomes (H1, H2)

delivered = Root approved (B) or the checker passed (C). blocked = no approval after the revision cap, so nothing executes. A violation reaches execution only inside a delivered plan.

| depth | cond | runs | delivered | delivered and fully compliant | delivered with a violation | formalized violations executed per run | unformalized violations executed per run | NL corrections per run | programmatic rejections per run | LLM calls per run |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | B | 16 | 100% [100, 100] | 100% [100, 100] | 0% [0, 0] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 1.25 | 0.00 | 4.5 |
| 1 | Bc | 16 | 100% [100, 100] | 0% [0, 0] | 100% [100, 100] | 22.88 [20.69, 25.38] | 8.44 [7.75, 9.12] | 0.12 | 0.00 | 2.2 |
| 4 | B | 16 | 100% [100, 100] | 100% [100, 100] | 0% [0, 0] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 1.00 | 0.00 | 4.0 |
| 4 | Bc | 16 | 100% [100, 100] | 0% [0, 0] | 100% [100, 100] | 22.62 [20.62, 24.81] | 8.00 [7.31, 8.62] | 0.69 | 0.00 | 3.4 |

B Root natural-language review: approved a plan that still had a violation in 0% [0, 0] of flawed plans; withheld approval from a fully correct plan in 0% [0, 0] of correct plans.

Bc Root natural-language review: approved a plan that still had a violation in 71% [68, 76] of flawed plans; withheld approval from a fully correct plan in n/a of correct plans.

Checker detection of formalized non-conditional violations (sanity check, expected 100%): n/a.
Formalized conditionals violated by acceptance but passed by the literal checker (antecedent made false by dropping the pinned value): n/a of conditional violations.

## 4. Planning autonomy (H3)

Free choices = settings, file owners and worker assignments no requirement touches. Diversity = mean share of free choices on which two independent samples of the same task differ. If the constraint layer took over planning, C diversity would collapse relative to A.

| plans | depth | sample pairs | free-choice diversity |
|---|---|---|---|
| B delivered | 1 | 8 | 73% [68, 79] |
| B delivered | 4 | 8 | 73% [66, 80] |
| Bc delivered | 1 | 8 | 73% [67, 80] |
| Bc delivered | 4 | 8 | 74% [67, 80] |

Redesign footprint (share of free choices changed between first and last attempt, runs with at least one revision): B 6% [4, 7] over 32 runs; Bc 0% [0, 0] over 13 runs.
Authorship: every delivered plan is the executor's own JSON output. The checker only returns ledger rows and the values it found; it never writes or edits a plan (see run.py, run_loop).

## Cost

LLM calls: 354. Input tokens: 1,309,352. Output tokens: 1,278,869.
Infrastructure failures (excluded): 0.