#!/bin/bash
echo -n "Build: " > version.txt
echo -n `git describe --tags --always HEAD` >> version.txt
echo -n " " >> version.txt
date >> version.txt
docker build -t quay.io/camillo/vkaci-init --target=vkaci-init  . &&  docker build -t quay.io/camillo/vkaci --target=vkaci .  &&  docker push quay.io/camillo/vkaci:latest &&  docker push quay.io/camillo/vkaci-init:latest
