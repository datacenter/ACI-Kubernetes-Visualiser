# Set your manifest name
export MANIFEST_NAME="vkaci"

# Set the required variables
export REGISTRY="quay.io"
export USER="camillo"
export IMAGE_NAME="vkaci"
export IMAGE_TAG="multi_arch_3.10"

# Create a multi-architecture manifest
buildah manifest create ${MANIFEST_NAME}

# Build your amd64 architecture container
buildah bud \
    --tag "${REGISTRY}/${USER}/${IMAGE_NAME}:${IMAGE_TAG}" \
    --arch=amd64 \
    --layers=true
    
buildah manifest add ${MANIFEST_NAME} "${REGISTRY}/${USER}/${IMAGE_NAME}:${IMAGE_TAG}"

# Build your arm64 architecture container
buildah bud \
    --tag "${REGISTRY}/${USER}/${IMAGE_NAME}:${IMAGE_TAG}" \
    --arch arm64 \
    --layers=true

buildah manifest add ${MANIFEST_NAME} "${REGISTRY}/${USER}/${IMAGE_NAME}:${IMAGE_TAG}"

# Push the full manifest, with both CPU Architectures
buildah manifest push --all \
    ${MANIFEST_NAME} \
    "docker://${REGISTRY}/${USER}/${IMAGE_NAME}:${IMAGE_TAG}"


export MANIFEST_NAME="vkaci-init"
export IMAGE_NAME="vkaci-init"
buildah manifest create ${MANIFEST_NAME}

# Build your amd64 architecture container
buildah bud \
    --tag "${REGISTRY}/${USER}/${IMAGE_NAME}:${IMAGE_TAG}" \
    --arch=amd64 \
    --layers=true \
    -f Dockerfile-init
    
buildah manifest add ${MANIFEST_NAME} "${REGISTRY}/${USER}/${IMAGE_NAME}:${IMAGE_TAG}"

# Build your arm64 architecture container
buildah bud \
    --tag "${REGISTRY}/${USER}/${IMAGE_NAME}:${IMAGE_TAG}" \
    --arch arm64 \
    --layers=true \
    -f Dockerfile-init

buildah manifest add ${MANIFEST_NAME} "${REGISTRY}/${USER}/${IMAGE_NAME}:${IMAGE_TAG}"

# Push the full manifest, with both CPU Architectures
buildah manifest push --all \
    ${MANIFEST_NAME} \
    "docker://${REGISTRY}/${USER}/${IMAGE_NAME}:${IMAGE_TAG}"