deploy: git-pull
	docker-compose --env-file .env  build --no-cache
	docker-compose --env-file .env  up -d

force-deploy: git-pull
	docker-compose --env-file .env  build --no-cache
	docker-compose --env-file .env  up -d --force-recreate


deploy-staging: git-pull
	docker-compose -f docker-compose.staging.yaml --env-file .env  build --no-cache
	docker-compose -f docker-compose.staging.yaml --env-file .env  up -d

force-deploy-staging: git-pull
	docker-compose -f docker-compose.staging.yaml --env-file .env  build --no-cache
	docker-compose -f docker-compose.staging.yaml --env-file .env  up -d --force-recreate

start-dev:
	docker-compose --env-file .env  up --build --force-recreate -d

stop:
	docker-compose --env-file .env  stop

git-pull:
	git pull origin master;

logs:
	docker-compose logs -f

create-superuser:
	docker-compose exec admin python manage.py createsuperuser

load-admin-fixtures:
	cd backend && make load-admin-fixtures
