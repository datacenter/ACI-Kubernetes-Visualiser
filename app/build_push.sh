#!/bin/bash
TAG="scale_testing"
echo -n "Build: " > version.txt
echo -n `git describe --tags --always HEAD` >> version.txt
echo -n " " >> version.txt
date >> version.txt
docker build -t quay.io/camillo/vkaci-init:$TAG --target=vkaci-init  . &&  docker build -t quay.io/camillo/vkaci:$TAG --target=vkaci .  &&  docker push quay.io/camillo/vkaci:$TAG &&  docker push quay.io/camillo/vkaci-init:$TAG
