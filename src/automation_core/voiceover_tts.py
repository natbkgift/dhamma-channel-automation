from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import wave
from pathlib import Path
from typing import Callable, Protocol

PIPELINE_DISABLED_MESSAGE = "Pipeline disabled by PIPELINE_ENABLED=false"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VOICEOVER_DIR = REPO_ROOT / "data" / "voiceovers"
SHA_PREFIX_LENGTH = 12
WAV_SAMPLE_RATE = 16000
WAV_CHANNELS = 1
WAV_SAMPLE_WIDTH_BYTES = 2
NULL_TTS_DURATION_SECONDS = 1.0
_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


class TTSEngine(Protocol):
    name: str

    def synthesize(self, text: str, output_path: Path) -> None:
        """Write a WAV file to output_path."""


def parse_pipeline_enabled(env_value: str | None) -> bool:
    if env_value is None:
        return True
    return env_value.strip().lower() not in ("false", "0", "no", "off", "disabled")


def is_pipeline_enabled() -> bool:
    return parse_pipeline_enabled(os.environ.get("PIPELINE_ENABLED"))


def _validate_identifier(value: str, field_name: str) -> str:
    if value is None or not str(value).strip():
        raise ValueError(f"{field_name} is required")

    if value in {".", ".."}:
        raise ValueError(f"{field_name} must not be '.' or '..'")

    for sep in (os.sep, os.altsep):
        if sep and sep in value:
            raise ValueError(f"{field_name} must not contain path separators")

    if not _IDENTIFIER_RE.fullmatch(value):
        raise ValueError(
            f"{field_name} must be filesystem-safe (letters, digits, _, -)"
        )

    return value


def compute_input_sha256(script_text: str) -> str:
    if not isinstance(script_text, str):
        raise TypeError("script_text must be a string")
    return hashlib.sha256(script_text.encode("utf-8")).hexdigest()


def build_voiceover_paths(
    run_id: str, slug: str, input_sha256: str, base_dir: Path | None = None
) -> tuple[Path, Path]:
    run_id = _validate_identifier(run_id, "run_id")
    slug = _validate_identifier(slug, "slug")

    if not input_sha256 or len(input_sha256) < SHA_PREFIX_LENGTH:
        raise ValueError("input_sha256 must be a full sha256 hex string")

    base_dir = base_dir or DEFAULT_VOICEOVER_DIR
    base_name = f"{slug}_{input_sha256[:SHA_PREFIX_LENGTH]}"
    wav_path = base_dir / run_id / f"{base_name}.wav"
    metadata_path = base_dir / run_id / f"{base_name}.json"
    return wav_path, metadata_path


def get_wav_duration_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as wav_file:
        frames = wav_file.getnframes()
        rate = wav_file.getframerate()
    if rate <= 0:
        return 0.0
    return frames / float(rate)


class NullTTSEngine:
    name = "null"

    def __init__(
        self,
        duration_seconds: float = NULL_TTS_DURATION_SECONDS,
        sample_rate: int = WAV_SAMPLE_RATE,
    ):
        if duration_seconds <= 0:
            raise ValueError("duration_seconds must be > 0")
        if sample_rate <= 0:
            raise ValueError("sample_rate must be > 0")
        self.duration_seconds = duration_seconds
        self.sample_rate = sample_rate

    def synthesize(self, text: str, output_path: Path) -> None:
        if not is_pipeline_enabled():
            return

        num_frames = int(round(self.duration_seconds * self.sample_rate))
        silence = b"\x00\x00" * num_frames
        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(WAV_CHANNELS)
            wav_file.setsampwidth(WAV_SAMPLE_WIDTH_BYTES)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(silence)


def _resolve_root_dir(root_dir: Path | None) -> Path:
    return (root_dir or REPO_ROOT).resolve()


def _resolve_base_dir(root_dir: Path, base_dir: Path | None) -> Path:
    return (base_dir or (root_dir / "data" / "voiceovers")).resolve()


def _relative_to_root(path: Path, root_dir: Path) -> str:
    return path.resolve().relative_to(root_dir).as_posix()


def generate_voiceover(
    script_text: str,
    run_id: str,
    slug: str,
    engine: TTSEngine | None = None,
    *,
    voice: str | None = None,
    style: str | None = None,
    created_utc: str | None = None,
    log: Callable[[str], None] | None = None,
    root_dir: Path | None = None,
    base_dir: Path | None = None,
) -> dict | None:
    if not is_pipeline_enabled():
        if log:
            log(PIPELINE_DISABLED_MESSAGE)
        return None

    if not isinstance(script_text, str) or not script_text.strip():
        raise ValueError("script_text must be a non-empty string")

    root_dir = _resolve_root_dir(root_dir)
    base_dir = _resolve_base_dir(root_dir, base_dir)
    try:
        base_dir.relative_to(root_dir)
    except ValueError as exc:
        raise ValueError("base_dir must be within root_dir") from exc

    input_sha256 = compute_input_sha256(script_text)
    wav_path, metadata_path = build_voiceover_paths(
        run_id, slug, input_sha256, base_dir=base_dir
    )
    wav_path.parent.mkdir(parents=True, exist_ok=True)

    engine = engine or NullTTSEngine()
    engine.synthesize(script_text, wav_path)

    if not wav_path.exists():
        raise RuntimeError(f"Expected WAV output was not created: {wav_path}")

    duration_seconds = round(get_wav_duration_seconds(wav_path), 6)
    engine_name = getattr(engine, "name", type(engine).__name__)

    metadata: dict[str, object] = {
        "run_id": run_id,
        "slug": slug,
        "input_sha256": input_sha256,
        "output_wav_path": _relative_to_root(wav_path, root_dir),
        "duration_seconds": duration_seconds,
        "engine_name": engine_name,
    }

    if voice is not None:
        metadata["voice"] = voice
    if style is not None:
        metadata["style"] = style
    if created_utc is not None:
        metadata["created_utc"] = created_utc

    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=True, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return metadata


def _read_script(script_path: Path | None) -> str:
    if script_path is None:
        if sys.stdin.isatty():
            raise ValueError("script must be provided via --script or stdin")
        return sys.stdin.read()
    return script_path.read_text(encoding="utf-8")


def cli_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate deterministic voiceover WAV + metadata."
    )
    parser.add_argument("--run-id", required=True, help="Run identifier (required)")
    parser.add_argument("--slug", required=True, help="Filesystem-safe slug (required)")
    parser.add_argument(
        "--script",
        type=Path,
        default=None,
        help="Path to script text file (reads stdin if omitted)",
    )
    parser.add_argument("--voice", default=None, help="Optional voice parameter")
    parser.add_argument("--style", default=None, help="Optional style parameter")

    args = parser.parse_args(argv)

    try:
        if not is_pipeline_enabled():
            print(PIPELINE_DISABLED_MESSAGE)
            return 0
        script_text = _read_script(args.script)
        metadata = generate_voiceover(
            script_text,
            args.run_id,
            args.slug,
            voice=args.voice,
            style=args.style,
            log=print,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if metadata is None:
        return 0

    print("Voiceover generated:")
    print(f"  WAV: {metadata['output_wav_path']}")
    _, metadata_path = build_voiceover_paths(
        args.run_id, args.slug, metadata["input_sha256"], base_dir=DEFAULT_VOICEOVER_DIR
    )
    print(f"  Metadata: {_relative_to_root(metadata_path, REPO_ROOT)}")
    print(f"  Engine: {metadata['engine_name']}")
    print(f"  Duration: {metadata['duration_seconds']}")
    return 0
