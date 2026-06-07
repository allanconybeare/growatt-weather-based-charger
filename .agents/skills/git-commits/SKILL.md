---
name: git-commits
description: Git commit workflow and standards for this repo. Use when committing code, staging changes, or preparing to push. Covers pre-commit hook execution, commit message format, batching strategy, and safety rules. Automatically triggered whenever the user asks to commit, stage, or push changes.
---

# Git Commit Standards

Standards for creating clean, well-organised commits in this Python/solar-charger repo.

## CRITICAL: Quality Gates (ALL MUST PASS)

Run these **before every commit**:

```powershell
# 1. Pre-commit hooks (formatting, lint, secrets check)
pre-commit run --files <changed files>

# 2. Tests
.\venv\Scripts\python.exe -m pytest -q --tb=short
```

**If any gate fails → fix it before committing. Never skip pre-commit hooks.**

## Pre-Commit Checklist

- [ ] `pre-commit run` passes on all staged files
- [ ] `pytest` passes (all tests)
- [ ] No credentials or API keys in code (use env vars)
- [ ] Changes are logically grouped
- [ ] Commit message follows format below
- [ ] No unrelated changes mixed in

## Commit Message Format

```
<type>: <subject> (50 chars max)

<body> (optional, wrap at 72 chars)
- Bullet points for multiple changes
- Focus on WHY, not just WHAT
```

### Types

| Type       | Use for                              |
|------------|--------------------------------------|
| `feat`     | New feature or behaviour             |
| `fix`      | Bug fix                              |
| `docs`     | Documentation only                   |
| `style`    | Formatting, no logic change          |
| `refactor` | Code restructure, no feature/fix     |
| `test`     | Adding or updating tests             |
| `chore`    | Build, deps, config, maintenance     |

### Examples

```bash
git commit -m "feat: add log maintenance class with CSV retention"

git commit -m "fix: prevent duplicate labels on triage re-run"

git commit -m "chore: add [maintenance] section to INI files

- csv_retention_days default 1095 (3 years)
- cache_max_age_days default 7"
```

## Batching Strategy

Each commit should:
- Represent one logical unit of work
- Leave the codebase in a working state (tests pass, app runs)
- Not mix unrelated changes

**Good:**
```
Commit 1: feat: add LogMaintenance class
Commit 2: chore: wire LogMaintenance into all entry points
Commit 3: chore: add [maintenance] config section to INI files
```

**Bad:**
```
Commit 1: add maintenance, fix bug in forecast, update README
```

## Workflow

```powershell
# 1. Stage changes
git add <files>          # specific files preferred over git add -A

# 2. Run pre-commit on staged files
pre-commit run --files <same files>

# 3. If isort/black modifies files, re-stage them
git add <modified files>
pre-commit run --files <modified files>   # re-run to confirm clean

# 4. Run tests
.\venv\Scripts\python.exe -m pytest -q --tb=short

# 5. Commit
git commit -m "<type>: <subject>"

# 6. Push
git push origin main
```

## Safety Rules

- **Never** `git reset --hard`, `git restore`, or `git checkout -- <file>` without explicit user permission
- **Never** force-push to `main`
- **Never** skip pre-commit hooks (`--no-verify`)
- **Never** commit secrets — use `GROWATT_USERNAME`, `GROWATT_PASSWORD`, `SOLCAST_API_KEY` env vars
- If you encounter merge conflicts or unexpected state → **stop and ask the user**
