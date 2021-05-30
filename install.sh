#!/bin/bash

# Before running this script, execute manually:
# apt update
# apt install -y git
# ssh-keygen -t rsa
# Configure the created ssh public key as deploy key on Github
# git clone git@github.com:iosifnicolae2/radio-crestin.ro.git
# Installing Docker
apt update
apt install -y apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu focal stable"
apt update
apt install -y docker-ce docker-compose
systemctl status docker
