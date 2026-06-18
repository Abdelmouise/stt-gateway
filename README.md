# TTS Gateway (FR / EN / AR)

Multilingual Text-to-Speech service for the banking virtual assistant.
Companion to the existing STT + translation gateway.

## Status

- **Phase 1 (current):** model evaluation / POC — short-list of 4 candidates.
- **Phase 2:** FastAPI service skeleton, ready to plug the winning backend.
- **Phase 3:** OpenShift deployment on A100/H100 GPUs.

## Short-list under evaluation

| Model | FR | EN | AR MSA | Voice cloning | License | Risk |
|---|---|---|---|---|---|---|
| Coqui XTTS-v2 | ✅ | ✅ | ✅ | 6s ref | CPML (NC) | 🔴 — reference baseline only |
| Chatterbox Multilingual | ✅ | ✅ | ❓ to verify | ✅ | MIT | 🟢 — primary commercial target |
| Higgs-Audio v3 (4B) | ✅ | ✅ | ⚠️ to verify | ✅ | TBD | 🟠 |
| Fish-Speech S2-Pro (5B) | ✅ | ✅ | ⚠️ to verify | ✅ | CC-BY-NC-SA | 🔴 — quality plan B |

Plus baseline: `facebook/mms-tts-{ara,fra,eng}` (NC, reference quality only).

## Quick start (local POC)

```bash
# Create env
python -m venv .venv && source .venv/bin/activate
pip install -e ".[bench,xtts]"   # add other extras as needed

# Run service skeleton with the dummy backend
uvicorn tts_gateway.app.main:app --reload --port 8000

# Smoke test
curl -X POST http://localhost:8000/v1/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text":"Bonjour, votre solde est de 1234 euros.","lang":"fr","voice_id":"brand_default"}' \
  --output out.wav
```

## Run the benchmark

```bash
# 1) Place a brand voice reference at bench/voice_refs/brand_fr.wav (~6-10s, 24kHz mono)
# 2) Pick which models to test
pip install -e ".[bench,xtts,chatterbox]"
python bench/run_bench.py --models xtts,chatterbox --langs fr,en,ar_msa
# Outputs: bench/results.csv + bench/audio/{model}/{lang}/{idx}.wav

# Note: on macOS, `chatterbox` extra is marker-gated and may be skipped due
# upstream torch/chatterbox wheel constraints. Use Linux GPU hosts for that backend.
```

## Repository layout

```
src/tts_gateway/    # service code (FastAPI app + backends)
bench/              # POC harness (prompts, runner, scoring, decision docs)
deploy/openshift/   # OCP manifests
tests/              # unit + integration tests
```

## Verification gates

See [memory/session/plan.md] (planning notes) for the 7 quality gates the project must pass before production rollout.
