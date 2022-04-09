### radio-crestin.com - a directory of christian radio stations

Feel free to contribute to this project or get in touch with us at: contact@radio-crestin.com

Obs. This project can be used only by christian organizations for non-comercial purposes.

#### Development
```bash
cd backend
cp ../.env.example .env
make start-dev
sleep 10s
make fresh-install

cd frontend
# Make sure to use local(dev) FRONTEND variables
cp ../.env.example .env.local
make install
make start-dev
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
apt install -y apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu focal stable"
apt update
apt install -y docker-ce docker-compose

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
