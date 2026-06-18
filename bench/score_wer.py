"""Compute round-trip WER: synthesized audio -> ASR -> compare to source text.

Run after run_bench.py:

    python bench/score_wer.py --whisper-model large-v3 --device cuda
    # adds wer / cer columns to bench/results.csv (or writes results_wer.csv)
"""

from __future__ import annotations

import argparse
import csv
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("score-wer")

BENCH_DIR = Path(__file__).parent
PROMPTS_DIR = BENCH_DIR / "prompts"
AUDIO_DIR = BENCH_DIR / "audio"

# Whisper expects ISO-639-1 codes; map our internal codes.
_WHISPER_LANG = {"fr": "fr", "en": "en", "ar_msa": "ar", "ar_darija": "ar"}


def load_prompt_text(lang: str) -> dict[str, str]:
    import json
    path = PROMPTS_DIR / f"{lang}.jsonl"
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        out[obj["id"]] = obj["text"]
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=BENCH_DIR / "results.csv")
    parser.add_argument("--out", type=Path, default=BENCH_DIR / "results_wer.csv")
    parser.add_argument("--whisper-model", default="large-v3")
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    try:
        from faster_whisper import WhisperModel  # noqa: PLC0415
        from jiwer import cer, wer  # noqa: PLC0415
    except ImportError as exc:
        raise SystemExit(
            "Missing deps. Install with: pip install -e '.[bench]'"
        ) from exc

    logger.info("Loading faster-whisper %s on %s ...", args.whisper_model, args.device)
    model = WhisperModel(args.whisper_model, device=args.device, compute_type="default")

    if not args.results.exists():
        raise SystemExit(f"{args.results} not found. Run run_bench.py first.")

    rows: list[dict] = []
    with args.results.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    prompts_cache: dict[str, dict[str, str]] = {}
    out_rows: list[dict] = []

    for row in rows:
        if row.get("error"):
            row["wer"] = ""
            row["cer"] = ""
            row["transcript"] = ""
            out_rows.append(row)
            continue

        lang = row["lang"]
        prompts_cache.setdefault(lang, load_prompt_text(lang))
        ref_text = prompts_cache[lang].get(row["prompt_id"], "")
        wav_path = AUDIO_DIR / row["model"] / lang / f"{row['prompt_id']}.wav"
        if not wav_path.exists() or not ref_text:
            row["wer"] = ""
            row["cer"] = ""
            row["transcript"] = ""
            out_rows.append(row)
            continue

        whisper_lang = _WHISPER_LANG.get(lang, lang)
        try:
            segments, _ = model.transcribe(str(wav_path), language=whisper_lang)
            hyp = " ".join(segment.text.strip() for segment in segments if segment.text).strip()
        except Exception as exc:
            logger.warning("ASR failed on %s: %s", wav_path, exc)
            hyp = ""

        try:
            row["wer"] = round(wer(ref_text, hyp), 4) if hyp else ""
            row["cer"] = round(cer(ref_text, hyp), 4) if hyp else ""
        except Exception:
            row["wer"] = ""
            row["cer"] = ""
        row["transcript"] = hyp
        out_rows.append(row)
        logger.info(
            "[%s/%s/%s] wer=%s cer=%s",
            row["model"], lang, row["prompt_id"], row["wer"], row["cer"],
        )

    fieldnames = list(out_rows[0].keys()) if out_rows else []
    with args.out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)
    logger.info("Wrote %d rows to %s", len(out_rows), args.out)


if __name__ == "__main__":
    main()
