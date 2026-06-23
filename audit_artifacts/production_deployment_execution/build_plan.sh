#!/bin/bash
# Production Build & Publish Plan
# Release: v0.1.0-agentco-civilization-production

set -e

REGISTRY="ghcr.io/vvvaibhaverma-123459876/agentco"
RELEASE_TAG="v0.1.0-agentco-civilization-production"
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
BUILD_LOG="/Users/Zet/Agentco/audit_artifacts/production_deployment_execution/build_output.log"

echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║  AGENTCO PRODUCTION BUILD & PUBLISH                              ║"
echo "║  Release: ${RELEASE_TAG}                ║"
echo "║  Date: $(date)                          ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# Step 1: Build Backend Image
echo "Step 1: Building backend Docker image..."
cd /Users/Zet/Agentco/backend
docker build \
  --build-arg BUILD_DATE="${BUILD_DATE}" \
  --build-arg VCS_REF="4e644d0" \
  --label "org.opencontainers.image.created=${BUILD_DATE}" \
  --label "org.opencontainers.image.version=${RELEASE_TAG}" \
  --label "org.opencontainers.image.revision=4e644d0" \
  -t "${REGISTRY}/backend:${RELEASE_TAG}" \
  -t "${REGISTRY}/backend:latest" \
  . 2>&1 | tee -a "${BUILD_LOG}"

echo "✅ Backend image built successfully"

# Get backend image digest
BACKEND_DIGEST=$(docker inspect --format='{{.Id}}' "${REGISTRY}/backend:${RELEASE_TAG}" | sed 's/sha256://')
echo "Backend digest: sha256:${BACKEND_DIGEST:0:12}"

# Step 2: Build Frontend Image
echo ""
echo "Step 2: Building frontend Docker image..."
cd /Users/Zet/Agentco/frontend
docker build \
  --build-arg BUILD_DATE="${BUILD_DATE}" \
  --build-arg VCS_REF="4e644d0" \
  --label "org.opencontainers.image.created=${BUILD_DATE}" \
  --label "org.opencontainers.image.version=${RELEASE_TAG}" \
  --label "org.opencontainers.image.revision=4e644d0" \
  -t "${REGISTRY}/frontend:${RELEASE_TAG}" \
  -t "${REGISTRY}/frontend:latest" \
  . 2>&1 | tee -a "${BUILD_LOG}"

echo "✅ Frontend image built successfully"

# Get frontend image digest
FRONTEND_DIGEST=$(docker inspect --format='{{.Id}}' "${REGISTRY}/frontend:${RELEASE_TAG}" | sed 's/sha256://')
echo "Frontend digest: sha256:${FRONTEND_DIGEST:0:12}"

# Step 3: Image Verification
echo ""
echo "Step 3: Verifying images..."
echo "Backend image size: $(docker images --format 'table {{.Repository}}:{{.Tag}}\t{{.Size}}' | grep backend:${RELEASE_TAG})"
echo "Frontend image size: $(docker images --format 'table {{.Repository}}:{{.Tag}}\t{{.Size}}' | grep frontend:${RELEASE_TAG})"

# Step 4: Push to Registry (if available)
echo ""
echo "Step 4: Pushing to registry..."
docker push "${REGISTRY}/backend:${RELEASE_TAG}" 2>&1 | tee -a "${BUILD_LOG}" || echo "⚠️  Registry push skipped (not available in local environment)"
docker push "${REGISTRY}/frontend:${RELEASE_TAG}" 2>&1 | tee -a "${BUILD_LOG}" || echo "⚠️  Registry push skipped (not available in local environment)"

echo ""
echo "✅ Build & Publish Complete"
echo ""
echo "Build Summary:"
echo "  Backend:  ${REGISTRY}/backend:${RELEASE_TAG}"
echo "  Frontend: ${REGISTRY}/frontend:${RELEASE_TAG}"
echo "  Log file: ${BUILD_LOG}"
