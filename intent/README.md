# Intent

This folder holds one file per requested change: what is wanted, why, and under which constraints, written before any design or code. It is the first link in the record of a change.

| Step | Where it lives |
|---|---|
| Intent: what was asked for | `intent/YYYY-MM-DD-<slug>.md` |
| Spec: what was decided | `docs/superpowers/specs/` |
| Plan: how it will be built | `docs/superpowers/plans/` |
| Result | the pull request |

Specs and plans stay where this repository already keeps them. The intent file links to them under **Chain**, so the record does not depend on filenames matching.

These files record what was asked and decided. Code and tests remain the source of truth for how the product behaves now.

## Writing one

1. Copy `TEMPLATE.md` to `intent/YYYY-MM-DD-<slug>.md`, dated the day it is written.
2. Fill it in using the originator's own words. No formal language is needed.
3. Open a pull request that adds the file with `Status: draft`.

## Accepting one

The reviewer corrects anything that was misunderstood, changes the status to `accepted`, and merges. Closing the pull request unmerged is the rejection. Either way the decision, its author and its date are in the git history.

## Keeping the chain current

- When a spec, plan or pull request exists, add it under **Chain** in the same commit.
- When the implementation departs from the plan, update the plan in the same commit.
- Once a spec exists, editing the intent means the request changed. Make that edit in its own commit.

## When to skip it

Changes with no product decision behind them, such as typo fixes, dependency bumps and formatting, do not need an intent.

## What stays out

This repository is public. Keep client names, credentials, personal data and commercial terms out of intent files.
