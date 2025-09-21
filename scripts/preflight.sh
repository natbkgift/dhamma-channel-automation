#!/usr/bin/env bash
# 
# Preflight check script (full mode)
# ใช้ก่อนเปิด PR เพื่อตรวจสอบคุณภาพโค้ดแบบครบถ้วน

set -euo pipefail

# สีสำหรับ output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# เก็บเวลาเริ่มต้น
START_TIME=$(date +%s)

echo -e "${BLUE}🚀 เริ่ม Preflight Check (Full Mode)${NC}"
echo "========================================"

# 1. ตรวจสอบ Python version
echo -e "\n${BLUE}1. ตรวจสอบ Python version${NC}"
python_version=$(python --version 2>&1)
echo "✓ $python_version"
if ! python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"; then
    echo -e "${RED}❌ ต้องใช้ Python 3.11 หรือใหม่กว่า${NC}"
    exit 1
fi

# 2. Ruff check (linting)
echo -e "\n${BLUE}2. Ruff check (linting)${NC}"
if ruff check .; then
    echo -e "${GREEN}✓ Ruff check passed${NC}"
else
    echo -e "${RED}❌ Ruff check failed${NC}"
    exit 1
fi

# 3. Ruff format check
echo -e "\n${BLUE}3. Ruff format check${NC}"
if ruff format --check .; then
    echo -e "${GREEN}✓ Code formatting is correct${NC}"
else
    echo -e "${RED}❌ Code formatting issues found${NC}"
    echo -e "${YELLOW}💡 Run 'ruff format .' to fix${NC}"
    exit 1
fi

# 4. Pytest (with coverage unless QUICK mode)
echo -e "\n${BLUE}4. Running tests${NC}"
if [[ "${QUICK:-0}" == "1" ]]; then
    echo "⚡ Quick mode: running tests without coverage"
    pytest --maxfail=1 --disable-warnings -q
else
    echo "📊 Full mode: running tests with coverage"
    pytest --maxfail=1 --disable-warnings --cov=src --cov-report=term-missing -q
fi
echo -e "${GREEN}✓ Tests passed${NC}"

# 5. MkDocs build (skip in QUICK mode)
if [[ "${QUICK:-0}" == "1" ]]; then
    echo -e "\n${YELLOW}⚡ Skipping MkDocs build (quick mode)${NC}"
elif [[ -f "mkdocs.yml" ]]; then
    echo -e "\n${BLUE}5. MkDocs build${NC}"
    if mkdocs build --strict; then
        echo -e "${GREEN}✓ Documentation build successful${NC}"
    else
        echo -e "${RED}❌ Documentation build failed${NC}"
        exit 1
    fi
else
    echo -e "\n${YELLOW}⚠️  No mkdocs.yml found, skipping docs build${NC}"
fi

# 6. รัน CLI Agent ตัวอย่าง
echo -e "\n${BLUE}6. Running CLI Agent (trend-scout)${NC}"
mkdir -p output
if python -m cli.main trend-scout \
    --input src/agents/trend_scout/mock_input.json \
    --out output/preflight_result.json \
    --no-table > /dev/null 2>&1; then
    echo -e "${GREEN}✓ CLI Agent ran successfully${NC}"
else
    echo -e "${RED}❌ CLI Agent failed${NC}"
    exit 1
fi

# 7. Validate result
echo -e "\n${BLUE}7. Validating agent output${NC}"
if python scripts/validate_result.py output/preflight_result.json; then
    echo -e "${GREEN}✓ Agent output validation passed${NC}"
else
    echo -e "${RED}❌ Agent output validation failed${NC}"
    exit 1
fi

# 8. MyPy (skip in QUICK mode, non-strict)
if [[ "${QUICK:-0}" == "1" ]]; then
    echo -e "\n${YELLOW}⚡ Skipping MyPy (quick mode)${NC}"
elif command -v mypy &> /dev/null; then
    echo -e "\n${BLUE}8. MyPy type check${NC}"
    if mypy src || true; then
        echo -e "${GREEN}✓ MyPy check completed (non-strict mode)${NC}"
    else
        echo -e "${YELLOW}⚠️  MyPy found issues (non-blocking)${NC}"
    fi
else
    echo -e "\n${YELLOW}⚠️  MyPy not found, skipping type check${NC}"
fi

# สรุปเวลาทั้งหมด
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo "========================================"
echo -e "${GREEN}🎉 Preflight Check Completed Successfully!${NC}"
echo -e "${BLUE}⏱️  Total time: ${DURATION} seconds${NC}"

if [[ "${QUICK:-0}" == "1" ]]; then
    echo -e "${YELLOW}⚡ Quick mode was used${NC}"
fi

echo ""
echo -e "${GREEN}✅ Ready for PR submission!${NC}"