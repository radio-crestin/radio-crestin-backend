### radio-crestin.com website

Feel free to contribute to this project or reach to us using iosif@mailo.dev

Obs. This project can be used only with christian stations!

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


cd backend/
cp .env.example .env
docker-compose up --build --force-recreate -d
```