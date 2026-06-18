# Multi-stage CUDA image for the TTS gateway.
# Base: NVIDIA CUDA 12.4 + cuDNN runtime on Ubuntu 22.04 (matches OpenShift A100/H100 nodes).
# Adapt the base tag to the cluster's CUDA driver version.

ARG CUDA_VERSION=12.4.1
ARG PYTHON_VERSION=3.11

FROM nvidia/cuda:${CUDA_VERSION}-cudnn-runtime-ubuntu22.04 AS base

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/cache/huggingface \
    XDG_CACHE_HOME=/cache

RUN apt-get update && apt-get install -y --no-install-recommends \
        python${PYTHON_VERSION} python${PYTHON_VERSION}-dev python3-pip \
        ffmpeg libsndfile1 \
        ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && update-alternatives --install /usr/bin/python python /usr/bin/python${PYTHON_VERSION} 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python${PYTHON_VERSION} 1

# Non-root user (OpenShift runs containers with arbitrary UIDs by default).
RUN useradd --create-home --uid 10001 --shell /bin/bash app
WORKDIR /app

# Install Python deps (build stage to leverage layer caching).
COPY pyproject.toml README.md ./
COPY src ./src

# Install only what the running service needs. Backend extras are passed via
# --build-arg BACKEND_EXTRA=chatterbox once the POC has selected the winner.
ARG BACKEND_EXTRA=
RUN pip install --upgrade pip wheel \
    && if [ -n "${BACKEND_EXTRA}" ]; then \
         pip install -e ".[${BACKEND_EXTRA}]"; \
       else \
         pip install -e "."; \
       fi

# Cache & voices live on PVCs mounted at runtime.
RUN mkdir -p /cache /app/voices \
    && chown -R app:app /app /cache

USER 10001

ENV TTS_VOICES_DIR=/app/voices \
    TTS_MODEL_CACHE_DIR=/cache/huggingface \
    TTS_LOG_LEVEL=INFO

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -fsS http://localhost:8000/healthz || exit 1

CMD ["uvicorn", "tts_gateway.app.main:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "1", "--log-config", "/dev/null"]
