---
name: upgrade-dependency
description: Review a dependency update against actual upstream release notes, repository usage, lockfiles, and affected checks.
---

1. Read the dependency diff, manifest, lockfile, runtime constraints, and CI configuration.
2. Consult the upstream release notes for the actual old and new versions. Pre-1.0 releases may break compatibility; do not infer safety from the version label.
3. Trace affected imports and APIs. Explain legitimate transitive lockfile updates rather than assuming every lock-only change is wrong.
4. Check relevant security advisories and run the affected lint, type, unit, integration, and build checks. Use non-watch test commands.
5. Use disposable local fixtures for integration or migration verification. Do not downgrade, reset, deploy, contact production collectors, or enqueue live actions as a smoke test.
6. Report evidence, remaining risks, and a merge recommendation. A successful check is not authorization to merge or push.

Paddle is the supported billing provider; do not extend legacy Stripe dependencies.
