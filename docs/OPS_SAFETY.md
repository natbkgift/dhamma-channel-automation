# Operational Safety Documentation

## Global Kill Switch: PIPELINE_ENABLED

The Dhamma Channel Automation system includes a **global kill switch** that allows operators to safely disable the pipeline without code changes. This is critical for production environments where immediate control is required.

## Purpose

The `PIPELINE_ENABLED` environment variable provides:

1. **Emergency Stop:** Pause all pipeline execution during incidents, API outages, or policy violations
2. **Maintenance Window:** Disable pipeline during system maintenance, updates, or configuration changes
3. **Manual Review Gate:** Temporarily halt automation while reviewing outputs or investigating issues
4. **Policy Compliance:** Quick response to content policy changes or legal requirements

## Environment Variable: PIPELINE_ENABLED

### Default Behavior
- **When not set:** Pipeline is **ENABLED** (runs normally)
- **When set to "false":** Pipeline is **DISABLED** (stops safely)

This default-enabled design ensures backward compatibility with existing deployments.

### Accepted Values

**Enable Pipeline (run normally):**
- Not set (environment variable absent)
- `PIPELINE_ENABLED=true`
- `PIPELINE_ENABLED=1`
- `PIPELINE_ENABLED=yes`
- `PIPELINE_ENABLED=on`
- `PIPELINE_ENABLED=enabled`

**Disable Pipeline (stop safely):**
- `PIPELINE_ENABLED=false` (recommended)
- `PIPELINE_ENABLED=0`
- `PIPELINE_ENABLED=no`
- `PIPELINE_ENABLED=off`
- `PIPELINE_ENABLED=disabled`

Values are case-insensitive: `False`, `FALSE`, `false` all work.

## How It Works

### Safe Stop Behavior

When `PIPELINE_ENABLED=false`:
1. **Orchestrator:** Main entry point checks the flag before loading pipeline YAML
2. **CLI Commands:** Individual commands check the flag before executing agents
3. **Web Dashboard:** Job runner checks the flag before starting agent processes
4. **Exit Code:** Returns `0` (success) to indicate intentional no-op, not an error
5. **Logging:** Logs message: `"Pipeline disabled by PIPELINE_ENABLED=false"`
6. **No Artifacts:** Pipeline does NOT create partial or incomplete outputs

### What Gets Blocked

- All agent execution (TrendScout, ScriptWriter, etc.)
- Pipeline orchestration steps
- New output generation
- API calls to external services (YouTube, OpenAI, etc.)

### What Still Works

- Web dashboard UI (login, navigation, viewing past logs)
- Configuration file reading
- Existing output file viewing
- Help commands and version info

## Usage Examples

### Command Line (Bash/Linux/macOS)

**Disable Pipeline:**
```bash
# Export for entire shell session
export PIPELINE_ENABLED=false

# Or set for single command
PIPELINE_ENABLED=false python orchestrator.py --pipeline pipeline.web.yml --run-id test_001

# CLI commands
PIPELINE_ENABLED=false python -m cli.main trend-scout --input data/mock.json --out output/test.json
```

**Enable Pipeline (explicitly):**
```bash
export PIPELINE_ENABLED=true
python orchestrator.py --pipeline pipeline.web.yml --run-id prod_001
```

**Enable Pipeline (default - no env var):**
```bash
# Just run without setting PIPELINE_ENABLED
python orchestrator.py --pipeline pipeline.web.yml --run-id prod_002
```

### Command Line (Windows CMD)

**Disable Pipeline:**
```cmd
set PIPELINE_ENABLED=false
python orchestrator.py --pipeline pipeline.web.yml --run-id test_001
```

**Enable Pipeline:**
```cmd
set PIPELINE_ENABLED=true
python orchestrator.py --pipeline pipeline.web.yml --run-id prod_001
```

### Command Line (Windows PowerShell)

