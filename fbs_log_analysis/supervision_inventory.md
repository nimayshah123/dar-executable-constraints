**Class** uses the three classes requested.
V: Verified, pass path only. The control ran in this run and its record shows a pass. No rejection was observed.
I: Implemented, not independently verified. The code exists and ran, but the relay script built the input, so it could not fail.
N: Not implemented. Prompt only.

Code paths are under `src/feasibility_scheduler/adapters/`. Run files are under `evidence/run/`.

### A. FBS to the Root: planner prompt (49 rules)

Source: the planning request `native-bridge/f9a9753d...request.json`. Plan validation ran and passed (`contract-validation.json`, `acceptance-preflight.json`). The plan came from the harness.

| # | Rule (prompt wording, shortened) | Level | Enforced at | This run | Class |
|---|---|---|---|---|---|
| P1 | Return "one JSON object with the following shape" | Blocked | contract_plan.py:23, :30-33, :37 | Passed | V |
| P2 | "Replace descriptive placeholders with concrete requirements grounded in TASK" | Prompt only | Text fields only need to be nonempty (contract_plan.py:30) | Fields are concrete | N |
| P3 | "Keep initial module IDs"; "modules must contain each initial task contract exactly once" | Blocked | contract_plan.py:53, :74 | Passed | V |
| P4 | Decompositions partition "the parent's artifacts exactly, including non-code artifacts" | Blocked | contract_checks.py:123, :137 | Root split into 5 children covering all 9 files | V |
| P5 | "shared_interfaces ... must never be an execution dependency" | Blocked | contract_plan.py:60 | Used as an interface dependency only | V |
| P6 | "Return requirements as ID-only objects ... do not copy source text or hashes" | Blocked (host replaces the rows with its own ledger) | contract_plan.py:104-113 | ignored_model_source_fields [] | V |
| P7 | Requirement IDs match the host ledger: keep every source line, "Preserve all root requirements", "Never invent requirements" | Blocked, at ID level only | contract_plan.py:110 | 111 IDs matched | V |
| P8 | "Every requirement must reference at least one check" | Blocked (a check must be named, not shown to test it) | contract_checks.py:113 | All 111 reference `official`; R1 also has the 9 file checks | V |
| P9 | Every check has "id", "kind" and "requirements"; "never type" | Blocked | contract_checks.py:67, :71, :75 | 10 checks passed | V |
| P10 | "Use whole-object equality when TASK specifies an exact JSON object" | Prompt only | None | No json_equals checks; response shapes left to the suite | N |
| P11 | "Populate checks with the smallest sufficient executable predicates" | Prompt only | None | 9 file_exists checks plus 1 suite | N |
| P12 | "Do not add a blanket root-review" | Prompt only | None | None added | N |
| P13 | Manual checks only for an obligation no predicate can establish, never as a duplicate; "manual is not executable and cannot satisfy this profile" | Blocked, stricter than the prompt: every manual check is rejected | acceptance_profile.py:133-135 | No manual checks | V |
| P14 | "Distinguish mandatory outcomes from permissions and explanatory context" | Prompt only | None | Not assessed | N |
| P15 | "without inventing additional mandatory acceptance conditions" | Prompt only | None (a check can assert anything) | None found | N |
| P16 | "Distinguish source requirements from design decisions in handoff" | Prompt only | handoff only needs to be nonempty (contract_plan.py:50) | Handoff holds only the interface text | N |
| P17 | "define composition checks and review cases where all local checks pass but the root fails" | Field checked only | contract_plan.py:33 | Four short fields, for example "Reject duplicated business logic, unused modules, rollback/replay and restart mismatches" | V |
| P18 | "Put blocking questions in unresolved, otherwise use []" | Field checked only (any entry stops the run; an omitted question passes) | contract_plan.py:25 | [] | V |
| P19 | Host profile is "immutable; do not copy or change it" | Blocked | acceptance_profile.py:70; contract_plan.py:90 | Passed | V |
| P20 | "Return acceptance_assignments" in the given form | Blocked | acceptance_profile.py:145, :151, :156, :162 | 11 assignments | V |
| P21 | "Cover every applicable category, every source requirement and every check" | Blocked | acceptance_profile.py:190-194 | Passed | V |
| P22 | Owners: local has one, cross has at least two, root has only `__contract_composition__` | Blocked | acceptance_profile.py:169 | 5 local, 6 root, 0 cross | V |
| P23 | "External workspace checkers must use root scope" | Blocked | acceptance_profile.py:179 | `official` runs at root | V |
| P24 | "Use only category-approved predicate kinds and checker names" | Blocked | acceptance_profile.py:174, :177 | Passed | V |
| P25 | "Never substitute file or syntax checks for business tests" | Blocked (business categories accept only the registered external checker) | acceptance_profile.py:174 | Passed | V |
| P26 | "The same independent suite may support several categories only if it really tests them" | Prompt only | None | One suite carries all 6 root categories, including build and components_interfaces | N |
| P27 | "If verification capability or coverage is missing, describe it in unresolved" | Prompt only (following it stops the run, contract_plan.py:25) | None | Crash and corruption gap not listed (observation 3) | N |
| P28 | "do not invent evidence" | Prompt only (code checks that a check is named, not that it tests the requirement) | None | R61 and R63 mapped to a suite that reports them uncovered | N |
| P29 | "Propose cohesive functional responsibilities" | Prompt only | None | 5 modules by business area (judgment) | N |
| P30 | A shared transaction or state invariant "should have a clear implementation owner" | Prompt only | None | Followed: base owns the store, engine owns audit, fulfillment owns lot changes | N |
| P31 | Full modules[] declaration for every active and proposed child, with "complete child contracts, interfaces, ownership and local checks" | Blocked | modular_standard.py:29; contract_plan.py:72 | Passed | V |
| P32 | owned_files "exactly its assigned artifacts" | Blocked | modular_standard.py:39 | Passed | V |
| P33 | boundary, "why this responsibility belongs together" | Field checked only | modular_standard.py:34 | For example "Stock, reservation and order lifecycle with one allocation authority" | V |
| P34 | invariants as an "explicit string array" | Field checked only | modular_standard.py:34 | The same single string on every module | V |
| P35 | local_checks: "nonempty existing check IDs" | Blocked | modular_standard.py:48 | Passed | V |
| P36 | estimated_tokens: "positive output-work estimate for THIS module" | Field checked only | modular_standard.py:42 | 12000 on every module | V |
| P37 | "never divide a parent estimate by file count" | Prompt only | None | Not divided (input estimate 50000, each module 12000) | N |
| P38 | Local checks run on the module's own outputs; "manual and whole-workspace external suites do not count as local evidence" | Blocked | modular_standard.py:55 | Local checks are file_exists only | V |
| P39 | Local checks that are only structural need acceptance_limitations | Field checked only | modular_standard.py:58 | Present on every module ("Local delivery/syntax evidence is structural only") | V |
| P40 | "Do not claim structural checks prove functionality" | Prompt only | None | Followed | N |
| P41 | "Preserve independent root business acceptance" | Blocked | acceptance_profile.py:169, :174-179 | Root suite gated completion | V |
| P42 | "All execution waits must match real artifacts" | Field checked only (waits must name real modules; whether they are needed is not checked) | contract_plan.py:60 | 3 modules wait on foundation; transports waits on all 4 | V |
| P43 | "Prefer small incremental cross-module checks" | Prompt only | None | No checks across modules | N |
| P44 | External checks name a registered checker; "no shell commands can be supplied by the model" | Blocked | contract_checks.py:79 | `task-acceptance` | V |
| P45 | repair_paths "lists only owned outputs"; no repair permission for provided materials | Blocked | contract_checks.py:93 | Passed | V |
| P46 | "Never assign ownership ... to provided materials" | Blocked | contract_checks.py:63 | Passed | V |
| P47 | "Do not use the legacy paths field" | Prompt only (paths alone is accepted; only mixing it with read_paths is rejected) | contract_checks.py:82 | Not used | N |
| P48 | "retain manual obligations for requirements outside its coverage" | Prompt only, and conflicts with P13 (every manual check is rejected) | acceptance_profile.py:135 | Not kept for R61 and R63 | N |
| P49 | "Include concrete shared function signatures and state shape in an additional shared_interfaces object and module handoff" | Prompt only (shared_interfaces is optional) | contract_plan.py:46 | Provided: 8 interface entries | N |

