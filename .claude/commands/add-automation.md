Create new automation for: $ARGUMENTS

## Checklist
1. Define automation in `core/automations/`
2. Create Pydantic schema
3. Implement trust gate conditions
4. Add Celery task
5. Create API endpoint
6. Write tests (90%+ coverage)
7. Add integration test

## Trust Requirements
- Minimum signal health threshold
- Data freshness requirement
- Anomaly tolerance
- Manual override capability
- Audit logging
