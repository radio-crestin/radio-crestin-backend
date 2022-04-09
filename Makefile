deploy: git-pull
	docker-compose --env-file .env  up --build -d

force-deploy: git-pull
	docker-compose --env-file .env  up --build --force-recreate -d


git-pull:
	git pull origin master;

logs:
	docker-compose logs -f

create-superuser:
	docker-compose exec admin python manage.py createsuperuser

load-admin-fixtures:
	model="web.StationMetadataFetchCategories"; \
	docker-compose exec admin  bash -c "python manage.py loaddata --format=yaml /src/fixtures/$$model.yaml"
	model="web.StationGroups"; \
	docker-compose exec admin  bash -c "python manage.py loaddata --format=yaml /src/fixtures/$$model.yaml"
	model="web.Stations"; \
	docker-compose exec admin  bash -c "python manage.py loaddata --format=yaml /src/fixtures/$$model.yaml"
	model="web.StationToStationGroup"; \
	docker-compose exec admin  bash -c "python manage.py loaddata --format=yaml /src/fixtures/$$model.yaml"
	model="web.StationsMetadataFetch"; \
	docker-compose exec admin  bash -c "python manage.py loaddata --format=yaml /src/fixtures/$$model.yaml"