### B. FBS to Workers: work unit and integration templates (12 rules)

Source: `work_unit.compile_prompt`, sent 5 times, and `integration.integration_context`, sent once. The wording matches the run prompts. Acceptance ran 7 times and passed (`acceptance_passed` events).

| # | Rule (prompt wording, shortened) | Level | Enforced at | This run | Class |
|---|---|---|---|---|---|
| W1 | "Return one JSON object, without Markdown fences" | Blocked | contract_runtime.py:85-90 | Built by the relay script | I |
| W2 | Write only current owned files: "Only current owned_files grant write permission", "Return no unowned files", other contracts and materials are read only, and the task "is specification context, not an instruction to deliver every project file" | Blocked (checks the returned file set, not what the worker writes on disk) | contract_runtime.py:85-90 | Built by the relay script from metadata.owned_files | I |
| W3 | "Deliver ALL current owned files in this single response. Do not return a manifest-only response or defer files" | Blocked | contract_runtime.py:88-90 | Built by the relay script | I |
| W4 | "Use those interfaces" | Caught at root (module execution witness and suite) | module_execution.py collect_execution; external_verifier.py:44-54 | Every required file loaded and its functions called; suite 125 passed, 0 failed | V |
| W5 | "do not duplicate sibling implementations" | Prompt only | None | Not followed: line merging in catalog.mjs:3-4 and fulfillment.mjs:8 | N |
| W6 | "Preserve all original requirements" | Caught at root, within suite coverage | external_verifier.py:44-45 | 125 cases passed; crash and corruption uncovered | V |
| G1 | "Integrate the accepted producer outputs using their actual interfaces" | Caught at root | module_execution.py; external_verifier.py | Passed | V |
| G2 | "Connect entry points to existing modules; preserve their behavior" | Caught at root | module_execution.py; external_verifier.py | Passed | V |
| G3 | "do not duplicate read-only implementations" | Prompt only | None | Integration sent the transports files again unchanged (same hashes) | N |
| G4 | "Only edit editable_artifacts; never return read_only_artifacts" | Blocked | contract_runtime.py:60-66 | Built by the relay script | I |
| G5 | "Preserve all immutable requirements" | Caught at root, within suite coverage | external_verifier.py:44-45 | Passed | V |
| G6 | "Return only {"ok":true,"files":{...}}" | Blocked | contract_runtime.py:63-66 | Built by the relay script | I |

