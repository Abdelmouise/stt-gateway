"""Streamlit MOS scoring app for human evaluation.

Run:
    streamlit run bench/score_subjective.py
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

import streamlit as st

BENCH_DIR = Path(__file__).parent
AUDIO_DIR = BENCH_DIR / "audio"
SCORES_CSV = BENCH_DIR / "subjective_scores.csv"


def list_audio_files() -> list[Path]:
    if not AUDIO_DIR.exists():
        return []
    return sorted(AUDIO_DIR.rglob("*.wav"))


def append_score(row: dict) -> None:
    new = not SCORES_CSV.exists()
    with SCORES_CSV.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if new:
            writer.writeheader()
        writer.writerow(row)


def main() -> None:
    st.set_page_config(page_title="TTS MOS", page_icon="🎙️")
    st.title("Subjective MOS scoring (1–5)")

    rater = st.text_input("Rater name", value="anon")
    files = list_audio_files()
    if not files:
        st.warning(f"No audio files found in {AUDIO_DIR}. Run run_bench.py first.")
        return

    idx = st.session_state.setdefault("idx", 0)
    if idx >= len(files):
        st.success("All clips scored. 🎉")
        return

    f = files[idx]
    rel = f.relative_to(AUDIO_DIR)
    parts = rel.parts  # model / lang / prompt_id.wav
    model, lang, prompt_id = parts[0], parts[1], parts[2].rsplit(".", 1)[0]

    st.subheader(f"Clip {idx + 1} / {len(files)}")
    st.caption(f"model={model} · lang={lang} · prompt_id={prompt_id}")
    st.audio(str(f))

    naturalness = st.slider("Naturalness (1=robotic, 5=human)", 1, 5, 3, key=f"nat-{idx}")
    intelligibility = st.slider("Intelligibility (1=unclear, 5=crisp)", 1, 5, 3, key=f"int-{idx}")
    accent = st.slider(
        "Accent appropriateness (1=foreign, 5=native target)", 1, 5, 3, key=f"acc-{idx}"
    )
    similarity = st.slider(
        "Voice similarity to brand reference (1=different, 5=same)", 1, 5, 3, key=f"sim-{idx}"
    )
    notes = st.text_area("Notes", key=f"notes-{idx}")

    if st.button("Save & next", type="primary"):
        append_score({
            "ts": datetime.utcnow().isoformat(),
            "rater": rater,
            "model": model,
            "lang": lang,
            "prompt_id": prompt_id,
            "naturalness": naturalness,
            "intelligibility": intelligibility,
            "accent": accent,
            "similarity": similarity,
            "notes": notes,
        })
        st.session_state["idx"] = idx + 1
        st.rerun()


if __name__ == "__main__":
    main()
