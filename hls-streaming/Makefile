deploy: generate-deployment
	docker-compose up -d --remove-orphans

force-deploy: generate-deployment
	mkdir -p /tmp/data/hls
	rm -r /tmp/data/hls/*
	docker-compose up -d --force-recreate --remove-orphans

generate-deployment: git-pull
	python3 generate_deployment.py

git-pull:
	git pull origin master
