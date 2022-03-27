start-dev:
	docker-compose -f docker-compose.dev.yaml up  --build --force-recreate

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

reload-hasura-metadata:
	hasura metadata reload --endpo
	
create-default-admin-superuser:
	docker exec -ti "$$(docker ps | grep backend_admin | cut -d " " -f1)" bash -c "echo \"from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('dev', 'dev@radio-crestin.com', 'dev-password')\"|python manage.py shell"