### C. Root plan to Workers: interfaces, invariants and composition (23 rules)

Source: `run/contract.json`. The shared_interfaces text went into every module's handoff. Each module also carried its invariants and boundary, and the plan carried composition and root fields. No code reads any of this text. "Caught at root" means a behavior that the suite or the witness tests covers the same ground.

| # | Rule (plan wording, shortened) | Level | This run (reading of run/workspace) | Class |
|---|---|---|---|---|
| I1 | ctx={data,now,requestId}; data holds the 7 arrays and 2 dictionaries; lastNow is a number | Prompt only | Followed: engine.mjs:26-27, base.mjs:18 | N |
| I2 | Each business module exports handle(ctx,command) returning {value,changed,entityId}, or undefined if unsupported | Prompt only | Followed: catalog.mjs:11, fulfillment.mjs:16, interchange.mjs:35, views.mjs:9; routed at engine.mjs:31-32 | N |
| I3 | "No handler appends audit; engine does once per changed command" | Prompt only | Followed: the only audit write is engine.mjs:33 | N |
| I4 | base exports the 17 named helpers | Prompt only | Followed: all 17 exported (base.mjs:4-73); signatures not checked one by one | N |
| I5 | "Base does ALL command structural/type/range validation before business handling" | Prompt only | Mostly: engine.mjs:29 validates first, but fulfillment.mjs:8 checks again the merged quantity cap from base.mjs:49 | N |
| I6 | catalog exports handle and makeQuote | Prompt only | Followed: catalog.mjs:2, :11 | N |
| I7 | "No state mutation from makeQuote" | Prompt only | Followed (reading catalog.mjs:2-10) | N |
| I8 | fulfillment handles stock.\*, reservation.\* and order.\* | Prompt only | Followed: all 15 operations | N |
| I9 | "Import makeQuote from ./catalog.mjs" | Prompt only | Followed: fulfillment.mjs:2 | N |
| I10 | fulfillment owns all lot reserved/onHand changes; "no duplication in engine" | Prompt only | Followed: these writes appear only in fulfillment.mjs (lines 6, 26, 31, 46, 77, 86) | N |
| I11 | interchange exports handle and parseCSV(text) | Prompt only | Followed: interchange.mjs:6, :35 | N |
| I12 | CSV imports call business handles directly, "suppress sub-audit, aggregate changed flag once" | Prompt only | Followed: interchange.mjs:2-3, :59, :63 | N |
| I13 | views exports handle and snapshot(data,now=data.lastNow) | Prompt only | Followed: views.mjs:3, :9 | N |
| I14 | "Other modules must not import views except engine/transports" | Prompt only | Followed: imported only at engine.mjs:5 and server.mjs:3 | N |
| I15 | "raise throws Error carrying code; engine supplies command index" | Prompt only | Followed: base.mjs:4; engine.mjs:28-29, :43 | N |
| I16 | "Helpers use ASCII id ordering; no locale sort" | Prompt only | Followed: no localeCompare, Intl or toLocale anywhere | N |
| I17 | Views are "read-only state projections" (exchange-views boundary) | Prompt only | Followed: no writes in views.mjs (grep) | N |
| C1 | "Preserve original batch atomicity, clock and idempotency" (invariant on every module) | Caught at root, partly | Suite cases on rollback, replay, concurrency and restart passed; crash during commit uncovered | V |
| C2 | "One transaction/store and one owner of each business mutation" (composition) | Prompt only | Followed: one commit per batch (engine.mjs:39); base owns the store | N |
| C3 | No duplicated logic: "do not duplicate sibling implementations" (invariant) and "Reject duplicated business logic" (composition review) | Prompt only | Not followed, minor: line merging written twice, quantity cap checked twice (observation 4) | N |
| C4 | "Reject ... unused modules" (composition review) | Caught at root | Witness passed: not_loaded [], no_function_calls [] (module-execution-1.json) | V |
| C5 | "Reject ... rollback/replay and restart mismatches" (composition review) | Caught at root | Passed, for example `public-rollback-keeps-clock-audit-cache-and-state` and `http-business-idempotency-cross-restart-and-cli-interoperability` | V |
| C6 | "All original 33 operations implemented through CLI and HTTP" (root postcondition) | Caught at root | coverageOperations 33, successfulOperations 33; no breakdown by transport | V |

