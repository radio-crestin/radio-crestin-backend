deploy: generate-deployment
	docker-compose up -d --remove-orphans

force-deploy: generate-deployment
	docker-compose up -d --force-recreate --remove-orphans

clear-hls-data:
	mkdir -p /tmp/data/hls
	rm -r /tmp/data/hls/*

generate-deployment: git-pull
	python3 generate_deployment.py

git-pull:
	git pull origin master
