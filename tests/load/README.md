# Stratum AI Load Testing

This directory contains k6 load testing scripts for the Stratum AI platform API.

## Prerequisites

### Install k6

**macOS:**
```bash
brew install k6
```

**Windows:**
```powershell
# Using Chocolatey
choco install k6

# Using winget
winget install k6
```

**Linux (Debian/Ubuntu):**
```bash
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6
```

**Docker:**
```bash
docker pull grafana/k6
```

## Test Files

| File | Description |
|------|-------------|
| `api-load-test.js` | Main API load testing script covering health, auth, and business endpoints |

## Test Scenarios

The load test script includes multiple scenarios that can be selected via environment variable:

### Smoke Test
Minimal load to verify system functionality.
- VUs: 1
- Duration: 1 minute
- Purpose: Quick sanity check

```bash
k6 run --env SCENARIO=smoke api-load-test.js
```

### Load Test (Default)
Typical expected production load.
- VUs: Ramps from 0 to 100
- Duration: ~16 minutes
- Stages:
  - Ramp up to 50 VUs (2m)
  - Hold at 50 VUs (5m)
  - Ramp up to 100 VUs (2m)
  - Hold at 100 VUs (5m)
  - Ramp down (2m)

```bash
k6 run api-load-test.js
# or explicitly:
k6 run --env SCENARIO=load api-load-test.js
```

### Stress Test
Push system beyond normal capacity to find breaking points.
- VUs: Ramps from 0 to 300
- Duration: ~26 minutes
- Purpose: Find system limits and observe degradation behavior

```bash
k6 run --env SCENARIO=stress api-load-test.js
```

### Spike Test
Sudden traffic spikes simulation.
- VUs: Sudden jumps to 400
- Duration: ~8 minutes
- Purpose: Test auto-scaling and recovery

```bash
k6 run --env SCENARIO=spike api-load-test.js
```

### Soak Test
Extended duration test for memory leaks and resource exhaustion.
- VUs: 50 constant
- Duration: 30 minutes
- Purpose: Detect memory leaks, connection leaks, long-running issues

```bash
k6 run --env SCENARIO=soak api-load-test.js
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BASE_URL` | `http://localhost:8000` | Target API base URL |
| `SCENARIO` | `load` | Test scenario to run |
| `TEST_EMAIL` | `admin@test-tenant.com` | Test user email for auth |
| `TEST_PASSWORD` | `TestPassword123!` | Test user password |
| `TEST_TENANT_ID` | `1` | Tenant ID for scoped endpoints |

### Example with Custom Configuration

```bash
k6 run \
  --env BASE_URL=https://api.staging.stratum.ai \
  --env SCENARIO=load \
  --env TEST_EMAIL=load-test@example.com \
  --env TEST_PASSWORD=SecurePassword123! \
  --env TEST_TENANT_ID=42 \
  api-load-test.js
```

## Thresholds

The tests enforce the following performance thresholds:

| Metric | Threshold | Description |
|--------|-----------|-------------|
| `http_req_duration p(95)` | < 500ms | 95th percentile response time |
| `http_req_duration p(99)` | < 1000ms | 99th percentile response time |
| `http_req_failed` | < 1% | Overall error rate |
| `health_check_duration p(95)` | < 200ms | Health check response time |
| `login_duration p(95)` | < 1000ms | Login response time |
| `emq_score_duration p(95)` | < 500ms | EMQ score endpoint response time |
| `campaigns_duration p(95)` | < 500ms | Campaigns list response time |
| `errors` | < 1% | Custom error rate |
| `auth_errors` | < 5% | Authentication error rate |

## Endpoints Tested

### Health Endpoints
- `GET /health` - Main health check
- `GET /health/ready` - Readiness probe
- `GET /health/live` - Liveness probe

### Authentication
- `POST /api/v1/auth/login` - User login

### EMQ Endpoints
- `GET /api/v1/tenants/{id}/emq/score` - EMQ score
- `GET /api/v1/tenants/{id}/emq/confidence` - Confidence band details
- `GET /api/v1/tenants/{id}/emq/playbook` - Fix playbook
- `GET /api/v1/tenants/{id}/emq/autopilot-state` - Autopilot state

### Campaign Endpoints
- `GET /api/v1/campaigns` - List campaigns
- `GET /api/v1/campaigns/{id}` - Get campaign details

## Running with Docker

If you don't want to install k6 locally:

```bash
# Linux/macOS
docker run --rm -i \
  -v $(pwd):/scripts \
  -e BASE_URL=http://host.docker.internal:8000 \
  grafana/k6 run /scripts/api-load-test.js

# Windows PowerShell
docker run --rm -i `
  -v ${PWD}:/scripts `
  -e BASE_URL=http://host.docker.internal:8000 `
  grafana/k6 run /scripts/api-load-test.js
```

## Output and Results

### Console Output
By default, k6 outputs results to the console with a summary after completion.

### JSON Output
Results are automatically saved to a JSON file with the naming pattern:
```
load-test-results-{scenario}-{timestamp}.json
```

### InfluxDB + Grafana (Recommended for CI/CD)

For continuous monitoring, send results to InfluxDB:

```bash
k6 run --out influxdb=http://localhost:8086/k6 api-load-test.js
```

### Cloud Monitoring with k6 Cloud

```bash
k6 cloud api-load-test.js
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Load Tests

on:
  schedule:
    - cron: '0 2 * * *'  # Run nightly at 2 AM
  workflow_dispatch:

jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install k6
        run: |
          sudo gpg -k
          sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
          echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
          sudo apt-get update
          sudo apt-get install k6

      - name: Run smoke test
        run: k6 run --env SCENARIO=smoke --env BASE_URL=${{ secrets.API_URL }} tests/load/api-load-test.js

      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: load-test-results
          path: load-test-results-*.json
```

## Interpreting Results

### Healthy Results
- All thresholds passing (green checkmarks)
- Error rate below 1%
- p95 response times under 500ms
- Consistent request rate

### Warning Signs
- Threshold failures
- Error rate increasing over time
- Response times degrading under load
- Requests per second plateauing

### Stress Test Indicators
- Find the VU count where errors start
- Note the response time at different load levels
- Identify recovery time after load reduction

## Troubleshooting

### Common Issues

**Connection Refused:**
- Ensure the API server is running
- Check BASE_URL is correct
- Verify firewall/network settings

**High Error Rate:**
- Check API logs for errors
- Verify test credentials are valid
- Ensure database connections are available

**Timeout Errors:**
- Increase timeout settings in k6
- Check for database bottlenecks
- Review API endpoint complexity

**Rate Limiting:**
- Reduce VU count
- Add longer sleep times between requests
- Whitelist test IP if possible

## Further Reading

- [k6 Documentation](https://k6.io/docs/)
- [k6 Thresholds](https://k6.io/docs/using-k6/thresholds/)
- [k6 Scenarios](https://k6.io/docs/using-k6/scenarios/)
- [Load Testing Best Practices](https://k6.io/docs/testing-guides/api-load-testing/)
