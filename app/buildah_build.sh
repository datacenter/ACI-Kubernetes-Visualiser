# Set your manifest name
export MANIFEST_NAME="vkaci"

# Set the required variables
export REGISTRY="quay.io"
export USER="datacenter"
export IMAGE_NAME="vkaci"
if [ -z "$1" ]
    then
        export IMAGE_TAG="test-15-AUG"
    else
        export IMAGE_TAG="$1"
fi

# Create a multi-architecture manifest
for i in `buildah manifest inspect ${MANIFEST_NAME} | jq -r ".manifests[].digest"`
    do
    buildah manifest remove ${MANIFEST_NAME}  $i
    done
buildah manifest rm ${MANIFEST_NAME} 
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

for i in `buildah manifest inspect ${MANIFEST_NAME} | jq -r ".manifests[].digest"`
    do
    buildah manifest remove ${MANIFEST_NAME}  $i
    done
buildah manifest rm ${MANIFEST_NAME} 
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