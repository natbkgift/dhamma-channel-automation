# GitHub Copilot Instructions for Dhamma Channel Automation

## 🚨 Hard Safety Rules (Must Not Violate)

- Do NOT change agent behavior without updating baseline references in samples/reference/ and docs/BASELINE.md.
- Do NOT introduce multi-channel or multi-tenant abstractions.
- Do NOT bypass PIPELINE_ENABLED kill switch (CLI orchestrator and web runner must enforce it).
- Do NOT write to output/ when the pipeline is disabled.
- Prefer orchestrator- or web-runner–initiated flows for production; avoid direct agent execution that skips guards.

This file provides guidance to GitHub Copilot coding agent when working on the Dhamma Channel Automation repository.

## 🎯 Project Overview

This is a YouTube content automation system for "ธรรมะดีดี" (Dhamma Channel) built with Python. The system uses AI Agents to automate content creation from trend analysis to script generation, with a goal of generating 100,000 THB/month from YouTube AdSense.

**Key Features:**
- AI Agent-based architecture for content automation
- TrendScoutAgent for trend analysis and topic generation
- LocalizationSubtitleAgent for subtitle generation
- CLI interface with Rich output
- Comprehensive testing with 85%+ coverage
- Thai language documentation for internal use

## 📌 Baseline Stability Rules

- samples/reference/ defines the expected, stable output structures and reference artifacts.
- Do not change output schemas, tone, or structure unless explicitly instructed to update baselines.
- When updating behavior or outputs, also update docs/BASELINE.md and the corresponding files under samples/reference/.
- Use baseline diffs to detect drift vs acceptable changes before merging.

## 🔧 Development Environment

### Requirements
- Python 3.11 or newer (3.11, 3.12 supported)
- Git
- 512MB RAM minimum
- 100MB disk space

### Setup Commands
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Install dependencies
pip install -e .

# Install development dependencies
pip install -e ".[dev]"
```

### Common Commands
```bash
# Linting
ruff check .
ruff format .

# Testing
pytest
pytest --cov=src --cov=cli --cov-report=html

# Type checking
mypy src/ cli/

# Documentation
mkdocs serve  # Preview docs at http://localhost:8000
mkdocs build  # Build documentation (internal use only)

# Preflight checks (before PR)
bash scripts/preflight.sh
make preflight

# Quick checks
bash scripts/preflight_quick.sh
make quick
```

## 📝 Coding Conventions

### Language Usage
- **Code (functions, variables, classes)**: English
- **Comments and docstrings**: Thai (ภาษาไทย)
- **Documentation files**: Thai (ภาษาไทย)
- **Git commit messages**: Can be English or Thai

### Python Style
- Follow **PEP 8** standards
- Use **type hints** for all function parameters and return values
- Line length: 88 characters (enforced by ruff)
- Use Pydantic for data models and validation
- Follow existing naming conventions in the codebase

### Code Organization
```
src/
├── automation_core/        # Core framework components
│   ├── base_agent.py      # BaseAgent abstract class (Generic[InputModel, OutputModel])
│   ├── config.py          # Pydantic Settings for configuration
│   ├── logging.py         # Rich console logging
│   ├── prompt_loader.py   # Prompt template loading
│   └── utils/             # Utility functions
└── agents/                # AI Agent implementations
    ├── agent_name/
    │   ├── __init__.py
    │   ├── model.py       # Pydantic Input/Output models
    │   └── agent.py       # Agent implementation (extends BaseAgent)
```

### Agent Development Pattern
1. Create Pydantic models in `model.py` for Input and Output
2. Create prompt template in `prompts/` directory
3. Implement agent in `agent.py` extending `BaseAgent[InputModel, OutputModel]`
4. Add tests in `tests/test_agent_name.py`
5. Update documentation in `docs/`

Example:
```python
from automation_core.base_agent import BaseAgent
from pydantic import BaseModel, Field

class MyAgentInput(BaseModel):
    """Input model สำหรับ MyAgent"""
    query: str = Field(description="คำค้นหา")

class MyAgentOutput(BaseModel):
    """Output model สำหรับ MyAgent"""
    result: str = Field(description="ผลลัพธ์")

class MyAgent(BaseAgent[MyAgentInput, MyAgentOutput]):
    """Agent สำหรับ..."""
    
    def run(self, input_data: MyAgentInput) -> MyAgentOutput:
        # Implementation
        pass
```

## 🧪 Testing Standards

### Testing Requirements
- Write unit tests for all new code
- Maintain 85%+ test coverage
- Use pytest framework
- Tests should be in `tests/` directory
- Follow naming convention: `test_*.py`

### Test Structure
```python
import pytest
from agents.my_agent import MyAgent, MyAgentInput

def test_my_agent_basic():
    """ทดสอบการทำงานพื้นฐานของ MyAgent"""
    agent = MyAgent()
    input_data = MyAgentInput(query="test")
    result = agent.run(input_data)
    
    assert result is not None
    assert result.result != ""
```

### Running Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_my_agent.py -v

# Run with coverage
pytest --cov=src --cov=cli --cov-report=html

# Run quick checks before commit
bash scripts/preflight_quick.sh
```

## 📚 Documentation Standards

### Documentation Location
- Main docs in `docs/` directory (Thai language)
- Use MkDocs with Material theme
- Documentation is for internal use (not publicly hosted)

