# License analysis — TTS short-list

> Status: **draft** — to be reviewed by the bank's legal team before any production use.
> Date of last update: 2026-06-15.

| Model | Repo | License | Commercial use | Distribution of derivatives | Risk |
|---|---|---|---|---|---|
| Coqui XTTS-v2 | huggingface.co/coqui/XTTS-v2 | Coqui Public Model License (CPML) | ❌ Not permitted | Restricted | 🔴 |
| Chatterbox Multilingual | huggingface.co/ResembleAI/chatterbox | MIT | ✅ Permitted | ✅ Permitted (with notice) | 🟢 |
| Higgs-Audio v3 | huggingface.co/bosonai/higgs-audio-v3-tts-4b | TBD — read the model card | TBD | TBD | 🟠 |
| Fish-Speech S2-Pro | huggingface.co/fishaudio/s2-pro | CC-BY-NC-SA-4.0 | ❌ Not permitted | ✅ but ShareAlike + NC | 🔴 |
| MMS-TTS (`facebook/mms-tts-{ara,fra,eng}`) | huggingface.co/facebook | CC-BY-NC-4.0 | ❌ Not permitted | NC | 🔴 |

## Per-model details

### Coqui XTTS-v2 — 🔴 NON-COMMERCIAL
- License URL: https://coqui.ai/cpml
- Reason for use in POC: industry reference for voice-cloning + AR support, used as a quality baseline only.
- Action: do NOT deploy to production. Document the comparison results.

### Chatterbox Multilingual (Resemble AI) — 🟢 PERMISSIVE (preferred target)
- License: MIT.
- Action: validate AR coverage empirically (POC step 5–6). If MOS gate is passed, this is the production candidate.
- Caveat: keep the upstream copyright notice in distributed images.

### Higgs-Audio v3 — 🟠 TO VERIFY
- Action: open the official model card, paste the LICENSE text into this file once confirmed.
- If permissive: candidate. Otherwise: dropped from production short-list.

### Fish-Speech S2-Pro — 🔴 NON-COMMERCIAL
- License: CC-BY-NC-SA-4.0.
- Reason for use in POC: quality reference / plan-B if Chatterbox AR fails.
- Action: do NOT deploy. Negotiate commercial license with Fish Audio if quality is decisive.

### MMS-TTS (Meta / Fairseq) — 🔴 NON-COMMERCIAL
- License: CC-BY-NC-4.0.
- Reason for use in POC: AR MSA quality baseline (small VITS, fast).
- Action: do NOT deploy.

## Decision rule for production

A backend is production-eligible only if **all** the following hold:
1. License is OSI-approved permissive (MIT / Apache-2.0 / BSD) **or** explicitly cleared by the bank's legal team.
2. Quality gates from `DECISION.md` are met for FR + EN + AR MSA.
3. The model weights are available with a stable hash and can be cached on a PVC.

## TODO
- [ ] Confirm Higgs-Audio v3 license text and update this file.
- [ ] Cross-check that any optional dependency installed alongside the chosen model does not relicense the inference code under a copyleft surface.
- [ ] Get formal written sign-off from legal before stamping a model "approved".
