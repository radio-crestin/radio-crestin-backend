start-dev:
	docker-compose -f docker-compose.dev.yaml up  --build --force-recreate

fresh-install:
	make apply-hasura-metadata;
	make apply-hasura-migrations;
	make apply-hasura-metadata;
	make load-admin-fixtures;
	make create-default-admin-superuser;

delete-all:
	@echo "Perform cleanup"; \
	docker-compose -f docker-compose.dev.yaml kill -s SIGINT;
	docker-compose -f docker-compose.dev.yaml down --volumes --remove-orphans;

open-admin:
    # Make sure to run `create-default-admin-superuser`
	# Default credentials: dev:dev-password
	python3 -m webbrowser http://localhost:8545/admin

start-hasura-console:
	hasura console --envfile .env

apply-hasura-migrations:
	hasura migrate apply --all-databases  --envfile .env

apply-hasura-metadata:
	hasura metadata apply  --envfile .env; \
	hasura metadata reload  --envfile .env; \
	hasura metadata ic list  --envfile .env;

list-hasura-metadata-list-inconsistency: apply-hasura-metadata
	hasura metadata inconsistency list  --envfile .env

squash-hasura-migrations:
	hasura migrate squash --delete-source --from 1648886276821 --envfile .env


reload-hasura-metadata:
	hasura metadata reload --endpo
	
create-default-admin-superuser:
	docker exec -ti "$$(docker ps | grep backend_admin | cut -d " " -f1)" bash -c "echo \"from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('dev', 'dev@radio-crestin.com', 'dev-password')\"|python manage.py shell"

create-admin-fixtures:
	docker exec -ti "$$(docker ps | grep backend_admin | cut -d " " -f1)"  bash -c "echo -e \"from web.models import *;\n\
Songs.objects.all().delete() \n\
Songs.objects.all().delete() \n\
Artists.objects.all().delete() \n\
StationsNowPlaying.objects.all().delete() \n\
StationsUptime.objects.all().delete() \n\
\"|python manage.py shell"; \

	model="web.StationMetadataFetchCategories"; \
	docker exec -ti "$$(docker ps | grep backend_admin | cut -d " " -f1)" bash -c "python manage.py dumpdata $$model --format=yaml -o /tmp/fixtures.yaml >/dev/null 2>&1  && cat /tmp/fixtures.yaml" > admin/fixtures/$$model.yaml; \

	model="web.StationGroups"; \
	docker exec -ti "$$(docker ps | grep backend_admin | cut -d " " -f1)" bash -c "python manage.py dumpdata $$model --format=yaml -o /tmp/fixtures.yaml >/dev/null 2>&1  && cat /tmp/fixtures.yaml" > admin/fixtures/$$model.yaml; \

	model="web.Stations"; \
	docker exec -ti "$$(docker ps | grep backend_admin | cut -d " " -f1)" bash -c "export ADMIN_DEBUG=false && python manage.py dumpdata_one $$model --fields=created_at,updated_at,order,title,website,email,stream_url,thumbnail,thumbnail_url" | python3 -c 'import sys, yaml, json; print(yaml.dump(json.loads(sys.stdin.read())))' > admin/fixtures/$$model.yaml; \

	model="web.StationToStationGroup"; \
	docker exec -ti "$$(docker ps | grep backend_admin | cut -d " " -f1)" bash -c "python manage.py dumpdata $$model --format=yaml -o /tmp/fixtures.yaml >/dev/null 2>&1  && cat /tmp/fixtures.yaml" > admin/fixtures/$$model.yaml; \

	model="web.StationsMetadataFetch"; \
	docker exec -ti "$$(docker ps | grep backend_admin | cut -d " " -f1)" bash -c "python manage.py dumpdata $$model --format=yaml -o /tmp/fixtures.yaml >/dev/null 2>&1  && cat /tmp/fixtures.yaml" > admin/fixtures/$$model.yaml; \


load-admin-fixtures:
	model="web.StationMetadataFetchCategories"; \
	docker exec -ti "$$(docker ps | grep backend_admin | cut -d " " -f1)" bash -c "python manage.py loaddata --format=yaml /src/fixtures/$$model.yaml"
	model="web.StationGroups"; \
	docker exec -ti "$$(docker ps | grep backend_admin | cut -d " " -f1)" bash -c "python manage.py loaddata --format=yaml /src/fixtures/$$model.yaml"
	model="web.Stations"; \
	docker exec -ti "$$(docker ps | grep backend_admin | cut -d " " -f1)" bash -c "python manage.py loaddata --format=yaml /src/fixtures/$$model.yaml"
	model="web.StationToStationGroup"; \
	docker exec -ti "$$(docker ps | grep backend_admin | cut -d " " -f1)" bash -c "python manage.py loaddata --format=yaml /src/fixtures/$$model.yaml"
	model="web.StationsMetadataFetch"; \
	docker exec -ti "$$(docker ps | grep backend_admin | cut -d " " -f1)" bash -c "python manage.py loaddata --format=yaml /src/fixtures/$$model.yaml"




