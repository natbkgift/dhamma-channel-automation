"""
Unit tests for global kill switch (PIPELINE_ENABLED)
Tests the parse_pipeline_enabled function and orchestrator behavior
"""

from pathlib import Path


def test_parse_pipeline_enabled_none_default_enabled():
    """When PIPELINE_ENABLED is not set, should default to enabled (True)"""
    # Import here to avoid early import issues
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from orchestrator import parse_pipeline_enabled

    assert parse_pipeline_enabled(None) is True


def test_parse_pipeline_enabled_true():
    """When PIPELINE_ENABLED is 'true', should be enabled"""
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from orchestrator import parse_pipeline_enabled

    assert parse_pipeline_enabled("true") is True
    assert parse_pipeline_enabled("True") is True
    assert parse_pipeline_enabled("TRUE") is True
    assert parse_pipeline_enabled("1") is True
    assert parse_pipeline_enabled("yes") is True
    assert parse_pipeline_enabled("YES") is True
    assert parse_pipeline_enabled("on") is True
    assert parse_pipeline_enabled("enabled") is True


def test_parse_pipeline_enabled_false():
    """When PIPELINE_ENABLED is 'false', should be disabled"""
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from orchestrator import parse_pipeline_enabled

    assert parse_pipeline_enabled("false") is False
    assert parse_pipeline_enabled("False") is False
    assert parse_pipeline_enabled("FALSE") is False
    assert parse_pipeline_enabled("0") is False
    assert parse_pipeline_enabled("no") is False
    assert parse_pipeline_enabled("NO") is False
    assert parse_pipeline_enabled("off") is False
    assert parse_pipeline_enabled("disabled") is False


def test_parse_pipeline_enabled_whitespace():
    """Should handle whitespace correctly"""
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from orchestrator import parse_pipeline_enabled

    assert parse_pipeline_enabled("  false  ") is False
    assert parse_pipeline_enabled("  true  ") is True


def test_orchestrator_main_with_kill_switch_disabled(tmp_path, monkeypatch, capsys):
    """
    Test that orchestrator.main() exits with 0 when PIPELINE_ENABLED=false
    and does NOT run the pipeline
    """
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from orchestrator import main

    # Create a minimal pipeline YAML file
    pipeline_file = tmp_path / "test_pipeline.yml"
    pipeline_file.write_text("""
pipeline: test_pipeline
steps:
  - id: test_step
    uses: prompt_pack
    output: test_output.txt
""")

    # Mock sys.argv to provide CLI args
    monkeypatch.setattr(
        "sys.argv",
        [
            "orchestrator.py",
            "--pipeline",
            str(pipeline_file),
            "--run-id",
            "test_kill_switch",
        ],
    )

    # Set PIPELINE_ENABLED=false
    monkeypatch.setenv("PIPELINE_ENABLED", "false")

    # Run main()
    exit_code = main()

    # Should exit with 0 (success/no-op)
    assert exit_code == 0

    # Should log the disabled message
    captured = capsys.readouterr()
    assert "Pipeline disabled by PIPELINE_ENABLED=false" in captured.out


def test_orchestrator_main_with_kill_switch_enabled(tmp_path, monkeypatch, capsys):
    """
    Test that orchestrator.main() attempts to run when PIPELINE_ENABLED=true
    We expect it to fail with agent not found (which proves kill switch is not active)
    """
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from orchestrator import main

    # Create a minimal pipeline YAML file
    pipeline_file = tmp_path / "test_pipeline.yml"
    pipeline_file.write_text("""
pipeline: test_pipeline_enabled
steps:
  - id: test_step
    uses: nonexistent_agent_for_testing
    output: test_output.txt
""")

    # Mock sys.argv to provide CLI args
    monkeypatch.setattr(
        "sys.argv",
        [
            "orchestrator.py",
            "--pipeline",
            str(pipeline_file),
            "--run-id",
            "test_enabled",
        ],
    )

    # Set PIPELINE_ENABLED=true (explicitly enabled)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    # Run main() - it will try to run the pipeline and fail with agent not found
    exit_code = main()

    # Should exit with 1 (error - agent not found)
    # This proves the kill switch was NOT active (pipeline tried to run)
    assert exit_code == 1

    # Should NOT show the disabled message
    captured = capsys.readouterr()
    assert "Pipeline disabled by PIPELINE_ENABLED=false" not in captured.out
    # Should show agent error instead
    assert "Agent not implemented" in captured.out


