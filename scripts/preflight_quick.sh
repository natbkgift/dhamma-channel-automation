#!/usr/bin/env bash
#
# Preflight check script (quick mode)  
# ใช้กับ pre-commit hooks สำหรับการตรวจสอบรวดเร็ว

set -euo pipefail

# สีสำหรับ output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}⚡ เริ่ม Preflight Check (Quick Mode)${NC}"
echo "========================================"

# 1. Ruff check
echo -e "\n${BLUE}1. Ruff check${NC}"
if ruff check .; then
    echo -e "${GREEN}✓ Ruff check passed${NC}"
else
    echo -e "${RED}❌ Ruff check failed${NC}"
    exit 1
fi

# 2. Quick tests (exclude slow tests)
echo -e "\n${BLUE}2. Quick tests${NC}"
if pytest -k "not slow" -q --disable-warnings; then
    echo -e "${GREEN}✓ Quick tests passed${NC}"
else
    echo -e "${RED}❌ Quick tests failed${NC}"
    exit 1
fi

# 3. Validate result (if preflight result exists)
if [[ -f "output/preflight_result.json" ]]; then
    echo -e "\n${BLUE}3. Validating existing result${NC}"
    if python scripts/validate_result.py output/preflight_result.json; then
        echo -e "${GREEN}✓ Existing result validation passed${NC}"
    else
        echo -e "${YELLOW}⚠️  Existing result validation failed (non-blocking in quick mode)${NC}"
    fi
else
    echo -e "\n${YELLOW}⚠️  No existing preflight result found${NC}"
fi

echo ""
echo "========================================"
echo -e "${GREEN}⚡ Quick Preflight Check Completed!${NC}"
echo -e "${BLUE}💡 Run 'bash scripts/preflight.sh' for full check${NC}"