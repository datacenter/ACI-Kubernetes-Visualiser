# Warning: This was not working on Buldah 1.22, it works perfectly fine on 1.28
# Set your manifest name
export MANIFEST_NAME="vkaci"
export MANIFEST_NAME_INIT="vkaci-init"
# Set the required variables
export REGISTRY="quay.io"
export USER="datacenter"
export IMAGE_NAME="vkaci"
export IMAGE_NAME_INIT="vkaci-init"
if [ -z "$1" ]
    then
        export IMAGE_TAG="v1.1.0"
    else
        export IMAGE_TAG="$1"
fi

# Clean up and Create a multi-architecture manifest
for i in `buildah manifest inspect ${MANIFEST_NAME} | jq -r ".manifests[].digest"`
    do
    buildah manifest remove ${MANIFEST_NAME}  $i
    done
buildah manifest rm ${MANIFEST_NAME} 
buildah manifest create ${MANIFEST_NAME}

for i in `buildah manifest inspect ${MANIFEST_NAME_INIT} | jq -r ".manifests[].digest"`
    do
    buildah manifest remove ${MANIFEST_NAME_INIT}  $i
    done
buildah manifest rm ${MANIFEST_NAME_INIT} 
buildah manifest create ${MANIFEST_NAME_INIT}

### INIT CONTAINER
# Build your amd64 architecture container
buildah bud \
    --tag "${REGISTRY}/${USER}/${IMAGE_NAME_INIT}:${IMAGE_TAG}" \
    --arch=amd64 \
    --layers \
    --manifest ${MANIFEST_NAME_INIT} \
    -f Dockerfile-init &
    

# Build your arm64 architecture container
buildah bud \
    --tag "${REGISTRY}/${USER}/${IMAGE_NAME_INIT}:${IMAGE_TAG}" \
    --arch arm64 \
    --manifest ${MANIFEST_NAME_INIT} \
    --layers \
    -f Dockerfile-init & 


### MAIN CONTAINER
# Build your amd64 architecture container
buildah bud \
    --tag "${REGISTRY}/${USER}/${IMAGE_NAME}:${IMAGE_TAG}" \
    --manifest ${MANIFEST_NAME} \
    --arch=amd64 \
    --layers &
    
# Build your arm64 architecture container
buildah bud \
    --tag "${REGISTRY}/${USER}/${IMAGE_NAME}:${IMAGE_TAG}" \
    --manifest ${MANIFEST_NAME} \
    --arch arm64 \
    --layers &

wait # Wait for all the builds to finish

# Push the full manifest, with both CPU Architectures
buildah manifest push --all \
    ${MANIFEST_NAME} \
    "docker://${REGISTRY}/${USER}/${IMAGE_NAME}:${IMAGE_TAG}"


#buildah manifest add ${MANIFEST_NAME} "${REGISTRY}/${USER}/${IMAGE_NAME}:${IMAGE_TAG}"

# Push the full manifest, with both CPU Architectures
buildah manifest push --all \
    ${MANIFEST_NAME_INIT} \
    "docker://${REGISTRY}/${USER}/${IMAGE_NAME_INIT}:${IMAGE_TAG}"