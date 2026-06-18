"""
Client examples for TTS Gateway via LiteLLM
Montre comment intégrer avec l'endpoint OpenAI-compatible
"""

# ============================================
# Python Client (Recommended)
# ============================================

import asyncio
from litellm import acompletion
from openai import AsyncOpenAI

# Option 1: Direct LiteLLM call
async def tts_synthesize_litellm(
    text: str,
    lang: str = "fr",
    voice_id: str = "brand_default",
    api_key: str = "sk-litellm-...",
):
    """
    Appel direct via LiteLLM
    """
    response = await acompletion(
        model="tts-gateway-chatterbox",
        messages=[
            {
                "role": "user",
                "content": text,
                "lang": lang,
                "voice_id": voice_id,
            }
        ],
        api_base="https://litellm-route.apps.openshift.local",
        api_key=api_key,
        timeout=60,
    )
    
    # Response contient l'audio WAV en base64 ou bytes
    audio_data = response.choices[0].content
    return audio_data


# Option 2: OpenAI-compatible client (recommandé pour migration)
async def tts_synthesize_openai_compatible(
    text: str,
    lang: str = "fr",
    voice_id: str = "brand_default",
    api_key: str = "sk-litellm-...",
):
    """
    Via client OpenAI-compatible (plus facile à intégrer)
    """
    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://litellm-route.apps.openshift.local/v1",
        timeout=60,
    )
    
    response = await client.audio.speech.create(
        model="tts-gateway",
        input=text,
        voice=voice_id,
        response_format="wav",
        extra_body={
            "language": lang,
            "voice_id": voice_id,
        },
    )
    
    audio_data = response.content
    return audio_data


# Option 3: Direct TTS Gateway (bypass LiteLLM for low latency)
async def tts_synthesize_direct(
    text: str,
    lang: str = "fr",
    voice_id: str = "brand_default",
    api_key: str = "sk-admin-...",
):
    """
    Appel direct au TTS Gateway (moins de latence, pas de load balancing)
    """
    import httpx
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://tts-gateway.voice-gateway.svc.cluster.local:8000/v1/synthesize",
            json={
                "text": text,
                "lang": lang,
                "voice_id": voice_id,
            },
            headers={
                "X-API-Key": api_key,
            },
            timeout=30,
        )
        
        if response.status_code != 200:
            raise Exception(f"TTS failed: {response.text}")
        
        return response.content


# ============================================
# FastAPI Integration
# ============================================

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
import io

app = FastAPI()

@app.post("/api/speak")
async def speak(
    text: str,
    lang: str = "fr",
    voice_id: str = "brand_default",
    stream: bool = False,
):
    """
    Endpoint qui appelle TTS Gateway via LiteLLM
    """
    try:
        # Call TTS via LiteLLM
        audio_bytes = await tts_synthesize_openai_compatible(
            text=text,
            lang=lang,
            voice_id=voice_id,
            api_key="sk-litellm-...",  # À passer via env var
        )
        
        if stream:
            # Stream audio response
            return StreamingResponse(
                io.BytesIO(audio_bytes),
                media_type="audio/wav",
                headers={"Content-Disposition": "attachment; filename=speech.wav"},
            )
        else:
            # Return full audio
            return StreamingResponse(
                io.BytesIO(audio_bytes),
                media_type="audio/wav",
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Celery Worker (Async processing)
# ============================================

from celery import Celery
import logging

celery_app = Celery("tts_tasks")
logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3)
def synthesize_audio(
    self,
    text: str,
    lang: str = "fr",
    voice_id: str = "brand_default",
):
    """
    Celery task pour TTS (utile pour batch processing)
    """
    try:
        audio_data = asyncio.run(
            tts_synthesize_openai_compatible(
                text=text,
                lang=lang,
                voice_id=voice_id,
            )
        )
        
        # Sauvegarder ou envoyer l'audio quelque part
        logger.info(f"✓ Synthesized {len(audio_data)} bytes")
        return {"status": "success", "size": len(audio_data)}
    
    except Exception as exc:
        logger.error(f"Task failed: {exc}")
        # Retry avec backoff exponentiel
        self.retry(exc=exc, countdown=2 ** self.request.retries)


# ============================================
# cURL Examples
# ============================================

