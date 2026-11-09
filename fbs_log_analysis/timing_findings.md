# Where the scoped-prompt speedup came from

Evidence: Before_Modification_EN.zip (run 01, original long context) and After_Modification_EN.zip (runs 02 and 03, scoped prompts). All numbers come from the saved native requests/responses and scheduler timelines. Reproduce with `python analyze_speedup.py --before <Before zip> --after <After zip>` (stdlib only), which writes `timing_tables.md`.

**Note added after reading the run drivers.** The three run drivers in the shared evidence answer each Worker and Root module request by submitting files already written to a drafts folder, and answer the planning request with a plan written before the run starts (built in the driver for run 01, loaded from the 3 November plan for runs 02 and 03). A step time in these logs is therefore the time an answer was submitted, not the time a model took to write it. That explains the 5.6 s transports step and the 9.4 s plan below. The timing tables stand as readings of the logs; the conclusion that Root did its work off the clock needs an independent replication with live agents, which has not been run.

## Short answer

The prompt got smaller and the run got faster, but one did not cause the other. These are two separate mechanisms.

1. **The prompt reduction is mechanical.** Total Worker prompt size fell from 374K to 149K characters (-60%). Cache hits and context reuse play no part. The scoped renderer stopped attaching three things to every Worker:
   - **Public test fixtures:** 33K characters per Worker, 74% of the cut.
   - **The full 15K-character task:** each Worker now gets only its own slice, 24 to 50% of the task, copied 96 to 99% verbatim. That is 22% of the cut.
   - **The shared verification contract:** replaced by a 1 to 2K-character API contract. That is 9% of the cut.

   Dependency code in the prompts actually grew by 32%.
2. **The speedup came from Root, not the Workers.**
   - Worker stages took 32 s longer in total. The three-way business batch went from 58 s to 182 s, because scoped Workers started cold and wrote 47 to 87% more code.
   - Root-owned steps took 180 s less: 194.6 s became 14.3 s. That is more than the whole 149 s saving.
   - Root's `transports` module came back as 8,444 characters of new code in 5.6 s, or 1,519 chars/s. Every Worker response in these logs arrives at 34 to 164 chars/s. So that code was written before its request arrived: Root built its own module against the API contract it had authored, in parallel with the Workers.
3. **Root could keep reusing its context after the format change because the change only touched Worker prompts.**
   - Root writes those prompts; it does not read them back as input.
   - Root's own inputs were identical across runs: the same task (sha256 d9d25668...), the same module boundaries, owned files, requirement IDs and verifier, plus its retained chat context.
   - The "new format" is mostly a selection of the same text, so nothing Root knew went stale.

## Evidence

### Timing by owner (seconds)

| stage | 01 original | 02 scoped | 03 scoped | 02 minus 01 |
|---|---|---|---|---|
| plan (Root) | 9.4 | 0 (Root supplied it) | 0 | -9.4 |
| foundation (Worker) | 231.0 | 138.2 | 133.3 | -92.9 |
| business batch x3 (Workers) | 58.0 | 182.4 | 184.2 | +124.5 |
| transports (Root) | 164.9 | 5.6 | 10.8 | -159.3 |
| integration (Root) | 20.3 | 8.7 | 23.8 | -11.6 |
| final acceptance (host, no model) | 43.0 | 42.4 | 47.3 | -0.6 |
| **total** | **528.2** | **378.8** | **401.0** | **-149.4** |
| Root-owned steps | 194.6 | 14.3 | 34.6 | -180.3 |
| Worker steps | 289.0 | 320.6 | 317.5 | +31.6 |

- **Integration took no new generation.** In all three runs the integration response is byte-identical to the transports response.
- **The run 01 plan was also pre-written.** It returned 31K characters in 9.4 s, about 3,300 chars/s, so in run 01 it was already done off the clock too.

### Why caching cannot explain it

- **No shared prefix.** Run 01 and run 02 Worker prompts share 0 characters of prefix, so an exact-prefix (KV/prompt) cache cannot hit across that change.
- **No inherited history.** Scoped Workers were new contexts (`workers_inherit_conversation: false` in source-manifest.json).
- **Round 1 to round 2 does share prefixes,** of 5.8K to 12.1K characters. Round 2 Workers were still no faster in practice: 317.5 s vs 320.6 s in total.
- **Root did not copy code either.** Root's transports files are 0.06 to 0.11 similar, line by line, between run 01 and run 02. The reuse is of design (the interface contract Root wrote), not of text.

### Smaller prompts did not make Workers faster

Worker latency tracked how much code each Worker wrote (`timing_tables.md` section 3), not prompt length:

| Worker | prompt (01 to 02) | code written (01 to 02) | time (01 to 02) |
|---|---|---|---|
| fulfillment | 72K to 26K | 8.2K to 12.0K | 50 s to 164 s |
| exchange-views | 72K to 26K | 6.6K to 9.9K | 58 s to 182 s |
| catalog | 72K to 23K | 2.4K to 4.4K | 52 s to 102 s |

Likely reason for run 01's fast batch (an inference, not logged): run 01 used three long-lived native Workers.
- foundation and catalog shared one Worker (producer `empty_base_catalog` on both requests). That Worker could have drafted catalog during the 231 s foundation step.
- The fulfillment and exchange Workers delivered at 164 and 113 chars/s, above any cold start in these logs.
- The scoped runs created all four Workers fresh at dispatch.

## So, does formalization reduce dependency overhead?

Partly yes, through a different route than prompt length.
- **What actually moved:** once Root owns a small formal interface contract (REQUIRED API CONTRACT, about 1 to 2K characters per Worker), the Root module that depends on the Workers no longer has to wait for their code. Root wrote `transports` against the contract while the Workers ran, which took 159 s off the critical path.
- **What the scheduler still did:** it kept the DAG edge and dispatched transports after the batch. The work itself had already happened in parallel.
- **What the timeline cannot see:** that work happens off the clock, so the timeline cannot record it.

## Caveats

- **Token usage was not measured.** The `estimated_input_tokens` field is utf8-bytes/3, and run 01's final composition step uses a synthetic `fake-000001` response.
- **Root's own compute is invisible.** These logs only show when a response file appeared, so Root's pre-work is not measured and its cost is not counted in the 378.8 s.
- **One run per arm, and the arms differ in more than prompts.** Runs 01 and 02 differ in Worker count and lifetime (3 long-lived vs 4 fresh), in run date (3 vs 7 November), and in Root's prior experience with the task.
- **Run-to-run noise is non-trivial.** The scoped round 1 vs round 2 gap is 22 s (6%).

## Test that would settle it

1. **Put Root on the clock.** Log when Root starts writing its own module, or make transports a Worker task, and compare stage times again.
2. **Ablate the renderer one component at a time on fresh Workers.** Run the full prompt, then without the fixtures, then with the task slice in place of the full task, then with the API contract in place of the shared contract. Run at least 3 seeds per arm and record real input/output token usage.
3. **Cross Worker lifetime (long-lived vs fresh) with prompt format.** This separates the head-start effect from the prompt effect.