def test_orchestrator_main_with_kill_switch_not_set(tmp_path, monkeypatch, capsys):
    """
    Test that orchestrator.main() attempts to run when PIPELINE_ENABLED is not set
    (default behavior = enabled). We expect it to fail with agent not found,
    which proves kill switch defaults to disabled/not active.
    """
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from orchestrator import main

    # Create a minimal pipeline YAML file
    pipeline_file = tmp_path / "test_pipeline.yml"
    pipeline_file.write_text("""
pipeline: test_pipeline_default
steps:
  - id: test_step
    uses: nonexistent_agent_for_testing
    output: test_output.txt
""")

    # Mock sys.argv to provide CLI args
    monkeypatch.setattr(
        "sys.argv",
        [
            "orchestrator.py",
            "--pipeline",
            str(pipeline_file),
            "--run-id",
            "test_default",
        ],
    )

    # Ensure PIPELINE_ENABLED is NOT set (remove if exists)
    monkeypatch.delenv("PIPELINE_ENABLED", raising=False)

    # Run main() - it will try to run the pipeline and fail with agent not found
    exit_code = main()

    # Should exit with 1 (error - agent not found)
    # This proves the kill switch was NOT active (pipeline tried to run)
    assert exit_code == 1

    # Should NOT show the disabled message
    captured = capsys.readouterr()
    assert "Pipeline disabled by PIPELINE_ENABLED=false" not in captured.out
    # Should show agent error instead
    assert "Agent not implemented" in captured.out


def test_web_runner_parse_pipeline_enabled():
    """Test the _parse_pipeline_enabled function in app/core/runner.py"""
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from app.core.runner import _parse_pipeline_enabled

    # Test default (None = enabled)
    assert _parse_pipeline_enabled(None) is True

    # Test false values
    assert _parse_pipeline_enabled("false") is False
    assert _parse_pipeline_enabled("FALSE") is False
    assert _parse_pipeline_enabled("0") is False

    # Test true values
    assert _parse_pipeline_enabled("true") is True
    assert _parse_pipeline_enabled("TRUE") is True
    assert _parse_pipeline_enabled("1") is True


def test_web_runner_no_subprocess_spawn_when_disabled(monkeypatch):
    """
    CRITICAL: When PIPELINE_ENABLED=false, ProcessJob.start() should
    NOT call asyncio.create_subprocess_exec()
    This ensures no partial output artifacts are created
    """
    import asyncio
    import sys
    from pathlib import Path
    from unittest.mock import AsyncMock, patch

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from app.core.runner import ProcessJob

    monkeypatch.setenv("PIPELINE_ENABLED", "false")

    job = ProcessJob("test_agent", ["python", "-c", "print('test')"])

    # Mock the subprocess function and _append_file_log
    with (
        patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_spawn,
        patch.object(job, "_append_file_log") as mock_file_log,
    ):
        # Run the async start() method
        asyncio.run(job.start())

        # ✅ ASSERT: subprocess MUST NOT be called
        mock_spawn.assert_not_called()

        # ✅ ASSERT: _append_file_log MUST NOT be called (no file artifacts when disabled)
        mock_file_log.assert_not_called()

        # ✅ ASSERT: status should be "disabled"
        assert job.status == "disabled", (
            f"Expected status='disabled', got '{job.status}'"
        )

        # ✅ ASSERT: log should contain [DISABLED] message
        log_text = "\n".join(job.log)
        assert "DISABLED" in log_text, f"Expected '[DISABLED]' in logs, got: {log_text}"

        # ✅ ASSERT: No process object created
        assert job.proc is None, "Process object should not be created when disabled"

        # ✅ ASSERT: Progress should be at 100 (completed state)
        assert job.progress == 100


def test_web_runner_subprocess_spawn_when_enabled(monkeypatch):
    """
    CONTROL: When PIPELINE_ENABLED=true (or not set), ProcessJob.start()
    SHOULD call asyncio.create_subprocess_exec() to spawn subprocess
    """
    import asyncio
    import sys
    from pathlib import Path
    from unittest.mock import AsyncMock, patch

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from app.core.runner import ProcessJob

    # Ensure PIPELINE_ENABLED is true
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    job = ProcessJob("test_agent", ["python", "-c", "print('enabled')"])

    # Mock the subprocess function to avoid actual spawn
    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_spawn:
        # Mock a process object
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"output", b""))
        mock_spawn.return_value = mock_proc

        # Run the async start() method
        asyncio.run(job.start())

        # ✅ ASSERT: subprocess MUST be called when enabled
        mock_spawn.assert_called_once()

        # ✅ ASSERT: status should be "starting" (not disabled)
        assert job.status != "disabled", "Status should not be 'disabled' when enabled"

        # ✅ ASSERT: No [DISABLED] in logs
        log_text = "\n".join(job.log)
        assert "DISABLED" not in log_text, (
            f"Should not have [DISABLED] when enabled, got: {log_text}"
        )


def test_web_runner_no_log_file_created_when_disabled(monkeypatch):
    """
    When PIPELINE_ENABLED=false, runner must NOT create a new log file
    under output/logs/ for that agent.
    """
    import asyncio
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from app.core.runner import LOG_DIR, ProcessJob

    monkeypatch.setenv("PIPELINE_ENABLED", "false")

    agent_key = "no_log_when_disabled"
    log_path = LOG_DIR / f"{agent_key}.log"
    # Ensure clean state
    try:
        if log_path.exists():
            log_path.unlink()
    except Exception:
        pass

    job = ProcessJob(agent_key, ["python", "-c", "print('noop')"])

    # Run disabled start
    asyncio.run(job.start())

    # Assert log file was NOT created
    assert not log_path.exists(), (
        f"Log file should not be created when disabled, but found: {log_path}"
    )
