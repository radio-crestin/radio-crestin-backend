<p align="center">
  <a href="https://github.com/iosifnicolae2/radio-crestin.com">
    <img src="https://user-images.githubusercontent.com/43387542/211213394-e0497c8c-7b8a-43ba-b144-f512653b682d.svg" alt="Radio Crestin logo" width="200" />
  </a>
</p>
<h1 align="center">Christian Radio Stations Directory ⚡️</h1>
<br>
<p align="center">
  <img alt="Bundle Size" src="https://img.shields.io/github/contributors/iosifnicolae2/radio-crestin.com"/>
  <img alt="Github Stars" src="https://badgen.net/github/stars/iosifnicolae2/radio-crestin.com" />
  <a href="https://radio-crestin.com/"><img alt="Website Status" src="https://img.shields.io/website?url=https%3A%2F%2Fradio-crestin.com%2F" /></a>
  <a href="https://github.com/iosifnicolae2/radio-crestin.com/blob/master/LICENSE">
    <img alt="Website Status" src="https://img.shields.io/badge/-License-blue" />
  </a>
</p>


Feel free to contribute to this project or get in touch with us at: contact@radio-crestin.com

Obs. This project can be used only by christian organizations for non-comercial purposes.

![Group 16 (2)](https://user-images.githubusercontent.com/43387542/221437934-2721d0b4-9402-42ed-b289-7f9a4d61796c.png)

#### Development
```bash
cd backend
cp ../.env.example .env
make start-dev
sleep 10s
make fresh-install
```

#### Production

```bash
apt update
apt install -y git make
ssh-keygen -t rsa
git clone git@github.com:iosifnicolae2/radio-crestin.com.git
cd radio-crestin.com/
  
# Installing Docker
apt update
curl https://releases.rancher.com/install-docker/20.10.sh | sh
apt install -y docker-compose

# Configuration (make sure to update all the secrets)
cp ./nginx/nginx.conf.example ./nginx/nginx.conf
cp .env.example .env

make deploy;

# Load Admin Fixtures
make load-admin-fixtures;

# Create a superuser
make create-superuser-production;
```
- setup CI/CD:
```bash
ssh-keygen -b 2048 -t rsa 
# Add the public key to ~/.ssh/authorized_keys
# Add the following secrets on Github Repo > Settings > Secrets > Actions:
# HOST
# PORT
# USERNAME
# KEY
```

#### HLS deployment
- do all the steps from the `Production` section
```bash
cd hls-streaming
make deploy;
```