"""
# 1️⃣ Direct call to TTS Gateway
curl -X POST http://localhost:8000/v1/synthesize \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-admin-..." \
  -d '{
    "text": "Bonjour, votre solde est de 1234 euros",
    "lang": "fr",
    "voice_id": "brand_default"
  }' \
  --output audio.wav


# 2️⃣ Via LiteLLM (with load balancing)
curl -X POST https://litellm-route.apps.openshift.local/v1/audio/speech \
  -H "Authorization: Bearer sk-litellm-..." \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tts-gateway",
    "input": "Bonjour test",
    "voice": "brand_default",
    "language": "fr"
  }' \
  --output audio.wav


# 3️⃣ Check health
curl http://localhost:8000/healthz
curl http://localhost:8000/readyz


# 4️⃣ Get available voices
curl -H "X-API-Key: sk-admin-..." \
  http://localhost:8000/v1/voices


# 5️⃣ Get metrics (Prometheus)
curl http://localhost:8000/metrics | grep tts_
"""


# ============================================
# Node.js Client Example
# ============================================

"""
import OpenAI from 'openai';
import fs from 'fs';

const client = new OpenAI({
  apiKey: process.env.LITELLM_API_KEY,
  baseURL: 'https://litellm-route.apps.openshift.local/v1',
});

async function synthesizeAudio(text, lang = 'fr', voiceId = 'brand_default') {
  const response = await client.audio.speech.create({
    model: 'tts-gateway',
    input: text,
    voice: voiceId,
    response_format: 'wav',
    extra_body: {
      language: lang,
      voice_id: voiceId,
    },
  });

  // Save to file
  const buffer = Buffer.from(await response.arrayBuffer());
  fs.writeFileSync('output.wav', buffer);
  console.log('✓ Audio saved to output.wav');
}

// Usage
synthesizeAudio('Bonjour le monde', 'fr', 'brand_default');
"""


# ============================================
# React / Web Frontend Example
# ============================================

"""
import React, { useState } from 'react';

export function TTSComponent() {
  const [text, setText] = useState('Bonjour');
  const [lang, setLang] = useState('fr');
  const [loading, setLoading] = useState(false);

  const handleSynthesize = async () => {
    setLoading(true);
    try {
      const response = await fetch(
        'https://litellm-route.apps.openshift.local/v1/audio/speech',
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${process.env.REACT_APP_LITELLM_KEY}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            model: 'tts-gateway',
            input: text,
            language: lang,
            voice: 'brand_default',
          }),
        }
      );

      if (!response.ok) throw new Error('TTS failed');

      // Create audio blob and play
      const blob = await response.blob();
      const audio = new Audio(URL.createObjectURL(blob));
      audio.play();
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <textarea value={text} onChange={(e) => setText(e.target.value)} />
      <select value={lang} onChange={(e) => setLang(e.target.value)}>
        <option value="fr">Français</option>
        <option value="en">English</option>
        <option value="ar">العربية</option>
      </select>
      <button onClick={handleSynthesize} disabled={loading}>
        {loading ? 'Speaking...' : 'Speak'}
      </button>
    </div>
  );
}
"""


# ============================================
# Monitoring & Logging
# ============================================

"""
# Check TTS Gateway metrics
oc port-forward -n voice-gateway svc/tts-gateway 8000:8000
curl http://localhost:8000/metrics | grep -E '(request|error|latency|gpu)'

# Check LiteLLM metrics
oc port-forward -n voice-gateway svc/litellm 8001:8001
curl http://localhost:8001/metrics

# Stream logs
oc -n voice-gateway logs -f deployment/tts-gateway --all-containers=true
oc -n voice-gateway logs -f deployment/litellm-proxy

# Get pod events
oc -n voice-gateway describe pod tts-gateway-xxxx
"""


# ============================================
# Error Handling & Retry Logic
# ============================================

from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
)
async def tts_with_retry(text: str, **kwargs):
    """Retry avec backoff exponentiel"""
    return await tts_synthesize_openai_compatible(text=text, **kwargs)


# ============================================
# Performance Optimization Tips
# ============================================

"""
✅ Performance Best Practices:

1. Batch requests (si possible):
   - Synthétiser plusieurs textes en parallèle
   - Utiliser Celery pour async processing
   - Utiliser connection pooling

2. Caching:
   - Cache les résultats audio pour textes identiques
   - Utiliser Redis pour cache distribué
   - TTL: 24h (les voix ne changent pas)

3. Load Balancing via LiteLLM:
   - Utiliser least_busy_requests strategy
   - Monitoring via Prometheus
   - Auto-scaling basé sur latency

4. GPU optimization:
   - Warm-up modèle au startup
   - Batch processing sur GPU
   - Monitoring VRAM leaks

5. Latency targets:
   - p50: < 0.5s (courte synthèse)
   - p95: < 2s (acceptable)
   - p99: < 3s (max SLA)
"""
