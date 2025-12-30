#!/usr/bin/env python3

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from automation_core.voiceover_tts import cli_main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(cli_main())
