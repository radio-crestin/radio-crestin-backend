deploy:
	git pull origin master;
	docker-compose up --env-file ./.env --build --force-recreate -d

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