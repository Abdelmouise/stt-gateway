#!/bin/bash
# Deploy TTS Gateway + LiteLLM to OpenShift
# Usage: ./deploy.sh <namespace> <image-tag> <model>

set -e

NAMESPACE="${1:-voice-gateway}"
IMAGE_TAG="${2:-latest}"
MODEL="${3:-chatterbox}"

echo "🚀 TTS Gateway + LiteLLM Deployment Script"
echo "=========================================="
echo "Namespace: $NAMESPACE"
echo "Image tag: $IMAGE_TAG"
echo "Model: $MODEL"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Function to print colored output
print_step() {
    echo -e "${GREEN}→${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# 1️⃣ Create namespace
print_step "Creating namespace..."
oc create namespace $NAMESPACE 2>/dev/null || true
oc label namespace $NAMESPACE openshift.io/cluster-monitoring=true --overwrite

# 2️⃣ Create secrets
print_step "Creating secrets..."

# Generate random API keys
ADMIN_API_KEY=$(openssl rand -hex 32)
LITELLM_MASTER_KEY=$(openssl rand -hex 32)

oc -n $NAMESPACE create secret generic tts-gateway-secrets \
  --from-literal=admin-api-key="$ADMIN_API_KEY" \
  --dry-run=client -o yaml | oc apply -f -

oc -n $NAMESPACE create secret generic litellm-secrets \
  --from-literal=master-key="$LITELLM_MASTER_KEY" \
  --dry-run=client -o yaml | oc apply -f -

print_warning "Generated API keys (save these!):"
echo "  Admin API Key: $ADMIN_API_KEY"
echo "  LiteLLM Master Key: $LITELLM_MASTER_KEY"

# 3️⃣ Create PVCs
print_step "Creating PersistentVolumeClaims..."
oc -n $NAMESPACE apply -f deploy/openshift/pvc.yaml

# Wait for PVCs to bind
print_step "Waiting for PVCs to bind..."
oc -n $NAMESPACE wait --for=jsonpath='{.status.phase}'=Bound pvc/tts-model-cache --timeout=300s 2>/dev/null || true
oc -n $NAMESPACE wait --for=jsonpath='{.status.phase}'=Bound pvc/tts-voices --timeout=300s 2>/dev/null || true

# 4️⃣ Update deployment image
print_step "Updating deployment image..."
# Adapter le tag d'image selon votre registry
REGISTRY="${REGISTRY:-image-registry.openshift-image-registry.svc:5000}"
REPO="${REPO:-voice-gateway}"

sed -i.bak "s|image-registry.openshift-image-registry.svc:5000/voice-gateway/tts-gateway:.*|${REGISTRY}/${REPO}/tts-gateway:${IMAGE_TAG}|g" \
  deploy/openshift/deployment.yaml
rm -f deploy/openshift/deployment.yaml.bak

# 5️⃣ Update configmap with model
print_step "Updating ConfigMap with model: $MODEL..."
oc -n $NAMESPACE patch configmap tts-gateway-config \
  --type merge \
  -p '{"data":{"TTS_BACKEND":"'"$MODEL"'"}}' \
  2>/dev/null || true

# 6️⃣ Apply all manifests
print_step "Applying Kubernetes manifests..."
oc -n $NAMESPACE apply -k deploy/openshift/

# 7️⃣ Apply LiteLLM
print_step "Deploying LiteLLM proxy..."
oc -n $NAMESPACE apply -f deploy/openshift/litellm.yaml

# 8️⃣ Apply monitoring
print_step "Deploying monitoring rules..."
oc -n $NAMESPACE apply -f deploy/openshift/monitoring.yaml

# 9️⃣ Wait for deployments
print_step "Waiting for deployments to be ready..."
oc -n $NAMESPACE rollout status deployment/tts-gateway --timeout=10m
oc -n $NAMESPACE rollout status deployment/litellm-proxy --timeout=5m

# 🔟 Smoke test
print_step "Running smoke test..."

# Get a pod name
POD=$(oc -n $NAMESPACE get pods -l app=tts-gateway -o jsonpath='{.items[0].metadata.name}')

if [ -z "$POD" ]; then
    print_error "No TTS Gateway pod found!"
    exit 1
fi

print_step "Testing endpoint on pod: $POD"

# Port-forward in background
oc -n $NAMESPACE port-forward "pod/$POD" 9999:8000 &
PF_PID=$!
sleep 2

# Test request
TEST_RESPONSE=$(curl -s -X GET http://localhost:9999/healthz)
if echo "$TEST_RESPONSE" | grep -q "ok"; then
    print_step "✓ Health check passed"
else
    print_error "Health check failed"
    echo "$TEST_RESPONSE"
fi

# Cleanup port-forward
kill $PF_PID 2>/dev/null || true

# 📊 Show status
print_step "Deployment complete! Status:"
echo ""
oc -n $NAMESPACE get deployments -o wide
echo ""
oc -n $NAMESPACE get svc
echo ""

# 🔗 Show routes
print_step "Routes:"
oc -n $NAMESPACE get routes

# 📝 Show next steps
echo ""
echo -e "${GREEN}✓ Deployment successful!${NC}"
echo ""
echo "Next steps:"
echo "  1. Verify pods are running: oc -n $NAMESPACE get pods"
echo "  2. Check logs: oc -n $NAMESPACE logs -f deployment/tts-gateway"
echo "  3. Port-forward to test:"
echo "     oc -n $NAMESPACE port-forward svc/tts-gateway 8000:8000"
echo "  4. Test synthesize:"
echo "     curl -X POST http://localhost:8000/v1/synthesize \\"
echo "       -H 'Content-Type: application/json' \\"
echo "       -H 'X-API-Key: $ADMIN_API_KEY' \\"
echo "       -d '{\"text\":\"Hello world\",\"lang\":\"en\",\"voice_id\":\"brand_default\"}' \\"
echo "       --output test.wav"
echo ""
echo "  5. Access LiteLLM:"
echo "     oc -n $NAMESPACE port-forward svc/litellm 8000:8000"
echo "     # Then use OpenAI-compatible client"
echo ""
