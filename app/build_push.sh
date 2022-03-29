#!/bin/bash
echo -n "Build: " > version.txt
echo -n `git describe --tags --always HEAD` >> version.txt
echo -n " " >> version.txt
date >> version.txt
docker build -t quay.io/camillo/vkaci-init:0.2 --target=vkaci-init  . &&  docker build -t quay.io/camillo/vkaci:0.2 --target=vkaci .  &&  docker push quay.io/camillo/vkaci:0.2 &&  docker push quay.io/camillo/vkaci-init:0.2
