---
name: upgrade-dependency
description: Use when reviewing a Dependabot PR or manually bumping a dependency in `backend/requirements*.txt`, `frontend/package.json`, or any lock file. Encodes the changelog → tests → security check process so we don't merge a breaking or vulnerable upgrade. Trigger when the user says "review dependabot", "bump version", "upgrade X", or asks to merge dep update PRs.
---

# Upgrade Dependency

Stratum AI auto-runs Dependabot. Most PRs are safe, some aren't. This is the checklist before clicking merge.

## Triage by version delta

```
0.0.X → 0.0.Y   patch   usually safe; still run tests
0.X.0 → 0.Y.0   minor   read changelog briefly; run tests + lint
X.0.0 → Y.0.0   major   manual review required; never auto-merge
```

For majors: open the package's release notes, read the breaking-changes section, search the codebase for usages of any deprecated API.

## The 5-step process

### 1. Identify what changed

```bash
# What package, what version?
git diff main...HEAD -- backend/requirements*.txt frontend/package.json frontend/package-lock.json

# Read the full diff to confirm the lock file changes match the manifest
git diff main...HEAD -- frontend/package-lock.json | head -100
```

A lock-file change without a manifest change is suspicious — flag it.

### 2. Read the changelog

- Backend (Python): `https://pypi.org/project/<pkg>/<new_version>/` → "Changelog" or "Release notes" link.
- Frontend (npm): `https://www.npmjs.com/package/<pkg>?activeTab=versions` → click the version → "Releases" link on GitHub.
- For majors, read EVERY breaking-changes line and grep the codebase for affected APIs:
  ```bash
  # If pydantic 2 → 3: grep for old patterns
  grep -rn "pydantic\." backend/app/ | head
  ```

### 3. Security advisories

```bash
# Backend
pip-audit -r backend/requirements.txt 2>&1 | grep -i "<pkg_name>"

# Frontend
cd frontend && npm audit --audit-level=moderate
```

Or check the GitHub Advisory Database: `https://github.com/advisories?query=<pkg>`.

A new advisory introduced by the upgrade is a BLOCKER (you'd be making things worse).

### 4. Run the test suite

```bash
# Backend
cd backend && make lint && make test

# Frontend
cd frontend && npm run test && npm run build
```

Both must pass. Type errors are not "safe to ignore" — they often indicate breaking API changes.

### 5. Smoke test the affected area

- If the package is `fastapi`: hit a few endpoints locally.
- If the package is `sqlalchemy`: run a migration up + down.
- If the package is `react` or `react-dom`: load the dashboard and click around.
- If the package is `httpx` / `requests`: run a collector that uses it.
- If the package is `celery`: enqueue a task and verify it runs.

## Decision matrix

| Result                                                        | Action                                            |
| ------------------------------------------------------------- | ------------------------------------------------- |
| Patch + tests pass + no advisory                              | ✅ merge                                          |
| Minor + tests pass + no advisory + brief changelog scan clean | ✅ merge                                          |
| Minor + tests fail                                            | 🛑 fix tests or hold                              |
| Major (any)                                                   | 🛑 manual review by maintainer; do not auto-merge |
| New advisory                                                  | 🛑 BLOCK — would regress security posture         |
| Lock file changes much larger than expected                   | 🛑 investigate transitive changes                 |
| Touches Python/Node/major framework version                   | 🛑 manual smoke test required                     |

## Special cases

- **`pydantic` major bump**: many Pydantic v2 → v3 migrations needed; budget time for it.
- **`sqlalchemy` minor bump**: async APIs occasionally tweaked; rerun integration tests.
- **`fastapi` minor bump**: typically safe but check for changes to `Depends` or response models.
- **React 18 → 19** or any frontend framework major: full E2E pass via `playwright`.
- **Node engines change**: confirm CI Node version supports the new range.

## Output (when reviewing a Dependabot PR)

```
## Dep Upgrade Review: <pkg> <old> → <new>

### Verdict
[MERGE | HOLD | BLOCK]

### Delta
patch | minor | major

### Changelog highlights
- ...
- ...

### Breaking changes that affect us
- API X used in Y files: [grep results]
- Or: none

### Tests
- Backend: pass/fail
- Frontend: pass/fail
- Lint: pass/fail

### Security
- Advisories: none / [list]

### Recommendation
<merge | hold + reason | block + reason>
```

Keep it short. If patch + clean → three sentences and merge.