**Disable Pipeline:**
```powershell
$env:PIPELINE_ENABLED="false"
python orchestrator.py --pipeline pipeline.web.yml --run-id test_001
```

**Enable Pipeline:**
```powershell
$env:PIPELINE_ENABLED="true"
python orchestrator.py --pipeline pipeline.web.yml --run-id prod_001
```

### Environment File (.env)

**Persistent Configuration:**
```bash
# Add to .env file in project root
PIPELINE_ENABLED=false
```

Then load with `python-dotenv` or manually:
```bash
source .env  # Linux/macOS
python orchestrator.py --pipeline pipeline.web.yml
```

### Docker / Container Environments

**Docker Compose:**
```yaml
services:
  dhamma-automation:
    environment:
      - PIPELINE_ENABLED=false
```

**Docker Run:**
```bash
docker run -e PIPELINE_ENABLED=false dhamma-automation:latest
```

**Kubernetes:**
```yaml
env:
  - name: PIPELINE_ENABLED
    value: "false"
```

### Web Dashboard

The kill switch applies to web-triggered jobs:
1. Set `PIPELINE_ENABLED=false` in the environment where web server runs
2. Jobs started via dashboard will see "Pipeline disabled by PIPELINE_ENABLED=false"
3. Job status shows "completed" (no-op) immediately

## Use Cases

### 1. API Outage Response
**Scenario:** OpenAI API is down or rate-limited  
**Action:**
```bash
export PIPELINE_ENABLED=false
# Pipeline stops, no wasted API calls or partial outputs
```

### 2. Content Policy Review
**Scenario:** New YouTube policy requires review of all content generation  
**Action:**
1. Set `PIPELINE_ENABLED=false` in production environment
2. Review existing outputs and prompts
3. Update agents/prompts as needed
4. Test with kill switch still enabled
5. Re-enable: `PIPELINE_ENABLED=true`

### 3. Scheduled Maintenance
**Scenario:** Deploying new agent versions, updating dependencies  
**Action:**
```bash
# Before maintenance
export PIPELINE_ENABLED=false

# Perform updates
pip install -r requirements.txt
git pull origin main

# Test with kill switch enabled
python orchestrator.py --pipeline pipeline.web.yml --run-id test_post_update

# Re-enable after validation
export PIPELINE_ENABLED=true
```

### 4. Manual Quality Control
**Scenario:** Reviewing outputs before enabling automation  
**Action:**
1. Keep `PIPELINE_ENABLED=false` during initial rollout
2. Manually trigger test runs with kill switch disabled locally
3. Review all outputs for quality/compliance
4. Enable globally once confident: `PIPELINE_ENABLED=true`

### 5. Cost Control
**Scenario:** Prevent runaway costs from accidental loops or scheduling issues  
**Action:**
```bash
# Immediately stop all pipeline execution
export PIPELINE_ENABLED=false

# Investigate cost spike
# Fix scheduling/loop issue
# Re-enable carefully
```

## Monitoring and Alerts

### Log Messages

When disabled, expect this log message:
```
[2025-12-26 17:30:45] [INFO] Pipeline disabled by PIPELINE_ENABLED=false
```

### Recommended Monitoring

- **Alert on Unexpected Disablement:** If `PIPELINE_ENABLED=false` appears in logs but no maintenance is scheduled
- **Alert on Re-enablement:** Notify team when pipeline is re-enabled after being disabled
- **Track Disabled Duration:** Measure how long pipeline stays disabled

### Exit Codes

- **0 (success):** Pipeline disabled intentionally (no-op, not an error)
- **1 (error):** Actual pipeline failure (bug, API error, etc.)

This distinction allows monitoring systems to differentiate between intentional disablement and real failures.

## Testing the Kill Switch

### Manual Test

