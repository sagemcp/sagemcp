#!/bin/bash

# Build script for SageMCP Docker images
# Ensures correct architecture for Kubernetes deployment

set -e

AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-975050061848}"
AWS_REGION="${AWS_REGION:-us-east-1}"
BACKEND_REPO="sage/sagemcp-backend"
FRONTEND_REPO="sage/sagemcp-frontend"
PLATFORM="${PLATFORM:-linux/amd64}"
TAG="${TAG:-latest}"

BACKEND_IMAGE="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$BACKEND_REPO:$TAG"
FRONTEND_IMAGE="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$FRONTEND_REPO:$TAG"

echo "Building SageMCP images for platform: $PLATFORM"
echo ""

# Login to ECR
echo "Logging in to AWS ECR..."
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

# Build backend
echo ""
echo "Building backend image..."
docker buildx build \
  --platform "$PLATFORM" \
  --tag "$BACKEND_IMAGE" \
  --file ./Dockerfile \
  .

# Build frontend
echo ""
echo "Building frontend image..."
docker buildx build \
  --platform "$PLATFORM" \
  --tag "$FRONTEND_IMAGE" \
  --file ./frontend/Dockerfile \
  ./frontend

echo ""
echo "Build complete!"
echo "Backend: $BACKEND_IMAGE"
echo "Frontend: $FRONTEND_IMAGE"
echo ""
echo "Pushing images to ECR..."
docker push "$BACKEND_IMAGE"
docker push "$FRONTEND_IMAGE"
echo ""
echo "Done!"
