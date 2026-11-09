FBS 7630497, Node v25.8.1

| Fault | What was planted | Nov 3 enforcement | Result | Check that fired | Run accepted |
|---|---|---|---|---|---|
| as-run clean | Nov 3 files as delivered |  | Accepted | no fault planted; run accepted | yes |
| as-run P1 | Two modules own the same file (lib/base.mjs) | Blocked by code | Blocked at plan | ValueError: decomposition must preserve artifact ownership exactly | no |
| as-run P2 | A TASK line (R177, the hidden test scenarios) is left without any check | Blocked by code | Blocked at plan | ValueError: uncovered source requirements: ['R177'] | no |
| as-run P3 | A module owns a path outside the workspace (../views.mjs) | Blocked by code | Blocked at plan | ValueError: decomposition must preserve artifact ownership exactly | no |
| as-run P4 | Root replaces the independent suite with file existence checks | Blocked by code | Blocked at plan | ValueError: acceptance category build: check exists:lib/base.mjs has insufficient evidence kind file_exists | no |
| as-run P5 | Root edits the host acceptance profile (functional tests marked not applicable) | Blocked by code | Blocked at plan | ValueError: planner changed the host acceptance profile | no |
| as-run P6 | Dependency cycle (foundation waits for transports) | Blocked by code | Blocked at plan | CycleError: 检测到环形依赖: exchange-views -> foundation -> transports -> exchange-views | no |
| as-run D1 | Worker omits one of its files (lib/views.mjs) | Blocked by code | Blocked at delivery | exchange-views: functional work unit must deliver all current owned files in one response | yes |
| as-run D2 | Worker also writes a sibling's file (lib/base.mjs with a loosened limit) | Blocked by code | Blocked at delivery | fulfillment: functional work unit must deliver all current owned files in one response | yes |
| as-run D3 | Worker writes outside the workspace (../../escape.mjs) | Blocked by code | Blocked at delivery | merchandising: functional work unit must deliver all current owned files in one response | yes |
| as-run D4 | Worker delivers code that does not parse | Blocked by code | Blocked at delivery | merchandising: node --check 失败 lib/catalog.mjs: D:\dar_planted_faults\runs\as-run-D4\run\workspace\lib\catalog.mjs:20 } ^ SyntaxError: Unexp... | yes |
| as-run B1 | Duplicate lot id returns INVALID_STATE instead of ALREADY_EXISTS (R96, R47) | Caught at root | Caught at root | official suite failed: public-rollback-keeps-clock-audit-cache-and-state, public-http-flow-real-socket-restart-and-cli, stock-adjust-move-di... | no |
| as-run B2 | Quote accepts an inactive SKU (R106) | Caught at root | Caught at root | official suite failed: reference-business-state-errors-and-partial-allocation-rollback | no |
| as-run B3 | Commit overwrites the state file in place, without temp file, rename or fsync (R63 crash safety) | Caught at root | Missed | no check fired; run accepted | yes |
| as-run B4 | A corrupt store is silently reset to empty instead of STORE_CORRUPT (R61) | Caught at root | Missed | no check fired; run accepted | yes |
| as-run C1 | Catalog repeats price validation that base owns (C3, no duplicated logic) | Prompt only | Missed | no check fired; run accepted | yes |
| as-run C2 | Catalog imports views (I14, only engine and transports may) | Prompt only | Missed | no check fired; run accepted | yes |
| as-run C3 | A handler writes its own audit record (I3, the engine is the only audit writer) | Prompt only | Missed | no check fired; run accepted | yes |
| as-run C4 | CSV import creates lots itself instead of calling fulfillment (I10, one owner of lot changes) | Prompt only | Missed | no check fired; run accepted | yes |
| as-run C5 | Inventory report sorts ids with localeCompare (R79, no locale order) | Prompt only | Caught at root | official suite failed: FEFO-expiry-priority-warehouse-lot-ASCII-null | no |
| formalized clean | Nov 3 files as delivered |  | Caught at root | rule:base-owns-validation: Business modules do not repeat structural validation that base owns; violated at lib/fulfillment.mjs:8 | no |
| formalized fixed | Nov 3 files, duplicated check removed |  | Accepted | no fault planted; run accepted | yes |
| formalized B3 | Commit overwrites the state file in place, without temp file, rename or fsync (R63 crash safety) | Caught at root | Missed | no check fired; run accepted | yes |
| formalized B4 | A corrupt store is silently reset to empty instead of STORE_CORRUPT (R61) | Caught at root | Caught at root | behavior:store-corrupt: A corrupt store is reported as STORE_CORRUPT and never silently reset; corrupt store answered ok=True code=None | no |
| formalized C1 | Catalog repeats price validation that base owns (C3, no duplicated logic) | Prompt only | Caught at root | rule:base-owns-validation: Business modules do not repeat structural validation that base owns; violated at lib/catalog.mjs:17 | no |
| formalized C2 | Catalog imports views (I14, only engine and transports may) | Prompt only | Caught at root | rule:views-import-boundary: Only the engine and transports import views; violated at lib/catalog.mjs:1 | no |
| formalized C3 | A handler writes its own audit record (I3, the engine is the only audit writer) | Prompt only | Caught at root | rule:single-audit-writer: Only the engine writes audit records; violated at lib/fulfillment.mjs:26 | no |
| formalized C4 | CSV import creates lots itself instead of calling fulfillment (I10, one owner of lot changes) | Prompt only | Caught at root | rule:single-lot-owner: Only fulfillment creates lots or changes lot quantities; violated at lib/interchange.mjs:58 | no |
| formalized C5 | Inventory report sorts ids with localeCompare (R79, no locale order) | Prompt only | Caught at root | official suite failed: FEFO-expiry-priority-warehouse-lot-ASCII-null | rule:no-locale-order: No locale dependent ordering; violated at lib/v... | no |
