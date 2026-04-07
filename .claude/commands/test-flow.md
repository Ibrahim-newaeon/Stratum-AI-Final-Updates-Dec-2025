Test end-to-end automation flow: $ARGUMENTS

## Test Sequence
1. Setup fixtures and mocks
2. Signal collection test
3. Trust gate evaluation test
4. Automation execution test
5. Full E2E test

```bash
pytest tests/e2e/test_flows.py -k "$ARGUMENTS" -v --cov
```

## Verify
- All tests pass
- Coverage >= 90%
- No type errors