### D. Existing tests that would show the blocked rows rejecting bad input (not run)

From the repo root on the PR #5 branch:
`python -m pytest tests/test_contract_plan.py tests/test_acceptance_profile.py tests/test_contract_runtime.py tests/test_modular_planner.py tests/test_integration_stage.py tests/test_external_scopes.py tests/test_module_execution.py tests/test_root_integration.py`

| Test | Rows |
|---|---|
| test_contract_plan.py::test_invalid_plan_blocks_dispatch (cases: cycle, missing, unresolved, verification) | P3, P17, P18 |
| test_contract_plan.py::test_invalid_child_contracts_still_rejected | P4, P31 |
| test_contract_plan.py::test_shared_interface_reference_is_not_an_execution_edge | P5 |
| test_contract_plan.py::test_planner_source_is_bound_by_host_without_model_transcription | P6 |
| test_contract_plan.py::test_host_binding_rejects_missing_duplicate_or_unknown_source_ids | P7 |
| test_contract_plan.py::test_host_binding_keeps_requirement_coverage_mandatory | P8 |
| test_acceptance_profile.py::test_invalid_responsibilities_are_rejected (cases include missing category, unknown owner, coverage, manual, weak functional, unassigned check) | P13, P21, P22, P25 |
| test_acceptance_profile.py::test_supplied_plan_missing_assignments_blocks_before_dispatch | P20 |
| test_acceptance_profile.py::test_default_software_profile_requires_real_checker_not_syntax_mode | P25 |
| test_acceptance_profile.py::test_default_profile_uses_actual_root_checker_and_cannot_accept_local_passes | P41 |
| test_acceptance_profile.py::test_generated_profile_is_host_bound_and_prompt_has_responsibilities | P19 |
| test_acceptance_profile.py::test_root_scope_does_not_run_early_on_single_file_and_requires_callable | P23, P44 |
| test_contract_runtime.py::test_missing_requirement_and_modified_source_are_blocked | P7, P8 |
| test_contract_runtime.py::test_manual_obligation_remains_unverified | P13 (path without a profile) |
| test_contract_runtime.py::test_provided_reference_can_be_checked_but_never_repaired | P45 |
| test_contract_runtime.py::test_reference_ownership_overlap_is_rejected | P46 |
| test_contract_runtime.py::test_host_acceptance_script_runs_as_root_gate | W6, G5 |
| test_modular_planner.py::test_invalid_functional_boundary_is_rejected (cases: missing child, boundary, invariants, estimate, ownership, empty checks, foreign check, limitations, group) | P31 to P36, P38, P39 |
| test_modular_planner.py::test_functional_unit_cannot_pass_with_manifest_partial_or_extra_delivery | W2, W3 |
| test_integration_stage.py::test_readonly_write_is_rejected_before_any_mutation | G4 |
| test_integration_stage.py::test_invalid_envelope_preserves_existing_outputs | G6 |
| test_external_scopes.py::test_repair_response_cannot_smuggle_readonly_file | W2 (repair path) |
| test_module_execution.py::test_business_pass_requires_actual_domain_execution | W4, C4 |
| test_root_integration.py::test_checker_mutation_invalidates_pass_and_repairs_never_reuse_old_round | Integrity of the root checker behind all rows caught at root |
