FBS rejection-path tests, run by Nimay on 2026-11-08
Repo: https://github.com/zionlinne/feasibility-scheduler  PR #5 head 7630497
Python 3.12.4 (3.10 and 3.11 fail at import: acceptance.py uses a MappingProxyType dataclass default,
which is only hashable from 3.12; pyproject declares requires-python >=3.10)
Command: python -m pytest tests/test_contract_plan.py tests/test_acceptance_profile.py tests/test_contract_runtime.py
         tests/test_modular_planner.py tests/test_integration_stage.py tests/test_external_scopes.py
         tests/test_module_execution.py tests/test_root_integration.py -q -rA
Result: 132 passed in 64.01s
