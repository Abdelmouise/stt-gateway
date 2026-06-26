"""STT benchmark runner (API mode).

Runs batch transcription against the local/remote STT API and writes a CSV
report with per-file transcription and latency metrics.

Usage examples:
    python bench/stt_run_bench.py \
      --audio-dir /Users/abdelmouise/Downloads/darija-2 \
      --api-url http://localhost:8000

    python bench/stt_run_bench.py \
      --audio-dir /Users/abdelmouise/Downloads/darija-2 \
      --out bench/stt_results.csv \
      --limit 20
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("stt-bench")

BENCH_DIR = Path(__file__).parent
DEFAULT_OUT = BENCH_DIR / "stt_results.csv"

EXT_TO_MIME = {
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
}


def _percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    if p <= 0:
        return min(values)
    if p >= 100:
        return max(values)
    sorted_values = sorted(values)
    rank = math.ceil((p / 100.0) * len(sorted_values)) - 1
    rank = max(0, min(rank, len(sorted_values) - 1))
    return sorted_values[rank]


def collect_audio_files(audio_dir: Path, recursive: bool) -> list[Path]:
    if recursive:
        candidates = [p for p in audio_dir.rglob("*") if p.is_file()]
    else:
        candidates = [p for p in audio_dir.iterdir() if p.is_file()]

    files = [p for p in candidates if p.suffix.lower() in EXT_TO_MIME]
    return sorted(files, key=lambda p: p.name.lower())


def build_multipart_body(
    field_name: str,
    filename: str,
    content_type: str,
    payload: bytes,
) -> tuple[bytes, str]:
    boundary = f"----sttbench{uuid.uuid4().hex}"
    head = (
        f"--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"{field_name}\"; filename=\"{filename}\"\r\n"
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode("utf-8")
    tail = f"\r\n--{boundary}--\r\n".encode("utf-8")
    return head + payload + tail, boundary


def parse_error_detail(response_body: bytes) -> str:
    if not response_body:
        return ""
    try:
        obj = json.loads(response_body.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return response_body.decode("utf-8", errors="replace").strip()

    if isinstance(obj, dict) and "detail" in obj:
        return str(obj["detail"])
    return json.dumps(obj, ensure_ascii=False)


def check_health(api_url: str, timeout_s: float) -> None:
    health_url = f"{api_url.rstrip('/')}/healthz"
    req = urllib.request.Request(health_url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout_s):
        pass


def transcribe_one(
    api_url: str,
    audio_file: Path,
    timeout_s: float,
    lang: str | None,
) -> dict:
    mime = EXT_TO_MIME[audio_file.suffix.lower()]
    audio_bytes = audio_file.read_bytes()
    started = time.perf_counter()

    if len(audio_bytes) == 0:
        elapsed = time.perf_counter() - started
        return {
            "filename": audio_file.name,
            "transcription": "",
            "language": "",
            "processing_time_s": round(elapsed, 3),
            "status_code": 0,
            "error": "Empty file",
        }

    form_body, boundary = build_multipart_body(
        field_name="file",
        filename=audio_file.name,
        content_type=mime,
        payload=audio_bytes,
    )

    endpoint = f"{api_url.rstrip('/')}/v1/transcribe"
    if lang:
        endpoint = f"{endpoint}?{urllib.parse.urlencode({'lang': lang})}"

    req = urllib.request.Request(
        endpoint,
        data=form_body,
        method="POST",
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            elapsed = time.perf_counter() - started
            body = resp.read()
            payload = json.loads(body.decode("utf-8", errors="replace"))
            return {
                "filename": audio_file.name,
                "transcription": str(payload.get("text", "")),
                "language": str(payload.get("language") or ""),
                "processing_time_s": round(elapsed, 3),
                "status_code": resp.status,
                "error": "",
            }
    except urllib.error.HTTPError as exc:
        elapsed = time.perf_counter() - started
        detail = parse_error_detail(exc.read())
        return {
            "filename": audio_file.name,
            "transcription": "",
            "language": "",
            "processing_time_s": round(elapsed, 3),
            "status_code": exc.code,
            "error": detail or f"HTTP {exc.code}",
        }
    except (urllib.error.URLError, TimeoutError) as exc:
        elapsed = time.perf_counter() - started
        return {
            "filename": audio_file.name,
            "transcription": "",
            "language": "",
            "processing_time_s": round(elapsed, 3),
            "status_code": 0,
            "error": f"Request failed: {exc}",
        }
    except json.JSONDecodeError as exc:
        elapsed = time.perf_counter() - started
        return {
            "filename": audio_file.name,
            "transcription": "",
            "language": "",
            "processing_time_s": round(elapsed, 3),
            "status_code": 200,
            "error": f"Invalid JSON response: {exc}",
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="STT API benchmark runner")
    parser.add_argument(
        "--audio-dir",
        type=Path,
        required=True,
        help="Directory containing audio files (.wav, .m4a)",
    )
    parser.add_argument("--api-url", default="http://localhost:8000", help="Base API URL")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output CSV path")
    parser.add_argument("--timeout", type=float, default=120.0, help="Per-request timeout in seconds")
    parser.add_argument("--limit", type=int, default=0, help="Process only first N files (0 = all)")
    parser.add_argument("--lang", default="", help="Optional lang hint: fr|en|ar|ar_darija")
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Include audio files from subdirectories",
    )
    args = parser.parse_args()

    if not args.audio_dir.exists() or not args.audio_dir.is_dir():
        raise SystemExit(f"Audio directory not found: {args.audio_dir}")

    lang = args.lang.strip() or None
    if lang is not None and lang not in {"fr", "en", "ar", "ar_darija"}:
        raise SystemExit("Invalid --lang. Allowed values: fr,en,ar,ar_darija")

    try:
        check_health(args.api_url, timeout_s=min(args.timeout, 10.0))
    except Exception as exc:
        raise SystemExit(f"API health check failed on {args.api_url}/healthz: {exc}") from exc

    files = collect_audio_files(args.audio_dir, recursive=args.recursive)
    if not files:
        raise SystemExit(f"No supported audio files found in {args.audio_dir} (.wav, .m4a)")

    if args.limit > 0:
        files = files[: args.limit]

    logger.info(
        "Starting STT benchmark on %d files (recursive=%s, lang=%s)",
        len(files),
        args.recursive,
        lang or "auto",
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "filename",
        "transcription",
        "language",
        "processing_time_s",
        "status_code",
        "error",
    ]
    rows: list[dict] = []
    with args.out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        f.flush()

        for idx, audio_file in enumerate(files, start=1):
            row = transcribe_one(
                api_url=args.api_url,
                audio_file=audio_file,
                timeout_s=args.timeout,
                lang=lang,
            )
            rows.append(row)
            writer.writerow(row)
            f.flush()
            logger.info(
                "[%d/%d] %s status=%s t=%ss err=%s",
                idx,
                len(files),
                row["filename"],
                row["status_code"],
                row["processing_time_s"],
                row["error"] or "-",
            )

    ok_rows = [r for r in rows if not r["error"] and int(r["status_code"]) == 200]
    fail_count = len(rows) - len(ok_rows)
    latencies = [float(r["processing_time_s"]) for r in ok_rows]
    p50 = _percentile(latencies, 50)
    p95 = _percentile(latencies, 95)
    avg = statistics.mean(latencies) if latencies else None

    logger.info("Wrote %d rows to %s", len(rows), args.out)
    logger.info(
        "Summary: total=%d success=%d fail=%d avg=%.3fs p50=%s p95=%s",
        len(rows),
        len(ok_rows),
        fail_count,
        avg or 0.0,
        f"{p50:.3f}s" if p50 is not None else "n/a",
        f"{p95:.3f}s" if p95 is not None else "n/a",
    )


if __name__ == "__main__":
    main()
