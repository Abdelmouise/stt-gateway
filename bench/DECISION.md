# Decision record — TTS backend selection

> Status: **draft template** — to be filled at the end of the POC.
> Owner: Gateway Voice team.

## Selection criteria (weights)

| Criterion | Weight | How measured |
|---|---|---|
| AR quality (MSA + intelligibility) | 40% | MOS (natives) ≥ 3.5/5 + WER round-trip < 15% |
| License compatibility | 25% | See `LICENSE_ANALYSIS.md` |
| Latency on target GPU | 15% | RTF < 0.5 on A100; p95 first-byte < 2s |
| Voice cloning quality | 15% | Subjective similarity ≥ 3.5/5 vs brand reference |
| Cost / VRAM / cold-start | 5% | VRAM peak, model size, load time |

## Scoring matrix (to fill)

| Model | AR (40%) | License (25%) | Latency (15%) | Cloning (15%) | Cost (5%) | **Score** |
|---|---|---|---|---|---|---|
| XTTS-v2 | / 5 | 1 / 5 (NC) | / 5 | / 5 | / 5 | |
| Chatterbox | / 5 | 5 / 5 (MIT) | / 5 | / 5 | / 5 | |
| Higgs-Audio v3 | / 5 | / 5 | / 5 | / 5 | / 5 | |
| Fish-Speech S2-Pro | / 5 | 1 / 5 (NC) | / 5 | / 5 | / 5 | |

## Decision

> **Selected backend:** _TBD_
>
> **Rationale:** _TBD_
>
> **Risks accepted:** _TBD_
>
> **Follow-up actions before production:**
> - [ ] Legal sign-off on the chosen license
> - [ ] Darija fine-tune scope (V2)
> - [ ] Voice-of-brand recording approved by marketing
> - [ ] Load test passed on OpenShift staging (5 RPS / 5 min)
