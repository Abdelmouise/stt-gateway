"""POC bench harness.

Runs each (model × prompt × lang) combination, captures audio, and records
RTF / latency / VRAM metrics. WER (round-trip TTS->ASR) is computed in a
separate step to keep the heavy ASR model load optional.

Usage:
    python bench/run_bench.py --models xtts,chatterbox --langs fr,en,ar_msa
    python bench/run_bench.py --models all --langs all --voice-ref bench/voice_refs/brand_fr.wav

Outputs:
    bench/results.csv
    bench/audio/{model}/{lang}/{prompt_id}.wav
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import time
from pathlib import Path

import numpy as np
import soundfile as sf

from tts_gateway.app.backends import BackendBase, get_backend
from tts_gateway.app.backends.loader import import_all_backends

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("bench")

BENCH_DIR = Path(__file__).parent
PROMPTS_DIR = BENCH_DIR / "prompts"
AUDIO_DIR = BENCH_DIR / "audio"
RESULTS_CSV = BENCH_DIR / "results.csv"

ALL_LANGS = ["fr", "en", "ar_msa", "ar_darija"]
ALL_MODELS = ["xtts", "chatterbox", "higgs", "fish_speech", "piper"]


def load_prompts(lang: str) -> list[dict]:
    path = PROMPTS_DIR / f"{lang}.jsonl"
    if not path.exists():
        logger.warning("No prompts file for lang=%s (%s)", lang, path)
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def measure_vram_mb(device: str) -> float:
    if device != "cuda":
        return 0.0
    try:
        import torch  # noqa: PLC0415
    except ImportError:
        return 0.0
    if not torch.cuda.is_available():
        return 0.0
    return torch.cuda.max_memory_allocated() / (1024 * 1024)


def reset_vram_peak(device: str) -> None:
    if device != "cuda":
        return
    try:
        import torch  # noqa: PLC0415
    except ImportError:
        return
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()


def run_one(
    backend: BackendBase,
    prompt: dict,
    lang: str,
    voice_ref: Path | None,
    out_dir: Path,
) -> dict:
    out_path = out_dir / f"{prompt['id']}.wav"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    reset_vram_peak(backend.device)
    t0 = time.perf_counter()
    error: str | None = None
    audio_seconds = 0.0
    sample_rate = 0

    try:
        result = backend.synthesize(
            text=prompt["text"], lang=lang, voice_ref=voice_ref, speaker_id=None
        )
        elapsed = time.perf_counter() - t0
        audio = np.asarray(result.audio, dtype=np.float32)
        sample_rate = int(result.sample_rate)
        audio_seconds = len(audio) / sample_rate if sample_rate else 0.0
        sf.write(out_path, audio, sample_rate, subtype="PCM_16")
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        error = f"{type(exc).__name__}: {exc}"
        logger.exception("Failed: model=%s lang=%s id=%s", backend.name, lang, prompt["id"])

    rtf = (elapsed / audio_seconds) if audio_seconds > 0 else float("nan")
    return {
        "model": backend.name,
        "device": backend.device,
        "lang": lang,
        "prompt_id": prompt["id"],
        "category": prompt.get("category", ""),
        "text_len": len(prompt["text"]),
        "audio_seconds": round(audio_seconds, 3),
        "synth_seconds": round(elapsed, 3),
        "rtf": round(rtf, 3) if rtf == rtf else "",
        "sample_rate": sample_rate,
        "vram_peak_mb": round(measure_vram_mb(backend.device), 1),
        "error": error or "",
    }


def parse_csv_list(s: str, allowed: list[str]) -> list[str]:
    if s == "all":
        return list(allowed)
    items = [x.strip() for x in s.split(",") if x.strip()]
    unknown = set(items) - set(allowed)
    if unknown:
        raise SystemExit(f"Unknown values: {sorted(unknown)}; allowed: {allowed}")
    return items


def main() -> None:
    parser = argparse.ArgumentParser(description="TTS POC benchmark runner")
    parser.add_argument("--models", default="all", help=f"comma-separated; one of {ALL_MODELS} or 'all'")
    parser.add_argument("--langs", default="all", help=f"comma-separated; one of {ALL_LANGS} or 'all'")
    parser.add_argument("--device", default="cpu", help="cpu | cuda | mps")
    parser.add_argument(
        "--voice-ref",
        type=Path,
        default=BENCH_DIR / "voice_refs" / "brand_fr.wav",
        help="Path to brand voice WAV reference",
    )
    parser.add_argument("--out", type=Path, default=RESULTS_CSV, help="Output CSV path")
    args = parser.parse_args()

    import_all_backends()
    models = parse_csv_list(args.models, ALL_MODELS)
    langs = parse_csv_list(args.langs, ALL_LANGS)

    voice_ref = args.voice_ref if args.voice_ref.exists() else None
    if voice_ref is None:
        logger.warning("Voice ref %s not found — backends needing cloning will fail.", args.voice_ref)

    rows: list[dict] = []
    for model_name in models:
        try:
            backend_cls = get_backend(model_name)
        except KeyError:
            logger.error("Backend %s not registered (missing extras?). Skipping.", model_name)
            continue
        try:
            backend = backend_cls(device=args.device)
            backend.load()
        except Exception as exc:
            logger.error("Failed to load %s: %s. Skipping.", model_name, exc)
            continue

        for lang in langs:
            prompts = load_prompts(lang)
            if not prompts:
                continue
            if lang not in backend.supported_langs:
                logger.info("%s does not support %s — skipping.", model_name, lang)
                continue
            out_dir = AUDIO_DIR / model_name / lang
            for prompt in prompts:
                row = run_one(backend, prompt, lang, voice_ref, out_dir)
                rows.append(row)
                logger.info(
                    "[%s/%s/%s] rtf=%s err=%s",
                    row["model"], row["lang"], row["prompt_id"], row["rtf"], row["error"] or "-",
                )

    fieldnames = [
        "model", "device", "lang", "prompt_id", "category", "text_len",
        "audio_seconds", "synth_seconds", "rtf", "sample_rate",
        "vram_peak_mb", "error",
    ]
    with args.out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    logger.info("Wrote %d rows to %s", len(rows), args.out)


if __name__ == "__main__":
    main()