### Key Documentation Files
- `docs/ARCHITECTURE.md` - System architecture
- `docs/AGENT_LIFECYCLE.md` - Guide for adding new agents
- `docs/PROMPTS_OVERVIEW.md` - Prompt management
- `docs/ROADMAP.md` - Project roadmap
- `docs/TROUBLESHOOTING.md` - Common issues and solutions

### Docstring Style
Use Thai language for docstrings with clear descriptions:
```python
def calculate_score(value: float, weight: float) -> float:
    """
    คำนวณคะแนนโดยคูณค่ากับน้ำหนัก
    
    Args:
        value: ค่าที่ต้องการคำนวณ (0.0-1.0)
        weight: น้ำหนักสำหรับการคำนวณ
        
    Returns:
        คะแนนที่คำนวณได้
    """
    return value * weight
```

## 🔍 Code Quality Tools

### Linting with Ruff
- Target version: Python 3.11
- Line length: 88 characters
- Enabled checks: E, W, F, I, B, C4, UP
- Ignored: E501 (line length), B008, C901
- Auto-fix available: `ruff check --fix .`
- Format code: `ruff format .`

### Type Checking with MyPy
- Python version: 3.11
- Non-strict mode
- Check untyped defs enabled
- Run: `mypy src/ cli/`

### Pre-commit Hooks
Optional but recommended:
```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

## 🚀 CI/CD Pipeline

### GitHub Actions Workflows
- **Lint job**: Runs ruff check and format check (Python 3.11)
- **Test job**: Runs pytest with coverage (Python 3.11)
- **Docs job**: Builds documentation (main branch only)
- **Preflight job**: Full preflight check (main branch only)

### Before Opening PR
1. Run preflight checks: `bash scripts/preflight.sh`
2. Ensure all tests pass
3. Check code coverage is maintained
4. Update documentation if needed
5. Verify no linting errors

## 📁 File Structure Patterns

### Prompt Templates
- Location: `prompts/` directory
- Naming: `{agent_name}_v{version}.txt`
- Example: `prompts/trend_scout_v1.txt`
- Use placeholders for dynamic content

### Output Files
- Location: `output/` directory
- Format: JSON for structured data
- Include timestamps in output

### Configuration
- Environment variables via `.env` file
- Pydantic Settings in `src/automation_core/config.py`
- Example in `.env.example`

## 🎨 CLI Development

### Using Typer and Rich
- CLI commands in `cli/main.py`
- Use Typer for command structure
- Rich for beautiful terminal output
- Progress indicators for long-running tasks
- Colored output for better UX

Important Ops Guardrail:
- Direct agent CLI commands may bypass operational guards unless routed through the orchestrator. For production operations, prefer invoking via `orchestrator.py` or the web runner so that PIPELINE_ENABLED and other safety checks are enforced.

Example:
```python
import typer
from rich.console import Console

app = typer.Typer()
console = Console()

@app.command()
def my_command(input_file: str):
    """คำอธิบายคำสั่ง"""
    console.print("[green]Starting process...[/green]")
    # Implementation
```

## 🔐 Security and Safety

### Important Notes
- Never commit secrets or API keys
- Use `.env` files for sensitive data
- Keep `.env.example` updated (without actual values)
- Validate all user inputs
- Use Pydantic validation for data models

## 🌟 Best Practices

### When Adding New Features
1. Check existing patterns in the codebase
2. Follow the Agent architecture for new AI components
3. Write tests first (TDD approach recommended)
4. Update documentation
5. Run full preflight before PR

### When Fixing Bugs
1. Add a test that reproduces the bug
2. Fix the issue
3. Verify the test passes
4. Check for similar issues in the codebase

### When Refactoring
1. Ensure tests exist and pass before refactoring
2. Make small, incremental changes
3. Run tests after each change
4. Keep test coverage above 85%

## 📞 Getting Help

### Resources
- Documentation: `docs/` directory or `mkdocs serve`
- Troubleshooting: `docs/TROUBLESHOOTING.md`
- Agent guide: `docs/AGENT_LIFECYCLE.md`
- Architecture: `docs/ARCHITECTURE.md`

### Common Issues
- Python version: Must be 3.11+
- Virtual environment: Always activate before running commands
- Dependencies: Run `pip install -e ".[dev]"` if imports fail
- Tests failing: Check `docs/TROUBLESHOOTING.md`

## 🎯 Project Goals and Context

### Revenue Target
- Goal: 100,000 THB/month from YouTube AdSense
- Content: 20-30 high-quality videos per month
- Time savings: 70% reduction through AI automation

### Operating Mode
- Current operating mode: Client Product

### Key Principles
- Quality over quantity
- Thai language for Buddhist/Dhamma content
- Culturally appropriate and sensitive content
- Automation to reduce manual work
- Maintain high ethical standards

## 🔄 Workflow Integration

### Standard Development Workflow
1. Create feature branch from `main`
2. Implement changes following conventions
3. Write/update tests
4. Run preflight checks
5. Commit changes
6. Open pull request
7. Address review feedback
8. Merge after approval

### Quick Development Cycle
```bash
# Make changes
# ...

# Quick validation
make quick

# Full validation before PR
make preflight

# Run specific tests
pytest tests/test_my_changes.py -v
```

---

**Remember**: This is an internal project with Thai language documentation. Always prioritize code quality, test coverage, and following established patterns.
