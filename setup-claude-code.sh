#!/bin/bash

# =============================================================================
# Claude Code Setup Script for Stratum AI
# =============================================================================
# Run this script in your Stratum AI project root:
#   chmod +x setup-claude-code.sh && ./setup-claude-code.sh
# =============================================================================

set -e

echo "🚀 Setting up Claude Code for Stratum AI..."

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# -----------------------------------------------------------------------------
# 1. Create directory structure
# -----------------------------------------------------------------------------
echo -e "${BLUE}📁 Creating directory structure...${NC}"

mkdir -p .claude/commands
mkdir -p .claude/state
mkdir -p docs/architecture
mkdir -p docs/integrations

# -----------------------------------------------------------------------------
# 2. Create CLAUDE.md
# -----------------------------------------------------------------------------
echo -e "${BLUE}📝 Creating CLAUDE.md...${NC}"

cat > CLAUDE.md << 'EOF'
# Stratum AI Platform

## Overview
Revenue Operating System with Trust-Gated Autopilot architecture.
Automation executes ONLY when signal health passes safety thresholds.

## Core Concept
```
Signal Health Check → Trust Gate → Automation Decision
       ↓                  ↓              ↓
   [HEALTHY]         [PASS]         [EXECUTE]
   [DEGRADED]        [HOLD]         [ALERT ONLY]
   [UNHEALTHY]       [BLOCK]        [MANUAL REQUIRED]
```

## Tech Stack
- **Backend**: Python 3.11+, FastAPI, Pydantic
- **Database**: PostgreSQL 15, Redis (caching/queues)
- **Queue**: Celery + Redis
- **Frontend**: React 18, TypeScript, Tailwind CSS
- **Infra**: Docker, AWS (ECS, RDS, ElastiCache)
- **Monitoring**: Prometheus, Grafana, Sentry

## Project Structure
```
/stratum-ai/
├── api/              # FastAPI routes
├── core/             # Business logic, trust engine
│   ├── signals/      # Signal collectors & processors
│   ├── gates/        # Trust gate evaluators
│   └── automations/  # Automation executors
├── models/           # SQLAlchemy models
├── schemas/          # Pydantic schemas
├── services/         # External integrations
├── workers/          # Celery tasks
└── tests/
```

## Key Commands
```bash
make dev              # Start local env
make test             # Run pytest
make lint             # Ruff + mypy
make migrate          # Alembic migrations
docker compose up -d  # Full stack
```

## Code Standards
- Type hints REQUIRED on all functions
- Pydantic models for all API I/O
- Async/await for all I/O operations
- 90%+ test coverage for core/
- Docstrings on public functions

## Domain Terminology
| Term | Definition |
|------|------------|
| Signal | Input data point (metric, event, webhook) |
| Signal Health | Composite score (0-100) of signal reliability |
| Trust Gate | Decision checkpoint before automation |
| Autopilot | Automated action when trust passes |

## Trust Engine Rules
```python
HEALTHY_THRESHOLD = 70      # Green - autopilot enabled
DEGRADED_THRESHOLD = 40     # Yellow - alert + hold
# Never auto-execute when signal_health < 70
```

## Do NOT
- Skip trust gate checks for "quick fixes"
- Hardcode thresholds (use config)
- Execute automations without audit logging
- Merge without passing CI

## Git Workflow
- Branch: `feature/STRAT-123-description`
- Commit: `feat(signals): add anomaly detection [STRAT-123]`

## Imports
@docs/architecture/trust-engine.md
@docs/integrations/README.md
EOF

echo "✅ CLAUDE.md created"

# -----------------------------------------------------------------------------
# 3. Create CLAUDE.local.md (gitignored)
# -----------------------------------------------------------------------------
echo -e "${BLUE}📝 Creating CLAUDE.local.md...${NC}"

cat > CLAUDE.local.md << 'EOF'
# Local Development Preferences

## My Role
Project Lead / Developer

## Communication Style
- Robot-Nerd mode: technical + actionable
- Use tables for comparisons
- Provide checklists for processes

## Local Environment
- Python venv: `.venv`
- Node version: 20 (via nvm)
- Docker context: default

## Current Focus
- [Update this with your current sprint/focus]
EOF

echo "✅ CLAUDE.local.md created"

# -----------------------------------------------------------------------------
# 4. Create slash commands
# -----------------------------------------------------------------------------
echo -e "${BLUE}⚡ Creating slash commands...${NC}"

# Check Signal
cat > .claude/commands/check-signal.md << 'EOF'
Analyze signal health for: $ARGUMENTS

## Steps
1. Locate signal definition in `core/signals/`
2. Check signal collector implementation
3. Review signal health calculation logic
4. Identify potential degradation causes
5. Verify trust gate thresholds

## Output
- Current health formula
- Data freshness requirements
- Recommendations
EOF

