# FBS log analysis

Readings of the recorded FBS runs shared by the FBS author: the 3 November baseline run and the two 7 November scoped prompt rounds. Nothing here is a new FBS run, except the unit test record.

| File | What it is |
|---|---|
| `supervision_inventory.md` | The 84 rules given to an agent in the 3 November run, by channel (FBS to Root, FBS to Workers, Root plan to Workers), with the strongest control that enforces each: Blocked by code, Field check only, Caught at root, or Prompt only. 39 of 84 (46%) are prompt only, including 19 of the 23 rules the plan gave Workers. One of those, a duplicated validation, was broken in all three recorded runs while every test passed. |
| `evaluation_records_three_runs.md` | The team's evaluation record template, filled in for the 3 November run and the two 7 November rounds. |
| `timing_findings.md`, `timing_tables.md` | Where the 7 November speedup came from: Worker stages took 32 s longer in total, while Root owned steps fell from 195 s to 14 s. The run drivers submit prepared drafts, so step times are submission times; an independent replication with live agents has not been run. |
| `analyze_speedup.py` | Recomputes `timing_tables.md` from the two 7 November evidence archives (stdlib only). The archives are the FBS author's and are not included. |
| `fbs_unit_tests/` | FBS's own rejection path tests at PR #5 head 7630497: 132 passed on Python 3.12. The package declares Python 3.10 but fails to import on 3.10 and 3.11. |

The inventory and timing tables are also in `data/fbs_logs/` as CSV.

```
python analyze_speedup.py --before <Before_Modification_EN.zip> --after <After_Modification_EN.zip>
```
