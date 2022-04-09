### radio-crestin.com - a directory of christian radio stations

Feel free to contribute to this project or get in touch with us at: contact@radio-crestin.com

Obs. This project can be used only by christian organizations for non-comercial purposes.

#### Development
```bash
cd backend
cp ../env.example .env
make start-dev
sleep 10s
make fresh-install
```

#### Production

```bash
apt update
apt install -y git
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

# Deploy
cp ./nginx/nginx.conf.example ./nginx/nginx.conf
cp .env.example .env
# Update all the sensitive information from .env
docker-compose up --build --force-recreate -d

# Create a superuser
docker-compose exec admin python manage.py createsuperuser

```