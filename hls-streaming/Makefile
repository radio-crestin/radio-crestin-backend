deploy: generate-deployment
	docker-compose up -d

force-deploy: generate-deployment
	docker-compose up -d --force-recreate

generate-deployment: git-pull
	python3 generate_deployment.py

git-pull:
	git pull origin master
