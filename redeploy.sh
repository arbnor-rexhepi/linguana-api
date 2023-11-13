#!/bin/bash

echo "Repo pull"
git pull
echo "Building docker"
sudo docker build -t linguana-api .
echo "Running docker"
sudo docker stop linguana-api
sudo docker rm linguana-api
sudo docker run -d -p 8000:8000 --name linguana-api linguana-api
