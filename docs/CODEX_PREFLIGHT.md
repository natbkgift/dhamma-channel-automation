# Codex Pre-Flight Checklist

## Purpose

This document provides a comprehensive pre-flight checklist for Codex (AI coding agent) when working on this FlowBiz Client Product. It ensures all changes maintain compliance with FlowBiz standards while preserving existing functionality.

## Before Starting ANY Task

### 1. Understand the Architecture

- [ ] Read [ARCHITECTURE.md](./ARCHITECTURE.md) - System design and components
- [ ] Read [PROJECT_CONTRACT.md](./PROJECT_CONTRACT.md) - FlowBiz contract requirements
- [ ] Review existing code structure and patterns
- [ ] Identify integration points that must not break

### 2. Check FlowBiz Core Documentation

- [ ] Review [VPS_STATUS.md](https://github.com/natbkgift/flowbiz-ai-core/blob/main/docs/VPS_STATUS.md) for port allocations
- [ ] Check [ADR_SYSTEM_NGINX.md](https://github.com/natbkgift/flowbiz-ai-core/blob/main/docs/ADR_SYSTEM_NGINX.md) for network architecture
- [ ] Verify [CODEX_AGENT_BEHAVIOR_LOCK.md](https://github.com/natbkgift/flowbiz-ai-core/blob/main/docs/CODEX_AGENT_BEHAVIOR_LOCK.md) for behavioral rules

### 3. Review Hard Rules

**NEVER**:
- ❌ Rename the GitHub repository
- ❌ Change agent logic, scoring, prompts without baseline updates
- ❌ Modify existing business logic unless required
- ❌ Introduce public port bindings (0.0.0.0)
- ❌ Add Docker nginx for public traffic
- ❌ Bypass PIPELINE_ENABLED kill switch
- ❌ Write to output/ when pipeline disabled
- ❌ Suggest insecure operations (chmod 666 docker.sock, etc.)

**ALWAYS**:
- ✅ Bind services to localhost (127.0.0.1) only
- ✅ Use System Nginx as the ONLY public reverse proxy
- ✅ Update [BASELINE.md](./BASELINE.md) when changing agent outputs
- ✅ Verify changes don't break existing tests
- ✅ Run guardrails before PR
- ✅ Update documentation for user-facing changes

## Before Making Code Changes

### 4. Test Environment Setup

```bash
# Clone and setup
git clone <repo>
cd dhamma-channel-automation
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -e ".[dev]"

# Copy environment file
cp .env.example .env

# Verify setup
pytest --version
ruff --version
```

### 5. Baseline Validation

```bash
# Run existing tests to establish baseline
pytest -xvs

# Check current code quality
ruff check .
ruff format --check .

# Run guardrails
bash scripts/guardrails.sh

# Document baseline status
# All tests should pass before making changes
```

### 6. Identify Test Coverage

```bash
# Check what tests exist
pytest --collect-only

# Review test coverage
pytest --cov=src --cov=app --cov=cli --cov-report=term-missing

# Identify gaps in coverage for your changes
```

## During Implementation

### 7. Minimal Change Principle

**For Each Change**:
- [ ] Is this change absolutely necessary?
- [ ] Can I achieve the goal with fewer modifications?
- [ ] Am I changing only what's required?
- [ ] Am I preserving all existing behavior?
- [ ] Have I reviewed the diff to ensure minimality?

### 8. Incremental Validation

**After Each Significant Change**:
```bash
# 1. Format code
ruff format .

# 2. Lint
ruff check .

# 3. Run affected tests
pytest tests/test_<affected_area>.py -xvs

# 4. Check types (if applicable)
mypy src/ app/ cli/
```

### 9. Environment Contract Compliance

**When touching configuration**:
- [ ] All env vars have defaults (except APP_SERVICE_NAME)
- [ ] New env vars added to .env.example
- [ ] Env vars documented in PROJECT_CONTRACT.md
- [ ] No hardcoded secrets or credentials
- [ ] APP_SERVICE_NAME vs APP_NAME distinction clear

### 10. Endpoint Contract Compliance

**When touching endpoints**:
- [ ] /healthz returns correct schema
- [ ] /v1/meta returns correct schema
- [ ] Endpoints respond in <50ms
- [ ] Endpoints don't require authentication
- [ ] Endpoints don't touch external services
- [ ] Existing endpoints unchanged

### 11. Port Binding Compliance

**When touching Docker/networking**:
- [ ] All bindings use 127.0.0.1 (localhost)
- [ ] Port 3007 used consistently
- [ ] No 0.0.0.0 bindings introduced
- [ ] docker-compose.yml uses "127.0.0.1:3007:8000"
- [ ] Documentation reflects port allocation

## Before Creating PR

### 12. Comprehensive Testing

```bash
# Run full test suite
pytest -xvs

# Run with coverage
pytest --cov=src --cov=app --cov=cli --cov-report=html

# Check coverage meets threshold (85%+)
open htmlcov/index.html
```

### 13. Code Quality Checks

```bash
# Format code
ruff format .

# Lint (must pass)
ruff check .

# Type checking
mypy src/ app/ cli/

# Quick preflight
bash scripts/preflight_quick.sh

# Full preflight
bash scripts/preflight.sh
```

### 14. Guardrails Verification

```bash
# Run guardrails
bash scripts/guardrails.sh

# Expected: All checks PASS
# If WARN: Document reason
# If FAIL: Fix before PR
```

### 15. Manual Testing

**Web Service**:
```bash
# Start service
docker-compose up -d

# Test contract endpoints
curl http://127.0.0.1:3007/healthz
curl http://127.0.0.1:3007/v1/meta

# Test existing functionality
# - Visit http://127.0.0.1:3007
# - Login with credentials
# - Verify dashboard loads
# - Test changed features manually

# Check logs
docker logs dhamma-web --tail 50

# Cleanup
docker-compose down
```

**CLI Tools** (if applicable):
```bash
# Test CLI commands
dhamma-automation --help
dhamma-automation <your-command>
```

### 16. Documentation Review

- [ ] PROJECT_CONTRACT.md up to date
- [ ] DEPLOYMENT.md reflects any changes
- [ ] GUARDRAILS.md documents new checks
- [ ] README.md updated if user-facing changes
- [ ] Inline comments for complex logic
- [ ] Docstrings for new functions/classes

### 17. Baseline Updates

**If agent behavior changed**:
- [ ] Updated samples/reference/ with new outputs
- [ ] Updated docs/BASELINE.md with changes
- [ ] Documented reason for baseline change
- [ ] All baseline tests pass with new reference

### 18. Git Hygiene

```bash
# Check what's changed
git status
git diff

# Review each file
git diff <file>

# Ensure no accidental changes
git checkout -- <unintended-file>

# No debug code, console.logs, or temp files
git diff | grep -i "console\|debug\|todo\|fixme\|temp"
```

## PR Creation

### 19. PR Template Checklist

```markdown
## Summary
[Clear description of changes]

## Testing
- [ ] All tests pass
- [ ] New tests added for new functionality
- [ ] Manual testing completed
- [ ] Guardrails pass

## Checklist
- [ ] No breaking changes
- [ ] Documentation updated
- [ ] Environment variables documented
- [ ] Port binding verified (127.0.0.1)
- [ ] Contract endpoints tested
- [ ] Baseline updated (if applicable)
- [ ] No security vulnerabilities introduced

## Smoke Test Commands
```bash
# Commands to verify PR works
curl http://127.0.0.1:3007/healthz
curl http://127.0.0.1:3007/v1/meta
pytest -xvs
bash scripts/guardrails.sh
```
```

### 20. Pre-PR Validation

```bash
# Final check before pushing
bash scripts/preflight.sh

# Expected: All checks PASS

# Push to branch
git push origin feature/your-feature

# Create PR on GitHub
```

## Post-PR

### 21. CI/CD Monitoring

- [ ] Watch GitHub Actions workflows
- [ ] All jobs must pass (lint, test, docs)
- [ ] Guardrails workflow completes (warnings OK)
- [ ] No new security alerts
- [ ] Coverage maintained or improved

### 22. Address Review Feedback

- [ ] Respond to all comments
- [ ] Make requested changes
- [ ] Re-run validation after changes
- [ ] Mark conversations as resolved
- [ ] Request re-review after updates

### 23. Post-Merge Verification

**After merge to main**:
```bash
# Pull latest
git checkout main
git pull

# Verify locally
pytest -xvs
bash scripts/guardrails.sh

# Monitor production (if deployed)
curl https://dhamma.yourdomain.com/healthz
```

## Emergency Stop Conditions

**STOP IMMEDIATELY if**:

1. **Tests start failing unexpectedly**
   - Revert changes
   - Investigate root cause
   - Fix before proceeding

2. **Security vulnerability introduced**
   - Revert immediately
   - Assess impact
   - Fix with security review

3. **FlowBiz core docs conflict with task**
   - Stop work
   - Clarify requirements
   - Propose documentation-only PR if needed

4. **Cannot maintain minimal change principle**
   - Stop and reassess approach
   - May need architectural discussion
   - Don't force complex changes

5. **Agent behavior breaks baseline**
   - Either fix code or update baseline
   - Never leave in inconsistent state
   - Document reason for baseline change

## Success Criteria

Your changes are ready when:

- ✅ All tests pass
- ✅ Code quality checks pass (ruff, mypy)
- ✅ Guardrails pass (warnings documented)
- ✅ Manual testing successful
- ✅ Documentation complete and accurate
- ✅ Baseline updated if agent behavior changed
- ✅ Git history clean and meaningful
- ✅ PR template fully filled out
- ✅ No breaking changes to existing functionality
- ✅ No security vulnerabilities introduced
- ✅ Port binding verified (127.0.0.1 only)
- ✅ Contract endpoints operational

## References

- [Project Contract](./PROJECT_CONTRACT.md) - FlowBiz requirements
- [Deployment Guide](./DEPLOYMENT.md) - Production setup
- [Guardrails](./GUARDRAILS.md) - Compliance checks
- [Architecture](./ARCHITECTURE.md) - System design
- [Baseline](./BASELINE.md) - Agent output stability
- [Troubleshooting](./TROUBLESHOOTING.md) - Common issues

## Questions?

If uncertain about any requirement:
1. Check this document first
2. Review FlowBiz core documentation
3. Examine existing code patterns
4. Ask in team channel with context
5. When in doubt, prefer documentation-only PR

**Remember**: It's better to ask than to break production!