```bash
# 1. Disable pipeline
export PIPELINE_ENABLED=false

# 2. Run orchestrator - should exit immediately with 0
python orchestrator.py --pipeline pipeline.web.yml --run-id kill_switch_test
echo $?  # Should print: 0

# 3. Check output directory - should NOT contain new artifacts
ls -la output/kill_switch_test/  # Should not exist or be empty

# 4. Re-enable and verify
unset PIPELINE_ENABLED
python orchestrator.py --pipeline pipeline.web.yml --run-id normal_test
echo $?  # Should print: 0 after pipeline completes
ls -la output/normal_test/  # Should contain pipeline outputs
```

### Automated Test

See `tests/test_pipeline_kill_switch.py` for unit tests covering:
- Kill switch disables pipeline execution
- Default behavior is enabled
- Various disable values work correctly
- Exit code is 0 when disabled

## Security Considerations

### What Kill Switch Does NOT Do

- **Does not delete existing outputs:** Past runs remain in `output/` directory
- **Does not revoke API credentials:** Keys in `.env` are still valid
- **Does not stop web server:** Dashboard remains accessible (just jobs don't run)
- **Does not prevent code execution:** Other scripts/tools still work

### Additional Safety Measures

For comprehensive production safety, also implement:

1. **API Key Rotation:** Use `OPENAI_API_KEY`, `YOUTUBE_API_KEY` from `.env`
2. **Output Review:** Manually review outputs before publishing to YouTube
3. **Rate Limiting:** Set API quotas at provider level (OpenAI, YouTube)
4. **Monitoring:** Track costs, API usage, output quality
5. **Backup:** Keep backups of prompts, configurations, and key outputs

## Troubleshooting

### Pipeline Won't Start (But Should)

**Symptom:** Pipeline immediately exits with "Pipeline disabled" message

**Check:**
```bash
echo $PIPELINE_ENABLED  # Should be empty, true, or enabled value
env | grep PIPELINE_ENABLED  # Check for unexpected values
```

**Fix:**
```bash
unset PIPELINE_ENABLED  # Remove variable entirely
# OR
export PIPELINE_ENABLED=true  # Explicitly enable
```

### Kill Switch Not Working

**Symptom:** Pipeline runs despite `PIPELINE_ENABLED=false`

**Check:**
1. Verify environment variable is set: `echo $PIPELINE_ENABLED`
2. Ensure no typos: `PIPELINE_ENABLED` not `PIPLINE_ENABLED`
3. Check if running with different user/shell where env var not set
4. For web: ensure web server process has the env var set

**Fix:**
```bash
# Verify setting takes effect
export PIPELINE_ENABLED=false
python -c "import os; print('PIPELINE_ENABLED:', os.environ.get('PIPELINE_ENABLED'))"
# Should output: PIPELINE_ENABLED: false
```

## Rollout Plan

### Initial Deployment

1. **Deploy with kill switch disabled:**
   ```bash
   export PIPELINE_ENABLED=false
   ```

2. **Run manual tests:**
   - Verify kill switch works
   - Test one pipeline run with kill switch temporarily enabled
   - Review outputs for quality

3. **Enable gradually:**
   - Enable for staging environment first
   - Monitor for 24-48 hours
   - Enable for production if no issues

### Incident Response Plan

If production issues occur:

1. **Immediately disable:**
   ```bash
   export PIPELINE_ENABLED=false
   ```

2. **Investigate:**
   - Check logs in `output/logs/`
   - Review last successful run
   - Identify root cause

3. **Fix and test:**
   - Apply fix
   - Test with kill switch still disabled (local or staging)
   - Verify fix works

4. **Re-enable cautiously:**
   - `export PIPELINE_ENABLED=true`
   - Monitor closely for next few runs

## Contact

For questions about the kill switch:
- Review this document
- Check `docs/BASELINE.md` for related baseline behavior
- Contact repository maintainer

---

**Document Version:** 1.0  
**Last Updated:** 2025-12-26  
**Feature:** Global Kill Switch (PIPELINE_ENABLED)
