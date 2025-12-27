import json
import os

from dotenv import load_dotenv

load_dotenv()

# FlowBiz Standard Environment Variables
APP_SERVICE_NAME = os.getenv("APP_SERVICE_NAME", "dhamma-automation")
APP_ENV = os.getenv("APP_ENV", "dev")
APP_LOG_LEVEL = os.getenv("APP_LOG_LEVEL", "INFO")
FLOWBIZ_VERSION = os.getenv("FLOWBIZ_VERSION", "0.0.0")
FLOWBIZ_BUILD_SHA = os.getenv("FLOWBIZ_BUILD_SHA", "dev")

# Parse APP_CORS_ORIGINS from JSON string
_cors_origins_str = os.getenv("APP_CORS_ORIGINS", '["*"]')
try:
    APP_CORS_ORIGINS = json.loads(_cors_origins_str)
except json.JSONDecodeError:
    APP_CORS_ORIGINS = ["*"]

# Legacy APP_NAME for backwards compatibility
APP_NAME = os.getenv("APP_NAME", APP_SERVICE_NAME)

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
SESSION_COOKIE = os.getenv("SESSION_COOKIE_NAME", "dhamma_session")

# บัญชีผู้ดูแลระบบ (ไม่มีระบบสมัครสมาชิก)
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# ไดเรกทอรีข้อมูล/เอาต์พุต (ใช้ของโปรเจกต์เดิม)
DATA_DIR = os.getenv("DATA_DIR", "./data")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./output")

# ตั้งค่า LLM/API (ไม่บังคับในเว็บนี้)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# ตัวเรียก Python สำหรับ CLI (ช่วยให้ Windows กำหนดได้แม่นยำ)
PYTHON_BIN = os.getenv("PYTHON_BIN", "")

# พารามิเตอร์เว็บเซิร์ฟเวอร์ (สำหรับปุ่ม Restart Server)
WEB_HOST = os.getenv("WEB_HOST", "127.0.0.1")
WEB_PORT = int(os.getenv("WEB_PORT", "8000"))
