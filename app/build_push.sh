#!/bin/bash
echo -n "Build: " > version.txt
echo -n `git describe --tags --always HEAD` >> version.txt
echo -n " " >> version.txt
date >> version.txt
docker build -t quay.io/camillo/vkaci-init:1.0rc0 --target=vkaci-init  . &&  docker build -t quay.io/camillo/vkaci:1.0rc0 --target=vkaci .  &&  docker push quay.io/camillo/vkaci:1.0rc0 &&  docker push quay.io/camillo/vkaci-init:1.0rc0
