---
description: Run end-to-end automation flow tests matching a name or feature
argument-hint: <test_name_pattern>
allowed-tools: Bash(pytest:*), Bash(make:*), Read, Grep
---

Test end-to-end automation flow: $ARGUMENTS

## Test Sequence

1. Setup fixtures and mocks
2. Signal collection test
3. Trust gate evaluation test
4. Automation execution test
5. Full E2E test

```bash
pytest backend/tests/e2e/test_flows.py -k "$ARGUMENTS" -v --cov=backend/app --cov-report=term-missing
```

## Verify

- All tests pass
- Coverage >= 90% for `core/`, `autopilot/`, `analytics/`
- No type errors: `make lint`
- No flaky tests (run twice if any non-deterministic timing)