# Add Automation
cat > .claude/commands/add-automation.md << 'EOF'
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
EOF

# Debug Gate
cat > .claude/commands/debug-gate.md << 'EOF'
Debug trust gate failure for: $ARGUMENTS

## Investigation
1. Check recent signal health scores
2. Review gate evaluation logs
3. Check for anomaly flags
4. Verify data freshness
5. Look for config drift

## Output
- Root cause analysis
- Recommended fix
- Prevention measures
EOF

# Test Flow
cat > .claude/commands/test-flow.md << 'EOF'
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
EOF

# Deploy Check
cat > .claude/commands/deploy-check.md << 'EOF'
Pre-deployment verification

## Checklist
1. `make lint` - Code quality
2. `make test` - Full test suite
3. Migrations tested
4. Threshold changes reviewed
5. Monitoring alerts configured
6. CHANGELOG updated
EOF

echo "✅ Slash commands created"

# -----------------------------------------------------------------------------
# 5. Create placeholder docs
# -----------------------------------------------------------------------------
echo -e "${BLUE}📚 Creating documentation placeholders...${NC}"

cat > docs/architecture/trust-engine.md << 'EOF'
# Trust Engine Architecture

## Overview
The Trust Engine is the core decision-making component that evaluates
signal health before allowing automation execution.

## Components
1. Signal Collectors - Gather data from various sources
2. Health Calculator - Compute signal reliability scores
3. Trust Gate - Binary decision point (pass/hold/block)
4. Automation Executor - Execute actions when trust passes

## Flow Diagram
```
[Signal Sources] → [Collectors] → [Health Calculator]
                                         ↓
                                   [Trust Gate]
                                    ↙      ↘
                              [PASS]      [HOLD/BLOCK]
                                ↓              ↓
                          [Execute]      [Alert/Manual]
```

## Configuration
See `config/trust_engine.yaml` for threshold settings.
EOF

cat > docs/integrations/README.md << 'EOF'
# External Integrations

## Supported Platforms
- Google Ads API
- Meta Marketing API
- TikTok Ads API
- Snapchat Marketing API

## Adding New Integrations
1. Create service in `services/{platform}/`
2. Implement signal collector
3. Add health calculation logic
4. Register in integration registry
5. Document API requirements

## Authentication
All API credentials stored in environment variables.
Never commit credentials to repository.
EOF

echo "✅ Documentation placeholders created"

# -----------------------------------------------------------------------------
# 6. Update .gitignore
# -----------------------------------------------------------------------------
echo -e "${BLUE}🔒 Updating .gitignore...${NC}"

if [ -f .gitignore ]; then
    # Check if CLAUDE.local.md is already in gitignore
    if ! grep -q "CLAUDE.local.md" .gitignore; then
        echo "" >> .gitignore
        echo "# Claude Code" >> .gitignore
        echo "CLAUDE.local.md" >> .gitignore
        echo ".claude/state/" >> .gitignore
    fi
else
    cat > .gitignore << 'EOF'
# Claude Code
CLAUDE.local.md
.claude/state/
EOF
fi

echo "✅ .gitignore updated"

# -----------------------------------------------------------------------------
# 7. Create settings file
# -----------------------------------------------------------------------------
echo -e "${BLUE}⚙️ Creating Claude settings...${NC}"

mkdir -p .claude

cat > .claude/settings.json << 'EOF'
{
  "permissions": {
    "allow": [
      "Bash(grep:*)",
      "Bash(rg:*)",
      "Bash(find:*)",
      "Bash(cat:*)",
      "Bash(make:*)",
      "Bash(pytest:*)",
      "Bash(docker:*)",
      "Bash(git:*)"
    ]
  }
}
EOF

echo "✅ Settings created"

# -----------------------------------------------------------------------------
# Done!
# -----------------------------------------------------------------------------
echo ""
echo -e "${GREEN}✨ Claude Code setup complete!${NC}"
echo ""
echo "Files created:"
echo "  📄 CLAUDE.md              - Project configuration"
echo "  📄 CLAUDE.local.md        - Personal preferences (gitignored)"
echo "  📁 .claude/commands/      - Custom slash commands"
echo "  📁 .claude/settings.json  - Permission settings"
echo "  📁 docs/                  - Documentation placeholders"
echo ""
echo "Next steps:"
echo "  1. Review and customize CLAUDE.md for your project"
echo "  2. Update CLAUDE.local.md with your preferences"
echo "  3. Fill in docs/architecture/ and docs/integrations/"
echo "  4. Run 'claude' in this directory to start"
echo ""
echo "Available commands:"
echo "  /project:check-signal [name]     - Analyze signal health"
echo "  /project:add-automation [name]   - Create new automation"
echo "  /project:debug-gate [id]         - Debug trust gate issues"
echo "  /project:test-flow [name]        - Run E2E tests"
echo "  /project:deploy-check            - Pre-deployment verification"
echo ""
